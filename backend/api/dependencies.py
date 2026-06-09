"""FastAPI dependency — graph pre-built at startup, shared across requests."""
import traceback
from loguru import logger

_jarvis_graph = None
_graph_ok = False

def build_graph():
    """Build the agent graph. Called from lifespan startup."""
    global _jarvis_graph, _graph_ok
    try:
        from backend.agent.graph import get_graph
        from backend.tools.registry import ALL_TOOLS
        logger.info("Building agent graph...")
        _jarvis_graph = get_graph(tools=ALL_TOOLS)
        _graph_ok = True
        logger.info(f"Agent graph ready: {len(ALL_TOOLS)} tools loaded")
    except Exception as e:
        logger.error(f"Graph build failed: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())

def get_jarvis_graph():
    global _jarvis_graph
    if _jarvis_graph is not None:
        return _jarvis_graph
    build_graph()
    return _jarvis_graph
