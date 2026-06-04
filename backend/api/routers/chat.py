"""Chat endpoints: WS streaming with per-token real-time events."""
import asyncio
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.callbacks import BaseCallbackHandler
from loguru import logger

from backend.api.dependencies import get_jarvis_graph
from backend.models.chat import ChatRequest, ChatResponse, StreamChunk
from backend.core.file_extractor import build_file_context

router = APIRouter()


class WebSocketCallback(BaseCallbackHandler):
    """LangChain callback that sends events to WebSocket in real time."""

    def __init__(self, loop: asyncio.AbstractEventLoop, send_fn):
        self._loop = loop
        self._send = send_fn
        self._pending_tools: list[str] = []

    def _emit(self, **kwargs):
        chunk = StreamChunk(**kwargs)
        asyncio.run_coroutine_threadsafe(self._send(chunk), self._loop)

    def on_llm_new_token(self, token: str, **kwargs):
        self._emit(type="stream", content=token)

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        name = serialized.get("name", "unknown")
        self._pending_tools.append(name)
        args = {}
        try:
            args = json.loads(input_str) if input_str else {}
        except Exception:
            pass
        self._emit(type="tool_start", content=f"Usando {name}...", tool_name=name, tool_input=args)

    def on_tool_end(self, output: str, **kwargs):
        try:
            text = str(output) if not isinstance(output, str) else output
            content = text[:200] if output else ""
            tool_output = text[:500] if output else ""
        except Exception:
            content = ""
            tool_output = ""
        self._emit(type="tool_end", content=content, tool_output=tool_output)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Fast sync chat — max 512 tokens, 20s timeout (Railway 30s limit)."""
    import asyncio
    try:
        from backend.llm import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage
        llm = get_llm()
        llm.max_tokens = 512
        messages = [
            SystemMessage(content="Respondé en español natural, breve (1-2 oraciones). Sin markdown."),
            HumanMessage(content=request.message),
        ]
        response = await asyncio.wait_for(llm.ainvoke(messages), timeout=20)
        return ChatResponse(content=response.content, session_id=request.session_id)
    except asyncio.TimeoutError:
        return ChatResponse(content="Estoy procesando. Reintentá.", session_id=request.session_id)
    except Exception:
        return ChatResponse(content="Error temporal. Reintentá.", session_id=request.session_id)


async def _keepalive_ping(send_fn):
    while True:
        await asyncio.sleep(5)
        try:
            await send_fn(StreamChunk(type="token", content=""))
        except Exception:
            break

@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, graph=Depends(get_jarvis_graph)):
    await websocket.accept()
    logger.info(f"WS conectado desde {websocket.client}")
    loop = asyncio.get_running_loop()

    async def safe_send(chunk: StreamChunk):
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
            attachments = data.get("attachments", [])

            if not message and not attachments:
                continue

            combined_message = message
            if attachments:
                file_keys = [a["key"] for a in attachments]
                filenames = [a.get("filename", a["key"].split("/")[-1]) for a in attachments]
                await safe_send(StreamChunk(type="token", content=f"Procesando {len(attachments)} archivo(s)..."))
                try:
                    file_context = build_file_context(file_keys, filenames)
                    combined_message = f"{file_context}\n\n{message}"
                except Exception as e:
                    combined_message = f"[Archivos no procesados: {e}]\n\n{message}"

            input_state = {
                "messages": [HumanMessage(content=combined_message)],
                "session_id": session_id,
                "persona": persona,
            }

            callback = WebSocketCallback(loop, safe_send)
            config = {
                "configurable": {"thread_id": session_id},
                "callbacks": [callback],
            }

            try:
                await safe_send(StreamChunk(type="token", content="Pensando..."))

                # Keepalive ping every 5s to prevent Railway 30s timeout
                ping_task = asyncio.create_task(_keepalive_ping(safe_send))

                try:
                    state = await asyncio.wait_for(
                        graph.ainvoke(input_state, config=config),
                        timeout=60,
                    )
                finally:
                    ping_task.cancel()

                # Emit tool_end for any tools that didn't fire on_tool_end
                tool_messages = [m for m in state.get("messages", []) if isinstance(m, ToolMessage)]
                for tm in tool_messages:
                    name = getattr(tm, "name", "unknown")
                    raw = tm.content if hasattr(tm, "content") else str(tm)
                    try:
                        output = str(raw) if not isinstance(raw, str) else raw
                    except Exception:
                        output = ""
                    if name in callback._pending_tools:
                        await safe_send(StreamChunk(
                            type="tool_end",
                            content=output[:200] if output else "",
                            tool_name=name,
                            tool_output=output[:500],
                        ))

                ai_messages = [m for m in state.get("messages", []) if isinstance(m, AIMessage)]
                final = ai_messages[-1] if ai_messages else None

                if final and final.content:
                    await safe_send(StreamChunk(type="stream", content="\n"))
                    await safe_send(StreamChunk(type="done"))
                else:
                    await safe_send(StreamChunk(type="token", content="Listo."))
                    await safe_send(StreamChunk(type="done"))

            except asyncio.TimeoutError:
                await safe_send(StreamChunk(type="error", content="Timeout: el modelo tardó demasiado."))
            except Exception as e:
                logger.error(f"WS error: {e}")
                try:
                    await safe_send(StreamChunk(type="error", content=str(e)[:500]))
                except Exception:
                    pass

    except WebSocketDisconnect:
        logger.info("WS desconectado")
    except Exception as e:
        logger.error(f"WS fatal: {e}")
