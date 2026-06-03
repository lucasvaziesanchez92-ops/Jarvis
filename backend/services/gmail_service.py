"""Gmail API service — send, search, list emails."""
import base64
from email.mime.text import MIMEText
from typing import Optional

from google.oauth2.credentials import Credentials
from loguru import logger

from backend.services.google_auth import GoogleAuthService, get_refresh_token

DEFAULT_USER = "default_user"


def _get_gmail_service(user_id: str = DEFAULT_USER):
    token = get_refresh_token(user_id)
    if not token:
        raise RuntimeError("Google no está conectado. Hacé login en Google primero.")
    creds = GoogleAuthService.get_credentials(token)
    return GoogleAuthService.build_gmail(creds)


def list_emails(max_results: int = 10, query: str = "", user_id: str = DEFAULT_USER) -> list[dict]:
    """List recent emails from inbox."""
    service = _get_gmail_service(user_id)
    results = service.users().messages().list(userId="me", maxResults=max_results, q=query).execute()
    messages = results.get("messages", [])
    emails = []
    for msg in messages[:max_results]:
        detail = service.users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        emails.append({
            "id": msg["id"],
            "thread_id": detail.get("threadId", ""),
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", "(sin asunto)"),
            "date": headers.get("Date", ""),
            "snippet": detail.get("snippet", ""),
        })
    return emails


def search_emails(query: str, max_results: int = 20, user_id: str = DEFAULT_USER) -> list[dict]:
    """Search emails by query using Gmail's search syntax."""
    return list_emails(max_results=max_results, query=query, user_id=user_id)


def get_email(email_id: str, user_id: str = DEFAULT_USER) -> dict:
    """Get full email content by ID."""
    service = _get_gmail_service(user_id)
    detail = service.users().messages().get(userId="me", id=email_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
    body = ""
    if "parts" in detail["payload"]:
        for part in detail["payload"]["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
    elif "body" in detail["payload"] and "data" in detail["payload"]["body"]:
        body = base64.urlsafe_b64decode(detail["payload"]["body"]["data"]).decode("utf-8", errors="replace")
    return {
        "id": email_id,
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "body": body[:5000],
    }


def send_email(to: str, subject: str, body: str, user_id: str = DEFAULT_USER) -> dict:
    """Send an email via Gmail API."""
    service = _get_gmail_service(user_id)
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"id": sent["id"], "thread_id": sent.get("threadId", ""), "status": "sent"}
