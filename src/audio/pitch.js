const MIN_FREQ = 35;
const MAX_FREQ = 1600;

export function detectPitch(buffer, sampleRate) {
  let sum = 0;
  for (let i = 0; i < buffer.length; i++) sum += buffer[i] * buffer[i];
  const rms = Math.sqrt(sum / buffer.length);
  if (rms < 0.0001) return { frequency: NaN, confidence: 0, rms };

  const minOffset = Math.max(1, Math.floor(sampleRate / MAX_FREQ));
  const maxOffset = Math.min(Math.floor(sampleRate / MIN_FREQ), buffer.length - 2);
  let bestOffset = -1;
  let bestCorrelation = -1;
  const correlations = new Float64Array(maxOffset + 1);

  for (let offset = minOffset; offset <= maxOffset; offset++) {
    let correlation = 0, normA = 0, normB = 0;
    const count = buffer.length - offset;
    for (let i = 0; i < count; i++) {
      const a = buffer[i], b = buffer[i + offset];
      correlation += a * b;
      normA += a * a;
      normB += b * b;
    }
    const denominator = Math.sqrt(normA * normB);
    if (!denominator) continue;
    correlation /= denominator;
    correlations[offset] = correlation;
    if (correlation > bestCorrelation) {
      bestCorrelation = correlation;
      bestOffset = offset;
    }
  }

  // Diagnostic only: expose the strongest distinct local correlation peaks.
  // Do not alter pitch selection yet; this lets us measure octave/subharmonic
  // failures before changing the detector.
  const peaks = [];
  for (let offset = minOffset + 1; offset < maxOffset; offset++) {
    const value = correlations[offset];
    if (value < 0.3 || value < correlations[offset - 1] || value < correlations[offset + 1]) continue;
    peaks.push({
      offset,
      frequency: sampleRate / offset,
      midi: Math.round(69 + 12 * Math.log2((sampleRate / offset) / 440)),
      confidence: value
    });
  }
  peaks.sort((a, b) => b.confidence - a.confidence);
  const candidates = [];
  for (const peak of peaks) {
    if (candidates.some(x => Math.abs(x.midi - peak.midi) < 1)) continue;
    candidates.push(peak);
    if (candidates.length === 5) break;
  }

  if (bestOffset <= 0 || bestCorrelation < 0.3) {
    return { frequency: NaN, confidence: Math.max(0, bestCorrelation), rms, candidates };
  }
  return {
    frequency: sampleRate / bestOffset,
    confidence: bestCorrelation,
    rms,
    candidates
  };
}

export function frequencyToMidiFloat(frequency) {
  return 69 + 12 * Math.log2(frequency / 440);
}

export function frequencyToMidi(frequency) {
  return Math.round(frequencyToMidiFloat(frequency));
}
