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
    if (correlation > bestCorrelation) {
      bestCorrelation = correlation;
      bestOffset = offset;
    }
  }

  if (bestOffset <= 0 || bestCorrelation < 0.3) {
    return { frequency: NaN, confidence: Math.max(0, bestCorrelation), rms };
  }
  return { frequency: sampleRate / bestOffset, confidence: bestCorrelation, rms };
}

export function frequencyToMidiFloat(frequency) {
  return 69 + 12 * Math.log2(frequency / 440);
}

export function frequencyToMidi(frequency) {
  return Math.round(frequencyToMidiFloat(frequency));
}
