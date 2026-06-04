"""FastAPI dependency — lazy graph init to avoid startup timeout."""
from loguru import logger

_jarvis_graph = None

def get_jarvis_graph():
    global _jarvis_graph
    if _jarvis_graph is not None:
        return _jarvis_graph
    from backend.agent.graph import get_graph
    from backend.tools.registry import ALL_TOOLS
    logger.info("Building agent graph (first request)...")
    _jarvis_graph = get_graph(tools=ALL_TOOLS)
    logger.info(f"Agent graph ready: {len(ALL_TOOLS)} tools")
    return _jarvis_graph
