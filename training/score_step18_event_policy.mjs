#!/usr/bin/env node
// Scores two event policies on the same preserved hybrid-YIN replay.
// This is an event-order counterfactual, not a new acoustic/model run.
import fs from 'node:fs';
import path from 'node:path';

const [,, sourcePath, outPath, ...flags] = process.argv;
if (!outPath) throw Error('usage: node score_step18_event_policy.mjs hybrid_real.json out.json [--smoke]');
const source = JSON.parse(fs.readFileSync(sourcePath));
if (source.rows.length !== 384 || source.report.detector !== 'correlation-start-yin-votes') {
  throw Error('Expected complete 384-recording hybrid replay');
}
const all = source.rows;
const earlyCorrect = all.filter(r => r.early_singleton && r.early_singleton.midi === r.true_midi && r.early_singleton.string === r.true_string);
const earlyWrong = all.filter(r => r.early_singleton && (r.early_singleton.midi !== r.true_midi || r.early_singleton.string !== r.true_string));
const ordinary = all.filter(r => !r.early_singleton && r.fusion);
const missing = all.filter(r => !r.fusion);
const rows = flags.includes('--smoke')
  ? [...earlyCorrect.slice(0, 4), ...earlyWrong.slice(0, 4), ...ordinary.slice(0, 4), ...missing.slice(0, 1)]
  : all;
if (flags.includes('--smoke') && rows.length !== 13) throw Error(`Expected 13 targeted smoke rows, got ${rows.length}`);

const results = rows.map(r => {
  const current = r.first_event;
  const gated = r.fusion ? { midi: r.fusion.midi, string: r.fusion.string,
    elapsed_ms: r.capture_ms + r.inference_ms } : null;
  const correct = event => !!event && event.midi === r.true_midi && event.string === r.true_string;
  return { file: r.file, true_midi: r.true_midi, true_string: r.true_string,
    early_singleton: !!r.early_singleton, current, gated,
    current_correct: correct(current), gated_correct: correct(gated),
    delay_ms: current && gated ? gated.elapsed_ms - current.elapsed_ms : null };
});
function percentile(values, p) {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * p))] ?? null;
}
const changed = results.filter(r => r.early_singleton);
const report = { phase: flags.includes('--smoke') ? 'smoke' : 'real', recordings: rows.length,
  current_correct: results.filter(r => r.current_correct).length,
  gated_correct: results.filter(r => r.gated_correct).length,
  current_missing: results.filter(r => !r.current).length,
  gated_missing: results.filter(r => !r.gated).length,
  changed_first_events: changed.length,
  rescues: results.filter(r => !r.current_correct && r.gated_correct).length,
  regressions: results.filter(r => r.current_correct && !r.gated_correct).length,
  early_correct_delayed: changed.filter(r => r.current_correct).length,
  early_wrong: changed.filter(r => !r.current_correct).length,
  extra_delay_changed_median_ms: percentile(changed.map(r => r.delay_ms), .5),
  extra_delay_changed_p95_ms: percentile(changed.map(r => r.delay_ms), .95),
  current_first_median_ms: percentile(results.map(r => r.current?.elapsed_ms), .5),
  gated_first_median_ms: percentile(results.map(r => r.gated?.elapsed_ms), .5) };
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify({ report, rows: results }));
console.log(JSON.stringify(report, null, 2));
