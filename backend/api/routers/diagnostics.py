"""Diagnostic endpoints for agent health and memory."""
import asyncio
import time
import traceback
from collections import deque

from fastapi import APIRouter
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool

from backend.services.memory_service import memory_service
from backend.tools.registry import get_tool_status
from backend.config import settings
from backend.llm import get_llm

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

# Keep the last 50 errors from any source (WS chat, graph, tools)
# so the user can hit /last_ws_error and see the most recent
# failure with full stack trace, no Railway access required.
_error_log: deque = deque(maxlen=50)


def record_error(source: str, error: Exception, context: dict | None = None) -> None:
    """Append an error to the global error log. Called from the
    chat WS, the graph, and the tool_node when something fails.
    """
    _error_log.append({
        "ts": time.time(),
        "source": source,
        "type": type(error).__name__,
        "message": str(error)[:500],
        "trace": traceback.format_exc()[:1500],
        "context": (context or {})[:500] if isinstance(context, dict) else str(context)[:500],
    })


@router.get("/health")
async def agent_health():
    """Quick health check of the agent's memory and diagnostics system."""
    return memory_service.get_health()


@router.get("/report")
async def diagnostic_report():
    """Full diagnostic report of the agent."""
    return memory_service.run_diagnose()


@router.post("/cleanup")
async def agent_cleanup(compact_days: int = 30):
    """Run CCleaner-style cleanup: compact memory, clear old errors."""
    return memory_service.run_cleanup(compact_days=compact_days)


@router.get("/memory/categories")
async def memory_categories():
    """List all memory categories with counts."""
    return memory_service.list_categories()


@router.get("/tools")
async def tools_status():
    """List which tools the LLM currently has access to.

    Critical: Google tools (Gmail, Drive, Calendar) only appear here if
    OAuth is fully configured. If they don't appear, the LLM is NOT shown
    them and cannot hallucinate their execution.
    """
    return get_tool_status()


@router.get("/bind_tools_debug")
async def bind_tools_debug():
    """Reproduce bind_tools call with a trivial tool and capture the EXACT error."""
    out = {"model": settings.ollama_model, "base_url": settings.ollama_base_url}

    @tool
    def get_current_time(city: str = "UTC") -> str:
        """Devuelve la hora actual. Usar cuando el usuario pregunte la hora."""
        return f"Son las 21:45 en {city}"

    llm = get_llm()

    t = time.time()
    try:
        plain = await asyncio.wait_for(
            llm.ainvoke([SystemMessage(content="Sos JARVIS."), HumanMessage(content="hola")]),
            timeout=20,
        )
        out["plain_call"] = {
            "ok": True,
            "elapsed_s": round(time.time() - t, 2),
            "content": str(plain.content)[:200],
            "tool_calls": getattr(plain, "tool_calls", None),
        }
    except Exception as e:
        record_error("bind_tools_debug.plain", e, {"step": "plain_call"})
        out["plain_call"] = {
            "ok": False,
            "elapsed_s": round(time.time() - t, 2),
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc()[:1500],
        }

    t = time.time()
    try:
        llm_with_tools = llm.bind_tools([get_current_time])
        bound = await asyncio.wait_for(
            llm_with_tools.ainvoke([
                SystemMessage(content="Sos JARVIS. Usa get_current_time cuando te pregunten la hora."),
                HumanMessage(content="¿Qué hora es?"),
            ]),
            timeout=25,
        )
        out["bind_tools_call"] = {
            "ok": True,
            "elapsed_s": round(time.time() - t, 2),
            "content": str(bound.content)[:200],
            "tool_calls": getattr(bound, "tool_calls", None),
            "additional_kwargs": {k: str(v)[:300] for k, v in (bound.additional_kwargs or {}).items()},
        }
    except Exception as e:
        record_error("bind_tools_debug.bound", e, {"step": "bind_tools_call"})
        out["bind_tools_call"] = {
            "ok": False,
            "elapsed_s": round(time.time() - t, 2),
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc()[:2000],
        }

    return out


@router.get("/last_errors")
async def last_errors(limit: int = 20):
    """Return the most recent errors from any component.

    Critical for the user: 'JARVIS no funciona, no me dice que
    pasa'. They can hit this endpoint and see the actual failure
    without needing Railway access.
    """
    return {
        "count": len(_error_log),
        "errors": list(_error_log)[-limit:],
    }


@router.post("/clear_errors")
async def clear_errors():
    """Clear the error log."""
    _error_log.clear()
    return {"cleared": True}
