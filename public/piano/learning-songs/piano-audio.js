/** A small local Web Audio instrument. No autoplay, sample download or MIDI output. */
export class PianoAudio {
  constructor() { this.context = null; this.master = null; this.voices = new Set(); this.enabled = true; }
  async unlock() {
    const AudioContext = globalThis.AudioContext || globalThis.webkitAudioContext;
    if (!AudioContext) throw new Error('Audio playback is unavailable in this browser. You can still practice silently.');
    if (!this.context) {
      this.context = new AudioContext({latencyHint:'interactive'});
      this.master = this.context.createGain();
      this.master.gain.value = this.enabled ? 0.32 : 0;
      const compressor = this.context.createDynamicsCompressor();
      this.master.connect(compressor);
      compressor.connect(this.context.destination);
    }
    if (this.context.state !== 'running') await this.context.resume();
  }
  setEnabled(enabled) {
    this.enabled = !!enabled;
    if (this.master) this.master.gain.setTargetAtTime(this.enabled ? 0.32 : 0, this.context.currentTime, .015);
    if (!this.enabled) this.stopAll();
  }
  // A denied/suspended audio device must not freeze the lesson's clock.
  get time() { return performance.now() / 1000; }
  note(midi, duration = .35, when = this.time, velocity = .65) {
    if (!this.context || this.context.state !== 'running' || !this.enabled) return;
    const start = this.context.currentTime + Math.max(0, when - this.time);
    const length = Math.max(.04, duration);
    const gain = this.context.createGain();
    const frequency = 440 * Math.pow(2, (midi - 69) / 12);
    const fundamental = this.context.createOscillator();
    const overtone = this.context.createOscillator();
    fundamental.type = 'triangle'; fundamental.frequency.value = frequency;
    overtone.type = 'sine'; overtone.frequency.value = frequency * 2;
    const harmonicGain = this.context.createGain(); harmonicGain.gain.value = .11;
    fundamental.connect(gain); overtone.connect(harmonicGain); harmonicGain.connect(gain); gain.connect(this.master);
    const level = Math.max(.01, Math.min(1, velocity)) * .33;
    gain.gain.setValueAtTime(.0001, start);
    gain.gain.exponentialRampToValueAtTime(level, start + .008);
    gain.gain.exponentialRampToValueAtTime(Math.max(.0002, level * .35), start + Math.min(.3, length * .8));
    gain.gain.exponentialRampToValueAtTime(.0001, start + length + .12);
    const voice = {fundamental, overtone, gain, harmonicGain};
    this.voices.add(voice);
    fundamental.onended = () => {
      this.voices.delete(voice);
      fundamental.disconnect(); overtone.disconnect(); harmonicGain.disconnect(); gain.disconnect();
    };
    fundamental.start(start); overtone.start(start);
    fundamental.stop(start + length + .14); overtone.stop(start + length + .14);
  }
  stopAll() {
    for (const voice of this.voices) {
      try { voice.gain.gain.cancelScheduledValues(this.context.currentTime); voice.gain.gain.setValueAtTime(0, this.context.currentTime); voice.fundamental.stop(); voice.overtone.stop(); } catch (_) {}
    }
    this.voices.clear();
  }
}
