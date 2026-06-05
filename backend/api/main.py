"""FastAPI application -- Jarvis backend (v2 with production improvements)."""
import os
import warnings
from pathlib import Path
from contextlib import asynccontextmanager

# Suppress Pydantic V1 compatibility warnings (Python 3.14 + langchain v1)
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality", category=UserWarning)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from loguru import logger

from backend.config import settings
from backend.core.logging import setup_logging
from backend.core.middleware import RequestIDMiddleware, RequestResponseLoggingMiddleware
from backend.core.exceptions import (
    validation_exception_handler,
    pydantic_validation_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    AppError,
    app_error_handler,
)
from backend.core.rate_limiter import limiter
from backend.api.routers import chat, notes, todos, calendar, email, threads, messages, agent, diagnostics, search, tts, personas, backup, stt, auth, llm, voice, files, auth_google, gmail, drive, wiki


# -- Initialize Structured Logging -------------------------------
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("=" * 60)
    logger.info("Jarvis API starting up")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Data Directory: {settings.data_dir}")
    logger.info(f"LangSmith: {'enabled' if settings.enable_langsmith else 'disabled'}")
    logger.info("=" * 60)

    # Enable LangSmith observability if configured
    if settings.enable_langsmith and settings.langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = "jarvis"
        logger.info("LangSmith observability enabled")

    # Build agent graph synchronously at startup (Railway healthcheck waits up to 120s)
    import threading
    def _warm_graph():
        try:
            from backend.api.dependencies import build_graph
            build_graph()
        except Exception as e:
            logger.warning(f"Graph pre-build failed: {e}")
    threading.Thread(target=_warm_graph, daemon=True).start()
    logger.info("Agent graph pre-building in background...")

    # Pre-download TTS model in background — skips if low memory (< 400MB free)
    import psutil
    def _warm_tts():
        try:
            mem = psutil.virtual_memory()
            if mem.available < 400 * 1024 * 1024:
                logger.info(f"TTS pre-warm skipped: only {mem.available // 1024 // 1024}MB available")
                return
            from backend.services.tts_service import TextToSpeechService
            svc = TextToSpeechService()
            svc._init_voice()
            logger.info("TTS model pre-warmed successfully")
        except Exception as e:
            logger.warning(f"TTS pre-warm failed (ok, loads on first request): {e}")
    threading.Thread(target=_warm_tts, daemon=True).start()

    yield

    # Shutdown
    logger.info("Jarvis API shutting down")


# -- Application Factory --------------------------------------

app = FastAPI(
    title="Jarvis API",
    version="2.0.0",
    description="Personal AI assistant powered by LangGraph + Local LLM",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

# -- Middleware Stack (order matters: last added = first executed) ---

# 1. Response compression (GZip for responses > 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. CORS — allow both Railway frontend domains + local dev
_CORS_ORIGINS = [
    "https://frontend-production-6465.up.railway.app",
    "https://front-end-production.up.railway.app",
]
if os.getenv("NODE_ENV") != "production":
    _CORS_ORIGINS += ["http://localhost:3010", "http://localhost:3001", "http://localhost:8001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Request ID tracing
app.add_middleware(RequestIDMiddleware)

# 4. Request/Response logging
app.add_middleware(RequestResponseLoggingMiddleware)

# -- Exception Handlers ---------------------------------------
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Monkey-patch for HTTPException (FastAPI internal)
from fastapi import HTTPException
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(AppError, app_error_handler)

# -- Rate Limiter State ----------------------------------------
app.state.limiter = limiter

# Rate limit exceeded handler
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "type": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": int(exc.detail.retry_after) if hasattr(exc.detail, 'retry_after') else 60,
            }
        },
    )

from backend.services.google_auth import GoogleNotConfiguredError

@app.exception_handler(GoogleNotConfiguredError)
async def google_not_configured_handler(request: Request, exc: GoogleNotConfiguredError):
    return JSONResponse(
        status_code=503,
        content={"error": {"type": "google_not_configured", "message": str(exc)}},
    )


# -- Health Checks ---------------------------------------------

@app.get("/api/v1/health")
async def health():
    """Basic health check."""
    return {"status": "ok", "service": "jarvis", "version": "2.0.0"}


@app.get("/api/v1/health/ready")
async def readiness_check():
    """Readiness check -- is the app ready to serve requests?"""
    checks = {}

    # Check database
    try:
        from backend.storage.sqlite_store import get_store
        store = get_store()
        session = store.get_session()
        session.execute("SELECT 1")
        session.close()
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    # Check LLM provider
    try:
        from backend.llm import get_llm
        llm = get_llm()
        checks["llm_provider"] = f"{settings.llm_provider} (loaded)"
    except Exception as e:
        checks["llm_provider"] = f"unhealthy: {str(e)}"

    # Check circuit breakers
    from backend.core.resilience import get_circuit_breaker_states
    checks["circuit_breakers"] = get_circuit_breaker_states()

    all_healthy = all(v == "healthy" or "loaded" in str(v) for v in checks.values())

    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
    }


@app.get("/api/v1/health/live")
async def liveness_check():
    """Liveness check -- is the process alive?"""
    return {"status": "alive"}


# -- API v1 Routes -------------------------------------------

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(agent.router, prefix="/api/v1", tags=["agent"])
app.include_router(diagnostics.router, prefix="/api/v1", tags=["diagnostics"])
app.include_router(tts.router, prefix="/api/v1", tags=["tts"])
app.include_router(llm.router, prefix="/api/v1", tags=["llm"])
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])
app.include_router(todos.router, prefix="/api/v1/todos", tags=["todos"])
app.include_router(calendar.router, prefix="/api/v1/calendar", tags=["calendar"])
app.include_router(email.router, prefix="/api/v1/emails", tags=["email"])
app.include_router(threads.router, prefix="/api/v1/threads", tags=["threads"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(personas.router, prefix="/api/v1", tags=["personas"])
app.include_router(backup.router, prefix="/api/v1", tags=["backup"])
app.include_router(stt.router, prefix="/api/v1", tags=["stt"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])

# File storage (Railway Object Storage bucket)
app.include_router(files.router, prefix="/api/v1", tags=["files"])

# Google OAuth + Services (Gmail, Drive, Calendar)
app.include_router(auth_google.router, prefix="/auth", tags=["google-auth"])
app.include_router(gmail.router, prefix="/api/v1", tags=["gmail"])
app.include_router(drive.router, prefix="/api/v1", tags=["drive"])
# Calendar ya existe como router separado

# Wiki / Obsidian Second Brain
app.include_router(wiki.router, prefix="/api/v1", tags=["wiki"])


# -- Legacy Routes (backward compatibility) --------------------

app.include_router(chat.router, tags=["chat (legacy)"])
app.include_router(agent.router, tags=["agent (legacy)"])
app.include_router(diagnostics.router, tags=["diagnostics (legacy)"])
app.include_router(notes.router, prefix="/notes", tags=["notes (legacy)"])
app.include_router(todos.router, prefix="/todos", tags=["todos (legacy)"])
app.include_router(calendar.router, prefix="/calendar", tags=["calendar (legacy)"])
app.include_router(email.router, prefix="/emails", tags=["email (legacy)"])
app.include_router(threads.router, prefix="/threads", tags=["threads (legacy)"])
app.include_router(messages.router, prefix="/messages", tags=["messages (legacy)"])

# Legacy health endpoint
@app.get("/health")
async def health_legacy():
    return {"status": "ok", "service": "jarvis"}


@app.get("/api/v1/health")
async def health_v1():
    return {"status": "ok", "service": "jarvis"}


from fastapi.responses import RedirectResponse, FileResponse
from backend.api.dependencies import get_jarvis_graph

# -- Brain STL served from backend (Nixpacks no copia public/) --
_brain_stl = Path(__file__).parent.parent.parent / "data" / "brain.stl"
_brain_html = Path(__file__).parent.parent.parent / "web-next" / "public" / "brain.html"

@app.get("/brain.stl")
async def brain_stl():
    if _brain_stl.exists():
        return FileResponse(str(_brain_stl), media_type="application/octet-stream")
    return {"status": "error", "detail": "brain.stl not found"}

@app.get("/brain")
async def brain_page():
    """Serve the neural brain standalone page if available."""
    if _brain_html.exists():
        return FileResponse(str(_brain_html))
    return {"status": "ok", "service": "jarvis", "note": "Brain page not built"}

@app.get("/")
async def root_page():
    """API root -- frontend runs on port 3010."""
    return {"status": "ok", "service": "jarvis", "note": "Next.js frontend runs on port 3010"}
