# Source-supported melodic choices

## Purpose

Change a note inside a short written melodic sequence using another execution
already present in the same song. Keep the neighboring notes, rhythm, emphasis,
techniques and other parts unchanged. This is a local melody control, not a
phrase detector, inferred artist intention or permission to choose an arbitrary
note that belongs to a scale.

## Start decision

The first proposal (enumerating seven modes and adding a collection pitch owner)
was rejected before implementation. Existing collection coordinates already
reverse exactly; another report or pitch owner would not unlock a useful change.

The revised proposal was approved by ProjectPlanner3000 at the start and middle.
It uses the existing pitch relationship, all consecutive three-attack source
neighborhoods, and all retained surrounding-chord membership alternatives. The
selector and percentage policy are implemented; no new pitch owner was added.

## Acceptance checklist

- [x] Planner agrees the source neighborhood and locks mean something musically.
- [x] Freeze a small fixed-source opportunity experiment before inspecting its results.
- [x] Count all eligible neighborhoods and retain every refusal; no easier-song search.
- [x] Alternatives come from disjoint source examples with matching timing,
  physical lane, outer pitches, written emphasis and surrounding harmony.
- [x] The same existing relationship realizes the changed pitch/fret; no second
  note generator or stored original-pitch fallback.
- [x] Exact zero, source-supported 50/100 choices, unknowns and contradictory
  requests have independent tests.
- [x] Complete reconstructed source comparison permits only the intended middle
  note's fret to change; all timing and other facts remain equal.
- [x] Actual isolated inverse, composed-owner checks, fresh frozen-song trial and
  Planner END completed within the bounded/no-choice scope.
- [ ] A real admitted change, GP/rendered-audio checks and listening acceptance
  are still required before claiming a delivered melody control.

## Observed fixed-source results

These five previously captured songs are DEVELOPMENT inputs, not fresh random QA.
The census protocol was saved before inspecting the counts; its unchanged replay
matched all five complete inventories exactly. Original failures are preserved.

| Source | All consecutive neighborhoods | Qualified plain neighborhoods | Preliminary targets with independent alternatives |
| --- | ---: | ---: | ---: |
| Sweet Child | 6,666 | 446 | 2 |
| All Small Things | 4,519 | 296 | 0 |
| Queen capture | 2,930 | 50 | 0 |
| Knockin capture | 4,711 | 303 | 11 |
| Leper Messiah | 7,544 | 774 | 0 |

All 13 preliminary targets were checked against their entire-duration harmony.
The original strict qualification admitted **zero**. Three targets had only a
generic supporting-tie refusal. This exposed a missing relationship: complete,
resolved written tie chains were treated like unknown ties.

Planner approved a versioned opt-in qualification. It uses the accepted same-lane
tie equations; complete origin/chain references are recorded and included in all
target/donor exclusion closures. Missing origins, ambiguous attacks, pitch/gap
changes, unknown clocks and any other expression anywhere in the chain remain
refused. Selected notes cannot be part of a tie chain. Legacy contracts remain
strict. An independent raw-source checker follows literal continuations backward.

An intermediate v2 reported two Knockin contexts qualified. Self-review and
Planner's independent actual-source check exposed an omitted condition: their
supporting tie chains also had `letRing`. Pitch-effect flags alone did not enforce
the approved exclusion of other execution. The final rule checks literal
markings throughout each chain. On the actual bar10 source, producer and
independent checker now agree: **MISSING**, with identical complete qualified-ref
sets (247 each). The earlier v2 result and discrepancy remain preserved.

**Zero of the 13 targets admits a real changed note.** The final stricter ledger
completed on the same fixed development candidates: all13 retain a missing
supporting-harmony qualification. No weaker constraint,
extra source or manually picked note was introduced.

## Commands and artifacts

- `python -m unittest test_verified_written_tie_support test_context_membership test_melodic_contour_choices test_run_melodic_contour_qa -q`: **37 passed** (actual isolated percentage-policy executions and runner positive/no-choice cases included).
- `python audit_melodic_contour_opportunities.py ...`: all five source censuses, then identical frozen replay.
- `python audit_melodic_contour_choices.py ...`: every preliminary target, strict then opt-in written-tie context; both complete results retained.
- Private evidence: `local-artifacts/melodic-contour-v1/`, including protocols, all census rows, exact replay receipt, full-context failures, test failures and subsequent successful retests.
- `run_melodic_contour_qa.py`: shared-freeze-compatible runner. It records every neighborhood/choice/draw, actual source-denied zero/no-choice/changed workers, independent complete-source parity and independent changed-output check. No-choice is coverage, not creative acceptance.
- Final focused runner tests and final-rule fixed-source replay passed within their declared scope. Planner END approved the final guard and the bounded no-choice result. Code is frozen for root's shared random capture; only private evidence/documentation may change. No fresh selection has been made by this worker.

## Shared fresh-song QA

Root froze all code before selecting **System of a Down — B.Y.O.B., Songsterr6699**.
The capture environment failed once and was recovered using the same registered
seed; the original failure and recovery receipt remain. No replacement song was
selected. Code hashes remained unchanged through analysis and independent review.

- **92,617 original source facts:** exact reconstruction through the actual
  source-denied worker, checked outside the worker against captured JSON.
- **7,306 consecutive neighborhoods:** independently rebuilt from raw documents,
  accepted clocks and existing execution detectors. Every field/refusal matched.
- **6,424 excluded;882 qualified:** no qualified target had two independent
  matching source outcomes. All donor sets and dependency closures were checked.
- **701,376 draws checked:**233,792 at each of0/50/100%; releases0/116,896/233,792;
  **zero changes**.100% release never forces an unsupported note.
- Actual zero and no-choice policy workers both passed. Independent receipt:
  `local-artifacts/parallel-levers-v1/melody-independent-review.json`.

This verifies bounded negative coverage and exact reconstruction. It does not
close the melody lever or establish an audible improvement or artist fit.

## Remaining acceptance gaps

1. A real source-qualified changed melody example; none exists in the fixed development set or shared fresh source under the complete locks.
2. Native GP/MIDI/audio comparison and listening only after an actual admissible change exists. The full melody lever remains OPEN.

## Current limitations

Keys/modes remain provisional. A preserved direction or chord-membership label
does not establish phrase function, emotion, artist style or human playability.
Fresh-song and listening acceptance must remain separate from development tests.
