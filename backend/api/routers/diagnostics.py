"""Diagnostic endpoints for agent health and memory."""
import asyncio
import time
import traceback

from fastapi import APIRouter
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool

from backend.services.memory_service import memory_service
from backend.tools.registry import get_tool_status
from backend.config import settings
from backend.llm import get_llm

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


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
    """Reproduce bind_tools call with a trivial tool and capture the EXACT error.

    This is the diagnostic that found why 'JARVIS miente sobre sus tools':
    - Plain llm.ainvoke() works
    - llm.bind_tools([...]).invoke() fails with a specific exception

    Returns the full request body sent to the LLM, the response, and the error.
    """
    out = {"model": settings.ollama_model, "base_url": settings.ollama_base_url}

    @tool
    def get_current_time(city: str = "UTC") -> str:
        """Devuelve la hora actual. Usar cuando el usuario pregunte la hora."""
        return f"Son las 21:45 en {city}"

    llm = get_llm()

    # Plain call
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
        out["plain_call"] = {
            "ok": False,
            "elapsed_s": round(time.time() - t, 2),
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc()[:1500],
        }

    # bind_tools call
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
        out["bind_tools_call"] = {
            "ok": False,
            "elapsed_s": round(time.time() - t, 2),
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc()[:2000],
        }

    return out
