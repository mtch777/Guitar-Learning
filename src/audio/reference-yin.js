// Paired live trial implementation of the validated 22,050 Hz YIN decision.
// Keep this opt-in until live confidence and latency are measured.
const TARGET_RATE = 22050;

export function resampleLinear(input, inputRate) {
  if (inputRate === TARGET_RATE) return Float32Array.from(input);
  const length = Math.round(input.length * TARGET_RATE / inputRate);
  const output = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const position = i * inputRate / TARGET_RATE;
    const left = Math.min(input.length - 1, Math.floor(position));
    const right = Math.min(input.length - 1, left + 1);
    output[i] = input[left] + (input[right] - input[left]) * (position - left);
  }
  return output;
}

export function referenceYin(input, sampleRate) {
  const y = resampleLinear(input, sampleRate);
  const sr = TARGET_RATE;
  if (!y.length) return { frequency: NaN, confidence: 0 };
  const n = 4096, hop = 1024, minP = Math.floor(sr / 1600);
  const maxP = Math.min(Math.ceil(sr / 35), n - 1);
  const frequencies = [], confidences = [];
  for (let start = 0; start <= y.length; start += hop) {
    const frame = new Float64Array(n);
    for (let t = 0; t < n; t++) {
      const i = start + t - (n >> 1);
      if (i >= 0 && i < y.length) frame[t] = y[i];
    }
    let energy = 0;
    for (const v of frame) energy += v * v;
    const cm = new Float64Array(maxP + 1);
    let head = 0, run = 0;
    for (let lag = 1; lag <= maxP; lag++) {
      head += frame[lag - 1] * frame[lag - 1];
      let acf = 0;
      for (let t = 0; t < n - lag; t++) acf += frame[t] * frame[t + lag];
      const difference = 2 * (energy - acf) - head;
      run += difference;
      cm[lag] = difference * lag / (run + Number.MIN_VALUE);
    }
    let best = minP;
    for (let lag = minP + 1; lag <= maxP; lag++) if (cm[lag] < cm[best]) best = lag;
    let selected = best;
    for (let lag = minP; lag <= maxP; lag++) {
      const trough = lag === minP ? cm[lag] < cm[lag + 1]
        : lag === maxP ? cm[lag] < cm[lag - 1]
          : cm[lag] < cm[lag - 1] && cm[lag] <= cm[lag + 1];
      if (trough && cm[lag] < 0.1) { selected = lag; break; }
    }
    let shift = 0;
    if (selected > minP && selected < maxP) {
      const a = cm[selected + 1] + cm[selected - 1] - 2 * cm[selected];
      const b = (cm[selected + 1] - cm[selected - 1]) / 2;
      if (Math.abs(b) < Math.abs(a)) shift = -b / a;
    }
    frequencies.push(sr / (selected + shift));
    confidences.push(Math.max(0, Math.min(1, 1 - cm[selected])));
  }
  frequencies.sort((a, b) => a - b);
  confidences.sort((a, b) => a - b);
  const mid = Math.floor(frequencies.length / 2);
  const median = a => a.length % 2 ? a[mid] : (a[mid - 1] + a[mid]) / 2;
  return { frequency: median(frequencies), confidence: median(confidences) };
}
