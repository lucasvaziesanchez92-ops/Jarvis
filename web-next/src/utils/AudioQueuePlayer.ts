export class AudioQueuePlayer {
  private queue: string[] = [];
  public isPlaying = false;
  private onIdle?: () => void;
  private audioEl?: HTMLAudioElement;

  constructor(onIdle?: () => void, audioEl?: HTMLAudioElement) {
    this.onIdle = onIdle;
    if (typeof window !== 'undefined') {
      this.audioEl = audioEl || new Audio();
      this.audioEl.onended = () => {
        this.playNext();
      };
      this.audioEl.onerror = (e) => {
        console.error("Audio element error", e);
        this.playNext();
      };
    }
  }

  async resumeContext() {
    if (this.audioEl && this.audioEl.paused && !this.isPlaying) {
      try {
        // Reproducir un sonido en blanco para desbloquear el Autoplay Policy del navegador
        this.audioEl.src = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
        await this.audioEl.play();
      } catch (e) {
        // Se ignora, el intento ya cuenta como interacción para desbloquear
      }
    }
  }

  async queueAudioChunk(base64Data: string) {
    try {
      const binaryString = window.atob(base64Data);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Creamos un Blob de audio (soporta MP3 nativamente en todos los navegadores)
      const blob = new Blob([bytes], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(blob);
      
      this.queue.push(url);
      
      if (!this.isPlaying) {
        this.playNext();
      }
    } catch (e) {
      console.error("Error queueing audio chunk:", e);
    }
  }

  private playNext() {
    if (this.queue.length === 0 || !this.audioEl) {
      this.isPlaying = false;
      if (this.onIdle) this.onIdle();
      return;
    }

    this.isPlaying = true;
    const url = this.queue.shift()!;
    this.audioEl.src = url;
    this.audioEl.play().catch(e => {
      console.error("Audio play failed:", e);
      this.playNext();
    });
  }

  clearQueue() {
    this.queue = [];
    this.isPlaying = false;
    if (this.audioEl) {
      this.audioEl.pause();
      this.audioEl.src = '';
    }
  }
}

