"""API routes for messages."""
from typing import List, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.messages_service import (
    create_message,
    get_message,
    list_messages,
    delete_message,
    delete_thread_messages,
)

router = APIRouter()


class CreateMessageRequest(BaseModel):
    thread_id: str
    role: str = "user"
    content: str = ""
    metadata: dict[str, Any] | None = None


@router.post("", summary="Create a new message")
async def create_message_route(request: CreateMessageRequest):
    """Create a new message in a thread."""
    return create_message(
        thread_id=request.thread_id,
        role=request.role,
        content=request.content,
        metadata=request.metadata,
    )


@router.get("/{message_id}", summary="Get a message")
async def get_message_route(message_id: str):
    message = get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.get("/thread/{thread_id}", summary="List messages in a thread")
async def list_messages_route(thread_id: str, limit: int | None = None):
    return list_messages(thread_id, limit=limit)


@router.delete("/{message_id}", summary="Delete a message")
async def delete_message_route(message_id: str):
    result = delete_message(message_id)
    if "not found" in result:
        raise HTTPException(status_code=404, detail=result)
    return {"message": result}


@router.delete("/thread/{thread_id}", summary="Delete all messages in a thread")
async def delete_thread_messages_route(thread_id: str):
    result = delete_thread_messages(thread_id)
    return {"message": result}
