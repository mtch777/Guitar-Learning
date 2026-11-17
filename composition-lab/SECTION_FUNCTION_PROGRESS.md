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
