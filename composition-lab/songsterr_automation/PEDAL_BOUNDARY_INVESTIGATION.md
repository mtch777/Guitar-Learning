# Pedal repetition and continuation investigation

Status: open. User feedback supersedes earlier broad identification acceptance
for the specific failures below. Presentation patches are not analyzer fixes.

## Expanded investigation, 2026-10-18

Eight additional passage reports and two accepted exclusions are preserved in
the ignored private investigation folder, with case identities and uncertainty
about exact unmarked occurrences. These are development judgments, not held-out
accuracy labels. All 16 displayed cases were scripted against original track
rows, preserving ties and rational times. New private reports are audit.json and
audit-v2.json; original UI/data/audio remain preserved for comparison.

Confirmed failure classes:

- Example selection can show only a final, unclosed exchange. Four of the 16
  examples have a singleton selection. Parent membership does not prove local
  recurring pedal function.
- Section-wide hypotheses and selected-region event maps leak into local labels:
  fresh clip-local detection chooses different anchors in several reported cases.
  Notes outside the selected region can be gray despite nearby recurrence.
- The detector requires two separated contrasting attacks, which can be two notes
  in ONE answer. This does not establish two departures and returns.
- A dyad qualifies against its LOWEST pitch, allowing a high member with no higher
  answer. One displayed dyad has this problem.
- Event-level mixed labels were copied onto individual notes. The 16-case audit
  counts 73 anchor-member notes and 10 non-anchor notes labeled mixed. This loses
  member roles without establishing that the underlying anchor is correct.
- Historical negative examples are copied from older judgments rather than
  recomputed. One disputed negative remains missed by every tested policy.
- Changing anchor pitch/voicing can preserve a concept even when an exact-pitch
  region ends. Neither adjacent set overlap nor a manually extended clip validates
  that relationship.

Design correction: distinguish an anchor hypothesis, occurrence membership,
coattack texture, observed return, local repeated pattern and conceptual
continuation. No one of these is a substitute for the others. Preserve unknowns
instead of filling category slots with poorly supported evidence.

### Experiments actually run

Script: songsterr_api/audit_pedal_explorer.py. Frozen input hashes are in the
private report. All eligible corpus tracks are compared under the same inputs.
Changed tracks include changed evidence quantities, not only membership changes.

| Policy | Regions | Changed tracks | Removed / added anchor-section keys |
|---|---:|---:|---:|
| Frozen baseline | 1563 | 0 | 0 / 0 |
| Require two distinct return pairs | 1301 | 104 | 270 / 8 |
| Higher contrast above the whole anchor | 1531 | 68 | 32 / 0 |
| Both policies | 1276 | 146 | 295 / 8 |

The two accepted exclusion passages stay excluded in clip-local experiments.
However, tightening returns can remove a low candidate and expose a HIGHER
replacement in a reported problem passage. All variants still miss the disputed
changing-anchor negative. Therefore neither the combined policy nor the return
policy is accepted as a general repair. Defaults remain frozen; policy keyword
arguments are explicit experiment controls. No new musical accuracy is claimed.

### Implemented independent corrections

- The builder rejects a selected singleton or a pair without an observed anchor
  return. Regression covers both rejection and a valid returning example.
- Dialogue events now retain per-occurrence call/response/unknown memberships,
  while preserving the original coattack group kind and every source note.
  The builder uses individual memberships rather than painting all coattack
  members mixed. These roles remain conditional on the supplied anchor.
- New regression probes distinguish two answer notes from two returns and a
  high dyad member from a genuinely higher answer. These compare alternative
  policies; they are not proof of perceptual accuracy.

The current listening UI has NOT been regenerated as a supposedly corrected
review. Its old labels remain investigation evidence, not accepted results.
Continuation linking, stable-bass candidate competition, changing-anchor families
and simultaneously sounding response measurement still need general correction.
Next: compare context-local anchor families and candidate competition before
regenerating source-based evidence. Do not ask for another broad listening review
while these known failures remain unresolved.

Verification: Python unittest discovery ran 232 tests, one optional dependency
skip, no failures; node --test tests/*.test.mjs passed all 21; Vite production
build passed via node node_modules/vite/bin/vite.js build (npm unavailable on
this shell PATH). No source scores, private annotations or media committed.

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
