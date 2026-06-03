"""Business logic for Gmail integration via Google API."""
from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText

from backend.config import settings


def _get_gmail_service():
    """Build and return an authenticated Gmail API service."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    creds = None
    token_file = settings.gmail_token_file
    credentials_file = settings.gmail_credentials_file

    if token_file and os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif credentials_file:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise RuntimeError(
                "Gmail credentials not configured. Set GMAIL_CREDENTIALS_FILE in .env"
            )
        if token_file:
            with open(token_file, "w") as f:
                f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def list_emails(max_results: int = 10, label: str = "INBOX") -> list[dict]:
    service = _get_gmail_service()
    result = service.users().messages().list(
        userId="me", labelIds=[label], maxResults=max_results
    ).execute()
    messages = result.get("messages", [])
    emails = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        emails.append({
            "message_id": msg["id"],
            "sender": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "snippet": detail.get("snippet", ""),
            "date": headers.get("Date", ""),
        })
    return emails


def get_email(message_id: str) -> dict:
    service = _get_gmail_service()
    detail = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}

    # Extract body
    body = ""
    payload = detail.get("payload", {})
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    break
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return {
        "message_id": message_id,
        "sender": headers.get("From", ""),
        "recipient": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "body": body,
        "snippet": detail.get("snippet", ""),
        "date": headers.get("Date", ""),
        "labels": detail.get("labelIds", []),
    }


def send_email(to: str, subject: str, body: str) -> str:
    service = _get_gmail_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email sent to {to} with subject '{subject}'."


def search_emails(query: str, max_results: int = 10) -> list[dict]:
    service = _get_gmail_service()
    result = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    messages = result.get("messages", [])
    emails = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        emails.append({
            "message_id": msg["id"],
            "sender": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "snippet": detail.get("snippet", ""),
            "date": headers.get("Date", ""),
        })
    return emails
