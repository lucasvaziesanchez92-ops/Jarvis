"""FastAPI dependency — pre-compiled graph at import time to avoid 502 on first request."""
from loguru import logger

_jarvis_graph = None
_ready = False

try:
    from backend.agent.graph import get_graph
    from backend.tools.registry import ALL_TOOLS
    logger.info("Building agent graph at startup...")
    _jarvis_graph = get_graph(tools=ALL_TOOLS)
    _ready = True
    logger.info(f"Agent graph ready: {len(ALL_TOOLS)} tools loaded")
except Exception as e:
    logger.warning(f"Graph pre-build failed, will retry on first request: {e}")

def get_jarvis_graph():
    global _jarvis_graph, _ready
    if _ready and _jarvis_graph is not None:
        return _jarvis_graph
    from backend.agent.graph import get_graph
    from backend.tools.registry import ALL_TOOLS
    _jarvis_graph = get_graph(tools=ALL_TOOLS)
    _ready = True
    return _jarvis_graph
