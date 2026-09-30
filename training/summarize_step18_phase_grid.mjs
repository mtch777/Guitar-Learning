#!/usr/bin/env node
// Paired robustness summary: classify missing capture separately from an error.
import fs from 'node:fs';
import path from 'node:path';

const [,, baselinePath, variantDir, outPath, ...flags] = process.argv;
if (!outPath) throw Error('usage: node summarize_step18_phase_grid.mjs baseline.json variants_dir out.json [--smoke]');
const baseline = JSON.parse(fs.readFileSync(baselinePath));
const smoke = flags.includes('--smoke');
const original = new Map(baseline.rows.map(r => [r.file, r]));
const selected = smoke ? baseline.rows.filter(r => r.true_midi >= 54 && r.true_midi <= 60 && r.file.includes('_normal_')) : baseline.rows;
if (baseline.rows.length !== 384 || (smoke && selected.length !== 36)) throw Error('Unexpected baseline fixture');
const conditions = [1024, 2048, 3072, 4096, 8192];
const results = [];
function median(values) {
  if (!values.length) return null;
  const a = [...values].sort((x, y) => x - y), i = Math.floor(a.length / 2);
  return a.length % 2 ? a[i] : (a[i - 1] + a[i]) / 2;
}
for (const lead of conditions) {
  const file = path.join(variantDir, `lead_${lead}_${smoke ? 'smoke' : 'real'}.json`);
  const variant = JSON.parse(fs.readFileSync(file));
  if (variant.report.leading_samples !== lead || variant.rows.length !== selected.length) throw Error(`Incomplete ${file}`);
  const pairs = variant.rows.map(v => {
    const b = original.get(v.file);
    if (!b || b.true_midi !== v.true_midi || b.true_string !== v.true_string) throw Error(`Unpaired ${v.file}`);
    return { b, v };
  });
  const both = pairs.filter(({ b, v }) => b.fusion && v.fusion);
  const changes = pairs.filter(({ b, v }) => !!b.fusion !== !!v.fusion);
  results.push({ leading_samples: lead, leading_ms: lead / 44.1,
    recordings: pairs.length, baseline_captures: pairs.filter(({ b }) => b.fusion).length,
    variant_captures: pairs.filter(({ v }) => v.fusion).length,
    newly_missing: changes.filter(({ b, v }) => b.fusion && !v.fusion).length,
    newly_captured: changes.filter(({ b, v }) => !b.fusion && v.fusion).length,
    paired_captures: both.length,
    baseline_tuple_correct_on_pair: both.filter(({ b }) => b.tuple_correct).length,
    variant_tuple_correct_on_pair: both.filter(({ v }) => v.tuple_correct).length,
    rescues_on_pair: both.filter(({ b, v }) => !b.tuple_correct && v.tuple_correct).length,
    regressions_on_pair: both.filter(({ b, v }) => b.tuple_correct && !v.tuple_correct).length,
    baseline_first_correct_on_pair: both.filter(({ b }) => b.first_event?.midi === b.true_midi && b.first_event?.string === b.true_string).length,
    variant_first_correct_on_pair: both.filter(({ v }) => v.first_event?.midi === v.true_midi && v.first_event?.string === v.true_string).length,
    variant_decision_from_onset_median_ms: median(both.map(({ v }) => v.decision_from_onset_ms)),
    incomplete_files: changes.filter(({ b, v }) => b.fusion && !v.fusion).map(({ v }) => v.file) });
}
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify({ phase: smoke ? 'smoke' : 'real', conditions: results }));
console.log(JSON.stringify(results.map(({ incomplete_files, ...rest }) => rest), null, 2));
