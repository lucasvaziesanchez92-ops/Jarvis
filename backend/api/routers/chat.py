"""Chat endpoints — fast WS streaming (LLM direct) + tool execution via POST."""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from backend.models.chat import ChatRequest, ChatResponse, StreamChunk

router = APIRouter()

CHAT_SYSTEM = SystemMessage(content=(
    "Sos JARVIS, un asistente de IA. Respondé en español rioplatense (voseo), "
    "natural, directo y breve. Máximo 2-3 oraciones. Sin markdown, sin tablas. "
    "Si necesitás herramientas (notas, tareas, calendario, mail), avisá que "
    "el usuario debe usar el comando específico."
))

async def _stream_llm(prompt: str, send_fn):
    """Stream tokens from direct LLM call (fast, no graph)."""
    from backend.llm import get_llm
    llm = get_llm()
    llm.streaming = True
    full = []
    try:
        async for chunk in llm.astream([CHAT_SYSTEM, HumanMessage(content=prompt)]):
            if chunk.content:
                full.append(chunk.content)
                await send_fn(StreamChunk(type="stream", content=chunk.content))
    except Exception as e:
        logger.error(f"LLM stream error: {e}")
    return "".join(full)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return ChatResponse(content="JARVIS listo.", session_id=request.session_id)


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    logger.info(f"WS conectado desde {websocket.client}")

    async def send(chunk: StreamChunk):
        try:
            await websocket.send_text(chunk.model_dump_json())
        except Exception:
            pass

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            message = data.get("message", "").strip()
            if not message:
                continue

            await send(StreamChunk(type="token", content="Pensando..."))

            try:
                response = await asyncio.wait_for(
                    _stream_llm(message, send), timeout=45
                )
                await send(StreamChunk(type="done"))
            except asyncio.TimeoutError:
                await send(StreamChunk(type="error", content="Timeout."))
            except Exception as e:
                logger.error(f"WS error: {e}")
                await send(StreamChunk(type="error", content=str(e)[:200]))

    except WebSocketDisconnect:
        logger.info("WS desconectado")
    except Exception as e:
        logger.error(f"WS fatal: {e}")
