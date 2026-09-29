// 107 pitch-relative harmonic features in train_full_ringing.harmonic_features order.
// Input must already be librosa-equivalent trimmed mono audio at 22,050 Hz.
function spectrum(segment) {
  const n = Math.max(8192, 2 ** Math.ceil(Math.log2(Math.max(256, segment.length))));
  const re = new Float64Array(n), im = new Float64Array(n);
  for (let i = 0; i < segment.length; i++) {
    const w = segment.length <= 1 ? 1 : .5 - .5 * Math.cos(2 * Math.PI * i / (segment.length - 1));
    re[i] = segment[i] * w;
  }
  let j = 0;
  for (let i = 1; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const angle = -2 * Math.PI / len, cr = Math.cos(angle), ci = Math.sin(angle);
    for (let start = 0; start < n; start += len) {
      let wr = 1, wi = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = start + k, b = a + len / 2;
        const tr = wr * re[b] - wi * im[b], ti = wr * im[b] + wi * re[b];
        re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
        const next = wr * cr - wi * ci; wi = wr * ci + wi * cr; wr = next;
      }
    }
  }
  return Float64Array.from({ length: n / 2 + 1 }, (_, i) => Math.hypot(re[i], im[i]));
}
function median(values) {
  if (!values.length) return 1e-12;
  values.sort((a, b) => a - b);
  const middle = values.length >> 1;
  return values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
}
export function harmonicFusionFeatures(y, sampleRate, midi) {
  const f0 = 440 * 2 ** ((midi - 69) / 12), regions = [[0, .12], [.15, .40], [.40, .80]];
  const result = [], ratios = [];
  for (const [a, b] of regions) {
    let seg = y.slice(Math.floor(a * sampleRate), Math.min(y.length, Math.floor(b * sampleRate)));
    if (seg.length < 256) seg = y;
    const spec = spectrum(seg), nfft = (spec.length - 1) * 2, hzPerBin = sampleRate / nfft;
    const amps = [];
    for (let h = 1; h <= 8; h++) {
      const target = f0 * h;
      if (target >= sampleRate / 2) { amps.push(1e-12); continue; }
      const bandwidth = Math.max(4, target * .006);
      const low = Math.max(0, Math.ceil((target - bandwidth) / hzPerBin));
      const high = Math.min(spec.length - 1, Math.floor((target + bandwidth) / hzPerBin));
      let energy = 0;
      for (let k = low; k <= high; k++) energy += spec[k] * spec[k];
      amps.push(low <= high ? Math.sqrt(energy) : 1e-12);
    }
    const h1 = Math.max(amps[0], 1e-12), regionRatios = [];
    for (let h = 2; h <= 8; h++) {
      const ratio = 20 * Math.log10(Math.max(amps[h - 1], 1e-12) / h1);
      result.push(ratio); regionRatios.push(ratio);
    }
    ratios.push(regionRatios);
    for (let h = 1; h <= 8; h++) {
      const target = f0 * h;
      if (target >= sampleRate / 2) { result.push(0, 0, 0); continue; }
      const search = Math.max(8, target * .02);
      const low = Math.max(0, Math.ceil((target - search) / hzPerBin));
      const high = Math.min(spec.length - 1, Math.floor((target + search) / hzPerBin));
      if (low > high) { result.push(0, 0, 0); continue; }
      let peakIndex = low;
      for (let k = low + 1; k <= high; k++) if (spec[k] > spec[peakIndex]) peakIndex = k;
      const peakHz = Math.max(peakIndex * hzPerBin, 1e-9), peak = Math.max(spec[peakIndex], 1e-12);
      const cents = 1200 * Math.log2(peakHz / target), half = peak / Math.SQRT2;
      let left = peakIndex, right = peakIndex;
      while (left > 0 && spec[left] >= half) left--;
      while (right + 1 < spec.length && spec[right] >= half) right++;
      const excluded = Math.max(4, target * .006), noise = [];
      for (let k = low; k <= high; k++) if (Math.abs(k * hzPerBin - peakHz) > excluded) noise.push(spec[k]);
      result.push(cents, (right - left) * hzPerBin, 20 * Math.log10(peak / Math.max(median(noise), 1e-12)));
    }
  }
  for (const [a, b] of [[0, 1], [1, 2]]) for (let h = 0; h < 7; h++) result.push(ratios[b][h] - ratios[a][h]);
  if (result.length !== 107) throw new Error(`Expected 107 harmonic features, got ${result.length}`);
  return Float32Array.from(result);
}
