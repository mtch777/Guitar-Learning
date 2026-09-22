import { detectPitch, frequencyToMidi } from "./pitch.js";

export class GuitarMicrophone {
  constructor({ fftSize = 4096, onFrame = () => {} } = {}) {
    this.fftSize = fftSize;
    this.onFrame = onFrame;
    this.context = null;
    this.stream = null;
    this.source = null;
    this.processor = null;
    this.silentGain = null;
  }

  async start() {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) throw new Error("Web Audio API unavailable");

    this.context ||= new AudioContextClass();
    if (this.context.state === "suspended") await this.context.resume();

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false
      },
      video: false
    });

    this.source = this.context.createMediaStreamSource(this.stream);
    this.processor = this.context.createScriptProcessor(this.fftSize, 1, 1);
    this.silentGain = this.context.createGain();
    this.silentGain.gain.value = 0;

    this.source.connect(this.processor);
    this.processor.connect(this.silentGain);
    this.silentGain.connect(this.context.destination);

    this.processor.onaudioprocess = event => {
      const input = event.inputBuffer.getChannelData(0);
      const samples = new Float32Array(input);
      const pitch = detectPitch(samples, this.context.sampleRate);

      let peak = 0;
      for (const sample of samples) peak = Math.max(peak, Math.abs(sample));
      const dbfs = pitch.rms > 0 ? 20 * Math.log10(pitch.rms) : -Infinity;

      this.onFrame({
        samples,
        sampleRate: this.context.sampleRate,
        frequency: pitch.frequency,
        midi: Number.isFinite(pitch.frequency) ? frequencyToMidi(pitch.frequency) : null,
        pitchConfidence: pitch.confidence,
        rms: pitch.rms,
        peak,
        dbfs
      });
    };

    return { sampleRate: this.context.sampleRate };
  }

  stop() {
    if (this.processor) this.processor.onaudioprocess = null;
    for (const track of this.stream?.getTracks?.() || []) track.stop();
    this.source?.disconnect();
    this.processor?.disconnect();
    this.silentGain?.disconnect();
    this.stream = this.source = this.processor = this.silentGain = null;
  }
}
