#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { crossFitFusion } from '../src/classifier/isotonic-fusion.js';
const [, , input, output, ...args] = process.argv;
if (!input || !output) throw new Error('usage: node training/run_step18_fusion_selector.mjs input.json output.json [--smoke]');
const { rows, expected } = JSON.parse(fs.readFileSync(input, 'utf8'));
if (rows.length !== 384 || expected.length !== 384) throw new Error('Expected full preserved 384-recording OOF fixture');
const smoke = args.includes('--smoke');
const files = smoke ? new Set(rows.filter(r => r.midi >= 54 && r.midi <= 60 && r.strength === 'normal').map(r => r.file)) : null;
const start = performance.now(), predictions = crossFitFusion(rows, files), durationMs = performance.now() - start;
const reference = new Map(expected.map(r => [r.file, r]));
let identical = 0, correct = 0, maxScoreDiff = 0;
for (const p of predictions) {
  const e = reference.get(p.file);
  if (!e) throw new Error(`Missing Python reference: ${p.file}`);
  identical += Number(p.string === e.predicted_string);
  correct += Number(p.string === p.true_string);
  maxScoreDiff = Math.max(maxScoreDiff, Math.abs(p.confidence - e.score));
}
const summary = { phase: smoke ? 'smoke' : 'real', recordings: predictions.length,
  predicted_identical_to_python: identical, correct, max_score_abs_diff: maxScoreDiff, duration_ms: durationMs };
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, JSON.stringify({ summary, predictions }));
console.log(JSON.stringify(summary, null, 2));
if (identical !== predictions.length || maxScoreDiff > 1e-8) process.exitCode = 1;
