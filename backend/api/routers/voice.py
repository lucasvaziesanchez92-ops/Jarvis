"""Voice Pipeline — Groq STT + Direct LLM + Piper TTS.

POST /api/voice (multipart/form-data)
    1. Audio blob from browser (webm/opus) → Groq STT
    2. Direct LLM call (no agent graph, no tools — fast)
    3. Piper ONNX → WAV bytes (runs in thread pool)
    4. base64 encode → JSON response

POST /api/voice/tts
    { text } — Piper ONNX → { audio_base64 }
"""
import io
import base64
import asyncio
from functools import lru_cache

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from loguru import logger

from backend.config import settings
from backend.models.chat import TTSRequest, TTSResponse, VoicePipelineResponse

router = APIRouter()

# ── Voice system prompt (lightweight, no tools) ──────────────────────────
# NOTA: Ahora la voz usa el agent graph completo con herramientas.
# Este prompt se mantiene como fallback para respuestas rápidas sin tools.

_VOICE_FALLBACK_PROMPT = (
    "Eres JARVIS, un asistente de voz. Responde de forma CONCISA y NATURAL, "
    "como si estuvieras hablando. Máximo 2-3 oraciones cortas. Nada de markdown, "
    "listas, ni código. Solo texto plano para ser leído en voz alta. "
    "Sé amable y directo. Responde en español natural."
)

# ── Module A: Groq STT ──────────────────────────────────────────────────

async def _transcribe(audio_bytes: bytes) -> str:
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY no configurada.")
    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)
    response = client.audio.transcriptions.create(
        model=settings.groq_stt_model,
        file=("audio.webm", io.BytesIO(audio_bytes), "audio/webm"),
        language="es",
    )
    
    text = response.text.strip()
    # Filter common Whisper hallucinations on silent/noisy audio
    lower_text = text.lower().replace(".", "").replace(",", "").replace("!", "").strip()
    hallucinations = [
        "thank you", "thanks", "gracias", "muchas gracias", "thank you very much",
        "thanks for watching", "subtitles", "amaraorg", "suscribete", "suscribete al canal"
    ]
    if lower_text in hallucinations or len(lower_text) < 2:
        return ""
        
    return text

# ── Module B: Agent Graph (TOOLS ENABLED) ─────────────────────────

async def _chat_with_agent(transcript: str, session_id: str = "", persona: str = "profesional") -> tuple[str, bool]:
    """Usa el agente completo con herramientas. Retorna (respuesta, tools_used).
    Timeout ampliado a 90s para permitir tareas complejas como buscar en Drive/Gmail."""
    from langchain_core.messages import HumanMessage
    from backend.api.dependencies import get_jarvis_graph
    graph = get_jarvis_graph()
    config = {"configurable": {"thread_id": session_id or "voice-session"}}
    try:
        state = await asyncio.wait_for(
            graph.ainvoke(
                {
                    "messages": [HumanMessage(content=transcript)],
                    "session_id": session_id or "voice-session",
                    "persona": persona,
                },
                config=config,
            ),
            timeout=90,  # Aumentado para tareas complejas
        )
    except asyncio.TimeoutError:
        return "Me tardé demasiado procesando tu solicitud de red. Por favor, revisa el chat de texto para más detalles o intenta de nuevo.", False
    except Exception as e:
        error_msg = str(e)[:200]
        logger.warning("Agent graph falló en voice, usando fallback directo: {}", error_msg)
        try:
            return await asyncio.wait_for(
                _chat_direct_fallback(transcript), timeout=15
            ), False
        except Exception:
            return "Error procesando. Reintentá.", False

    ai_msgs = [m for m in state.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
    if not ai_msgs:
        return "Procesé tu solicitud pero no tengo una respuesta textual.", False
    final = ai_msgs[-1]
    content = final.content if hasattr(final, "content") else str(final)

    # Detectar si se usaron herramientas (tool_calls en el último AIMessage)
    tools_used = hasattr(final, "tool_calls") and bool(final.tool_calls)

    return content, tools_used


async def _chat_direct_fallback(transcript: str) -> str:
    """Fallback rápido sin herramientas — para cuando el agent graph no está disponible."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from backend.llm import get_llm
    llm = get_llm()
    messages = [
        SystemMessage(content=_VOICE_FALLBACK_PROMPT),
        HumanMessage(content=transcript),
    ]
    try:
        response = await asyncio.wait_for(llm.ainvoke(messages), timeout=20)
    except asyncio.TimeoutError:
        return "Lo siento, tardé demasiado. ¿Podés repetir la pregunta?"
    except Exception:
        response = await asyncio.to_thread(llm.invoke, messages)
    return response.content

# ── Module C: TTS in thread pool ────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_tts():
    from backend.services.tts_service import TextToSpeechService
    svc = TextToSpeechService()
    try:
        svc._init_voice()
    except Exception as e:
        logger.warning(f"Piper TTS no inicializo: {e}")
    return svc


def _synthesize_blocking(text: str) -> str:
    """Blocking synthesis — designed to run in executor."""
    tts = _get_tts()
    wav = tts.synthesize(text)
    return base64.b64encode(wav).decode("ascii")


async def _synthesize_base64(text: str) -> str:
    """Run TTS in thread pool. Returns empty string on failure."""
    try:
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _synthesize_blocking, text),
            timeout=60,
        )
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"TTS synthesis falló (voice seguirá sin audio): {e}")
        return ""

# ── Async Jobs Structure ──────────────────────────────────────────────

from typing import Dict, Any
from uuid import uuid4

# Global in-memory dict to track async voice tasks
# For production/scale, use Redis + Celery. For local/Railway single-instance, dict is fine.
voice_jobs: Dict[str, Dict[str, Any]] = {}

async def _process_voice_job(job_id: str, audio_bytes: bytes, session_id: str, persona: str):
    try:
        # 1. STT
        voice_jobs[job_id]["status"] = "transcribing"
        voice_jobs[job_id]["thought"] = "Escuchando..."
        try:
            transcript = await _transcribe(audio_bytes)
            voice_jobs[job_id]["transcript"] = transcript
            logger.info(f"[{job_id}] Voice STT: {transcript[:80]}")
        except Exception as e:
            logger.error(f"[{job_id}] STT failed: {e}")
            voice_jobs[job_id]["status"] = "error"
            voice_jobs[job_id]["response_text"] = "No pude entender el audio. ¿Podés repetir?"
            return
        
        if not transcript.strip():
            voice_jobs[job_id]["status"] = "error"
            voice_jobs[job_id]["response_text"] = "No escuché nada."
            return

        # 2. LLM Graph with Tools
        voice_jobs[job_id]["status"] = "thinking"
        voice_jobs[job_id]["thought"] = "Pensando..."
        
        from langchain_core.messages import HumanMessage
        from langchain_core.callbacks import AsyncCallbackHandler
        from backend.api.dependencies import get_jarvis_graph
        from backend.api.routers.chat import _session_history, _MAX_HISTORY, _prune_history
        
        graph = get_jarvis_graph()
        config = {"configurable": {"thread_id": session_id or "voice-session"}}
        
        class VoiceCallback(AsyncCallbackHandler):
            async def on_tool_start(self, serialized, input_str, **kwargs):
                tool_name = serialized.get("name", "tool")
                voice_jobs[job_id]["thought"] = f"Usando herramienta: {tool_name}..."

        try:
            from langchain_core.messages import SystemMessage
            voice_prompt = SystemMessage(
                content="[MODO VOZ ACTIVO]: El usuario te está hablando por micrófono. "
                        "REGLA 1: Debes MENCIONAR LA INFORMACIÓN CLAVE de los resultados (ej. los asuntos "
                        "de los correos, los nombres de los eventos) de forma hablada y natural. NUNCA "
                        "digas 'aquí los tienes' asumiendo que el usuario puede leerlos. "
                        "REGLA 2: VELOCIDAD CRÍTICA. Cuando uses herramientas como listar correos o buscar "
                        "en Drive, debes pasar OBLIGATORIAMENTE el parámetro max_results=3 (o similar) para "
                        "que la búsqueda sea instantánea."
            )
            history = list(_session_history[session_id])
            input_state = {
                "messages": history + [voice_prompt, HumanMessage(content=transcript)],
                "session_id": session_id or "voice-session",
                "persona": persona,
            }
            
            state = await asyncio.wait_for(
                graph.ainvoke(
                    input_state,
                    config={"callbacks": [VoiceCallback()], **config}
                ),
                timeout=300
            )
            
            if state.get("messages"):
                _session_history[session_id] = _prune_history(list(state["messages"]), _MAX_HISTORY)
            
            ai_msgs = [m for m in state.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
            if not ai_msgs:
                raise ValueError("No AI messages generated")
            final_msg_content = ai_msgs[-1].content
                
            voice_jobs[job_id]["response_text"] = final_msg_content
            logger.info(f"[{job_id}] Voice LLM: {final_msg_content[:80]}")
            
        except asyncio.TimeoutError:
            logger.warning(f"[{job_id}] Graph timeout")
            voice_jobs[job_id]["status"] = "error"
            voice_jobs[job_id]["response_text"] = "Me tardé demasiado procesando eso. ¿Podés repetirlo más breve?"
            return
        except Exception as e:
            logger.error(f"[{job_id}] Agent failed: {e}")
            voice_jobs[job_id]["status"] = "error"
            voice_jobs[job_id]["response_text"] = "Tuve un problema al procesar la solicitud."
            return

        # 3. TTS
        voice_jobs[job_id]["status"] = "speaking"
        voice_jobs[job_id]["thought"] = "Generando voz..."
        try:
            import re
            def limpiar_texto_para_voz(texto_crudo):
                texto = texto_crudo
                # 1. Quitar pensamientos
                texto = re.sub(r'<thought>.*?</thought>', '', texto, flags=re.DOTALL)
                # 2. Dejar solo texto visible de los links
                texto = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', texto)
                # 2.5. Reemplazar URLs crudas (http/https) por la palabra "enlace"
                texto = re.sub(r'https?://[^\s]+', 'enlace', texto)
                # 3. Eliminar "Visión general..."
                texto = texto.split("Visión general creada por IA")[0]
                
                # 4. Convertir viñetas en pausas (comas)
                texto = re.sub(r'^\s*[-*•]\s+', ', ', texto, flags=re.MULTILINE)
                
                # 5. Eliminar hashtags y asteriscos
                texto = re.sub(r'[*#_]', '', texto)
                
                # 6. Convertir saltos de línea en puntos para forzar la respiración del TTS
                texto = re.sub(r'\n+', '. ', texto)
                
                # 7. Limpiar espacios y puntos redundantes
                texto = re.sub(r'\.{2,}', '.', texto)
                texto = re.sub(r'\s+', ' ', texto)
                texto = texto.replace(" .", ".")
                
                return texto.strip()
                
            texto_hablado = limpiar_texto_para_voz(final_msg_content)
            
            audio_b64 = await asyncio.wait_for(
                _synthesize_base64(texto_hablado), timeout=15
            )
            voice_jobs[job_id]["audio_base64"] = audio_b64
        except Exception as e:
            logger.warning(f"[{job_id}] TTS skipped (timeout/error): {e}")
            voice_jobs[job_id]["audio_base64"] = ""

        # Done
        voice_jobs[job_id]["status"] = "done"

    except Exception as e:
        logger.error(f"[{job_id}] Global job error: {e}")
        voice_jobs[job_id]["status"] = "error"
        voice_jobs[job_id]["response_text"] = "Error interno procesando tu solicitud."

# ── Endpoints Async Polling ───────────────────────────────────────────

from pydantic import BaseModel

class JobStartResponse(BaseModel):
    job_id: str

@router.post("/start", response_model=JobStartResponse)
async def voice_start(
    audio: UploadFile = File(...),
    session_id: str = Form(default=""),
    persona: str = Form(default="profesional"),
):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    try:
        content = await audio.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el audio: {e}")

    job_id = str(uuid4())
    voice_jobs[job_id] = {
        "status": "queued",
        "thought": "Iniciando...",
        "transcript": "",
        "response_text": "",
        "audio_base64": "",
    }

    # Start background task to bypass HTTP proxy timeouts
    asyncio.create_task(_process_voice_job(job_id, content, session_id, persona))
    
    return JobStartResponse(job_id=job_id)

@router.get("/status/{job_id}")
async def voice_status(job_id: str):
    if job_id not in voice_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return voice_jobs[job_id]

# ── Endpoint: POST /api/voice/tts ───────────────────────────────────────

@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        audio_b64 = await _synthesize_base64(request.text)
        return TTSResponse(audio_base64=audio_b64)
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ── Endpoint: WebSocket /ws/stream (Real-Time Audio Streaming) ───────

# Variable global que actúa como un búfer circular de tamaño 1 en la RAM
ultimo_frame_pantalla = None

@router.websocket("/stream")
async def websocket_voice_stream(websocket: WebSocket):
    global ultimo_frame_pantalla
    await websocket.accept()
    from backend.api.routers.chat import _session_history, _MAX_HISTORY, _prune_history
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from backend.api.dependencies import get_jarvis_graph
    import re
    import asyncio
    
    def limpiar_texto_para_voz(texto_crudo):
        texto = texto_crudo
        texto = re.sub(r'<thought>.*?</thought>', '', texto, flags=re.DOTALL)
        texto = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', texto)
        texto = texto.split("Visión general creada por IA")[0]
        texto = re.sub(r'^\s*[-*•]\s+', ', ', texto, flags=re.MULTILINE)
        texto = re.sub(r'[*#_]', '', texto)
        texto = re.sub(r'\n+', '. ', texto)
        texto = re.sub(r'\.{2,}', '.', texto)
        texto = re.sub(r'\s+', ' ', texto)
        texto = texto.replace(" .", ".")
        return texto.strip()

    stream_task = None

    async def process_audio(audio_bytes, session_id, persona):
        try:
            await websocket.send_json({"type": "state", "status": "thinking"})
            
            # 1. STT
            try:
                transcript = await _transcribe(audio_bytes)
            except Exception as e:
                logger.error(f"STT failed: {e}")
                await websocket.send_json({"type": "error", "payload": "No escuché nada."})
                return
            
            if not transcript.strip():
                await websocket.send_json({"type": "error", "payload": "No escuché nada."})
                return
            
            # 2. System Prompt
            voice_prompt = SystemMessage(
                content="[MODO VOZ ACTIVO]: El usuario te está hablando por micrófono. "
                        "REGLA 1: Debes MENCIONAR LA INFORMACIÓN CLAVE de los resultados de forma hablada y natural. "
                        "NUNCA digas 'aquí los tienes' asumiendo que el usuario puede leerlos. "
                        "REGLA 2: VELOCIDAD CRÍTICA. Usa max_results=3 en herramientas para ser rápido."
            )
            
            history = list(_session_history[session_id])
            
            # Inyección Multimodal
            if ultimo_frame_pantalla:
                logger.info("👁️ [Visión Omnisciente] Adjuntando contexto de pantalla al LLM multimodal...")
                
                user_content = [
                    {
                        "type": "text", 
                        "text": f"{transcript}\n\n[Instrucción técnica]: El usuario está compartiendo su pantalla en tiempo real. Analiza los elementos visuales, código o errores de consola visibles en la imagen adjunta para enriquecer tu respuesta."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{ultimo_frame_pantalla}"}
                    }
                ]
                human_msg = HumanMessage(content=user_content)
            else:
                human_msg = HumanMessage(content=transcript)
                
            input_state = {
                "messages": history + [voice_prompt, human_msg],
                "session_id": session_id,
                "persona": persona,
            }
            
            graph = get_jarvis_graph()
            config = {"configurable": {"thread_id": f"{session_id}-{uuid4()}"}}
            
            buffer_frase = ""
            full_response = ""
            
            # Usamos astream_events v2
            async for event in graph.astream_events(input_state, config=config, version="v2"):
                # Permitir interrupción en cada iteración
                await asyncio.sleep(0)
                kind = event["event"]
                
                if kind == "on_tool_start":
                    tool_name = event.get("name", "tool")
                    await websocket.send_json({
                        "type": "thought",
                        "payload": f"Usando herramienta: {tool_name}..."
                    })
                    
                elif kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        chunk_content = chunk.content
                        if isinstance(chunk_content, str) and chunk_content:
                            buffer_frase += chunk_content
                            full_response += chunk_content
                            
                            if any(signo in chunk_content for signo in [".", "!", "?", "\n"]):
                                texto_limpio = limpiar_texto_para_voz(buffer_frase)
                                if len(texto_limpio) > 5:
                                    audio_chunk_b64 = await _synthesize_base64(texto_limpio)
                                    if audio_chunk_b64:
                                        await websocket.send_json({
                                            "type": "audio_chunk",
                                            "payload": audio_chunk_b64,
                                            "text_segment": texto_limpio
                                        })
                                buffer_frase = ""
                                
            if buffer_frase.strip():
                texto_limpio = limpiar_texto_para_voz(buffer_frase)
                if len(texto_limpio) > 2:
                    audio_chunk_b64 = await _synthesize_base64(texto_limpio)
                    if audio_chunk_b64:
                        await websocket.send_json({
                            "type": "audio_chunk",
                            "payload": audio_chunk_b64,
                            "text_segment": texto_limpio
                        })

            _session_history[session_id].append(HumanMessage(content=transcript))
            _session_history[session_id].append(AIMessage(content=full_response))
            _session_history[session_id] = _prune_history(list(_session_history[session_id]), _MAX_HISTORY)
                        
            await websocket.send_json({
                "type": "done",
                "transcript": transcript,
                "response_text": full_response
            })

        except asyncio.CancelledError:
            logger.info("process_audio was cancelled via Barge-in (abort).")
            try:
                await websocket.send_json({"type": "aborted"})
            except Exception:
                pass
            raise
        except Exception as e:
            logger.error(f"Streaming LLM/TTS error: {e}")
            await websocket.send_json({"type": "error", "payload": "Hubo un error procesando el audio en tiempo real."})

    try:
        while True:
            data = await websocket.receive_json()
            
            # 1. Capturar el frame óptico enviado silenciosamente por React de fondo
            if data.get("type") == "screen_chunk":
                ultimo_frame_pantalla = data.get("payload")
                continue
                
            if data.get("type") == "clear_screen":
                ultimo_frame_pantalla = None
                logger.info("👁️ [Visión Omnisciente] Memoria óptica borrada.")
                continue
            
            if data.get("type") == "abort":
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                continue

            if data.get("type") == "audio_input":
                if stream_task and not stream_task.done():
                    stream_task.cancel()

                audio_base64 = data.get("payload")
                session_id = data.get("session_id", "voice-session")
                persona = data.get("persona", "profesional")
                
                audio_bytes = base64.b64decode(audio_base64)
                stream_task = asyncio.create_task(process_audio(audio_bytes, session_id, persona))

    except WebSocketDisconnect:
        logger.info("[WebSocket Voice Stream Disconnected]")
        if stream_task and not stream_task.done():
            stream_task.cancel()

