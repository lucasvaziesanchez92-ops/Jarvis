"""Google OAuth 2.0 service — con PKCE + auto-refresh de tokens."""
import base64
import hashlib
import json
import os
import secrets
import sqlite3
import urllib.parse
from datetime import datetime, timezone
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
        if CLIENT_SECRET_FILE.exists():
            cfg = json.loads(CLIENT_SECRET_FILE.read_text())["web"]
            # Strip whitespace from loaded values — they can sneak in from
            # copy-paste, env var editors that pad with spaces, etc.
            _client_config_cache = {
                k: v.strip() if isinstance(v, str) else v for k, v in cfg.items()
            }
        else:
            # CRITICAL: strip whitespace from env vars. Railway's variable
            # editor can add a leading space, Google rejects any client_secret
            # with non-stripped whitespace ("invalid_client"). This single bug
            # bit us for a full day.
            client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
            if client_id and client_secret:
                _client_config_cache = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": os.getenv("GOOGLE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth").strip(),
                    "token_uri": os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token").strip(),
                }
            else:
                _client_config_cache = {}
    return _client_config_cache


class GoogleNotConfiguredError(RuntimeError):
    """Raised when Google APIs are not configured — callers should return 503."""
    pass


def _ensure_config():
    if not _get_client_config():
        raise GoogleNotConfiguredError(
            "Google APIs no están configuradas. Falta client_secret.json o las variables GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET."
        )


def _generate_pkce() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = urllib.parse.quote(
        base64.urlsafe_b64encode(digest).rstrip(b"=").decode(),
        safe="",
    )
    return code_verifier, code_challenge


def _get_auth_db_path() -> Path:
    data_dir = os.environ.get("DATA_DIR", "data")
    return Path(data_dir) / "google_tokens.db"


def _get_pkce_conn():
    db_path = _get_auth_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pkce_store (
            state TEXT PRIMARY KEY,
            code_verifier TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def _save_pkce(state: str, code_verifier: str):
    conn = _get_pkce_conn()
    conn.execute("INSERT OR REPLACE INTO pkce_store (state, code_verifier, created_at) VALUES (?, ?, datetime('now'))", (state, code_verifier))
    conn.commit()
    conn.close()


def _pop_pkce(state: str) -> str | None:
    conn = _get_pkce_conn()
    row = conn.execute("SELECT code_verifier FROM pkce_store WHERE state = ?", (state,)).fetchone()
    if row:
        conn.execute("DELETE FROM pkce_store WHERE state = ?", (state,))
        conn.commit()
        conn.close()
        return row[0]
    conn.close()
    return None


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
        _save_pkce(state, code_verifier)

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
            code_verifier = _pop_pkce(state)

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

        # Fetch user email from the userinfo endpoint so we can show
        # the connected account in the UI. Best effort: if it fails
        # we just save without an email.
        email = ""
        try:
            info_resp = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {body['access_token']}"},
                timeout=10,
            )
            if info_resp.status_code == 200:
                email = info_resp.json().get("email", "")
        except Exception:
            pass

        return {
            "access_token": body["access_token"],
            "refresh_token": body.get("refresh_token", ""),
            "expires_at": (
                datetime.now(timezone.utc).timestamp() + body.get("expires_in", 3600)
                if "expires_in" in body else None
            ),
            "token_uri": self.token_uri,
            "scopes": body.get("scope", "").split(),
            "email": email,
        }

    @staticmethod
    def get_credentials(refresh_token: str, access_token: str | None = None, expires_at: float | None = None) -> Credentials:
        config = _get_client_config()
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            scopes=SCOPES,
        )
        if expires_at:
            # The Google client libs internally compare creds.expiry
            # to datetime.utcnow() (naive) using a strict equality.
            # If creds.expiry is tz-aware, you get
            # "TypeError: can't compare offset-naive and offset-aware datetimes"
            # even though the semantic comparison is fine.
            # We store expiry as naive UTC to match what the libs expect.
            creds.expiry = datetime.utcfromtimestamp(expires_at)
        if not creds.valid and creds.refresh_token:
            logger.info("Refrescando access token...")
            creds.refresh(google.auth.transport.requests.Request())
            if creds.expiry and creds.expiry.tzinfo is not None:
                creds.expiry = creds.expiry.replace(tzinfo=None)
            _update_access_token_in_db(refresh_token, creds.token, creds.expiry.timestamp() if creds.expiry else 0)
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


# No longer using local SQLite db for tokens. We use backend.storage now.
from backend.storage import get_store
from backend.storage.models import GoogleTokenModel

def save_tokens(user_id: str, refresh_token: str, email: str = "", access_token: str = "", expires_at: float = 0):
    store = get_store()
    session = store.get_session()
    try:
        token_entry = session.query(GoogleTokenModel).filter(GoogleTokenModel.user_id == user_id).first()
        exp_dt = datetime.fromtimestamp(expires_at, timezone.utc) if expires_at else None
        if token_entry:
            token_entry.refresh_token = refresh_token
            token_entry.access_token = access_token
            token_entry.email = email
            token_entry.expires_at = exp_dt
        else:
            token_entry = GoogleTokenModel(
                user_id=user_id,
                refresh_token=refresh_token,
                access_token=access_token,
                email=email,
                expires_at=exp_dt
            )
            session.add(token_entry)
        session.commit()
    finally:
        session.close()


def _update_access_token_in_db(refresh_token: str, new_access_token: str, new_expires_at: float):
    store = get_store()
    session = store.get_session()
    try:
        token_entry = session.query(GoogleTokenModel).filter(GoogleTokenModel.refresh_token == refresh_token).first()
        if token_entry:
            token_entry.access_token = new_access_token
            token_entry.expires_at = datetime.fromtimestamp(new_expires_at, timezone.utc) if new_expires_at else None
            session.commit()
            logger.info("Access token actualizado en DB")
    finally:
        session.close()


def get_refresh_token(user_id: str) -> Optional[str]:
    store = get_store()
    session = store.get_session()
    try:
        token_entry = session.query(GoogleTokenModel).filter(GoogleTokenModel.user_id == user_id).first()
        return token_entry.refresh_token if token_entry else None
    finally:
        session.close()



def get_token_pair(user_id: str) -> tuple[str | None, str | None, float | None]:
    store = get_store()
    session = store.get_session()
    try:
        token_entry = session.query(GoogleTokenModel).filter(GoogleTokenModel.user_id == user_id).first()
        if token_entry:
            exp_float = token_entry.expires_at.timestamp() if token_entry.expires_at else None
            return token_entry.refresh_token, token_entry.access_token, exp_float
        return None, None, None
    finally:
        session.close()



def get_user_info(user_id: str) -> dict | None:
    store = get_store()
    session = store.get_session()
    try:
        token_entry = session.query(GoogleTokenModel).filter(GoogleTokenModel.user_id == user_id).first()
        if not token_entry:
            return None
        return {"email": token_entry.email or ""}
    finally:
        session.close()


def delete_token(user_id: str):
    store = get_store()
    session = store.get_session()
    try:
        token_entry = session.query(GoogleTokenModel).filter(GoogleTokenModel.user_id == user_id).first()
        if token_entry:
            session.delete(token_entry)
            session.commit()
    finally:
        session.close()
