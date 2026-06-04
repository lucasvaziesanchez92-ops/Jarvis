"""Chat endpoints — agent graph with tools, keepalive for Railway."""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.callbacks import BaseCallbackHandler
from loguru import logger

from backend.api.dependencies import get_jarvis_graph
from backend.models.chat import ChatRequest, ChatResponse, StreamChunk
from backend.core.file_extractor import build_file_context

router = APIRouter()


class WebSocketCallback(BaseCallbackHandler):
    def __init__(self, loop, send_fn):
        self._loop = loop
        self._send = send_fn
        self._pending_tools = []

    def _emit(self, **kw):
        chunk = StreamChunk(**kw)
        asyncio.run_coroutine_threadsafe(self._send(chunk), self._loop)

    def on_llm_new_token(self, token, **kw):
        self._emit(type="stream", content=token)

    def on_tool_start(self, serialized, input_str, **kw):
        name = serialized.get("name", "unknown")
        self._pending_tools.append(name)
        self._emit(type="tool_start", content=f"Usando {name}...", tool_name=name)

    def on_tool_end(self, output, **kw):
        try:
            text = str(output) if not isinstance(output, str) else output
        except Exception:
            text = ""
        self._emit(type="tool_end", content=text[:200], tool_output=text[:500])


async def _keepalive(send_fn):
    while True:
        await asyncio.sleep(3)
        try:
            await send_fn(StreamChunk(type="token"))
        except Exception:
            break


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return ChatResponse(content="JARVIS listo.", session_id=request.session_id)


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    logger.info(f"WS conectado desde {websocket.client}")
    loop = asyncio.get_running_loop()

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
            session_id = data.get("session_id", "default")
            persona = data.get("persona", "profesional")

            if not message:
                continue

            input_state = {
                "messages": [HumanMessage(content=message)],
                "session_id": session_id,
                "persona": persona,
            }

            callback = WebSocketCallback(loop, send)
            config = {
                "configurable": {"thread_id": session_id},
                "callbacks": [callback],
            }

            try:
                await send(StreamChunk(type="token", content="Pensando..."))

                graph = get_jarvis_graph()
                ping = asyncio.create_task(_keepalive(send))

                try:
                    state = await asyncio.wait_for(
                        graph.ainvoke(input_state, config=config), timeout=90
                    )
                finally:
                    ping.cancel()

                ai_msgs = [m for m in state.get("messages", []) if isinstance(m, AIMessage)]
                final = ai_msgs[-1] if ai_msgs else None

                if final and final.content:
                    await send(StreamChunk(type="done"))
                else:
                    await send(StreamChunk(type="token", content="Listo."))
                    await send(StreamChunk(type="done"))

            except asyncio.TimeoutError:
                await send(StreamChunk(type="error", content="Timeout."))
            except Exception as e:
                logger.error(f"WS error: {e}")
                try:
                    await send(StreamChunk(type="error", content=str(e)[:500]))
                except Exception:
                    pass

    except WebSocketDisconnect:
        logger.info("WS desconectado")
    except Exception as e:
        logger.error(f"WS fatal: {e}")
