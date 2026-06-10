"""
Groq Cloud TTS - lightweight cloud-based text-to-speech.

Uses Groq's playai-tts model. ~1-2s latency, no model download,
no on-prem compute. Much better than Piper for production (Piper
needs 200MB ONNX models + onnxruntime, breaks Railway free tier).

Falls back to a no-op if GROQ_API_KEY is not set.
"""
import os
import io
import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# Available PlayAI voices (English + Spanish)
PLAYAI_VOICES = [
    "Fritz-PlayAI",     # male, deep, confident
    "Caleb-PlayAI",     # male, deep
    "Arista-PlayAI",    # female, energetic
    "Celeste-PlayAI",   # female, warm
    "Cheyenne-PlayAI",  # female, confident
    "Clyde-PlayAI",     # male, warm
    "Indigo-PlayAI",    # female, calm
    "Maverick-PlayAI",  # male, energetic
    "Quinn-PlayAI",     # neutral, balanced
    "Ruby-PlayAI",      # female, expressive
    "Thunder-PlayAI",   # male, deep narrator
]

DEFAULT_VOICE = os.getenv("GROQ_TTS_VOICE", "Fritz-PlayAI")
DEFAULT_FORMAT = os.getenv("GROQ_TTS_FORMAT", "wav")
DEFAULT_SAMPLE_RATE = 48000


def is_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def _clean_text(text: str) -> str:
    """Strip emojis and weird characters that the TTS engine can't pronounce.
    Also collapse multiple spaces/newlines for a smoother voice."""
    # Drop emojis (basic range; if you need full coverage, use regex)
    text = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2700-\u27BF]+", "", text)
    # Markdown symbols that sound awful when spoken
    text = re.sub(r"[*_`#>|~]+", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Cap length (PlayAI accepts up to ~10K chars; cap at 4K for safety)
    if len(text) > 4000:
        text = text[:4000].rsplit(" ", 1)[0] + "..."
    return text


def synthesize(
    text: str,
    voice: Optional[str] = None,
    response_format: Optional[str] = None,
    sample_rate: Optional[int] = None,
) -> bytes:
    """Synthesize text to speech using Groq PlayAI TTS.

    Returns raw audio bytes (wav/mp3/ogg depending on response_format).
    Raises RuntimeError if the request fails.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY no configurada — no puedo sintetizar voz")

    voice = voice or DEFAULT_VOICE
    response_format = response_format or DEFAULT_FORMAT
    sample_rate = sample_rate or DEFAULT_SAMPLE_RATE

    if voice not in PLAYAI_VOICES:
        logger.warning(f"Voice {voice!r} not in known list, passing through to Groq anyway")

    clean = _clean_text(text)
    if not clean:
        raise RuntimeError("Texto vacío después de limpieza — nada que sintetizar")

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.audio.speech.create(
            model="playai-tts",
            voice=voice,
            input=clean,
            response_format=response_format,
            sample_rate=sample_rate,
        )
        # response.read() returns bytes; .write_to_file exists too
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
    """Return the catalog of available PlayAI voices."""
    return [
        {"id": v, "engine": "playai", "provider": "groq"}
        for v in PLAYAI_VOICES
    ]


def get_status() -> Dict[str, Any]:
    """Diagnostic: whether TTS is ready to use."""
    return {
        "engine": "groq-playai",
        "model": "playai-tts",
        "configured": is_configured(),
        "default_voice": DEFAULT_VOICE,
        "available_voices": len(PLAYAI_VOICES),
    }
