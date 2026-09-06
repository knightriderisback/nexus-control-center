// Sci-Fi Tactical Sound Synthesizer via Web Audio API (Zero external assets required)

class SoundEngine {
  private ctx: AudioContext | null = null;
  public enabled: boolean = false; // default off until user opts in or clicks toggle

  constructor() {
    // AudioContext will be initialized on first user interaction
  }

  private initCtx() {
    if (!this.ctx && typeof window !== 'undefined') {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioContextClass) {
        this.ctx = new AudioContextClass();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  public toggle(): boolean {
    this.enabled = !this.enabled;
    if (this.enabled) {
      this.initCtx();
      this.beep(880, 0.08, 'sine');
    }
    return this.enabled;
  }

  public click() {
    if (!this.enabled) return;
    this.initCtx();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'triangle';
    osc.frequency.setValueAtTime(1400, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(400, this.ctx.currentTime + 0.03);

    gain.gain.setValueAtTime(0.06, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.03);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start();
    osc.stop(this.ctx.currentTime + 0.03);
  }

  public beep(freq = 750, duration = 0.08, type: OscillatorType = 'sine') {
    if (!this.enabled) return;
    this.initCtx();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(freq, this.ctx.currentTime);

    gain.gain.setValueAtTime(0.05, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start();
    osc.stop(this.ctx.currentTime + duration);
  }

  public success() {
    if (!this.enabled) return;
    this.beep(587.33, 0.08, 'sine'); // D5
    setTimeout(() => {
      this.beep(880, 0.12, 'sine'); // A5
    }, 60);
  }

  public alert() {
    if (!this.enabled) return;
    this.beep(330, 0.15, 'sawtooth');
    setTimeout(() => {
      this.beep(280, 0.2, 'sawtooth');
    }, 120);
  }

  public panic() {
    if (!this.enabled) return;
    this.initCtx();
    if (!this.ctx) return;
    
    for (let i = 0; i < 3; i++) {
      setTimeout(() => {
        this.beep(220 + i * 40, 0.12, 'square');
      }, i * 100);
    }
  }
}

export const sound = new SoundEngine();
