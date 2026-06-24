"""FastAPI application -- Jarvis backend (v2 with production improvements)."""
import os
# Fix ONNX/PyTorch memory spikes on Railway
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

os.environ['HF_HOME'] = os.path.join(os.getcwd(), 'data', 'hf_cache')
os.environ['XDG_CACHE_HOME'] = os.path.join(os.getcwd(), 'data', 'xdg_cache')
import warnings
from pathlib import Path
from contextlib import asynccontextmanager

# Suppress Pydantic V1 compatibility warnings (Python 3.14 + langchain v1)
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality", category=UserWarning)

# Memory tracing — log RSS at key import points to diagnose OOM kills
# on Railway free tier (512MB). Remove once stable.
def _rss_mb() -> float:
    import psutil
    return round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 1)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from loguru import logger
logger.info(f"[mem] after fastapi imports: {_rss_mb()} MB")

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
logger.info(f"[mem] after core imports: {_rss_mb()} MB")

# Routers: import with fallback. Heavy ones (TTS/STT) can be missing in
# slim Railway builds — we register them only if importable so a broken
# optional dep no longer kills the whole app at startup.
from backend.api.routers import (
    chat, notes, todos, calendar, email, threads, messages,
    diagnostics, search, personas, backup, auth, llm, voice, files,
    auth_google, gmail, drive, chat_smoke,
)
logger.info(f"[mem] after non-agent routers: {_rss_mb()} MB")
try:
    from backend.api.routers import agent  # langgraph graph build, heaviest
    _agent_available = True
    logger.info(f"[mem] after agent router: {_rss_mb()} MB")
except Exception as _e:
    logger.warning(f"agent router not loaded (skip): {_e}")
    agent = None
    _agent_available = False
try:
    from backend.api.routers import tts  # piper + onnxruntime, ~200MB
    _tts_available = True
except Exception as _e:
    logger.warning(f"tts router not loaded (skip): {_e}")
    tts = None
    _tts_available = False
try:
    from backend.api.routers import stt  # faster-whisper, ~300MB
    _stt_available = True
except Exception as _e:
    logger.warning(f"stt router not loaded (skip): {_e}")
    stt = None
    _stt_available = False

# Wiki router is loaded LAZILY (ChromaDB + sentence-transformers ~300MB)
# to keep Railway free tier (1GB RAM) under the OOM threshold.


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
    logger.info(f"[mem] startup: {_rss_mb()} MB")
    logger.info("=" * 60)

    # Enable LangSmith observability if configured
    if settings.enable_langsmith and settings.langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = "jarvis"
        logger.info("LangSmith observability enabled")

    # Build agent graph LAZILY (Railway 1GB OOMs on pre-warm with 36 tools).
    # The graph is built on first WS/agent request via get_jarvis_graph().
    logger.info("Graph build deferred to first request (memory: lazy)")

    # Wiki indexing deferred to first wiki_query call (was causing OOM by loading
    # 79MB embedding model at startup). See wiki_engine.py _get_collection() lazy init.
    logger.info("Wiki index deferred to first query (memory: lazy)")

    # Iniciar Cache Worker de LanceDB
    try:
        from backend.services.cache_worker import cache_worker
        import asyncio
        worker_task = asyncio.create_task(cache_worker.start())
        logger.info("Background Cache Worker started")
    except Exception as e:
        logger.error(f"Failed to start Cache Worker: {e}")

    # NO pre-warm de TTS: causa descargas múltiples (60MB) cuando Railway
    # spawns varios workers. Lazy-load on first voice request.

    yield

    # Shutdown
    logger.info("Jarvis API shutting down")
    try:
        cache_worker.stop()
        worker_task.cancel()
    except Exception:
        pass


# -- Application Factory --------------------------------------

app = FastAPI(
    title="Jarvis API",
    version="2.0.0",
    description="Personal AI assistant powered by LangGraph + Local LLM",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    redirect_slashes=False,
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
    _CORS_ORIGINS += ["http://localhost:3000", "http://localhost:3010", "http://localhost:3001", "http://localhost:8001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.railway\.app",
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
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        },
    )


# -- Health Checks ---------------------------------------------

@app.get("/api/v1/proxy-image")
async def proxy_image(url: str):
    """Proxy images to bypass hotlinking protection (403) from search engines."""
    import httpx
    from fastapi.responses import StreamingResponse
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                follow_redirects=True,
            )
            if resp.status_code == 200:
                return StreamingResponse(
                    iter([resp.content]),
                    media_type=resp.headers.get("content-type", "image/jpeg"),
                    headers={"Cache-Control": "public, max-age=86400"},
                )
            return JSONResponse(status_code=502, content={"error": f"Upstream returned {resp.status_code}"})
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.get("/api/v1/health")
async def health():
    """Basic health check."""
    import os
    import psutil
    proc = psutil.Process(os.getpid())
    mem = proc.memory_info()
    return {
        "status": "ok",
        "service": "jarvis",
        "version": "2.0.0",
        "optional_routers": {
            "tts": _tts_available,
            "stt": _stt_available,
        },
        "memory_mb": {
            "rss": round(mem.rss / 1024 / 1024, 1),
            "vms": round(mem.vms / 1024 / 1024, 1),
        },
        "pid": os.getpid(),
    }


@app.get("/api/v1/health/ready")
async def readiness_check():
    """Readiness check -- is the app ready to serve requests?"""
    checks = {}

    # Check database
    try:
        from backend.storage import get_store
        from sqlalchemy import text
        store = get_store()
        session = store.get_session()
        session.execute(text("SELECT 1"))
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
if agent is not None:
    app.include_router(agent.router, prefix="/api/v1", tags=["agent"])
app.include_router(diagnostics.router, prefix="/api/v1", tags=["diagnostics"])
app.include_router(chat_smoke.router, prefix="/api/v1", tags=["diagnostics"])
if tts is not None:
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
if stt is not None:
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

# Wiki / Obsidian Second Brain — register an opt-in endpoint to load
# ChromaDB only when the user actually visits the Wiki tab.
_wiki_loaded = False


@app.get("/api/v1/wiki/lazy_load", tags=["wiki"])
async def wiki_lazy_load():
    """Load the wiki router + ChromaDB on demand. Called when the user
    opens the Wiki tab. Keeps startup memory under 1GB on Railway free tier."""
    global _wiki_loaded
    if not _wiki_loaded:
        try:
            from backend.api.routers import wiki
            app.include_router(wiki.router, prefix="/api/v1", tags=["wiki"])
            _wiki_loaded = True
            return {"loaded": True, "message": "Wiki + ChromaDB ready"}
        except Exception as e:
            logger.warning(f"Wiki lazy-load failed: {e}")
            return {"loaded": False, "error": str(e)}
    return {"loaded": True, "message": "Already loaded"}


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

@app.get("/api/v1/proxy-image")
async def proxy_image(url: str):
    """Proxy for external images to bypass hotlink protection (DDG, Bing, etc).
    The tool buscar_imagenes_web generates /api/v1/proxy-image?url=... links.
    This endpoint fetches the image server-side and returns it to the browser."""
    import urllib.request
    import urllib.error
    from fastapi.responses import Response
    ALLOWED_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml")
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/webp,image/png,image/jpeg,*/*",
                "Referer": "https://duckduckgo.com/",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            if content_type not in ALLOWED_TYPES:
                content_type = "image/jpeg"
            data = resp.read()
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400", "Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        logger.warning(f"proxy-image failed for {url[:80]}: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail=f"Could not fetch image: {e}")


@app.get("/")
async def root_page():
    """API root -- frontend runs on port 3010."""
    return {"status": "ok", "service": "jarvis", "note": "Next.js frontend runs on port 3010"}
