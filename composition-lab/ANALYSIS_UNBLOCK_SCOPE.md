# Analysis unblock scope — 2026-10-18

Read-only initial investigation; no detector, source score or export repairs made.
Main was pulled with `git pull --ff-only origin main` (already current).
Existing uncommitted composition work was preserved. Pedals remain approved.

## Checklist and acceptance

- [x] Inspect timing, tie, technique and export code; query actual captured data.
- [x] Separate observed causes from repair hypotheses; preserve unknowns.
- [x] Rank work by recovered analysis, repair risk and existing alternatives.
- [ ] Fix whole-bar rest interpretation only after confirming source semantics;
  preserve literal duration, use meter for explicitly established measure rests.
- [ ] Localize timing exclusion to affected regions and relationships, with
  cross-boundary guards; do not silently restore uncertain sustain contexts.
- [ ] Distinguish unpitched/dead ties from pitched sustain; independently check
  all resolved links and keep mixed dead/pitched transitions unresolved.
- [ ] Decode slide relationships with endpoint/type-specific tests.
- [ ] Quantify and repair bend curve path differences; independent GP reopen and
  unchanged passing cases required. No listening verdict inferred.

## Priority and measured pulse

| Rank | Issue | Findings | Smallest useful next action |
|---|---|---|---|
| 1 | Bar overflow | 20 program-eligible guitar/bass tracks contain 2,152 track-bars; 39 flagged voice/bar observations occupy 39 distinct track-bars. Only 94 of their 10,323 regular segments lie in flagged bars. 27 flags are single whole rests (`type:1`, duration `[1,1]`) in meter spans 1/2, 5/2 or 3 quarter notes. Remaining 12 flags have just two duration patterns: ten total13/4 vs span3; two total3 vs span2. No grace or tuplet fields on these flagged voices. | Confirm measure-rest semantics; separate silent convention from actual note overflow. Localize exclusion rather than guessing note durations. |
| 2 | Unresolved ties / dead notes | Of 21 unresolved guitar/bass destinations on timing-eligible tracks, all have contiguous timing and matching frets; all previous notes are dead. 18 destinations also dead; three become pitched. Current sustain matcher requires known MIDI, so dead/dead cannot match. | Test an explicit unpitched continuity representation; do not turn dead notes into pitched sustain or assume dead→pitched is valid. |
| 3 | Slides | Program24–39 regular segments contain 1,651 shift, 1,054 legato, 166 downwards, 75 below, three above slide values (2,949 total). Type vocabulary already exists. | Resolve specified-note shift/legato candidates separately from entry/exit slides; verify same-string timing, tie and grace behavior. Endpoint coverage not yet measured. |
| 4 | Bend exports | Saved numeric61-sample snapshots cover435 bend-note comparisons;176 differ. None changes sampled start, end or peak. Path deltas vary, so this is not established as a harmless representation change. Snapshot-format cohort is not the entire corpus. | Inspect exporter curve representability and intermediate-point timing; quantify error per note without weakening comparison tolerance. Raw-source bend analysis remains available. |
| 5 | Ghost notes | Program24–39 regular segments contain928 active ghost markings;31 carry explicit note/beat velocity. | Preserve annotation separately from dynamics. Compute marked-note context now; never invent calibrated loudness for the other897. |

Dead notes are bundled with ties because they share the observed cause. All1,939
active dead markings in this initial program-filtered scan already have null
written pitch. This is not a missing dead-note detector. Counting/placing them
does not require reconstructing their exact percussive sound.

## Interpretation limits

- 2,113/2,152 track-bars (98.2%) are not directly flagged. This is recovery
  opportunity, not a guarantee all can immediately re-enter every relationship.
- 94/10,323 regular segments (0.91%) lie in flagged bars; cross-boundary ties,
  overlap and context still need guards. Track-wide exclusion is much broader.
- These scans use instrument programs24–39, not every later catalog/temporal
  eligibility filter. They are scoped diagnostics, not replacement corpus rates.
- The27rest flags are a strong representation hypothesis, not a proved fix.
- The21ties describe guitar/bass timing-eligible material, not all51 corpus ties.
- Bend sample checks compare saved intermediate-model/export snapshots, not raw
  precise API curves or recorded performance. No audible severity established.
- Existing source data remains immutable. No copyrighted notation published.

## Evidence and commands

Read `songsterr_automation/songsterr_api/analyze_relationships.py`
(`occurrences`, `pitch`, `track_analysis`), `source_semantics.py`
(`sustain_context`) and `export_csv_gp7.mjs` (`curve`, `snapshot`, `simplify`).
Python/Fraction read-only scans consumed all captured track JSONs and saved
roundtrip snapshots. Aggregate diagnostic outputs are privately retained at
`local-artifacts/analysis-unblock-scope.json` and
`local-artifacts/analysis-unblock-followup.json`. Follow-up scan classified the
two pitched-overflow patterns and18dead/dead versus3dead/pitched tie cases.
No implementation tests claimed: this change is an investigation report only.
