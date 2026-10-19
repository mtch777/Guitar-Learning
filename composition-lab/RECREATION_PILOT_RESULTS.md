# G3 — eight-case recreation diagnostic

Eight real-source windows across six previously examined held-out song families
were tested. Both fitted models exclude these families. This is a bounded
diagnostic, not a fresh accuracy test or musical acceptance.

## Requirements verified

| Requirement | Actual result |
|---|---|
| Separate replay from learning | Replay restores converted-source target XML; learned methods receive files with all target annotations removed |
| Preserve the arrangement | Original occurrences, pitch/rhythm/voicing and non-target GPIF/archive data preserved; only declared eligible window fields overlaid |
| Do not leak original targets | Turning every target marker on versus off leaves 100% proposal decisions unchanged in all eight cases |
| Scope complete relationships | Directed pairs remain complete; outside/cross-boundary directed relationships unchanged in all four directed cases |
| Independent native interpretation | All 16 replay/learned GPs import and export MIDI; actual mute flags, directed links or selected bend contours agree with written expectations |
| Preserve failures | All misses, false positives, ineligible notes and the tied-bend refusal retained locally |
| Protect private inputs | Scores, annotations, model files, case identities and MIDI remain under ignored local-artifacts |

The reusable runner is `recreation_pilot.py`; `recreation_window.py` performs
redaction, source replay and eligible proposal overlay without rebuilding the
score. It rejects shared note definitions, unredacted targets, mismatched audit
hashes and changes outside the requested feature. Replay also rejects altered
archive members/comments. Repeating all eight replays under this final archive
guard produced byte-identical files. The first muting case reproduces the earlier
first-pair GP byte for byte.

## What learning did — and did not — reconstruct

TP = source annotation recreated; FN = source annotation missed;
FP = annotation added elsewhere; TN = eligible unannotated unit left unannotated.
Units differ by technique: coattack group, note attack or directed pair. Do not
pool these into an artist-accuracy percentage.

| Case | Technique | Eligible units | TP | FN | FP | TN |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Palm mute | 33 | 7 | 1 | 0 | 25 |
| 2 | Bend | 23 | 0 | 1 | 2 | 20 |
| 3 | Hammer from open | 4 | 2 | 2 | 0 | 0 |
| 4 | Pull to open | 4 | 0 | 4 | 0 | 0 |
| 5 | Bend | 11 | 0 | 1 | 0 | 10 |
| 6 | Hammer from open | 3 | 0 | 1 | 1 | 1 |
| 7 | Pull to open | 3 | 2 | 1 | 0 | 0 |
| 8 | Palm mute | 29 | 0 | 5 | 0 | 24 |

The same muting method that performed well in case 1 missed all five positive
groups in case 8. Both bend cases missed the source bend locations. Passing
serialization, permission or native-curve checks does not resolve these misses.
These results do not justify promoting the methods as faithful artist recreation.
The original first-pair static comparison remains separately recorded; this
eight-case batch is not an eight-case controlled method-improvement claim.

## Refusals and representation limits

- **Tied bends:** all 40 bends in the first attempted additional source were on tied
  notes, which the existing generator excludes. That coverage/refusal probe is
  preserved separately. Tied source annotations retained in final outputs are
  locked data, not learned reconstruction successes.
- **Raw API versus converted GP curves:** converted-GP replay/native contour
  agreement passes, but the two selected original API curves differ from their
  converted-GP encodings. Maximum sampled discrepancies are approximately
  **0.029 and 0.462 semitones**. No claim of lossless raw-API replay is made.
  Existing paired-bend workflow and parked standalone-native repair remain
  separate; neither source conversion nor its truth was silently rewritten.
- **Harmonic context:** case 7 contains two API written-base pitches differing
  from stored GP pitches by 24/36 semitones. Actual string/fret base pitches agree.
  These harmonic notes are ineligible and preserved exactly. Broad equivalence
  of raw-base and sounding-pitch context/register features remains unverified.
- **String convention:** API/GPIF index reversal is checked against actual
  tunings; synthetic 6-, 7- and 8-string tests reject mismatched conventions. The initial
  naive failed source join is retained, not erased.
- Human musical/source-feel acceptance is still open. No listening judgment was
  invented, and no new review UI or generator-default promotion occurred.
- No new WAV render or listening review was performed in this gate. Native
  import/MIDI/contour agreement is not evidence of audible recreation quality.

## Verification and reproduction

- Python discovery: **500 run, 499 passed, one optional skip**. Includes the still
  uncommitted rejected tuning candidate's tests; that candidate is not accepted.
- **39 JS tests passed; Vite build passed.** No website files changed.
- Five focused replay/window tests include archive tampering and shared-ID refusal.
- Two end-to-end runner/partition tests preserve failed predictions and refuse
  fitted source families or training bend-shape leakage. All eight real cases
  satisfy the final guard. Family assignment comes from the frozen plan; it is
  not inferred or independently authenticated from the GP file itself.
- Native tools: `verify_gp.mjs`, `verify_note_flags.mjs`,
  `verify_technique_links.mjs`, and `verify_window_curves.mjs`. The curve verifier
  checks contour samples/breakpoints, finite values and actual curve presence.
- CLI: `recreation_pilot.py --plan PRIVATE_PLAN --output NEW_PRIVATE_DIRECTORY
  --performance-model MODEL --shapes SHAPES --sequence-model MODEL`.
  Existing folders are refused. Native validation remains a separate step.
- Private evidence: `local-artifacts/g3-recreation-v1/eight-case-final-verification.json`,
  frozen plan, generation source snapshots/hashes, all original per-case reports,
  native logs, raw-conversion/context investigations and actual GP/MIDI files.

ProjectPlanner3000 accepted the bounded diagnostic/replay scope, with the
listening and family-guard clarifications above. Engineering replay/lock/native
criteria pass; faithful learned reconstruction remains mixed/unestablished.
Delivery/CI remain pending. G4 has not started. Next is exploratory changed-context
transfer, carrying these misses/representation gaps forward without promotion.
