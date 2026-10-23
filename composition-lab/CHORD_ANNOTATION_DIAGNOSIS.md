# Source chord-annotation diagnosis — active 2026-10-23

Planner START: compare source declarations before multiplying modal hypotheses.
This is a DIAGNOSTIC study using music21==9.9.2, not new Tier2 ownership or a new
generation engine. Existing complete-source inverses remain separate evidence;
they do NOT validate the library parser's musical interpretation.

## Acceptance frozen before parsing/predictions

- [x] Freeze ALL chord/text declarations in the two already frozen captures:
  Queen371(50) and MotleyCrue12719(14), including failures and empty labels.
- [x] Exact literal text, declaring part/voice/beat, rational source clock and
  source evidence address; no assumed annotation duration or cross-track scope.
- [x] Parse independently of note/model results; version/code hash frozen,
  warnings/errors retained. No ad-hoc grammar or substitutions to improve yield.
- [x] Separate parser interpretation, declaring-part starts/nominal overlaps,
  ensemble overlaps and ALL scored alternatives at the declaration clock.
- [x] Source labels are NOT verified harmony/training targets. Shape-versus-
  concert-pitch convention remains unresolved if not declared, including capo.
- [x] Compare complete source accounting and independent source/time joins;
  retain disagreement examples. No aggregate musical-accuracy percentage.
- [ ] Planner MIDPOINT/END; relevant tests, commands/results and next action.

Graph windows are explicit source MEASURES, not durations inferred for labels.
Part-local and ensemble scopes remain distinct. Resource failures remain failures;
no quieter/easier replacement window or song. Library dependency integration and
shared forward/reverse parsed-symbol contract require a separate justified step.

## Observations and controlled experiment

Private frozen `chord-annotation-diagnosis-v2`: all64 declarations accounted,
53parsed/11refused, zero source/time join errors;51 exact declaring-part PC sets,
2subsets. These are source comparisons, NOT accuracy estimates.

`chord-glyph-adapter-v1`: pinned library accidental glyph/modifier mapping at
root/slash-bass positions ONLY; raw text and lexical inverse retained. All64
reparsed against unchanged source/model/library;62parsed,2refused (`F#m3`),
60exact-PC sets,2subsets. Never rewrite chord quality to guess a meaning.
All64 baseline parser results reproduced before experiment. Original diagnostic
source snapshot retained; later warning-retention fix explicitly separated.

Planner independently froze all17 Queen part-local omissions and recomputed
full-measure graph optima from raw notes: all17 are outside the published
3/4-PC vocabulary (16root/fifth dyads,1root/major-third dyad). No demonstrated
segmentation/scoring bug or source-time mismatch. Artifacts:
`local-artifacts/queen-omission-audit-v2/`. No change to graph vocabulary/scoring.

## Next bounded acceptance: observed sonority versus template completion

- [x] New versioned chord-motion request; keep legacy output unchanged.
- [x] Report actual nominal written overlap, registers, lowest known pitch,
  source IDs and existing exact interval equations; root is not inferred bass.
- [x] Separate unobserved template tones, outside-template tones and incomplete
  pitched evidence; percussion does not supply harmonic pitch evidence.
- [x] SAME pure evaluator checks assertions from reconstructed complete Tier1;
  stale observed-PC assertion rejected. No notes repaired from templates.
- [x] Frozen random-source rerun, actual isolated inverse and independent source
  comparison; Planner verifies bounded musical meaning against original notes.
- [x] Full regression results recorded:950run949pass1optional skip; four new
  saved-prediction tests also pass under bare stdlib. Delivery/CI pending.

Targeted annotation/glyph tests6pass; chord-motion tests9pass including dyad,
inverted-register, third-dyad, full-triad contrasts and legacy/inverse checks.
Commands: `.venv/Scripts/python.exe -m unittest discover -s composition-lab
-p test_source_chord_annotation_diagnosis.py` and corresponding chord-motion
module. Full suite and `run_chord_motion_qa.py` frozen12719rerun underway.

Final corrected-code full suite946run945pass1optional skip; bare stdlib946run
936pass10optional skips (including optional library diagnostics). Targeted
chord-motion suite now10pass after Planner's timing-uncertainty counterexample.

Preserved v3 invalidated run: source changed while forward analysis was running
to add timing-uncertainty ownership. Freeze unchanged=false; actual worker
rejected stale contextual assertions. This is NOT accepted as a passed inverse.
Corrected unchanged-code v4 and new-source runs remain separate.

QA1 next capture: Queens of the Stone Age, I Appear Missing385798/rev9350241,
8tracks, seed12187565454334629665/queryq. Prior corpus plus Queen371/Motley12719
excluded BEFORE selection. Private `chord-overlay-fresh-v1/selection.json`.
Unchanged logic running on that source; no replacement if it fails.

Final actual workers PASS: frozen Motley regressionv4 reconstructs94324typed
fields/containers; fresh Queens of the Stone Age reconstructs71772. Both
unchanged=true, zero mismatches, retained detector parity=true. Fresh6749note
occurrences,12queries/64label pairs/128contexts,4896pitched-domain+1853explicit
nonpitched. Private independent raw-source overlay auditPASS, zero discrepancies.
Final Planner overall bounded approval/commitCI still pending at this log entry.

Planner END: APPROVED bounded QA3. Independent raw meter/duration/fret/tuning
audit checked all32regression and128fresh overlay contexts, zero issues. No
core parser/scorer imports in independent audit. No source key/mode/chord
accuracy or acoustic claim. Accepted pedal/technique detectors unchanged.

## Tonal-center evidence diagnosis (research only)

Planner added repeatable `diagnose_ordered_tonal_help_hurt.py`,4testsPASS.
`ordered-tonal-help-hurt-v1` freezes saved models, predictions, support data and
script before ranking. No fitting, inference, retuning or deployment. All13385
held-out cells accounted:76quarantined,13309scored,7496help/5813hurt under exact
saved target log-loss differences. Reproduces original aggregate marginalNLL
1.23813363892862 versus ordered1.2272952240213557. Two works improve, two worsen.
Fixed top5help/top5hurt retain rational source clocks/current+previousPCs and
numeric count/emission/message-odds identities. Not causal cadence attribution,
not an independent new accuracy study, and not7-mode or guitar validation.

Keys/modes remain hypotheses, not established tonal centers. This chord
diagnosis and observed-sonority layer do not establish modal or key accuracy.
