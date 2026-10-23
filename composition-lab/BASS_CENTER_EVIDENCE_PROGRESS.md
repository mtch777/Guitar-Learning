# Tonal evidence: source integrity and lowest-note experiment

2026-10-23. Requirements: musical meaning; the same relationships forward and
backward; all three QA gates; review with ProjectPlanner3000. Research only.

## Acceptance and outcome

| Requirement | Status | Verified scope / remaining gap |
|---|---|---|
| Source inputs independent of evaluation labels | PASS | All 54 pieces; 64,486 source-valid cells. Label mutations cannot change inference inputs. |
| Lowest active written note, with source witnesses | PASS | Independent raw-note audit: 63,870 known, 616 empty. Unknown handling has synthetic tests; no actual unknown cases here. |
| Same tonal kernel; no manual tonic preference | PASS | Original model kernel and fixed parameter grids unchanged. Source-only inputs; teacher labels used separately for training/scoring. |
| Added bass evidence improves reliable key selection | REJECT | Ordered model worsened on three of four test works. Tiny average gain does not justify promotion. |
| Accurate guitar keys, modes and harmonic functions | OPEN | Piano research results do not establish guitar accuracy, seven-mode identification or function. |
| Original detectors / source codecs | PRESERVED | No edits; exact detector parity on the new song. |
| Planner review | COMPLETE | Independent source, factor, training/control and metric audits passed; model promotion rejected. |

## Root cause found and corrected

Legacy evaluation uncertainty could remove source-valid intervals and break the
model's input sequence. Across 54 pieces this omitted **129 cells** (111 train,
18 test) and introduced **46 extra breaks**, six in test material.

New `tonal_source_stream.py` reads only source clocks, pitch classes, source
eligibility and note witnesses. Teacher availability never selects inference
cells. Invalid order/overlap, negative IDs and unknown eligibility enums fail.

Training still needs known current targets. Its separate join preserves the
source predecessor but resets supervised key-transition learning when a target
is missing. It never bridges an unknown teacher state.

Frozen legacy-model replay: ordered NLL 1.227295224 → 1.226671870, with **zero
chosen-key changes**. Thus this was a real provenance defect, but did not explain
the weak tonal results. Historical reports remain preserved and qualified.

## Controlled lowest-note test

Source feature: minimum **active nominal MIDI pitch**, with all tied minimum
witnesses. This does not claim a structural bass role or perceived sounding pitch.

Relationship tested:

`P(key at t | all PC sets, bass at t) ∝ P(key at t | all PC sets) × P(bass at t | key at t, current PC set)`

This is query-local conditional evidence under a stated independence assumption,
not joint inference over every bass event in the song. It is not a bass-equals-
tonic rule. Empty/unknown evidence is neutral.

- Same frozen whole-work split: 11 train, three validation, four test works.
- All test works were previously inspected: exploratory follow-up, not fresh accuracy.
- Unchanged 24 major/minor states; no unsupported seven-mode inference.
- Learned TRAIN-only tonic-relative counts and empirical smoothing.
- Validation chooses alpha from 1 / 10 / 100; selection sealed before test.
- Control shuffles TRAIN bass within the same work and exact source PC set.
- Independent audit reproduced 44,169 training rows, 43,707 donor assignments,
  validation selections and all 72 test-piece variants and per-work metrics.

| Test method | Key-label NLL ↓ | Top-label agreement | Interpretation |
|---|---:|---:|---|
| Clean ordered baseline | 1.226527 | 81.644% | Research baseline, not guitar accuracy |
| Ordered + actual bass | 1.226181 | 81.609% | Three works worse; calibration worse: reject |
| Ordered + shuffled bass | 1.228546 | 81.626% | Control |
| Clean marginal baseline | 1.236122 | 81.542% | Research baseline |
| Marginal + actual bass | 1.230087 | 81.604% | Small NLL benefit in all four works; calibration worse |
| Marginal + shuffled bass | 1.231435 | 81.619% | Better Brier/calibration than actual-bass variant |

No product deployment or claim of reliable tonic, mode, emotion or audio quality.
No copyrighted source, annotations or fitted research weights are published.

## All three QA gates: new Songsterr song

**Eyedress — Jealous**, song 479770 / revision 3393310, five tracks.
Seed 3372550108100465328, query `e`; prior corpus and all previous captured
selection IDs excluded before capture. First complete source bar selected before
analysis; no easier replacement or per-song fix.

| Gate | Result | Exact scope |
|---|---|---|
| 1. New random song, unchanged logic | PASS | Complete source populated; no unsupported-source repair; detectors unchanged. |
| 2. Remove lower data and reconstruct | PASS | Complete T1 recovered: **34,977 typed fields/containers exact**. Same equations; no separate generator. |
| 3. Meaningful musical abstraction | PASS, bounded | Independent raw-source first-bar audit: 34 occurrences, including 10 pitched and 24 explicit percussion; six optimal edges, nine chord-label assignments. |

Musical audit checks: 39 primary chord-degree inverses; 432 compatible theory
entries with 1,836 degree checks; 466 conditional reference comparisons; all
30 source triples, including four conditional patterns and 26 refusals.
No actual held boundary in this bar; positive held-note coverage is elsewhere.

The reference A-minor candidate remains provisional, with equivalent alternatives.
The graph's retained hypotheses are not established song key, mode or intent.
The worker stages neither source/cache nor expected answers. It uses `-I -S`
and Python audit guards, **not an OS sandbox**; no native memory/disk quota claim.
Exact captured JSON equality is not a GP playback or sound-quality claim.

## Commands, artifacts and delivery

- `.venv/Scripts/python.exe -m unittest discover -s composition-lab -p test_*.py`
  → **999 run, 998 passed, one optional skip**.
- `python -S -m unittest discover -s composition-lab -p test_*.py`
  → **999 run, 988 passed, 11 optional skips**.
- Node source inspector / dead-tie / bend-fidelity suites → **19 passed**.
- `run_clean_tonal_study.py <clean> <original-plan> <output>`: same fixed grid,
  source-only inputs, separate teachers, frozen models and selection hashes.
- `run_conditional_bass_study.py <clean> <clean-study> <output>`: verifies complete
  clean-model inventories and provenance before fitting. Empty/partial seals fail.
- `run_passage_roles_qa.py <frozen-capture> <output>`: source/inverse checks above.

Final private artifacts:

- `local-artifacts/source-bass-clean-v2`: all raw-source feature audits.
- `local-artifacts/clean-tonal-refit-v4`: final clean baseline and model hashes.
- `local-artifacts/conditional-bass-study-v2`: final study and independent audit.
- `local-artifacts/tonal-final-fresh-v1`: frozen new-song selection/capture.
- `local-artifacts/tonal-final-passage-qa-v1`: actual worker and independent audit.

Earlier artifacts remain: clean refits v1–v3 are provenance iterations; bass v1
predates final guard hardening. Final results repeat their numerical values.
No test-driven model retuning occurred. No website files changed.

## Next boundary

Do not chase this inspected piano test with extra features or invented artist
rules. Preserve source-linked chord alternatives and note roles. Reliable guitar
key/mode/function selection still needs independent, domain-appropriate evidence
or expert adjudication; exact reconstruction cannot substitute for it.
