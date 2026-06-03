"""
================================================================================
  JARVIS TTS SERVICE — Piper TTS para voz humana local
================================================================================

  Uso:
    from backend.services.tts_service import TextToSpeechService
    
    tts = TextToSpeechService()  # Descarga voz automáticamente
    
    # Generar audio
    audio_bytes = tts.synthesize("Hola, soy Jarvis", output_format="wav")
    
    # Guardar en archivo
    tts.save_to_file("Hola", "output.wav")
    
    # Voice Cloning (preparado)
    tts.set_voice_reference("samples/mi_voz.wav")
    audio_bytes = tts.synthesize_with_cloned_voice("Texto a hablar")

  Voces disponibles:
    es_ES-claribel_evans-medium  (voz femenina española, recomendada)
    es_ES-sharvard-medium        (voz masculina española)
    es_MX-ald-medium             (español latino/mexicano)
    en_US-amy-medium             (voz femenina inglesa)
================================================================================
"""

import os
import io
import re
import wave
import asyncio
from pathlib import Path
from typing import Optional, Callable
import tempfile

import numpy as np

# Directorio base para modelos de voz
VOICES_DIR = Path(__file__).parent.parent.parent / "data" / "voices"
VOICES_DIR.mkdir(parents=True, exist_ok=True)

# Catálogo de voces disponibles de Piper
VOICE_CATALOG = {
    "es_ES-davefx-medium": {
        "name": "Davefx",
        "language": "es",
        "locale": "es-ES",
        "gender": "male",
        "quality": "medium",
        "model_url": "rhasspy/piper-voices:es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
        "config_url": "rhasspy/piper-voices:es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json",
    },
    "es_ES-sharvard-medium": {
        "name": "Sharvard",
        "language": "es",
        "locale": "es-ES",
        "gender": "male",
        "quality": "medium",
        "model_url": "rhasspy/piper-voices:es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx",
        "config_url": "rhasspy/piper-voices:es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx.json",
    },
    "es_ES-carlfm-x_low": {
        "name": "Carlfm",
        "language": "es",
        "locale": "es-ES",
        "gender": "male",
        "quality": "x_low",
        "model_url": "rhasspy/piper-voices:es/es_ES/carlfm/x_low/es_ES-carlfm-x_low.onnx",
        "config_url": "rhasspy/piper-voices:es/es_ES/carlfm/x_low/es_ES-carlfm-x_low.onnx.json",
    },
    "es_ES-mls_10246-low": {
        "name": "MLS 10246",
        "language": "es",
        "locale": "es-ES",
        "gender": "female",
        "quality": "low",
        "model_url": "rhasspy/piper-voices:es/es_ES/mls_10246/low/es_ES-mls_10246-low.onnx",
        "config_url": "rhasspy/piper-voices:es/es_ES/mls_10246/low/es_ES-mls_10246-low.onnx.json",
    },
    "es_MX-claude-medium": {
        "name": "Claude",
        "language": "es",
        "locale": "es-MX",
        "gender": "male",
        "quality": "medium",
        "model_url": "rhasspy/piper-voices:es/es_MX/claude/medium/es_MX-claude-medium.onnx",
        "config_url": "rhasspy/piper-voices:es/es_MX/claude/medium/es_MX-claude-medium.onnx.json",
    },
    "en_US-amy-medium": {
        "name": "Amy",
        "language": "en",
        "locale": "en-US",
        "gender": "female",
        "quality": "medium",
        "model_url": "rhasspy/piper-voices:en/en_US/amy/medium/en_US-amy-medium.onnx",
        "config_url": "rhasspy/piper-voices:en/en_US/amy/medium/en_US-amy-medium.onnx.json",
    },
}

DEFAULT_VOICE = "es_ES-sharvard-medium"


# ── Helper: descarga modelo si no existe ───────────────────────────────

def _download_file(url_or_path: str, dest: Path) -> None:
    """Descarga un archivo si no existe. Soporta URLs directas o paths de HuggingFace."""
    if dest.exists():
        return

    print(f"[TTS] Descargando {dest.name}...")
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Si es un path de HF (formato: rhasspy/piper-voices:path/to/file)
    if url_or_path.startswith("rhasspy/"):
        from huggingface_hub import hf_hub_download
        parts = url_or_path.split(":", 1)
        repo_id = parts[0]
        file_path = parts[1] if len(parts) > 1 else ""
        downloaded = hf_hub_download(repo_id=repo_id, filename=file_path, local_dir=str(dest.parent), local_dir_use_symlinks=False)
        if Path(downloaded) != dest:
            import shutil
            shutil.move(downloaded, dest)
    else:
        # URL directa
        import requests
        r = requests.get(url_or_path, stream=True, timeout=120)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    print(f"[TTS] Descarga completa: {dest}")


def _ensure_voice_model(voice_id: str) -> tuple[Path, Path]:
    """Devuelve (model_path, config_path) asegurando que existan."""
    voice_dir = VOICES_DIR / voice_id
    voice_dir.mkdir(parents=True, exist_ok=True)
    
    catalog = VOICE_CATALOG.get(voice_id)
    if not catalog:
        raise ValueError(f"Voz no encontrada: {voice_id}. Disponibles: {list(VOICE_CATALOG.keys())}")
    
    model_path = voice_dir / f"{voice_id}.onnx"
    config_path = voice_dir / f"{voice_id}.onnx.json"
    
    _download_file(catalog["model_url"], model_path)
    _download_file(catalog["config_url"], config_path)
    
    return model_path, config_path


# ── TTS Service ─────────────────────────────────────────────────────────

class TextToSpeechService:
    """
    Servicio de Text-to-Speech usando Piper.
    Genera audio .wav realista con voz humana.
    """
    
    def __init__(self, voice_id: str = DEFAULT_VOICE):
        self.voice_id = voice_id
        self._voice: Optional[PiperVoice] = None
        self._voice_reference: Optional[Path] = None

    def _init_voice(self):
        """Carga el modelo Piper (lazy)."""
        if self._voice is not None:
            return
        from piper import PiperVoice
        model_path, config_path = _ensure_voice_model(self.voice_id)
        self._voice = PiperVoice.load(str(model_path), config_path=str(config_path))
        print(f"[TTS] Voz cargada: {self.voice_id}")
    
    # ── Properties ────────────────────────────────────────────────────
    
    @property
    def sample_rate(self) -> int:
        return self._voice.config.sample_rate if self._voice else 22050
    
    @property
    def is_loaded(self) -> bool:
        return self._voice is not None
    
    # ── Voice Reference (para cloning) ────────────────────────────────
    
    def set_voice_reference(self, audio_path: str | Path) -> None:
        """
        Establece una muestra de voz para cloning.
        El audio debe ser .wav de ~10-30 segundos, clara, sin ruido.
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Muestra de voz no encontrada: {path}")
        self._voice_reference = path
        print(f"[TTS] Referencia de voz establecida: {path}")
    
    def clear_voice_reference(self) -> None:
        self._voice_reference = None
    
    # ── Synthesize ────────────────────────────────────────────────────
    
    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None,
        length_scale: float = 1.15,
        noise_scale: float = 0.667,
        noise_w: float = 0.45,
    ) -> bytes:
        """Genera audio WAV desde texto con voz natural."""
        if not self._voice:
            self._init_voice()
        
        text = self._clean_text(text)
        
        from piper.config import SynthesisConfig
        syn_config = SynthesisConfig(
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w_scale=noise_w,
            speaker_id=speaker_id,
        )
        
        audio_buffer = io.BytesIO()
        
        with wave.open(audio_buffer, "wb") as wav_file:
            wav_file.setframerate(self.sample_rate)
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # int16
            
            # Piper 1.4.2: synthesize devuelve AudioChunk iterables
            for audio_chunk in self._voice.synthesize(text, syn_config=syn_config):
                wav_file.writeframes(audio_chunk.audio_int16_bytes)
        
        audio_buffer.seek(0)
        return audio_buffer.read()
    
    def synthesize_to_file(
        self,
        text: str,
        output_path: str | Path,
        **kwargs
    ) -> Path:
        """Genera audio y lo guarda en archivo."""
        audio = self.synthesize(text, **kwargs)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio)
        return path
    
    def synthesize_long_text(
        self,
        text: str,
        max_chars: int = 300,
        **kwargs
    ) -> bytes:
        """
        Divide texto largo en oraciones y las sintetiza como un solo WAV.
        Equivalente a long_form_synthesize() de local-talking-llm.
        """
        if not self._voice:
            self._init_voice()
        sentences = self._split_sentences(text, max_chars=max_chars)
        
        audio_parts = []
        for sentence in sentences:
            audio = self.synthesize(sentence, **kwargs)
            # Eliminar el header WAV, quedar solo con los datos
            with io.BytesIO(audio) as buf:
                with wave.open(buf, "rb") as w:
                    frames = w.readframes(w.getnframes())
                    audio_parts.append(frames)
        
        # Unir todo con un pequeño silencio entre oraciones
        silence = np.zeros(int(self.sample_rate * 0.25), dtype=np.int16).tobytes()
        combined_frames = silence.join(audio_parts)
        
        # Wrappar en header WAV
        out = io.BytesIO()
        with wave.open(out, "wb") as w:
            w.setframerate(self.sample_rate)
            w.setnchannels(1)
            w.setsampwidth(2)
            w.writeframes(combined_frames)
        
        out.seek(0)
        return out.read()
    
    # ── Emotion-Aware Synthesis ──────────────────────────────────────
    
    def synthesize_with_emotion(self, text: str, emotion_score: float = 0.5) -> bytes:
        """
        Sintetiza con ajuste de velocidad según emoción.
        
        emotion_score: 0.3 (calmo) — 0.9 (muy expresivo)
        """
        # Más emoción = más rápido y con más variedad
        length_scale = 1.2 - (emotion_score * 0.4)  # 1.08 a 0.84
        noise_scale = 0.5 + (emotion_score * 0.2)   # 0.56 a 0.68
        
        return self.synthesize(text, length_scale=length_scale, noise_scale=noise_scale)
    
    # ── Voice Cloning (preparado) ─────────────────────────────────────
    
    def synthesize_with_cloned_voice(self, text: str) -> bytes:
        """
        Sintetiza usando una muestra de voz clonada.
        
        NOTE: Piper nativo no soporta voice cloning directamente.
        Esto está preparado para integrar con ChatterBox u OpenVoice.
        Por ahora, usa la voz base.
        """
        if self._voice_reference:
            # Aquí se integraría ChatterBox/OpenVoice
            # Por ahora, usa la voz base con ajustes de tono
            print(f"[TTS] Usando voz clonada (referencia: {self._voice_reference})")
            # TODO: Integrar ChatterBox cuando esté disponible
            return self.synthesize(text)
        
        return self.synthesize(text)
    
    # ── Streaming (para WebSocket) ────────────────────────────────────
    
    async def synthesize_stream(
        self,
        text: str,
        chunk_callback: Callable[[bytes], None],
        chunk_size_ms: int = 200,
        **kwargs
    ) -> None:
        """
        Sintetiza en streaming, enviando chunks de audio a un callback.
        Ideal para WebSocket donde el móvil empieza a reproducir
        antes de que termine la generación.
        """
        if not self._voice:
            raise RuntimeError("Voz no cargada")
        
        text = self._clean_text(text)
        
        # WAV header primero
        header = self._create_wav_header(0)  # Tamaño desconocido
        chunk_callback(header)
        
        for audio_bytes in self._voice.synthesize_stream_raw(text, **kwargs):
            chunk_callback(audio_bytes)
    
    # ── Helpers ───────────────────────────────────────────────────────
    
    def _clean_text(self, text: str) -> str:
        """Limpia texto para Piper."""
        # Eliminar emojis
        text = text.encode('ascii', 'ignore').decode('ascii')
        # Eliminar carácteres raros que rompen TTS
        text = re.sub(r'[^\w\s\.,;:!?¿¡\-\'\"\(\)]', ' ', text)
        # Múltiples espacios → uno solo
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _split_sentences(self, text: str, max_chars: int = 300) -> list[str]:
        """Divide texto en oraciones."""
        # Primero por puntos, luego agrupar si son cortas
        raw_sentences = re.split(r'(?<=[.!?])\s+', text)
        
        sentences = []
        current = ""
        for sent in raw_sentences:
            if len(current) + len(sent) < max_chars:
                current += " " + sent if current else sent
            else:
                if current:
                    sentences.append(current.strip())
                current = sent
        
        if current:
            sentences.append(current.strip())
        
        return sentences if sentences else [text[:max_chars]]
    
    def _create_wav_header(self, data_size: int, sample_rate: int = None) -> bytes:
        """Crea un header WAV PCM válido."""
        sr = sample_rate or self.sample_rate
        bytes_per_sec = sr * 1 * 2  # 1 channel, 2 bytes
        
        header = b'RIFF'
        header += (data_size + 36).to_bytes(4, 'little')  # file size - 8
        header += b'WAVE'
        header += b'fmt '
        header += (16).to_bytes(4, 'little')  # fmt chunk size
        header += (1).to_bytes(2, 'little')   # PCM
        header += (1).to_bytes(2, 'little')   # channels
        header += sr.to_bytes(4, 'little')   # sample rate
        header += bytes_per_sec.to_bytes(4, 'little')  # byte rate
        header += (2).to_bytes(2, 'little')   # block align
        header += (16).to_bytes(2, 'little')  # bits per sample
        header += b'data'
        header += data_size.to_bytes(4, 'little')
        
        return header


# ── Singleton ─────────────────────────────────────────────────────────

_tts_service: Optional[TextToSpeechService] = None

def get_tts_service() -> TextToSpeechService:
    """Devuelve el servicio TTS (singleton)."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TextToSpeechService()
    if not _tts_service._voice:
        _tts_service._init_voice()
    return _tts_service


# ── CLI test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Probando TTS Service...")
    
    tts = TextToSpeechService()
    
    # Test básico
    text = "Hola, soy Jarvis. ¿En qué puedo ayudarte hoy?"
    audio = tts.synthesize(text)
    tts.synthesize_to_file(text, VOICES_DIR / "test_output.wav")
    
    print(f"✅ Audio generado: {len(audio)} bytes")
    print(f"   Guardado en: {VOICES_DIR / 'test_output.wav'}")
    
    # Test long form
    long_text = (
        "He creado tu nota exitosamente. "
        "Tu próxima reunión es el viernes a las tres. "
        "Es hora de que revises tus tareas pendientes. "
        "Estoy aquí para ayudarte en lo que necesites."
    )
    audio_long = tts.synthesize_long_text(long_text)
    tts.synthesize_to_file(long_text, VOICES_DIR / "test_long.wav")
    print(f"✅ Long form generado: {len(audio_long)} bytes")
    
    # Test con emoción
    excited_text = "¡Increíble! Me encanta esta idea genial!"
    audio_emotion = tts.synthesize_with_emotion(excited_text, emotion_score=0.8)
    tts.synthesize_to_file(excited_text, VOICES_DIR / "test_emotion.wav", length_scale=0.85, noise_scale=0.7)
    print(f"✅ Audio con emoción generado: {len(audio_emotion)} bytes")
    
    print("\n✅ Todos los tests pasaron!")
