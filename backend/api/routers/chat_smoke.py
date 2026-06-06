"""Smoke test endpoint that reproduces the chat path step-by-step.

GET /api/v1/diagnostics/chat_smoke?msg=hola
"""
import asyncio
import time
import traceback

from fastapi import APIRouter

from backend.config import settings
from backend.llm import get_llm

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/chat_smoke")
async def chat_smoke(msg: str = "hola"):
    """Reproduce what the WS chat does, but step-by-step with timing + errors."""
    out = {"steps": [], "ok": False}
    t_start = time.time()

    # Step 1: import graph deps
    t = time.time()
    try:
        from backend.api.dependencies import get_jarvis_graph
        from backend.agent.personalities import get_persona
        out["steps"].append({"step": "imports", "ok": True, "elapsed_s": round(time.time() - t, 2)})
    except Exception as e:
        out["steps"].append({"step": "imports", "ok": False, "error": str(e), "trace": traceback.format_exc()[:600]})
        return out

    # Step 2: get LLM
    t = time.time()
    try:
        llm = get_llm()
        out["steps"].append({
            "step": "get_llm",
            "ok": True,
            "elapsed_s": round(time.time() - t, 2),
            "llm_type": type(llm).__name__,
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
            "has_key": bool(settings.ollama_api_key),
        })
    except Exception as e:
        out["steps"].append({"step": "get_llm", "ok": False, "error": str(e), "trace": traceback.format_exc()[:600]})
        return out

    # Step 3: plain LLM call (no tools, no graph)
    t = time.time()
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        persona = get_persona("profesional")
        messages = [SystemMessage(content=persona.system_prompt), HumanMessage(content=msg)]

        async def _call():
            return await asyncio.wait_for(llm.ainvoke(messages), timeout=22)

        resp = await _call()
        out["steps"].append({
            "step": "llm_ainvoke_plain",
            "ok": True,
            "elapsed_s": round(time.time() - t, 2),
            "content_preview": str(resp.content)[:200],
        })
    except Exception as e:
        out["steps"].append({
            "step": "llm_ainvoke_plain",
            "ok": False,
            "elapsed_s": round(time.time() - t, 2),
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc()[:800],
        })
        return out

    # Step 4: get graph
    t = time.time()
    try:
        graph = get_jarvis_graph()
        out["steps"].append({
            "step": "get_jarvis_graph",
            "ok": True,
            "elapsed_s": round(time.time() - t, 2),
            "graph_type": type(graph).__name__,
        })
    except Exception as e:
        out["steps"].append({"step": "get_jarvis_graph", "ok": False, "error": str(e), "trace": traceback.format_exc()[:600]})
        return out

    # Step 5: graph ainvoke (the actual call that fails in WS)
    t = time.time()
    try:
        from langchain_core.messages import HumanMessage as HM
        from backend.api.dependencies import get_jarvis_graph as _g
        graph = _g()
        result = await asyncio.wait_for(
            graph.ainvoke(
                {"messages": [HM(content=msg)], "session_id": "diag", "persona": "profesional"},
                config={"configurable": {"thread_id": "diag"}, "recursion_limit": 10},
            ),
            timeout=25,
        )
        msgs = result.get("messages", [])
        last = msgs[-1] if msgs else None
        out["steps"].append({
            "step": "graph_ainvoke",
            "ok": True,
            "elapsed_s": round(time.time() - t, 2),
            "n_messages": len(msgs),
            "last_content": str(getattr(last, "content", ""))[:200],
        })
    except Exception as e:
        out["steps"].append({
            "step": "graph_ainvoke",
            "ok": False,
            "elapsed_s": round(time.time() - t, 2),
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc()[:1500],
        })
        return out

    out["ok"] = True
    out["total_elapsed_s"] = round(time.time() - t_start, 2)
    return out
