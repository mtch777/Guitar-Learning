# Bounded original-reference boundary diagnostic

## Verdict
The released model can prefer the reference chord locally and still choose a different global segmentation. The converse also occurs: global context recovers reference labels that lose the isolated local score. This supports evaluating local recognition AND boundary/transition behavior together; it does not justify hardcoded chord overrides or adopting this checkpoint.

## Frozen scope and checks
- Preregistered seed 14981540351586935811 selected original Fold1 TEST score 003306b from five eligible scores, before examining its predictions. This is an examined published reference domain, not pristine holdout or a replacement for the inconclusive Sum41 capture.
- Exact original observed event/note data retained; annotations removed from decoder input and used only by a separate assessment process.
- Original checkpoint, count map, features, maxSpan and official GENERIC_ADDED_NOTES setting unchanged. Two dummy-label passes agree. Runtime 246.98 seconds within 360-second/4-GiB limit.
- All 33 frozen execution/input/model files unchanged after inference.
- 148 events, q3–92; 71 reference spans, 64 decoded spans. No scope truncation. 112/148 event labels agree with the normalized source reference. This is single-score reference concordance, not benchmark accuracy or musician adjudication.

## Local versus global
All 90 labels were scored at each of the 71 original annotation spans, without changing boundaries in the actual decoder. Reference/top feature contributions independently sum exactly.

| Reference is unique local winner? | Entire span globally matches | Partial match | No match |
|---|---:|---:|---:|
| Yes (57 spans) | 47 | 1 | 9 |
| No (14 spans) | 5 | 1 | 8 |

Examples: q9–9.5 A:min7 and q9.5–10 D:maj7 each rank first locally, but both are merged into global A:min. At q20–21 the reference A:min ranks fifth locally, yet the global path recovers A:min. These are model/context discrepancies; local scores exclude transition terms, so this table alone does not isolate which global term caused each choice. Generic-added-note labels such as D:maj7 must not be read automatically as a unique conventional major-seventh chord.

## Boundaries and repetitions
- 70 adjacent normalized reference-label changes; 61 exactly hit by predicted label-change boundaries, 9 missed, 2 additional predicted boundaries. No post hoc tolerance window.
- Source-selected literal repeated voicings yield 38 same-voicing/same-reference comparison groups; within each group decoded labels are consistent. Repeated examples are dependent, not 38 independent generalization tests. Different source labels on the same sonority are separated rather than declared errors.

## Requirements conclusion and next action
This completes only the authorized reference-domain method diagnostic. Fresh Sum41 annotation-backed evaluation remains inconclusive; exact recreation/meaningful analysis-tier inverse remains unimplemented, not passed. No engine, weights, musical rules, source corrections or promoted method were introduced.

Next bounded decision: retain this model as a measured comparator, not the musical authority. Before choosing an active Tier2 method, freeze a small independently annotated multi-context evaluation that separately measures local chord evidence, harmonic span boundaries and temporal context, including recoveries as well as regressions. Repeated voicing alone must not force equal harmony. Any future Tier2 implementation must also pass the independent source-stripped inverse and meaningful-abstraction gates; this research cannot substitute for them.

Evidence: experiment-plan.json; input-audit.json; source-assessment-inventory.json; run-freeze.json; segmental-reference-status.json; predictions.json; local-reference-scores.json; reference-assessment.json. Repeatable assessment: .local/segmental-crf-pilot/assess_reference.py. All artifacts remain private.

## Related graph-head evidence
The existing graph head predicts annotation-change coincidence, not generic note attack or independently established harmonic truth. Its declared class order is True, False. Existing Beatles readouts are exploratory, not held-out accuracy. Guitar-only voicing controls can gain other ensemble notes (q51, q53, q56); therefore four positive-looking cases and five negative-looking cases must not become a 4/4 plus 5/5 accuracy claim. Source scopes and original evidence remain separate.

## Completion boundary
The frozen reference experiment is complete as a bounded diagnostic. The fresh Songsterr annotation-backed experiment remains inconclusive; these results do not close a musical-engine or inverse gate. Exact signed nearest-boundary offsets, including equal-distance alternatives, are preserved in the private assessment rather than summarized through a chosen tolerance.
