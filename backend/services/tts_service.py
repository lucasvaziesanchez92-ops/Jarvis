"""
================================================================================
  JARVIS TTS SERVICE — Cloud TTS (gTTS Fallback)
================================================================================

  Uso:
    from backend.services.tts_service import TextToSpeechService
    
    tts = TextToSpeechService()
    
    # Generar audio
    audio_bytes = tts.synthesize("Hola, soy Jarvis", output_format="wav")
================================================================================
"""

import io
from loguru import logger
import traceback

class TextToSpeechService:
    def __init__(self):
        self._voice_cloning_ref = None

    def _init_voice(self):
        """No-op. Se inicializa dinamicamente."""
        pass

    def synthesize(self, text: str, output_format: str = "wav", speed: float = 1.0) -> bytes:
        """Sintetiza texto usando gTTS (requiere conexion a internet, pero no binarios locales)."""
        logger.info(f"[gTTS] Sintetizando: {text[:50]}...")
        if not text.strip():
            return b""
            
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang="es", tld="es")
            
            # gTTS genera mp3 internamente.
            # Convertimos el mp3 a wav en memoria si output_format es wav (el frontend espera webm o wav base64).
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            audio_data = fp.getvalue()
            
            if output_format == "wav":
                # Convert MP3 to WAV using pydub if available, otherwise just return the mp3 data 
                # (browsers like Chrome/Safari can usually play mp3 data via base64 audio tags directly).
                try:
                    from pydub import AudioSegment
                    fp.seek(0)
                    sound = AudioSegment.from_file(fp, format="mp3")
                    out_fp = io.BytesIO()
                    sound.export(out_fp, format="wav")
                    return out_fp.getvalue()
                except ImportError:
                    logger.warning("pydub no instalado, devolviendo mp3 directamente aunque se pidio wav.")
                    return audio_data
                except Exception as e:
                    logger.warning(f"Fallo pydub conversion: {e}")
                    return audio_data
            
            return audio_data
            
        except Exception as e:
            logger.error(f"[gTTS] Error sintetizando voz: {e}")
            traceback.print_exc()
            return b""

    def save_to_file(self, text: str, filepath: str, speed: float = 1.0) -> bool:
        """Sintetiza y guarda a disco."""
        data = self.synthesize(text, output_format="wav", speed=speed)
        if not data:
            return False
        with open(filepath, "wb") as f:
            f.write(data)
        return True

    def set_voice_reference(self, reference_audio_path: str):
        self._voice_cloning_ref = reference_audio_path

    def synthesize_with_cloned_voice(self, text: str, output_format: str = "wav") -> bytes:
        return self.synthesize(text, output_format)
