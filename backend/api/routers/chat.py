"""Chat endpoints — agent graph with tools, keepalive for Railway."""
import asyncio
import json
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.callbacks import BaseCallbackHandler
from loguru import logger

from backend.api.dependencies import get_jarvis_graph
from backend.api.routers.diagnostics import record_error
from backend.models.chat import ChatRequest, ChatResponse, StreamChunk
from backend.core.file_extractor import build_file_context
from backend.agent.personalities import get_persona

router = APIRouter()

# Per-session in-memory message history. The graph no longer uses a
# checkpointer (it caused 'Not the same number of function calls and
# responses' by re-injecting stale tool_calls into the next turn).
# We manage history here so each turn sees its own previous turn
# exactly as the LLM produced it.
_session_history: dict[str, list] = defaultdict(list)
_MAX_HISTORY = 20  # messages per session

def _prune_history(messages: list, max_msgs: int) -> list:
    """Safely truncates history without breaking ToolMessage/AIMessage pairs.
    Always starts the truncated history with a HumanMessage."""
    if len(messages) <= max_msgs:
        return messages
    start_idx = len(messages) - max_msgs
    for i in range(start_idx, len(messages)):
        if getattr(messages[i], "type", "") == "human":
            return messages[i:]
    return messages[-max_msgs:]

# Railway free tier proxy window = 30s. Cap the graph at 22s; fallback
# to plain LLM (no tools) if the agent times out. Keeping this low
# because the user sees a fast fallback message instead of staring at
# "Pensando..." for a minute.
_GRAPH_TIMEOUT = 55
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

            # Try to add user name to context
            try:
                from backend.storage.sqlite_store import get_store
                from backend.storage.models import UserModel
                store = get_store()
                session = store.get_session()
                try:
                    db_user = session.query(UserModel).filter(UserModel.id == "default_user").first()
                    if db_user and db_user.name:
                        full_message = f"[System Context: El usuario se llama {db_user.name}]\n\n{full_message}"
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"No se pudo obtener el nombre del usuario: {e}")

            # Reconstruct history from frontend if backend lost it (e.g. Railway restart)
            client_history = data.get("history", [])
            if not _session_history[session_id] and client_history:
                rebuilt = []
                for m in client_history:
                    role = m.get("role")
                    cont = m.get("content", "")
                    if role == "user":
                        rebuilt.append(HumanMessage(content=cont))
                    elif role == "assistant":
                        rebuilt.append(AIMessage(content=cont))
                _session_history[session_id] = rebuilt

            # Build the input: prior session history (already in
            # the exact shape the LLM produced, including
            # AIMessage.tool_calls and ToolMessage pairs) plus the
            # new user turn. This replaces the InMemorySaver
            # checkpointer that was duplicating messages and
            # breaking tool_call pairing.
            history = list(_session_history[session_id])
            input_state = {
                "messages": history + [HumanMessage(content=full_message)],
                "session_id": session_id,
                "persona": persona,
            }

            callback = WebSocketCallback(loop, send)
            config = {
                "configurable": {"thread_id": session_id},
                "callbacks": [callback],
                "recursion_limit": 25,  # enough for ~5 tool iterations
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
                        state = {"messages": history + [HumanMessage(content=full_message), ai_resp]}
                    except Exception as e2:
                        logger.error(f"plain LLM fallback failed: {type(e2).__name__}: {e2}")
                        await send(StreamChunk(type="token", content=(
                            f"Error técnico con el modelo: {type(e2).__name__}: {str(e2)[:200]}"
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

                # Persist this turn's full message list into the
                # session history so the next turn sees the
                # complete conversation (including AIMessage
                # tool_calls paired with their ToolMessage
                # responses). The graph returns the FULL state
                # (history + new turn), so we replace, not append.
                if state.get("messages"):
                    _session_history[session_id] = _prune_history(list(state["messages"]), _MAX_HISTORY)

                # Fire knowledge extractor in background so it doesn't block UI or timeout
                from backend.agent.knowledge_extractor import extract_knowledge
                loop.run_in_executor(None, extract_knowledge, state)

            except Exception as e:
                logger.exception("WS error in chat loop")
                record_error("ws_chat_loop", e, {
                    "session_id": session_id,
                    "message_preview": (message or "")[:200],
                })
                try:
                    await send(StreamChunk(type="error", content=str(e)[:500]))
                except Exception:
                    pass

    except WebSocketDisconnect:
        logger.info("WS desconectado")
    except Exception as e:
        logger.error("WS fatal: {}", str(e))
    finally:
        connected[0] = False
