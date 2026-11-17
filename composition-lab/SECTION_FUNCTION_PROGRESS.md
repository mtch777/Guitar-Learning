# Verse/chorus candidate pilot — 2026-11-17

Latest user direction: continue from bar-level repeat detection toward verse and
chorus identification. This supersedes historical generation-tier next actions;
no generation, chord-estimator, source-score or UI change is part of this pass.

## Acceptance checklist
- [x] Inspect repeat candidates and constraints; isolate new module.
- [x] Produce traceable verse/chorus hypotheses without equating recurrence with function.
- [x] Cover loops, missing evidence, equal alternatives, contrasting arrangements,
      configurable weights, no mutation and full bar coverage in synthetic tests.
- [ ] Run on frozen fresh Invent Animate songs, retain failures and compare independent labels.
- [ ] Publish source, tests and honest limitations; verify remote commit and CI state.

## Initial evidence / blocker
DESKTOP-DULDH56 listed offline and actual attach returned unavailable/offline.
No Windows files changed. Work uses an isolated cloud clone of existing
riff-walkthrough-ui-20261113 branch at 99d4cbf, preserving unrelated dirty cloud
checkout. Fresh PC corpus and detailed pilot reports are unavailable currently.
No accuracy, listening readiness or verified fresh-song result is claimed.

Strong counterexample: a repeated instrumental breakdown or ostinato can recur
more often and be louder than a chorus. A quiet chorus can recur exactly like a
verse. Repetition, density and position cannot alone establish function. Preserve
ambiguous alternatives and evidence provenance; weights are engineering settings,
not learned confidence. No fixed form, section length, order or key constraint.

## Cloud technical checkpoint
Added isolated `section_functions.py` and 12 synthetic tests. Existing 19 repeat
tests plus 12 new checks pass (`python -B -m unittest test_section_repeats
test_section_functions -v`). The module reports ranked support shares for existing
repeat groups, explicit contributing features, known-foreground availability and
one row per source bar. No input mutation; no forced final partition.

Important: this is a candidate-ranking prototype, NOT completed verse/chorus
identification. Role labels deliberately remain unknown at this checkpoint;
ranking strengths and unknown shares are uncalibrated engineering heuristics.
Confirmed foreground track IDs must come from source metadata/caller evidence,
not inferred from highest note. An instrumental lead is not proof of vocal form.
Shared recurrence/boundary evidence supports both roles. Arrangement fullness
is not loudness. Lead repeat/variation is only soft support, not lyric identity.

Fresh-song and independent-label validation are NOT RUN: PC offline, and no
verified fresh Invent Animate whole-song bar captures located in the cloud copy.
Do not claim listening readiness or accuracy. Next concrete step: on reconnect,
freeze previously unused songs, run existing source adapters, inspect source
foreground/channel evidence, and record first hypotheses against independently
identified verse/chorus spans before enabling automatic decisions. No need for
another broad external-dataset search or full-corpus run.


## 2026-11-17: opt-in boundary proposal research

Checklist:
- [x] Preserve first frozen outcomes; correct subsequent sampling to song families.
- [x] Test duration-invariant ordered note groups independently of exact rhythm.
- [x] Separate contextual boundary scoring from maximal matching runs.
- [x] Run targeted regression tests (40 passed).
- [x] Freeze algorithm hashes before evaluating two previously untouched song families.
- [ ] Validated verse/chorus classification or final song segmentation. NOT COMPLETE.

New callable: `section_boundary_proposals.analyze_boundary_proposals(features)`.
Returns original repeat output, duration-invariant alternatives, and contextual
boundary-ranked alternatives. Defaults of `section_repeats` and the generator
are unchanged. No section markers or editor labels enter inference.

Context boundaries compare within-context and cross-context bar similarity at
all available window sizes, excluding self similarity. Alternatives are ranked
by paired boundary evidence and retained repeat span. Endpoint extension defaults
to one bar and is explicit/configurable. Single-bar motifs remain in original
output, not treated as refined multi-bar sections. Additional note-order evidence
preserves simultaneous-note groups, condenses consecutive identical attacks, and
ignores duration. It is not an exact-rhythm match or evidence of vocal repetition.

Development evidence: 19 source-editor verse/chorus regions across four Invent
Animate songs. Source-editor labels are not verified ground truth. Oracle best
candidate overlap measures proposal recall/geometry, NOT chosen-label accuracy.
Duration-invariant-only experiment improved seven regions and regressed two while
doubling groups (248 to 504); not shipped as a replacement. Context-boundary
alternatives fix multiple chorus endpoint errors, but still fail to capture whole
transformed verse regions. Candidate count alone is never a success criterion.

Evaluation was frozen before loading Lightfinder and Naturehold. Lightfinder had
no editor section labels: execution only, unscored. Naturehold's two eight-bar
chorus regions retained exact-boundary candidates; verse overlap remained 0.5 and
0.444. No weight changes after that evaluation. These families are now consumed
holdouts, not fresh evaluation data for future tuning.

Limitations: this is opt-in research output, no final partition and no calibrated
function probabilities. Guitar melody recurrence is not chorus proof. Shared
repeat/boundary evidence supports sectionhood, not verse/chorus discrimination.
All existing automatic role labels remain unknown. More candidate recall does not
prove specificity. No audible playback, private annotations, or source scores are
published. Local experiment manifests/results remain on F:.

Next: investigate transformed verse coverage and independent function cues, with
new reserved families before tuning. Do not lower unknown just to produce labels.

Measured boundary-alternative development results: mean best IoU 0.553 -> 0.686; exact-boundary regions 2/19 -> 8/19; >=0.75 IoU 8/19 -> 9/19; thirteen improved, one regressed. Originals remain available, so consumers need not discard the regressed motif hypothesis. These are oracle candidate-coverage metrics, not classifier accuracy.
