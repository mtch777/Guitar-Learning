/**
 * Buffers one pluck long enough for the full ringing-only classifier.
 *
 * Training extractor uses:
 *   attack: 0.00–0.12 s
 *   sustain: 0.15–0.80 s
 * so live inference must retain at least 0.80 s from the detected onset.
 *
 * This module does NOT classify muted articulations; the production model is
 * intentionally ringing-only.
 */
export class RingingPluckBuffer {
  constructor({ minDbfs = -48, releaseDbfs = -54, captureSeconds = 0.82 } = {}) {
    this.minDbfs = minDbfs;
    this.releaseDbfs = releaseDbfs;
    this.captureSeconds = captureSeconds;
    this.reset();
  }

  reset() {
    this.active = false;
    this.sampleRate = null;
    this.chunks = [];
    this.length = 0;
    this.midiVotes = new Map();
    this.bestPitchConfidence = 0;
  }

  push(frame) {
    if (!frame?.samples?.length || !frame.sampleRate) return null;

    if (!this.active) {
      if (frame.midi == null || frame.pitchConfidence < 0.55 || frame.dbfs < this.minDbfs) {
        return null;
      }
      this.active = true;
      this.sampleRate = frame.sampleRate;
    }

    // Ignore sample-rate changes inside one capture.
    if (frame.sampleRate !== this.sampleRate) {
      this.reset();
      return null;
    }

    this.chunks.push(new Float32Array(frame.samples));
    this.length += frame.samples.length;

    if (frame.midi != null && frame.pitchConfidence >= 0.55) {
      const weight = Math.max(0, frame.pitchConfidence);
      this.midiVotes.set(frame.midi, (this.midiVotes.get(frame.midi) || 0) + weight);
      this.bestPitchConfidence = Math.max(this.bestPitchConfidence, frame.pitchConfidence);
    }

    const enough = this.length >= Math.ceil(this.captureSeconds * this.sampleRate);
    if (!enough) return null;

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
    this.reset();
    return result;
  }
}
