"""Google OAuth router — login, callback, status."""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from loguru import logger

from backend.services.google_auth import (
    GoogleAuthService, GoogleNotConfiguredError,
    save_tokens, get_refresh_token, get_user_info, delete_token,
    _get_client_config,
)

router = APIRouter(prefix="/google", tags=["google"])


def _get_redirect_uri(request: Request) -> str:
    host = request.headers.get("host", "localhost:8001")
    scheme = "https" if "up.railway.app" in host else "http"
    return f"{scheme}://{host}/auth/google/callback"


@router.get("/login")
async def google_login(request: Request):
    svc = GoogleAuthService(redirect_uri=_get_redirect_uri(request))
    url, state = svc.get_auth_url()
    return RedirectResponse(url=url)


@router.get("/callback")
async def google_callback(code: str = Query(...), state: str = Query(None), request: Request = None):
    svc = GoogleAuthService(redirect_uri=_get_redirect_uri(request) if request else "https://backend-production-cabf.up.railway.app/auth/google/callback")
    try:
        tokens = svc.exchange_code(code, state=state)
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth failed: {e}")

    user_id = "default_user"
    email = tokens.get("email", "")
    save_tokens(user_id, tokens["refresh_token"], email)
    logger.info(f"Google OAuth connected for {email}")

    frontend_url = "https://frontend-production-6465.up.railway.app"
    if request and "localhost" in str(request.url):
        frontend_url = "http://localhost:3010"
    return RedirectResponse(url=frontend_url)


@router.get("/status")
async def google_status():
    token = get_refresh_token("default_user")
    if not token:
        return {"connected": False}
    user = get_user_info("default_user")
    return {"connected": True, "email": user.get("email", "") if user else ""}


@router.post("/disconnect")
async def google_disconnect():
    delete_token("default_user")
    return {"connected": False}


@router.get("/debug-config")
async def debug_config():
    """Diagnostic: shows what config the server is using RIGHT NOW.
    Redacts the client_secret but shows its length, prefix, and suffix
    so you can compare with what Google has on file."""
    import os
    cfg = _get_client_config()
    if not cfg:
        return {
            "configured": False,
            "reason": "No client_id/client_secret loaded from file or env vars",
            "client_id_env_set": bool(os.getenv("GOOGLE_CLIENT_ID")),
            "client_secret_env_set": bool(os.getenv("GOOGLE_CLIENT_SECRET")),
        }
    secret = cfg.get("client_secret", "")
    return {
        "configured": True,
        "client_id": cfg.get("client_id"),
        "client_id_matches_known": cfg.get("client_id") == "215682122179-8h57u5ctvbgtot79jasa27hnilrvbhl5.apps.googleusercontent.com",
        "client_secret_length": len(secret),
        "client_secret_prefix": secret[:10] if secret else "",
        "client_secret_suffix": secret[-6:] if secret else "",
        "auth_uri": cfg.get("auth_uri"),
        "token_uri": cfg.get("token_uri"),
    }
