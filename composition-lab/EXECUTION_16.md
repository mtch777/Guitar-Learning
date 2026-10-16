# Autonomous execution: all 16 workstreams

Started 2026-10-15, baseline main b236c98. User authorized independent execution and defers collaborative musical review until a consolidated output set is ready. Do not stop for routine decisions; no fabricated human judgments. SMART values are targets, not achieved measurements. Record pass/fail/unsupported evidence for every stream; failed research gates do not stop independent engineering.

| Step | Acceptance evidence | State |
|---|---|---|
| 1 Freeze | Versioned hashes of all current inputs, outputs, weights, feedback and source commits; representative reproduction | Pass: 757 unchanged hashes; fresh two-piece pipeline reproduction |
| 2 Representation | All original occurrences accounted for, rational sustains/voices/metadata, >=30 edge cases, independent audit | Core pass: 15,452 occurrences, 1,445 tie joins; 30 parametrized cases; performance interpretation partial |
| 3 Corpus | Provenance/rights manifest, inventory and gaps against 100-piece/5-style target; no inferred blanket licensing | Partial: 2,000 pieces; five-style target failed; research rights only |
| 4 Splits | Song/family split manifest, exact/relative duplicates separated, untouched test; overlap unknowns explicit | Pass for scratch grouped split; external pretraining overlap unknown |
| 5 Relationships | Versioned motif/phrase/section/harmony/role hypotheses with provenance, integrity checks and uncertainty | Partial: two GP occurrence-linked graphs; semantic truth / 20 contrasting sources missing |
| 6 Structural validation | Independent annotated held-out boundaries/relationships; compare simple baselines and report SMART pass/fail | Failed target: boundary F1 .571 vs .354 baseline, below .70 |
| 7 Architecture | >=3 researched candidates, >=2 runnable paths, resource/license/feature decision | Research paths run; integration and licenses explicitly limited |
| 8 Phrase learning | Actual training/inference, context/permutation/baseline metrics, held-out predictions and generated GP | Partial: official context evidence positive; guitar adaptation gate failed; 126 sampled neural phrases |
| 9 Form | Learned arrangement/phrase sequence experiment, >=30 64-bar outputs if feasible, supplied vs learned form explicit | 100 outputs; failed learned-form baseline gate (4.412 vs 4.292 NLL) |
| 10 Roles | Joint contextual accompaniment/bass experiment vs independent role sampling; held-out metrics | Partial: +4.36% / +11.27% two-song NLL; scope and timing limited |
| 11 Playability | Instrument constraints, source tunings, validation reports; human assessment deferred | Mechanical pass 100 compositions + 15 controls; musician assessment pending |
| 12 Controls | 0/25/50/75/100 sweep, exact-zero invariants, monotonicity and cross-dimension coupling reports | Partial: 1,600 feasible / 400 rejected; zero lock violations; structure/roles unsupported |
| 13 Compositions | >=20 full GP compositions, >=3 roles, independent import/event checks, seeds/provenance | Artifact pass: 100 x 64 bars / 3 roles; quality unjudged |
| 14 Originality | Source/train/test copying windows and near-match audit; style/seed generalization, no legal-certification claim | Partial: zero 16/32-event exact relative matches vs 2,002 pieces; short/coarse matches; style gate untested |
| 15 Musical validation | Consolidated comparison outputs and blind protocol; 3-listener/preference gate deferred to final collaboration | 22-case review ready; shorter references mean exploratory comparison; human gates pending |
| 16 Workflow | Repeatable CLI + review/export workflow, regression/CI/build, push verified main and check Pages for site edits | Local CLI / 102 Python / 12 JS / build pass; remote release verification below |

## Execution log

- Synced main via fetch and fast-forward; clean starting tree. Prior reviews and heuristic baseline outputs frozen rather than overwritten. Existing external learned-model results remain evidence, including negative guitar adaptation.
- Executed source extraction, tie/lane audits, grouped corpus preparation, scratch boundary/form fitting, official neural phrase sampling, joint-role training and 100 full-length GP generations. Independent alphaTab imported all 100 with expected event/program/tuning checks. Commands and exact acceptance results: [AUTONOMOUS_RESULTS.md](AUTONOMOUS_RESULTS.md); source-free machine-readable evidence: [benchmarks/autonomous_results.json](benchmarks/autonomous_results.json).
- Corrected form scoring to allocate smoothing probability to an explicit unknown state; reran in structure-v3. Persisted model hash unchanged from v2, generated sampling unaffected. Form still fails independent baseline. No post-hoc success threshold change.
- Rhythm control originally could not change uniform-duration bars; added duration profiles from actual sampled neural phrases while preserving event count and ordered pitch/rest units. Reran 2,000 controls into a new report: harmony/rhythm target means exact, melody within .53 points; 300 monotonic sweeps minimum Spearman ~1; zero exact-zero violations. Exported and independently checked 15 GP control examples.
- `run_composition_pipeline.py` reproduced every pipeline stage in a NEW private directory, count=2, pool-count=8: all subprocess return codes zero, two 64-bar GPs independently checked, validation and review bundle produced. This is a reproducibility smoke run, not five consecutive full research runs.
- Private generated-only ZIP: 3,020,547 bytes, 118 entries, CRC checked, SHA256 e2bfd59d1ea314d85efc59bec306b0486d49938c46b2ab1e1521289bd3f3eca7. All 757 frozen earlier files rehashed unchanged. Nothing from the private corpus, weights, annotations or commercial source GPs is staged.
- Browser: private 22-case bundle loaded; A/B durations both 128s, B play state active and A paused; B piano roll followed correct piece; zero console errors. QA ratings explicitly labelled non-human in isolated storage. Desktop native file chooser hung/crashed the preview tab; added and verified paste-JSON fallback. No listening or quality judgment inferred from browser playback.
- `.venv/Scripts/python.exe -m unittest discover -s composition-lab -p test_*.py`: 102 pass. Bundled Node `--test tests/*.test.mjs`: 12 pass. `npm run build`: pass. These are the pre-integration results; concurrent main fetched before commit has unrelated guitar UI/workflow updates, retained by rebase before final combined checks.

## Open gates for consolidated collaboration

No routine user input was required during implementation. The remaining human task is musical judgment; the remaining engineering/research gaps are substantive (multi-style rights-appropriate data, guitar structural truth, form beating its baseline, independent structure/roles, learned accompaniment timing and voice leading). They are not marked complete by an export, a passing parser, or deployment. Review outputs first; use evidence to choose the next training intervention.
