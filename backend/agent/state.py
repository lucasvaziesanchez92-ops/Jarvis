"""JarvisState extends MessagesState with session metadata."""
from typing import Annotated
import operator
from langgraph.graph import MessagesState


class JarvisState(MessagesState):
    user_id: str | None = None
    session_id: str | None = None
    persona: str = "default"
    retrieved_context: Annotated[list[str], operator.add] = []
    tool_iterations: int = 0
    tools_executed: list[str] = []
