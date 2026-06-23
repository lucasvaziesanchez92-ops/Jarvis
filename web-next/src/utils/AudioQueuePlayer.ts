export class AudioQueuePlayer {
  private audioCtx: AudioContext | null = null;
  private queue: AudioBuffer[] = [];
  public isPlaying = false;
  private nextStartTime = 0;
  private onIdle?: () => void;

  constructor(onIdle?: () => void) {
    this.onIdle = onIdle;
    if (typeof window !== 'undefined') {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
      }
    }
  }

  async resumeContext() {
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      try {
        await this.audioCtx.resume();
      } catch (e) {
        console.error("Failed to resume AudioContext", e);
      }
    }
  }

  async queueAudioChunk(base64Data: string) {
    if (!this.audioCtx) return;

    if (this.audioCtx.state === 'suspended') {
      await this.audioCtx.resume();
    }

    try {
      const binaryString = window.atob(base64Data);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const audioBuffer = await this.audioCtx.decodeAudioData(bytes.buffer);
      this.queue.push(audioBuffer);
      
      if (!this.isPlaying) {
        this.playNext();
      }
    } catch (e) {
      console.error("Error decodificando el fragmento de audio stream:", e);
    }
  }

  private playNext() {
    if (this.queue.length === 0 || !this.audioCtx) {
      this.isPlaying = false;
      if (this.onIdle) this.onIdle();
      return;
    }

    this.isPlaying = true;
    const buffer = this.queue.shift()!;
    const source = this.audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioCtx.destination);

    const currentTime = this.audioCtx.currentTime;
    
    if (this.nextStartTime < currentTime) {
      this.nextStartTime = currentTime;
    }

    source.start(this.nextStartTime);
    this.nextStartTime += buffer.duration;
    
    source.onended = () => {
      this.playNext();
    };
  }

  clearQueue() {
    this.queue = [];
    this.isPlaying = false;
    this.nextStartTime = 0;
  }
}
