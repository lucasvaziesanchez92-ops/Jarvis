"""API routes for threads."""
from typing import List, Literal
from fastapi import APIRouter, HTTPException

from backend.services.threads_service import (
    create_thread,
    get_thread,
    list_threads,
    update_thread_status,
    archive_thread,
    delete_thread,
)

router = APIRouter()


@router.post("", summary="Create a new thread")
async def create_thread_route(title: str | None = None, metadata: dict | None = None):
    """Create a new conversation thread."""
    return create_thread(title=title, metadata=metadata)


@router.get("", summary="List all threads")
async def list_threads_route(status: Literal["active", "archived", "deleted"] | None = None):
    """List all threads, optionally filtered by status."""
    return list_threads(status=status)


@router.get("/{thread_id}", summary="Get a thread")
async def get_thread_route(thread_id: str):
    """Get a specific thread by ID."""
    thread = get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.put("/{thread_id}/status", summary="Update thread status")
async def update_thread_status_route(
    thread_id: str, 
    status: Literal["active", "archived", "deleted"]
):
    """Update thread status."""
    thread = update_thread_status(thread_id, status)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.post("/{thread_id}/archive", summary="Archive a thread")
async def archive_thread_route(thread_id: str):
    """Archive a thread."""
    thread = archive_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.delete("/{thread_id}", summary="Delete a thread")
async def delete_thread_route(thread_id: str):
    """Delete a thread."""
    result = delete_thread(thread_id)
    if "not found" in result:
        raise HTTPException(status_code=404, detail=result)
    return {"message": result}
