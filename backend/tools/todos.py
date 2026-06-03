"""LangChain tools for to-do management."""
from typing import Literal
from langchain_core.tools import tool

from backend.services import todos_service


@tool
def create_todo(text: str, priority: Literal["low", "medium", "high"] = "medium", due_date: str | None = None) -> dict:
    """Create a new to-do item. due_date should be ISO format string (e.g. 2024-12-31T10:00:00)."""
    return todos_service.create_todo(text, priority, due_date)


@tool
def list_todos(show_completed: bool = False) -> list[dict]:
    """List to-do items. By default only shows incomplete items."""
    return todos_service.list_todos(show_completed)


@tool
def complete_todo(todo_id: str) -> dict | None:
    """Mark a to-do item as completed."""
    return todos_service.complete_todo(todo_id)


@tool
def update_todo(todo_id: str, text: str | None = None, priority: Literal["low", "medium", "high"] | None = None, due_date: str | None = None) -> dict | None:
    """Update a to-do item's text, priority, or due_date (ISO format)."""
    return todos_service.update_todo(todo_id, text, priority, due_date)


@tool
def delete_todo(todo_id: str) -> str:
    """Delete a to-do item by its ID."""
    return todos_service.delete_todo(todo_id)
