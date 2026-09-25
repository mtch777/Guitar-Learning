/**
 * Buffers exactly one ringing pluck for the full classifier.
 *
 * A completed capture does not immediately re-arm.  The input must fall below
 * releaseDbfs first, preventing one decaying note from being classified over
 * and over as multiple plucks.
 */
export class RingingPluckBuffer {
  constructor({
    minDbfs = -48,
    releaseDbfs = -54,
    captureSeconds = 0.82,
    releaseFrames = 2
  } = {}) {
    this.minDbfs = minDbfs;
    this.releaseDbfs = releaseDbfs;
    this.captureSeconds = captureSeconds;
    this.releaseFrames = releaseFrames;
    this.reset();
  }

  reset() {
    this.active = false;
    this.armed = true;
    this.releaseCount = 0;
    this.sampleRate = null;
    this.chunks = [];
    this.length = 0;
    this.midiVotes = new Map();
    this.bestPitchConfidence = 0;
  }

  clearCapture() {
    this.active = false;
    this.sampleRate = null;
    this.chunks = [];
    this.length = 0;
    this.midiVotes = new Map();
    this.bestPitchConfidence = 0;
  }

  getDiagnostics() {
    return {
      active: this.active,
      armed: this.armed,
      releaseCount: this.releaseCount,
      minDbfs: this.minDbfs,
      releaseDbfs: this.releaseDbfs,
      captureSeconds: this.captureSeconds,
      capturedSamples: this.length,
      sampleRate: this.sampleRate
    };
  }

  push(frame) {
    if (!frame?.samples?.length || !frame.sampleRate) return null;

    if (!this.armed) {
      if (frame.dbfs <= this.releaseDbfs) {
        this.releaseCount++;
        if (this.releaseCount >= this.releaseFrames) {
          this.armed = true;
          this.releaseCount = 0;
        }
      } else {
        this.releaseCount = 0;
      }
      return null;
    }

    if (!this.active) {
      if (
        frame.midi == null ||
        frame.pitchConfidence < 0.55 ||
        frame.dbfs < this.minDbfs
      ) return null;

      this.active = true;
      this.sampleRate = frame.sampleRate;
    }

    if (frame.sampleRate !== this.sampleRate) {
      this.clearCapture();
      return null;
    }

    this.chunks.push(new Float32Array(frame.samples));
    this.length += frame.samples.length;

    if (frame.midi != null && frame.pitchConfidence >= 0.55) {
      const weight = Math.max(0, frame.pitchConfidence);
      this.midiVotes.set(frame.midi, (this.midiVotes.get(frame.midi) || 0) + weight);
      this.bestPitchConfidence = Math.max(this.bestPitchConfidence, frame.pitchConfidence);
    }

    if (this.length < Math.ceil(this.captureSeconds * this.sampleRate)) return null;

    let midi = null;
    let best = -Infinity;
    for (const [candidate, weight] of this.midiVotes) {
      if (weight > best) {
        best = weight;
        midi = candidate;
      }
    }

    const samples = new Float32Array(this.length);
    let offset = 0;
    for (const chunk of this.chunks) {
      samples.set(chunk, offset);
      offset += chunk.length;
    }

    const result = {
      samples,
      sampleRate: this.sampleRate,
      midi,
      pitchConfidence: this.bestPitchConfidence
    };

    this.clearCapture();
    this.armed = false;
    this.releaseCount = 0;
    return result;
  }
}
