# Declared chord-degree placement: bounded voicing experiment

## Question

Can a source-supported chord keep its identity, bass and doubling while its
tones move to a different observed placement, using the existing inverse?

Earlier per-string pitch-class locks could only move a string's existing tone
by octaves. This experiment explicitly releases that allocation, not the chord
or its doubling. Highest chord tone is not asserted to be a melody.

## Ownership and unchanged equations

- A source-written chord on its exact declaring beat must already qualify for
  the declared degree owner. Unknown/incomplete annotations stay fallback.
- Only owned `degree_token` and `relative_octaves` may change.
- The SAME `pitch_from_degree` and tuning/fret equations reconstruct the result.
- Root, formula, degree multiset, cardinality, exact bass pitch, actual strings,
  track/voice/occurrences, timing, all source markings and every outside fact
  stay locked. Chord display width is known presentation data and stays exact.
- Unmodeled diagrams/finger/spelling declarations, pedal sounding ends, pinned
  execution/ties, unsupported physical or overlapping-string conditions refuse.
- Complete source donor must be in the same part/root/formula/cardinality/
  doubling/bass/string stratum. Map by actual string, not note-list order.
- Candidate must retain global execution/tie and approved pedal interpretations,
  affected vertical pitch-class sets and coattack technique classifications.
- Changed incident lane edges/triples require independent source witnesses
  outside the changed neighborhood. Unknown selected execution refuses.
- Exact target PC multiplicity in every time cell preserves its contribution
  to any unchanged outside context. Outside execution uncertainty is retained,
  not treated as resolved, and outside source facts/projections stay exact.

## Controls

`declared_degree_allocation`, `voicing=0..100`, `register=0`, explicit target
source event and deterministic seed. Zero is exact. At intermediate values,
release probability is percentage/100. Once released, choose empirically among
admitted whole source allocations, weighted by their source occurrences. At100,
coincidence remains possible; difference is never forced. This is a bounded
source-supported trial, not a completed artist-wide unlocked generator.

## Acceptance checklist

- [x] Planner START: scope and preserved dimensions agreed.
- [x] Authored positive: actual changed isolated inverse from owned parameters.
- [x] Authored negatives: absent motion witnesses, earlier pedal, unknown other
  track execution, locked dimensions. Source display width remains exact.
- [x] 0/50/100 release behavior and actual-string correspondence tested.
- [x] Planner MID independent inventory and complete proposal denominator agree.
- [x] Freeze code before a new random capture; keep its outcome regardless.
- [x] V2 selected captures pass actual whole/pair zero workers and independent
  raw checks; unsupported fresh material is retained as failure, never replaced.
- [x] Enumerate every qualified declared target/donor; independently check all
  admitted changed candidates; retain rejection reasons.
- [x] At least one real admitted change through actual isolated inverse, or
  precise blocker and failed hypothesis recorded. No guard bypass for a demo.
- [ ] Deferred (no real change admitted): GP export/reimport and audible before/after
  artifact checks, with analysis/execution/export/listening limitations explicit.
- [ ] Regression tests, Planner END, source-only commit/push and CI.

## Limits

Written annotations are conditional evidence, not validated harmonic truth.
No base key, mode, note-role, phrase intention, artist fit or emotional quality
is invented. Reversibility, meaningful degree ownership, and audible artistic
acceptance are separate claims. Existing technique detectors remain unchanged.

## Frozen allocation-v1 result and next correction

Seven development captures:41,755notes/430,881facts, actual whole/pair zero
workers pass.291declared groups;48changed directed donor links in Queen reduce
to10unique target/layout proposals.0admitted. Independent raw inventory agrees.
Fresh Police3706/revision9697344 fails on72explicit keySignature:null fields;
retain the original failure. Known object declarations and absence stay distinct.

Planner tested48proposals against all4096possible outsidePCsets (196,608checks).
Blanket outside-knownness was unnecessary for the stated nominal-PC invariant.
Four proposals blocked there ALSO fail incident dead/slide paths; removing the
unnecessary veto is not an audible-result claim. Those incident guards remain.
Allocation-v2 uses exact target contribution + unchanged outside projection,
retain outside uncertainty, admit the known null-key field type without key
inference, and return nonzero CLI status for failed QA. Connected ownership
currently preserves key declarations as source choices; its musical core does
not yet use the separate declared-key context module. Do not imply it does.

V2 END: Planner independently matched496project/266native hashes, frozenZIP,
allthree capture sets, actualsix whole/pair outputs and allrawproposal ledgers.
22,117notes/224,470facts exact; still0real changedlayouts admitted. Threecurrent
capture gates pass within that bounded scope; source/artist abstraction and the
complete voicing lever remain unfinished. Fullsuite1206pass/1optional skip.
