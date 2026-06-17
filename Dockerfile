# Jarvis Backend Dockerfile (Railway production)
# Uses requirements.production.txt: pinned, slim, no local TTS/STT heavy deps.
FROM python:3.12-slim

WORKDIR /app

# System deps — minimal, only what's needed for wheel builds.
# No ffmpeg/libsndfile (TTS runs on the frontend via Web Speech API).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ---- Single source of truth: requirements.production.txt -----------------
# ~250MB installed (was ~840MB with requirements.railway.txt).
COPY requirements.production.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---- App code -------------------------------------------------------------
COPY backend/ ./backend/
COPY main.py knowledge_engine.py librarian.py sync_service.py alembic.ini ./
COPY web-next/public/models/brain.stl ./data/

# ---- Directories ----------------------------------------------------------
RUN mkdir -p /app/data/logs /app/data/voices /app/data/chroma_wiki \
             /app/data/chroma_db /app/data/sources /app/data/checkpoints

EXPOSE 8000

# Workers=1 OBLIGATORIO en free tier (512MB).
# timeout-keep-alive alto para WebSockets del chat.
CMD ["sh", "-c", "python -m uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 120 --workers 1"]
