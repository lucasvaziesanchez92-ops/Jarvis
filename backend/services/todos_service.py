"""Business logic for to-do management."""
from datetime import datetime
from typing import Literal, List

from sqlalchemy.orm import Session

from backend.models.todo import Todo
from backend.storage.sqlite_store import get_store, TodoModel


def create_todo(text: str, priority: Literal["low", "medium", "high"] = "medium", due_date: str | None = None) -> dict:
    store = get_store()
    session: Session = store.get_session()
    try:
        todo = Todo(
            text=text,
            priority=priority,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
        )
        todo_model = TodoModel(
            id=todo.id,
            text=todo.text,
            completed=todo.completed,
            priority=todo.priority,
            due_date=todo.due_date,
            created_at=todo.created_at
        )
        session.add(todo_model)
        session.commit()
        return todo.model_dump()
    finally:
        session.close()


def list_todos(show_completed: bool = False) -> List[dict]:
    store = get_store()
    session: Session = store.get_session()
    try:
        query = session.query(TodoModel)
        if not show_completed:
            query = query.filter(TodoModel.completed == False)
        todos_models = query.all()
        todos = []
        for tm in todos_models:
            todo = Todo(
                id=tm.id,
                text=tm.text,
                completed=tm.completed,
                priority=tm.priority,
                due_date=tm.due_date,
                created_at=tm.created_at
            )
            todos.append(todo.model_dump())
        return todos
    finally:
        session.close()


def get_todo(todo_id: str) -> dict | None:
    store = get_store()
    session: Session = store.get_session()
    try:
        todo_model = session.query(TodoModel).filter(TodoModel.id == todo_id).first()
        if not todo_model:
            return None
        todo = Todo(
            id=todo_model.id,
            text=todo_model.text,
            completed=todo_model.completed,
            priority=todo_model.priority,
            due_date=todo_model.due_date,
            created_at=todo_model.created_at
        )
        return todo.model_dump()
    finally:
        session.close()


def complete_todo(todo_id: str) -> dict | None:
    store = get_store()
    session: Session = store.get_session()
    try:
        todo_model = session.query(TodoModel).filter(TodoModel.id == todo_id).first()
        if not todo_model:
            return None
        todo_model.completed = True
        session.commit()
        # Return updated todo
        todo = Todo(
            id=todo_model.id,
            text=todo_model.text,
            completed=todo_model.completed,
            priority=todo_model.priority,
            due_date=todo_model.due_date,
            created_at=todo_model.created_at
        )
        return todo.model_dump()
    finally:
        session.close()


def update_todo(todo_id: str, text: str | None = None, priority: Literal["low", "medium", "high"] | None = None, due_date: str | None = None) -> dict | None:
    store = get_store()
    session: Session = store.get_session()
    try:
        todo_model = session.query(TodoModel).filter(TodoModel.id == todo_id).first()
        if not todo_model:
            return None
        if text is not None:
            todo_model.text = text
        if priority is not None:
            todo_model.priority = priority
        if due_date is not None:
            todo_model.due_date = datetime.fromisoformat(due_date)
        session.commit()
        todo = Todo(
            id=todo_model.id,
            text=todo_model.text,
            completed=todo_model.completed,
            priority=todo_model.priority,
            due_date=todo_model.due_date,
            created_at=todo_model.created_at
        )
        return todo.model_dump()
    finally:
        session.close()


def delete_todo(todo_id: str) -> str:
    store = get_store()
    session: Session = store.get_session()
    try:
        todo_model = session.query(TodoModel).filter(TodoModel.id == todo_id).first()
        if not todo_model:
            return f"Todo {todo_id} not found."
        session.delete(todo_model)
        session.commit()
        return f"Todo {todo_id} deleted."
    finally:
        session.close()
