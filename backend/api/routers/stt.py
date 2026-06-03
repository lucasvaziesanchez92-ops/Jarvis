"""STT API Endpoint — /api/v1/stt

Recibe audio, devuelve texto transcrito usando Whisper.

Uso:
  POST /api/v1/stt/transcribe
  Content-Type: audio/wav (o multipart/form-data)
  {
    "language": "es",
    "task": "transcribe",  // or "translate"
  }

  Response: { "text": str, "language": str, "duration": float }
"""
import io

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.services.stt_service import transcribe_audio, check_whisper_model

router = APIRouter(prefix="/stt", tags=["stt"])


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration: float
    segments: list[dict]


@router.post("/transcribe", response_model=TranscribeResponse)
async def stt_transcribe(
    audio: UploadFile = File(...),
    language: str = Form(default="es"),
    task: str = Form(default="transcribe"),
):
    """
    Transcribe audio to text using OpenAI Whisper.
    Accepts WAV, MP3, OGG audio formats.
    """
    if audio.content_type not in [
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/ogg",
        "audio/webm",
        "application/octet-stream",
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {audio.content_type}. Use WAV, MP3, or OGG.",
        )

    try:
        audio_bytes = await audio.read()

        if len(audio_bytes) < 1000:
            raise HTTPException(status_code=400, detail="Audio file too small")

        if len(audio_bytes) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio file too large (max 50MB)")

        result = transcribe_audio(
            audio_data=audio_bytes,
            language=language if language else "es",
            task=task if task in ("transcribe", "translate") else "transcribe",
        )

        return TranscribeResponse(
            text=result["text"],
            language=result["language"],
            duration=result["duration"],
            segments=result["segments"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/transcribe/direct")
async def stt_transcribe_direct(body: dict):
    """
    Transcribe from base64-encoded audio bytes.

    Body:
      {
        "audio_b64": "base64-encoded-audio...",
        "language": "es",
        "task": "transcribe"
      }
    """
    import base64

    audio_b64 = body.get("audio_b64")
    if not audio_b64:
        raise HTTPException(status_code=400, detail="audio_b64 required")

    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    language = body.get("language", "es")
    task = body.get("task", "transcribe")

    try:
        result = transcribe_audio(
            audio_data=audio_bytes,
            language=language,
            task=task,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def stt_status():
    """Check STT service status and Whisper model availability."""
    return check_whisper_model()


@router.get("/voices")
async def stt_voices():
    """List supported languages for transcription."""
    return {
        "languages": [
            {"code": "es", "name": "Spanish", "flag": "🇪🇸"},
            {"code": "en", "name": "English", "flag": "🇺🇸"},
            {"code": "fr", "name": "French", "flag": "🇫🇷"},
            {"code": "de", "name": "German", "flag": "🇩🇪"},
            {"code": "pt", "name": "Portuguese", "flag": "🇵🇹"},
            {"code": "it", "name": "Italian", "flag": "🇮🇹"},
        ],
        "models": ["tiny", "base", "small", "medium", "large"],
        "default_model": "base",
    }