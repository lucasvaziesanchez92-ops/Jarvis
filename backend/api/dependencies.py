"""FastAPI dependency — graph pre-built in background, served when ready."""
import threading
import time
from loguru import logger

_jarvis_graph = None
_build_started = False
_build_lock = threading.Lock()

def _build():
    global _jarvis_graph
    from backend.agent.graph import get_graph
    from backend.tools.registry import ALL_TOOLS
    _jarvis_graph = get_graph(tools=ALL_TOOLS)
    logger.info(f"Agent graph ready: {len(ALL_TOOLS)} tools")

def _start_build():
    global _build_started
    with _build_lock:
        if not _build_started:
            _build_started = True
            threading.Thread(target=_build, daemon=True).start()
            logger.info("Agent graph build started in background")

_start_build()

def get_jarvis_graph():
    global _jarvis_graph
    if _jarvis_graph is not None:
        return _jarvis_graph
    # Build synchronously as fallback (should already be built from background thread)
    from backend.agent.graph import get_graph
    from backend.tools.registry import ALL_TOOLS
    _jarvis_graph = get_graph(tools=ALL_TOOLS)
    return _jarvis_graph
