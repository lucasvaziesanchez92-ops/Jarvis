"""Google OAuth 2.0 service — con PKCE (code verifier/challenge)."""
import base64
import hashlib
import json
import os
import secrets
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from loguru import logger

CLIENT_SECRET_FILE = Path(__file__).parent.parent.parent / "client_secret.json"
_client_config_cache: dict | None = None

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _get_client_config() -> dict:
    global _client_config_cache
    if _client_config_cache is None:
        if not CLIENT_SECRET_FILE.exists():
            raise FileNotFoundError(f"client_secret.json not found at {CLIENT_SECRET_FILE}")
        _client_config_cache = json.loads(CLIENT_SECRET_FILE.read_text())["web"]
    return _client_config_cache


def _generate_pkce() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = urllib.parse.quote(
        base64.urlsafe_b64encode(digest).rstrip(b"=").decode(),
        safe="",
    )
    return code_verifier, code_challenge


_pkce_store: dict[str, str] = {}


class GoogleAuthService:
    def __init__(self, redirect_uri: str = "http://localhost:8001/auth/google/callback"):
        self.redirect_uri = redirect_uri
        config = _get_client_config()
        self.client_id = config["client_id"]
        self.client_secret = config["client_secret"]
        self.auth_uri = config.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")
        self.token_uri = config.get("token_uri", "https://oauth2.googleapis.com/token")

    def get_auth_url(self) -> tuple[str, str]:
        code_verifier, code_challenge = _generate_pkce()
        state = secrets.token_urlsafe(16)
        _pkce_store[state] = code_verifier

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        url = f"{self.auth_uri}?{urllib.parse.urlencode(params)}"
        return url, state

    def exchange_code(self, code: str, state: str | None = None) -> dict:
        code_verifier = None
        if state:
            code_verifier = _pkce_store.pop(state, None)

        data: dict = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier

        resp = requests.post(self.token_uri, data=data, timeout=15)
        body = resp.json()
        if "error" in body:
            raise ValueError(body.get("error_description", body["error"]))

        return {
            "token": body["access_token"],
            "refresh_token": body.get("refresh_token", ""),
            "token_uri": self.token_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scopes": body.get("scope", "").split(),
            "expiry": None,
        }

    @staticmethod
    def get_credentials(refresh_token: str) -> Credentials:
        config = _get_client_config()
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            scopes=SCOPES,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        return creds

    @staticmethod
    def build_gmail(creds: Credentials):
        return build("gmail", "v1", credentials=creds)

    @staticmethod
    def build_drive(creds: Credentials):
        return build("drive", "v3", credentials=creds)

    @staticmethod
    def build_calendar(creds: Credentials):
        return build("calendar", "v3", credentials=creds)


def _get_auth_db_path() -> Path:
    data_dir = os.environ.get("DATA_DIR", "data")
    return Path(data_dir) / "google_tokens.db"


def _get_auth_conn():
    db_path = _get_auth_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            user_id TEXT PRIMARY KEY,
            refresh_token TEXT NOT NULL,
            email TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def save_tokens(user_id: str, refresh_token: str, email: str = ""):
    conn = _get_auth_conn()
    conn.execute(
        "INSERT OR REPLACE INTO tokens (user_id, refresh_token, email, updated_at) VALUES (?, ?, ?, datetime('now'))",
        (user_id, refresh_token, email),
    )
    conn.commit()
    conn.close()


def get_refresh_token(user_id: str) -> Optional[str]:
    conn = _get_auth_conn()
    row = conn.execute("SELECT refresh_token FROM tokens WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else None


def get_user_info(user_id: str) -> Optional[dict]:
    conn = _get_auth_conn()
    row = conn.execute("SELECT user_id, email, created_at FROM tokens WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "email": row[1], "created_at": row[2]}
    return None


def delete_token(user_id: str):
    conn = _get_auth_conn()
    conn.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
