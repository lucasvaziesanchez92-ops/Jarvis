"""TTS API Endpoint — /api/v1/tts

Recibe texto, devuelve audio WAV generado por Piper TTS.

Uso:
  POST /api/v1/tts
  {
    "text": "Hola, soy Jarvis",
    "voice_id": "es_ES-davefx-medium",
    "format": "wav",
    "emotion": "neutral",
    "speed": 1.0,
  }
  
  Response: audio/wav
"""

import io
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.services.tts_service import get_tts_service, TextToSpeechService

router = APIRouter(prefix="/tts", tags=["tts"])


# ── Models ────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Texto a sintetizar")
    voice_id: str = Field(default="es_ES-davefx-medium", description="ID de la voz")
    format: str = Field(default="wav", description="Formato de audio: wav, mp3, ogg")
    emotion: str = Field(default="neutral", description="Emoción: neutral, happy, excited, calm, sad")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Velocidad: 0.5-2.0")
    long_form: bool = Field(default=False, description="Si es texto largo, dividir en oraciones")


class TTSVoiceList(BaseModel):
    voices: list[dict]
    default_voice: str


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/synthesize")
async def tts_synthesize(request: TTSRequest):
    """Sintetiza texto a audio."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío")
    
    try:
        tts = TextToSpeechService(voice_id=request.voice_id)
        emotion_config = _map_emotion(request.emotion)
        length_scale = max(0.5, min(2.0, 2.0 - request.speed))
        
        if request.long_form:
            audio = tts.synthesize_long_text(
                request.text,
                length_scale=length_scale,
                noise_scale=emotion_config["noise_scale"],
            )
        else:
            audio = tts.synthesize(
                request.text,
                length_scale=length_scale,
                noise_scale=emotion_config["noise_scale"],
            )
        
        if request.format == "mp3":
            audio = _convert_to_mp3(audio)
        elif request.format == "ogg":
            audio = _convert_to_ogg(audio)
        
        content_type = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "ogg": "audio/ogg",
        }.get(request.format, "audio/wav")
        
        return Response(
            content=audio,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="tts_output.{request.format}"',
                "X-Generated-By": "jarvis-piper-tts",
                "X-Voice-ID": request.voice_id,
            },
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando audio: {str(e)}")


@router.post("/synthesize/stream")
async def tts_synthesize_stream(request: TTSRequest):
    """Sintetiza en streaming — el móvil empieza a reproducir antes
    de que termine la generación completa."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío")
    
    tts = TextToSpeechService(voice_id=request.voice_id)
    tts._init_voice()  # FIX: initialize voice before streaming
    
    async def audio_generator():
        import wave
        wav_buffer = io.BytesIO()
        wav_file = wave.open(wav_buffer, "wb")
        wav_file.setframerate(tts.sample_rate)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_buffer.seek(0)
        header = wav_buffer.read()
        yield header
        
        if tts._voice:
            for chunk in tts._voice.synthesize_stream_raw(request.text):
                yield chunk
        wav_file.close()
    
    return StreamingResponse(
        audio_generator(),
        media_type="audio/wav",
        headers={"X-Voice-ID": request.voice_id},
    )


@router.get("/voices")
async def tts_list_voices():
    """Lista todas las voces disponibles."""
    from backend.services.tts_service import VOICE_CATALOG
    
    voices = []
    for voice_id, info in VOICE_CATALOG.items():
        voices.append({
            "id": voice_id,
            "name": info["name"],
            "language": info["language"],
            "locale": info["locale"],
            "gender": info["gender"],
            "quality": info["quality"],
        })
    
    return TTSVoiceList(
        voices=voices,
        default_voice="es_ES-davefx-medium",
    )


@router.post("/voice/upload")
async def tts_upload_voice(request: Request):
    """Sube una muestra de voz para cloning."""
    import shutil
    body = await request.body()
    if len(body) < 1000:
        raise HTTPException(status_code=400, detail="Archivo de audio demasiado pequeño")
    
    from backend.services.tts_service import VOICES_DIR
    sample_path = VOICES_DIR / "user_voice_sample.wav"
    sample_path.write_bytes(body)
    
    tts = get_tts_service()
    tts.set_voice_reference(sample_path)
    
    return {
        "status": "ok",
        "message": "Muestra de voz subida correctamente.",
        "sample_path": str(sample_path),
        "sample_size": len(body),
    }


def _map_emotion(emotion: str) -> dict:
    emotion_map = {
        "neutral": {"noise_scale": 0.667, "length_scale": 1.0},
        "happy": {"noise_scale": 0.6, "length_scale": 0.95},
        "excited": {"noise_scale": 0.55, "length_scale": 0.85},
        "calm": {"noise_scale": 0.7, "length_scale": 1.15},
        "sad": {"noise_scale": 0.75, "length_scale": 1.3},
    }
    return emotion_map.get(emotion, emotion_map["neutral"])


def _convert_to_mp3(wav_bytes: bytes) -> bytes:
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        out = io.BytesIO()
        audio.export(out, format="mp3", bitrate="128k")
        return out.getvalue()
    except ImportError:
        return wav_bytes


def _convert_to_ogg(wav_bytes: bytes) -> bytes:
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        out = io.BytesIO()
        audio.export(out, format="ogg")
        return out.getvalue()
    except ImportError:
        return wav_bytes
