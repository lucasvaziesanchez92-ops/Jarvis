"""REST endpoints for Email (Gmail) — read-only list/get/search + send."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.services import email_service

router = APIRouter()


def _gmail_available() -> bool:
    from backend.config import settings
    return bool(settings.gmail_credentials_file or settings.gmail_token_file)


@router.get("")
def list_emails(label: str = "INBOX", max: int = Query(default=10, ge=1, le=100)):
    if not _gmail_available():
        raise HTTPException(status_code=503, detail="Gmail not configured")
    return email_service.list_emails(max_results=max, label=label)


@router.get("/search")
def search_emails(q: str, max: int = Query(default=10, ge=1, le=100)):
    if not _gmail_available():
        raise HTTPException(status_code=503, detail="Gmail not configured")
    return email_service.search_emails(query=q, max_results=max)


@router.get("/{message_id}")
def get_email(message_id: str):
    if not _gmail_available():
        raise HTTPException(status_code=503, detail="Gmail not configured")
    return email_service.get_email(message_id)


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str


@router.post("/send")
def send_email(request: SendEmailRequest):
    if not _gmail_available():
        raise HTTPException(status_code=503, detail="Gmail not configured")
    return {"result": email_service.send_email(request.to, request.subject, request.body)}
