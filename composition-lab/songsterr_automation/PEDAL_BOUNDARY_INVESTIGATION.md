# Pedal repetition and continuation investigation

Status: open. User feedback supersedes earlier broad identification acceptance
for the specific failures below. Presentation patches are not analyzer fixes.

## Reported failures and confirmed evidence

- Nocturne: Lost Faith, explorer example-12: the user hears the same pedal idea
  continuing after the original excerpt. Region boundaries change at a reduced
  anchor voicing. A manually extended bars 4–12 preview is available, but does
  not establish a general continuation correction. The adjacent-subset category
  exclusion is a narrow presentation rule, not validated phrase segmentation.
- Forest Haven, Track 1, bars 13–15, explorer example-03: the private case has
  exactly one call attack, at rational quarter-time 52, and one unclosed response.
  Its selected cycle has no anchor return. Its label claims a two-note returning
  pedal even though this call contains only one of the region's two anchor pitches.
  The selector iterates every cycle and takes `cycles[i:i+2]`, allowing the final
  singleton. Category `interval` checks the parent anchor size, not the excerpt's
  actual repetition or dyad attacks. This establishes a selection/label failure;
  it does not alone prove the parent detector is wrong.
- Forest Haven's parent region spans quarter-time 0–211/4, with 95 call events
  grouped into only two call bursts starting at 0 and 52. Investigate whether long
  gaps, rests, or unrelated intervening material are being absorbed into bursts.
  The next region starts at 211/4 with a reduced single-note anchor. Do not assume
  that related pitch sets alone establish continuity.

## Required procedure and acceptance criteria

1. [x] Record what the user reported without replacing it with a convenient
   numerical interpretation. Both reports and their affected examples are above.
2. [x] Inspect the exact private examples and their source-located analysis.
   Record actual calls/returns, scope and labels; retain original artifacts.
3. [ ] Trace why each original scope/excerpt ended where it did, from source
   occurrences through candidate detection, dialogue grouping and UI selection.
4. [ ] Trace why continuation/repetition was missed or misrepresented. Distinguish
   detector, event-role, burst, region-boundary, clip and label failures.
5. [ ] Review the design contract: pedal evidence requires returning anchors;
   parent-region membership, adjacent subsets, two arbitrary slices and category
   variety do not independently prove a local musical pattern. Separate literal
   measurements from musical-function claims and preserve explicit uncertainty.
6. [ ] Establish root causes with minimal source-derived regressions and negative
   controls. Include a lone note, sustained/tied note, long silence, one-off dyad,
   arpeggio, repeated anchor, voicing reduction and unrelated adjacent shared pitch.
7. [ ] Compare alternatives: excerpt evidence gates alone; gap-aware burst
   segmentation; candidate-local recurrence; continuity links retaining original
   regions. Record tradeoffs before selecting a correction; no song-specific rules.
8. [ ] Compare corpus-wide deltas against frozen accepted examples and negatives.
   Report changed membership, durations, call counts, truncations and abstentions;
   inspect newly joined/split/accepted/rejected cases. Passing parser tests or
   increasing counts is not musical correctness. Set thresholds using evidence,
   not these two cases alone.
9. [ ] Implement the supported general correction; regenerate affected private
   analysis/UI from scripts, preserve baselines, run relevant Python/JS/build and
   remote checks, commit/push. Remove reliance on manual clip overrides for claims
   of analyzer correctness. Keep copyrighted source material and feedback private.
10. [ ] Present source-grounded before/after examples, unchanged accepted controls
    and difficult counterexamples with complete visible pitch ranges and playback
    tracking. Ask whether boundaries and returning anchors match the user's ear/eye.
    Only human feedback can close this musical acceptance gate.

## Inspection log

- 2026-10-18: pulled origin/main safely (already current at 44b2f99), inspected
  explorer selection, dialogue runner, private example-03 and parent dialogue.
  Scripted private JSON queries confirmed the counts/times above. No detector
  correction, experiment comparison or new listening acceptance claimed.
- Next action: inspect the event/burst construction and original region candidate
  support for both failures; build the shared regression/evaluation set before
  choosing a boundary rule. No user input is needed for this investigation yet.
