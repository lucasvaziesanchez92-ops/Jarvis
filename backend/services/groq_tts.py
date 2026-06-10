"""
Groq Cloud TTS - lightweight cloud-based text-to-speech.

Uses Groq's Canopy Labs Orpheus model (English) or playai-tts
(deprecated, may still work). ~1-2s latency, no model download,
no on-prem compute. Much better than Piper for production (Piper
needs 200MB ONNX models + onnxruntime, breaks Railway free tier).

Falls back to a no-op if GROQ_API_KEY is not set.

NOTE: playai-tts was deprecated 2025-12-31. Orpheus v1 (English
only) is the recommended replacement. For Spanish TTS, the user
should integrate ElevenLabs or open-source eSpeak-ng on the client.
"""
import os
import io
import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# Canopy Labs Orpheus v1 voices (English). Recommended replacement
# for the deprecated playai-tts.
ORPHEUS_VOICES = [
    "tara",   # female, warm
    "leah",   # female, balanced
    "jess",   # female, energetic
    "leo",    # male, warm
    "dan",    # male, balanced
    "mia",    # female, expressive
    "zac",    # male, deep
    "zoe",    # female, calm
]

# Default model + voice
DEFAULT_MODEL = "canopylabs/orpheus-v1-english"
DEFAULT_VOICE = os.getenv("GROQ_TTS_VOICE", "tara")
DEFAULT_FORMAT = os.getenv("GROQ_TTS_FORMAT", "wav")
DEFAULT_SAMPLE_RATE = 24000  # Orpheus native rate


def is_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def _clean_text(text: str) -> str:
    """Strip emojis and weird characters that the TTS engine can't pronounce.
    Also collapse multiple spaces/newlines for a smoother voice."""
    text = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2700-\u27BF]+", "", text)
    text = re.sub(r"[*_`#>|~]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 4000:
        text = text[:4000].rsplit(" ", 1)[0] + "..."
    return text


def synthesize(
    text: str,
    voice: Optional[str] = None,
    response_format: Optional[str] = None,
    sample_rate: Optional[int] = None,
    model: Optional[str] = None,
) -> bytes:
    """Synthesize text to speech using Groq Orpheus TTS.

    Returns raw audio bytes (wav by default).
    Raises RuntimeError if the request fails.

    Note: Orpheus v1 is English-only. For Spanish, the synthesis
    will still go through but the voice sounds accented. Best UX
    is to fall back to browser's Web Speech API (free, native) for
    non-English languages.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY no configurada — no puedo sintetizar voz")

    voice = voice or DEFAULT_VOICE
    response_format = response_format or DEFAULT_FORMAT
    sample_rate = sample_rate or DEFAULT_SAMPLE_RATE
    model = model or DEFAULT_MODEL

    clean = _clean_text(text)
    if not clean:
        raise RuntimeError("Texto vacío después de limpieza — nada que sintetizar")

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=clean,
            response_format=response_format,
            sample_rate=sample_rate,
        )
        return response.read()
    except Exception as e:
        logger.exception(f"Groq TTS failed: {e}")
        raise RuntimeError(f"Error en Groq TTS: {type(e).__name__}: {str(e)[:200]}")


def synthesize_to_file(
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    response_format: Optional[str] = None,
) -> str:
    """Synthesize text to a file. Returns the output path."""
    audio = synthesize(text, voice=voice, response_format=response_format)
    with open(output_path, "wb") as f:
        f.write(audio)
    return output_path


def list_voices() -> List[Dict[str, Any]]:
    """Return the catalog of available Orpheus voices."""
    return [
        {"id": v, "engine": "orpheus", "provider": "groq", "language": "en"}
        for v in ORPHEUS_VOICES
    ]


def get_status() -> Dict[str, Any]:
    """Diagnostic: whether TTS is ready to use."""
    return {
        "engine": "groq-orpheus",
        "model": DEFAULT_MODEL,
        "configured": is_configured(),
        "default_voice": DEFAULT_VOICE,
        "available_voices": len(ORPHEUS_VOICES),
        "note": "English only. For Spanish TTS, use browser Web Speech API.",
    }
