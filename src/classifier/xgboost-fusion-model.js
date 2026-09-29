// Browser evaluator for exported multiclass XGBoost trees and StandardScaler.
// Classes are stored in physical-string order, 1..8.
export function predictFusionModel(bundle, features, alreadyScaled = false) {
  const { mean, scale, trees, classes, baseScore } = bundle;
  if (features.length !== mean.length || scale.length !== mean.length) throw new Error('Fusion feature count mismatch');
  // StandardScaler.transform preserves the input Float32 dtype before XGBoost.
  const x = alreadyScaled ? features : features.map((v, i) =>
    Math.fround(Math.fround(v - Math.fround(mean[i])) / Math.fround(scale[i])));
  const logits = Array.from(baseScore);
  for (let t = 0; t < trees.length; t++) {
    const tree = trees[t];
    let index = 0;
    for (;;) {
      if (tree.left[index] < 0) { logits[tree.class] += tree.value[index]; break; }
      const v = x[tree.feature[index]];
      index = Number.isNaN(v) || v === undefined ?
        (tree.defaultLeft[index] ? tree.left[index] : tree.right[index]) :
        (v < Math.fround(tree.value[index]) ? tree.left[index] : tree.right[index]);
    }
  }
  const max = Math.max(...logits), exp = logits.map(v => Math.exp(v - max));
  const sum = exp.reduce((a, b) => a + b, 0);
  const probabilities = Array(8).fill(0);
  for (let i = 0; i < classes.length; i++) probabilities[classes[i] - 1] = exp[i] / sum;
  return probabilities;
}

export function maskFusionProbabilities(probabilities, midi) {
  const open = [27, 34, 39, 44, 49, 54, 58, 63];
  const p = probabilities.map((v, i) => midi >= open[i] && midi <= open[i] + 24 ? v : 0);
  const sum = p.reduce((a, b) => a + b, 0);
  return sum ? p.map(v => v / sum) : p;
}
