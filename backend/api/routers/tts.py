"""TTS API Endpoint — /api/v1/tts

Recibe texto, devuelve audio generado por Groq Canopy Labs Orpheus TTS.

Uso:
  POST /api/v1/tts
  {
    "text": "Hola, soy Jarvis",
    "voice_id": "tara",
    "format": "wav"
  }

  Response: audio/wav

Voice catalog: tara, leah, jess, leo, dan, mia, zac, zoe (English only).
Orpheus v1 doesn't support Spanish; for es-ES, use browser Web Speech API.
"""
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/tts", tags=["tts"])


# ── Models ────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Texto a sintetizar")
    voice_id: str = Field(default="tara", description="ID de la voz Orpheus (tara/leah/jess/leo/dan/mia/zac/zoe)")
    format: str = Field(default="wav", description="Formato de audio: wav, mp3")
    speed: float = Field(default=1.0, ge=0.5, le=5.0, description="Velocidad: 0.5-5.0")


class TTSVoiceList(BaseModel):
    voces: list[dict]
    default_voice: str
    engine: str


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/status")
async def tts_status():
    """Diagnostic: whether TTS is configured and ready."""
    from backend.services.groq_tts import get_status
    return get_status()


@router.get("/voices", response_model=TTSVoiceList)
async def list_voices():
    """List all available Orpheus voices (English)."""
    from backend.services.groq_tts import list_voices, DEFAULT_VOICE
    return TTSVoiceList(
        voces=list_voices(),
        default_voice=DEFAULT_VOICE,
        engine="groq-orpheus",
    )


@router.post("/synthesize")
async def tts_synthesize(request: TTSRequest):
    """Sintetiza texto a audio via Groq Orpheus TTS. Devuelve audio crudo."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacio")

    from backend.services import groq_tts

    if not groq_tts.is_configured():
        raise HTTPException(
            status_code=503,
            detail="TTS no configurado: GROQ_API_KEY no esta en las variables de entorno de Railway.",
        )

    try:
        audio = groq_tts.synthesize(
            text=request.text,
            voice=request.voice_id,
            response_format=request.format,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    content_types = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
        "mulaw": "audio/basic",
    }
    media_type = content_types.get(request.format, "audio/wav")

    return Response(
        content=audio,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="jarvis_tts_{request.voice_id}.{request.format}"',
            "X-Voice-ID": request.voice_id,
            "X-Audio-Format": request.format,
        },
    )


@router.post("/synthesize/stream")
async def tts_synthesize_stream(request: TTSRequest):
    return await tts_synthesize(request)


@router.post("/voice/upload")
async def tts_upload_voice(request):
    raise HTTPException(
        status_code=501,
        detail="Voice cloning no esta soportado en Orpheus TTS.",
    )
