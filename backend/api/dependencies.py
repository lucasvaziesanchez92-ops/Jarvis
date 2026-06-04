"""FastAPI dependency — graph built in lifespan, chat waits max 15s for readiness."""
import threading
import time
from loguru import logger

_jarvis_graph = None
_graph_ready = threading.Event()
_build_failed = threading.Event()

def _build_graph():
    global _jarvis_graph
    try:
        from backend.agent.graph import get_graph
        from backend.tools.registry import ALL_TOOLS
        _jarvis_graph = get_graph(tools=ALL_TOOLS)
        _graph_ready.set()
        logger.info(f"Agent graph ready: {len(ALL_TOOLS)} tools")
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        _build_failed.set()

threading.Thread(target=_build_graph, daemon=True).start()

def wait_graph_ready(timeout=15):
    if _graph_ready.wait(timeout):
        return True
    return False

def get_jarvis_graph():
    global _jarvis_graph
    if _jarvis_graph is not None:
        return _jarvis_graph
    _graph_ready.wait(20)
    if _jarvis_graph is not None:
        return _jarvis_graph
    from backend.agent.graph import get_graph
    from backend.tools.registry import ALL_TOOLS
    _jarvis_graph = get_graph(tools=ALL_TOOLS)
    _graph_ready.set()
    return _jarvis_graph
