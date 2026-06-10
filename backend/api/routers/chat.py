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
from backend.agent.personalities import get_persona

router = APIRouter()

# Railway free tier proxy window = 30s. The Ollama cloud large models
# (qwen2.5:72b, gpt-oss:120b) can take 15-30s on first-token. Cap the
# graph at 60s; fall back to plain LLM (no tools) on timeout.
_GRAPH_TIMEOUT = 60
_PLAIN_TIMEOUT = 30


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


async def _keepalive(send_fn, connected_ref):
    while connected_ref[0]:
        await asyncio.sleep(3)
        if not connected_ref[0]:
            break
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
    connected = [True]
    loop = asyncio.get_running_loop()

    async def send(chunk: StreamChunk):
        if not connected[0]:
            return
        try:
            await websocket.send_text(chunk.model_dump_json())
        except Exception:
            connected[0] = False

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

            # Accept both 'attachments' (object array from frontend) and 'file_keys' (raw)
            attachments = data.get("attachments") or []
            file_keys = data.get("file_keys") or [a.get("key") or a.get("url", "") for a in attachments if isinstance(a, dict)]
            filenames = data.get("filenames") or [a.get("name", "") for a in attachments if isinstance(a, dict)]

            if not message and not file_keys:
                continue

            full_message = message
            if file_keys:
                try:
                    ctx = build_file_context(file_keys, filenames)
                    full_message = f"{ctx}\n\n{message}" if message else ctx
                except Exception as e:
                    logger.warning(f"build_file_context failed: {e}")

            input_state = {
                "messages": [HumanMessage(content=full_message)],
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

                ping = asyncio.create_task(_keepalive(send, connected))

                loop = asyncio.get_running_loop()
                graph = get_jarvis_graph()

                async def _run_graph():
                    return await asyncio.wait_for(
                        graph.ainvoke(input_state, config=config),
                        timeout=_GRAPH_TIMEOUT,
                    )

                try:
                    state = await _run_graph()
                except asyncio.TimeoutError:
                    logger.warning("graph timeout — falling back to plain LLM")
                    try:
                        from backend.llm import get_llm
                        llm = get_llm()
                        persona = get_persona(persona_name := persona)
                        sys_msg = SystemMessage(content=persona.system_prompt)
                        user_msg = HumanMessage(content=full_message)

                        async def _plain():
                            return await asyncio.wait_for(
                                llm.ainvoke([sys_msg, user_msg]),
                                timeout=_PLAIN_TIMEOUT,
                            )

                        ai_resp = await _plain()
                        state = {"messages": [ai_resp]}
                    except Exception as e2:
                        logger.error(f"plain LLM fallback failed: {e2}")
                        await send(StreamChunk(type="token", content=(
                            "Tuve un problema de latencia con mi modelo. "
                            "¿Probás de nuevo en unos segundos?"
                        )))
                        await send(StreamChunk(type="done"))
                        continue
                finally:
                    ping.cancel()

                ai_msgs = [m for m in state.get("messages", []) if isinstance(m, AIMessage)]
                final = ai_msgs[-1] if ai_msgs else None

                if final and final.content:
                    await send(StreamChunk(type="token", content=str(final.content)))
                else:
                    await send(StreamChunk(type="token", content="Listo."))
                await send(StreamChunk(type="done"))

            except Exception as e:
                logger.error(f"WS error: {type(e).__name__}: {e}")
                try:
                    await send(StreamChunk(type="error", content=str(e)[:500]))
                except Exception:
                    pass

    except WebSocketDisconnect:
        logger.info("WS desconectado")
    except Exception as e:
        logger.error(f"WS fatal: {e}")
    finally:
        connected[0] = False
