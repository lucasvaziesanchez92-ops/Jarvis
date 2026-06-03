"""FastAPI dependency: provides a lazy-initialized singleton compiled graph with all tools."""
from functools import lru_cache


@lru_cache
def get_jarvis_graph():
    """Return the singleton Jarvis graph, built with all registered tools.
    
    LAZY INIT: Graph only compiles when first accessed, not at server startup.
    This prevents crashes when LLM provider is unavailable.
    """
    from backend.agent.graph import get_graph
    from backend.tools.registry import ALL_TOOLS
    return get_graph(tools=ALL_TOOLS)
