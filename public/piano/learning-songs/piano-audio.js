/** A small, offline piano-like Web Audio instrument. No autoplay or MIDI output. */
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
  // Optional long-hold attenuation; other notes keep their original envelope.
  note(midi, duration = .35, when = this.time, velocity = .65, softenAfterSeconds = null) {
    if (!this.context || this.context.state !== 'running' || !this.enabled) return;
    const start = this.context.currentTime + Math.max(0, when - this.time);
    const length = Math.max(.04, duration);
    const frequency = 440 * Math.pow(2, (midi - 69) / 12);
    const level = Math.max(.01, Math.min(1, velocity));
    // A piano string is struck, then its brighter partials decay more quickly
    // than its fundamental. Slightly stretched harmonics mimic string stiffness.
    // Four sines avoid the steady triangle-wave/organ quality of the old tone.
    const partials = [
      {multiple: 1, amplitude: .38, decay: 1.8},
      {multiple: 2, amplitude: .20, decay: .65},
      {multiple: 3, amplitude: .085, decay: .24},
      {multiple: 4, amplitude: .045, decay: .085},
    ];
    const oscillators = [];
    const gains = [];
    const release = .15;
    const end = start + length + release;
    const soften = Number.isFinite(softenAfterSeconds)
      && softenAfterSeconds >= 0 && softenAfterSeconds < length;
    const sustainGain = soften ? this.context.createGain() : null;
    if (sustainGain) {
      // Keep the old tone untouched until the threshold, then settle at 60%
      // over 25 ms to avoid a sudden discontinuity in the waveform.
      const fadeTime = start + softenAfterSeconds;
      if (softenAfterSeconds === 0) {
        // A resumed note may already be beyond four beats.
        sustainGain.gain.setValueAtTime(.6, start);
      } else {
        const fadeEnd = Math.min(start + length, fadeTime + .025);
        sustainGain.gain.setValueAtTime(1, start);
        sustainGain.gain.setValueAtTime(1, fadeTime);
        sustainGain.gain.linearRampToValueAtTime(.6, fadeEnd);
      }
      sustainGain.connect(this.master);
    }
    for (const {multiple, amplitude, decay} of partials) {
      const oscillator = this.context.createOscillator();
      const gain = this.context.createGain();
      oscillator.type = 'sine';
      oscillator.frequency.value = multiple === 1 ? frequency
        : frequency * multiple * Math.sqrt(1 + .00012 * multiple * multiple);
      oscillator.connect(gain);
      gain.connect(sustainGain || this.master);
      const peak = Math.max(.0002, level * amplitude);
      const held = Math.max(.0001, peak * Math.exp(-length / decay));
      gain.gain.setValueAtTime(.0001, start);
      gain.gain.exponentialRampToValueAtTime(peak, start + .004);
      gain.gain.exponentialRampToValueAtTime(held, start + length);
      gain.gain.exponentialRampToValueAtTime(.0001, end);
      oscillators.push(oscillator);
      gains.push(gain);
    }
    const voice = {oscillators, gains, sustainGain};
    this.voices.add(voice);
    oscillators[0].onended = () => {
      this.voices.delete(voice);
      for (const oscillator of oscillators) oscillator.disconnect();
      for (const gain of gains) gain.disconnect();
      sustainGain?.disconnect();
    };
    for (const oscillator of oscillators) {
      oscillator.start(start);
      oscillator.stop(end + .01);
    }
  }
  stopAll() {
    for (const voice of this.voices) {
      for (const gain of voice.gains) {
        gain.gain.cancelScheduledValues(this.context.currentTime);
        gain.gain.setValueAtTime(0, this.context.currentTime);
      }
      for (const oscillator of voice.oscillators) {
        try { oscillator.stop(); } catch (_) {}
      }
      voice.sustainGain?.disconnect();
    }
    this.voices.clear();
  }
}
