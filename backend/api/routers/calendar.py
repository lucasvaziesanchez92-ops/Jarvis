"""Google Calendar API router."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import asyncio
from loguru import logger
from backend.services.calendar_service import list_events, create_event, update_event, delete_event
from backend.services.google_auth import GoogleNotConfiguredError

router = APIRouter(tags=["calendar"])

class CreateEventRequest(BaseModel):
    summary: str
    start_time: str
    end_time: str
    description: str = ""
    location: str = ""
    attendees: list[str] = []

class UpdateEventRequest(BaseModel):
    summary: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None


def _handle_calendar_error(e: Exception) -> HTTPException:
    if isinstance(e, GoogleNotConfiguredError):
        return HTTPException(503, str(e))
    if isinstance(e, RuntimeError) and ("Google" in str(e) or "credentials" in str(e).lower() or "OAuth" in str(e)):
        return HTTPException(503, f"Google Calendar no configurado: {e}")
    logger.exception(f"Calendar endpoint failed: {e}")
    return HTTPException(500, f"Calendar error: {type(e).__name__}: {e}")


@router.get("/events")
async def get_events(max_results: int = Query(20, le=100)):
    try:
        return await asyncio.to_thread(list_events, max_results=max_results)
    except Exception as e:
        raise _handle_calendar_error(e)

@router.post("/events")
async def add_event(request: CreateEventRequest):
    try:
        return await asyncio.to_thread(create_event, request.summary, request.start_time, request.end_time, request.description, request.location, request.attendees)
    except Exception as e:
        raise _handle_calendar_error(e)

@router.put("/events/{event_id}")
async def edit_event(event_id: str, request: UpdateEventRequest):
    try:
        return await asyncio.to_thread(update_event, event_id, request.summary, request.start_time, request.end_time, request.description)
    except Exception as e:
        raise _handle_calendar_error(e)

@router.delete("/events/{event_id}")
async def remove_event(event_id: str):
    try:
        return await asyncio.to_thread(delete_event, event_id)
    except Exception as e:
        raise _handle_calendar_error(e)
