#!/usr/bin/env node
// Select an early-event rule on other entire MIDI notes, then score each held-out note.
import fs from 'node:fs';
import path from 'node:path';

const [,, sourcePath, outPath, ...flags] = process.argv;
if (!outPath) throw Error('usage: node score_step18_selective_early.mjs diagnostic_replay.json output.json [--smoke]');
const source = JSON.parse(fs.readFileSync(sourcePath));
if (source.report.detector !== 'correlation-start-yin-votes' || source.rows.length !== 384)
  throw Error('Expected full hybrid diagnostic replay');
const full = source.rows;
if (full.some(r => r.early_singleton && !Number.isFinite(r.early_singleton.pitch_confidence)))
  throw Error('Missing early-event confidence diagnostics');
const correct = (e, r) => !!e && e.midi === r.true_midi && e.string === r.true_string;
const gate = (r, rule) => {
  const e = r.early_singleton;
  return !!e && (rule.kind === 'midi' ? e.midi >= rule.cut
    : rule.kind === 'confidence' ? e.pitch_confidence >= rule.cut
    : e.dbfs >= rule.cut);
};
const candidates = [
  ...Array.from({ length: 62 }, (_, i) => ({ kind: 'midi', cut: 27 + i })),
  ...Array.from({ length: 45 }, (_, i) => ({ kind: 'confidence', cut: .55 + i * .01 })),
  ...Array.from({ length: 37 }, (_, i) => ({ kind: 'dbfs', cut: -48 + i })),
];
function choose(training) {
  const safe = candidates.map(rule => {
    const emitted = training.filter(r => gate(r, rule));
    return { rule, kept: emitted.filter(r => correct(r.early_singleton, r)).length,
      wrong: emitted.filter(r => !correct(r.early_singleton, r)).length };
  }).filter(x => x.wrong === 0);
  // Prefer the most correct fast events. On a tie, prefer a narrow MIDI range;
  // the final fallback is the always-wait rule when no safe events are seen.
  safe.sort((a, b) => b.kept - a.kept ||
    (a.rule.kind === 'midi' ? 0 : 1) - (b.rule.kind === 'midi' ? 0 : 1) ||
    b.rule.cut - a.rule.cut);
  return safe[0]?.kept ? safe[0] : { rule: { kind: 'wait', cut: null }, kept: 0, wrong: 0 };
}
const heldOut = new Map([...new Set(full.map(r => r.true_midi))].map(midi =>
  [midi, choose(full.filter(r => r.true_midi !== midi))]));
const rows = (flags.includes('--smoke') ? full.filter(r => r.true_midi === 27 || r.true_midi === 51 || r.true_midi === 87) : full)
  .map(r => {
    const selected = heldOut.get(r.true_midi);
    const emitEarly = selected.rule.kind !== 'wait' && gate(r, selected.rule);
    const early = emitEarly ? r.early_singleton : null;
    const final = r.fusion ? { midi: r.fusion.midi, string: r.fusion.string,
      elapsed_ms: r.capture_ms + r.inference_ms } : null;
    const chosen = early || final;
    return { file: r.file, true_midi: r.true_midi, true_string: r.true_string,
      fold_rule: selected.rule, early_singleton: r.early_singleton, final,
      emitted_early: emitEarly, chosen, chosen_correct: correct(chosen, r),
      final_correct: correct(final, r), immediate_correct: correct(r.first_event, r),
      time_saved_ms: early && final ? final.elapsed_ms - early.elapsed_ms : null };
  });
const allEarly = full.filter(r => r.early_singleton);
const kinds = Object.fromEntries(['midi','confidence','dbfs'].map(kind => {
  const family = candidates.filter(c => c.kind === kind).map(rule => ({ rule,
    correct: allEarly.filter(r => gate(r, rule) && correct(r.early_singleton, r)).length,
    wrong: allEarly.filter(r => gate(r, rule) && !correct(r.early_singleton, r)).length }));
  const best = family.filter(x => !x.wrong).sort((a,b) => b.correct-a.correct || b.rule.cut-a.rule.cut)[0];
  return [kind, best];
}));
const report = { phase: flags.includes('--smoke') ? 'smoke' : 'real', recordings: rows.length,
  immediate_correct: rows.filter(r => r.immediate_correct).length,
  always_wait_correct: rows.filter(r => r.final_correct).length,
  selective_correct: rows.filter(r => r.chosen_correct).length,
  immediate_wrong_early: rows.filter(r => r.early_singleton && !correct(r.early_singleton, r)).length,
  selective_wrong_early: rows.filter(r => r.emitted_early && !correct(r.early_singleton, r)).length,
  selective_correct_early: rows.filter(r => r.emitted_early && correct(r.early_singleton, r)).length,
  rescues_vs_wait: rows.filter(r => !r.final_correct && r.chosen_correct).length,
  regressions_vs_wait: rows.filter(r => r.final_correct && !r.chosen_correct).length,
  missing: rows.filter(r => !r.chosen).length,
  safe_in_sample_by_family: kinds,
  fold_rules: Object.fromEntries([...heldOut].map(([midi, x]) => [midi, x])),
};
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify({ report, rows }));
console.log(JSON.stringify({ ...report, fold_rules: 'in output rows/report' }, null, 2));
