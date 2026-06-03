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

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
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
        language=None,
    )
    return response.text

# ── Module B: Agent Graph (TOOLS ENABLED) ─────────────────────────

async def _chat_with_agent(transcript: str, session_id: str = "") -> tuple[str, bool]:
    """Usa el agente completo con herramientas. Retorna (respuesta, tools_used)."""
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
                    "persona": "profesional",
                },
                config=config,
            ),
            timeout=60,
        )
    except asyncio.TimeoutError:
        return "Me tardé demasiado procesando eso. ¿Podés repetirlo más breve?", False
    except Exception as e:
        logger.warning(f"Agent falló, usando fallback directo: {e}")
        return await _chat_direct_fallback(transcript), False

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

# ── Endpoint: POST /api/voice ───────────────────────────────────────────

@router.post("", response_model=VoicePipelineResponse)
async def voice_pipeline(
    audio: UploadFile = File(...),
    session_id: str = Form(default=""),
):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    transcript = ""
    response_text = ""
    audio_b64 = ""

    try:
        content = await audio.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el audio: {e}")

    # STT
    try:
        transcript = await _transcribe(content)
        logger.info(f"Voice STT: {transcript[:80]}")
    except Exception as e:
        logger.error("STT failed: {}", str(e)[:200])
        return VoicePipelineResponse(transcript="", response_text="No pude entender el audio. ¿Podés repetir?", audio_base64="")

    # LLM — Agent Graph con herramientas
    if transcript.strip():
        try:
            response_text, _tools_used = await _chat_with_agent(transcript, session_id)
            logger.info(f"Voice LLM (agent): {response_text[:80]}")
        except Exception as e:
            logger.error(f"Agent failed: {e}")
            response_text = "Entendí lo que dijiste pero tuve un problema para procesarlo."

    # TTS (optional — voice works without it)
    if response_text:
        try:
            audio_b64 = await _synthesize_base64(response_text)
        except Exception as e:
            logger.warning(f"TTS skipped: {e}")

    return VoicePipelineResponse(
        transcript=transcript,
        response_text=response_text or "Procesado.",
        audio_base64=audio_b64,
        session_id=session_id,
    )

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
