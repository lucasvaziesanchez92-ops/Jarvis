"""Gmail API router — list, search, get, send emails."""
import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from loguru import logger
from backend.services.gmail_service import list_emails, search_emails, get_email, send_email
from backend.services.google_auth import GoogleNotConfiguredError

router = APIRouter(prefix="/gmail", tags=["gmail"])

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str


def _handle_gmail_error(e: Exception) -> HTTPException:
    if isinstance(e, GoogleNotConfiguredError):
        return HTTPException(503, str(e))
    if isinstance(e, RuntimeError) and ("Google" in str(e) or "credentials" in str(e).lower() or "OAuth" in str(e)):
        return HTTPException(503, f"Gmail no configurado: {e}")
    logger.exception(f"Gmail endpoint failed: {e}")
    return HTTPException(500, f"Gmail error: {type(e).__name__}: {e}")


@router.get("/list")
async def list_inbox(max_results: int = Query(10, le=50)):
    try:
        return await asyncio.to_thread(list_emails, max_results)
    except Exception as e:
        raise _handle_gmail_error(e)

@router.get("/search")
async def search(q: str = Query(...), max_results: int = Query(20, le=50)):
    try:
        return await asyncio.to_thread(search_emails, q, max_results)
    except Exception as e:
        raise _handle_gmail_error(e)

@router.get("/{email_id}")
async def read_email(email_id: str):
    try:
        return await asyncio.to_thread(get_email, email_id)
    except Exception as e:
        raise _handle_gmail_error(e)

@router.post("/send")
async def send(request: SendEmailRequest):
    try:
        return await asyncio.to_thread(send_email, request.to, request.subject, request.body)
    except Exception as e:
        raise _handle_gmail_error(e)
