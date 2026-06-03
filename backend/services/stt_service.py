"""Speech-to-Text service using OpenAI Whisper."""
import io
import os
from typing import Optional

model = None


def _get_model():
    global model
    if model is None:
        try:
            import whisper
            model_name = os.getenv("WHISPER_MODEL", "base")
            model = whisper.load_model(model_name)
        except ImportError:
            raise ImportError(
                "whisper not installed. Run: pip install openai-whisper"
            )
    return model


def transcribe_audio(
    audio_data: bytes,
    language: Optional[str] = "es",
    task: str = "transcribe",
) -> dict:
    """
    Transcribe audio bytes to text using Whisper.

    Args:
        audio_data: Raw audio bytes (WAV, MP3, OGG, etc.)
        language: Language code (ISO 639-1, e.g., "es", "en")
        task: "transcribe" or "translate" (es → en)

    Returns:
        {"text": str, "language": str, "duration": float, "segments": list}
    """
    try:
        import numpy as np
        import wave

        audio_np = _bytes_to_audio_array(audio_data)
        wmodel = _get_model()

        result = wmodel.transcribe(
            audio_np,
            language=language,
            task=task,
            fp16=False,
        )

        return {
            "text": result["text"].strip(),
            "language": result.get("language", language),
            "duration": result.get("duration", 0.0),
            "segments": [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                }
                for seg in result.get("segments", [])
            ],
        }

    except Exception as e:
        raise RuntimeError(f"Whisper transcription failed: {e}")


def transcribe_from_file(
    file_path: str,
    language: Optional[str] = "es",
) -> dict:
    """Transcribe from a saved audio file."""
    with open(file_path, "rb") as f:
        audio_data = f.read()
    return transcribe_audio(audio_data, language=language)


def _bytes_to_audio_array(audio_bytes: bytes):
    """Convert audio bytes to numpy array for Whisper."""
    import numpy as np
    import wave

    try:
        wav_buffer = io.BytesIO(audio_bytes)
        with wave.open(wav_buffer, "rb") as wav:
            sample_rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
            audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            audio_np = audio_np / 32768.0

        return audio_np

    except wave.BadWaveFile:
        raise ValueError("Audio must be WAV format or convert to WAV first")


def check_whisper_model() -> dict:
    """Check if Whisper model is loaded and available."""
    try:
        model_name = os.getenv("WHISPER_MODEL", "base")
        wmodel = _get_model()
        return {
            "status": "loaded",
            "model": model_name,
            "sample_rate": 16000,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }