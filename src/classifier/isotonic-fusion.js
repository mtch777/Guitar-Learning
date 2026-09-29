// Cross-fitted isotonic model selector for the three physical-string models.
// Input confidences are the maxima AFTER each model's MIDI feasibility mask.
// Model order is significant for ties: baseline, harmonic, early MFCC.
export const FUSION_MODELS = ['baseline', 'harmonic', 'mfcc'];

export function fitIsotonic(confidences, correct) {
  if (confidences.length !== correct.length || !confidences.length) {
    throw new Error('Isotonic inputs must have equal nonzero length');
  }
  const paired = confidences.map((x, i) => ({ x, y: Number(correct[i]) })).sort((a, b) => a.x - b.x);
  const points = [];
  for (const { x, y } of paired) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error('Nonfinite calibration input');
    if (points.length && points[points.length - 1].x === x) {
      points[points.length - 1].sum += y;
      points[points.length - 1].weight++;
    } else points.push({ x, sum: y, weight: 1 });
  }
  const blocks = [];
  for (let i = 0; i < points.length; i++) {
    blocks.push({ first: i, last: i, sum: points[i].sum, weight: points[i].weight });
    while (blocks.length > 1) {
      const right = blocks[blocks.length - 1], left = blocks[blocks.length - 2];
      if (left.sum / left.weight <= right.sum / right.weight) break;
      left.last = right.last; left.sum += right.sum; left.weight += right.weight;
      blocks.pop();
    }
  }
  const x = points.map(p => p.x), y = new Array(points.length);
  for (const b of blocks) for (let i = b.first; i <= b.last; i++) y[i] = b.sum / b.weight;
  // scikit-learn removes interior points of a flat plateau before interpolation;
  // this does not change its piecewise-linear prediction function.
  const keep = x.map((_, i) => i).filter(i => i === 0 || i === x.length - 1 || y[i] !== y[i - 1] || y[i] !== y[i + 1]);
  return { x: keep.map(i => x[i]), y: keep.map(i => y[i]) };
}

export function predictIsotonic(model, value) {
  const { x, y } = model;
  if (value <= x[0] || x.length === 1) return y[0];
  const last = x.length - 1;
  if (value >= x[last]) return y[last];
  let lo = 0, hi = last;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (x[mid] <= value) lo = mid; else hi = mid; }
  return y[lo] + (value - x[lo]) * (y[hi] - y[lo]) / (x[hi] - x[lo]);
}

export function chooseIsotonicFusion(models, predictions, confidences) {
  let best = 0, bestScore = -Infinity;
  const scores = models.map((model, i) => {
    const score = predictIsotonic(model, confidences[i]);
    if (score > bestScore) { best = i; bestScore = score; }
    return score;
  });
  return { string: predictions[best], confidence: bestScore, model: FUSION_MODELS[best], scores };
}

export function crossFitFusion(rows, evalFiles = null) {
  const midis = [...new Set(rows.map(r => r.midi))].sort((a, b) => a - b);
  const outputs = [];
  for (const midi of midis) {
    const train = rows.filter(r => r.midi !== midi);
    const test = rows.filter(r => r.midi === midi && (!evalFiles || evalFiles.has(r.file)));
    if (!test.length) continue;
    const models = FUSION_MODELS.map(name => fitIsotonic(
      train.map(r => r[`${name}_conf`]), train.map(r => r[`${name}_pred`] === r.string ? 1 : 0)
    ));
    for (const row of test) outputs.push({ file: row.file, midi, true_string: row.string,
      ...chooseIsotonicFusion(models, FUSION_MODELS.map(name => row[`${name}_pred`]), FUSION_MODELS.map(name => row[`${name}_conf`])) });
  }
  return outputs;
}
