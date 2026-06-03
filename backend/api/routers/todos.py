"""REST endpoints for Todos."""
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.todo import Todo
from backend.services import todos_service

router = APIRouter()


class TodoCreate(BaseModel):
    text: str
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: str | None = None


@router.get("", response_model=list[Todo])
def list_todos(show_completed: bool = False):
    return todos_service.list_todos(show_completed)


@router.post("", response_model=Todo, status_code=201)
def create_todo(body: TodoCreate):
    return todos_service.create_todo(body.text, body.priority, body.due_date)


class TodoUpdate(BaseModel):
    text: str | None = None
    priority: Literal["low", "medium", "high"] | None = None
    due_date: str | None = None


@router.get("/{todo_id}", response_model=Todo)
def get_todo(todo_id: str):
    data = todos_service.get_todo(todo_id)
    if not data:
        raise HTTPException(status_code=404, detail="Todo not found")
    return data


@router.put("/{todo_id}", response_model=Todo)
def update_todo(todo_id: str, body: TodoUpdate):
    data = todos_service.update_todo(todo_id, body.text, body.priority, body.due_date)
    if not data:
        raise HTTPException(status_code=404, detail="Todo not found")
    return data


@router.patch("/{todo_id}/complete", response_model=Todo)
def complete_todo(todo_id: str):
    data = todos_service.complete_todo(todo_id)
    if not data:
        raise HTTPException(status_code=404, detail="Todo not found")
    return data


@router.delete("/{todo_id}", status_code=204)
def delete_todo(todo_id: str):
    result = todos_service.delete_todo(todo_id)
    if "not found" in result:
        raise HTTPException(status_code=404, detail="Todo not found")
