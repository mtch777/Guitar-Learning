#!/usr/bin/env node
import fs from 'node:fs';
import { predictFusionModel } from '../src/classifier/xgboost-fusion-model.js';
const [, , vectorsPath, modelDir] = process.argv;
if (!vectorsPath || !modelDir) throw new Error('usage: node check_step18_fusion_model_parity.mjs vectors.json models_dir');
const vectors = JSON.parse(fs.readFileSync(vectorsPath, 'utf8'));
if (!vectors.length) throw new Error('No parity vectors');
let maxAbs = 0, scaledMaxAbs = 0, decisions = 0, count = 0;
for (const name of ['baseline', 'harmonic', 'mfcc']) {
  const model = JSON.parse(fs.readFileSync(`${modelDir}/${name}.json`, 'utf8'));
  for (const row of vectors) {
    const predicted = predictFusionModel(model, row[`${name}_features`]);
    const scaledPredicted = predictFusionModel(model, row[`${name}_scaled`], true);
    const expected = row[`${name}_probabilities`];
    for (let i = 0; i < 8; i++) maxAbs = Math.max(maxAbs, Math.abs(predicted[i] - expected[i]));
    for (let i = 0; i < 8; i++) scaledMaxAbs = Math.max(scaledMaxAbs, Math.abs(scaledPredicted[i] - expected[i]));
    decisions += Number(predicted.indexOf(Math.max(...predicted)) === expected.indexOf(Math.max(...expected)));
    count++;
  }
}
const result = { recordings: vectors.length, model_predictions: count, identical_raw_argmax: decisions,
  max_probability_abs_difference: maxAbs, scaled_input_max_abs_difference: scaledMaxAbs };
console.log(JSON.stringify(result, null, 2));
if (decisions !== count || maxAbs > 1e-4 || scaledMaxAbs > 1e-4) process.exitCode = 1;
