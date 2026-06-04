"""FastAPI dependency — graph built at startup, ready for instant requests."""
import threading
from loguru import logger

_jarvis_graph = None
_graph_ok = False

def _build_graph_sync():
    global _jarvis_graph, _graph_ok
    try:
        from backend.agent.graph import get_graph
        from backend.tools.registry import ALL_TOOLS
        _jarvis_graph = get_graph(tools=ALL_TOOLS)
        _graph_ok = True
        logger.info(f"Agent graph ready: {len(ALL_TOOLS)} tools")
    except Exception as e:
        logger.error(f"Graph build failed: {e}")

_build_graph_sync()

def get_jarvis_graph():
    global _jarvis_graph, _graph_ok
    if not _graph_ok:
        _build_graph_sync()
    return _jarvis_graph
