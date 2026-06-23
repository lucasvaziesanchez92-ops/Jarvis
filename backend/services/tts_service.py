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
        """Sintetiza texto usando Piper TTS si esta instalado, sino usa gTTS."""
        logger.info(f"Sintetizando: {text[:50]}...")
        if not text.strip():
            return b""
            
        # Intentar con Piper primero (Rápido y Local)
        try:
            from backend.config import settings
            import os
            
            if os.path.exists(settings.piper_model_path):
                if getattr(self, '_piper_voice', None) is None:
                    from piper.voice import PiperVoice
                    logger.info(f"Cargando modelo Piper desde {settings.piper_model_path}")
                    self._piper_voice = PiperVoice.load(settings.piper_model_path)
                
                # Sintetizar con Piper
                audio_parts = []
                for chunk in self._piper_voice.synthesize(text):
                    audio_parts.append(chunk.audio_int16_bytes)
                
                combined_frames = b"".join(audio_parts)
                
                if output_format == "wav":
                    # Crear WAV header
                    sr = self._piper_voice.config.sample_rate
                    bytes_per_sec = sr * 1 * 2
                    data_size = len(combined_frames)
                    header = b'RIFF' + (data_size + 36).to_bytes(4, 'little') + b'WAVEfmt ' + (16).to_bytes(4, 'little') + (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little') + sr.to_bytes(4, 'little') + bytes_per_sec.to_bytes(4, 'little') + (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little') + b'data' + data_size.to_bytes(4, 'little')
                    return header + combined_frames
                
                return combined_frames # PCM crudo si no es wav
        except Exception as e:
            logger.warning(f"Piper TTS falló, intentando gTTS como fallback. Error: {e}")

        # Fallback a gTTS
        try:
            from gtts import gTTS
            logger.info(f"[gTTS] Fallback para: {text[:50]}...")
            tts = gTTS(text=text, lang="es", tld="es")
            
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            audio_data = fp.getvalue()
            
            if output_format == "wav":
                try:
                    from pydub import AudioSegment
                    fp.seek(0)
                    sound = AudioSegment.from_file(fp, format="mp3")
                    out_fp = io.BytesIO()
                    sound.export(out_fp, format="wav")
                    return out_fp.getvalue()
                except ImportError:
                    logger.warning("pydub no instalado, devolviendo mp3 directamente.")
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
