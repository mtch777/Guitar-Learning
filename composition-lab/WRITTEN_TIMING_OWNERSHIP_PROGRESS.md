# Written timing versus permission to change rhythm

## Why this change is needed

Adding an accent or palm mute previously invalidated a stored rhythmic group,
even when every written start and duration stayed identical. The model had used
the rules for changing a plain repeated rhythm as rules for representing time.
Those are different questions.

## Acceptance checklist

- [x] Planner START and MID agree on the distinction and bounded versioning.
- [x] Existing `source-group-rhythm/1` admission and default behavior stay exact.
- [x] Explicit `/2` represents valid written timing with independently owned
  expression, dynamic boundaries or different known pitches.
- [x] Both versions use the same span/share/prefix equations.
- [x] All current rhythm-change restrictions remain unchanged.
- [x] Unknown fields/clocks, unsupported notation and conflicting references
  remain failures; unknown future refusal reasons fail closed.
- [x] An actual accent edit preserves `/2` time ownership; a subsequent
  incompatible rhythm request remains refused.
- [x] Complete palm-mute owner combinations, corruption checks and isolated runs.
- [x] Complete real-source comparison and the unchanged new-song run.
- [x] Independent Planner END review of the declared scope.
- [ ] Publication and exact-commit CI.

`python -m unittest test_structural_rhythm_ownership test_group_rhythm_relations
test_local_group_rhythm test_local_lever_combinations -q`: **18 passed**.
Planner independently reran the four new structural tests and five palm-mute
owner tests. This is representation compatibility, not permission for arbitrary
joint musical changes or a physical-performance model.

## Actual source and regression evidence

`python -m unittest discover -s . -p 'test_*.py' -q`: **1,556 run,
1,555 passed, one optional skip**, 223.777 seconds. Full private log:
`local-artifacts/palm-mute-full-regression.log`.

Sweet Child's actual isolated 0/50/100 runs preserve all locked source facts.
The first source-selected change removes one beat's palm-mute marking from
three simultaneous notes. Independent GP and MIDI checks allow only those
three mute flags and their three performed release times to differ. Source
and zero PCM match; changed PCM differs. Its pre-existing standalone GP bend
loss remains explicit; this comparison uses the hash-bound bend companion.

After freezing 667 code dependencies, the new random capture was Innuendo
(24056, revision 6955102, 16 parts). Actual zero and no-choice inverse workers
recover all **91,443 source facts**. Independent source review finds all
**4,320 coattacks lack a palm-mute marking**: no on/off alternative is available.
All 414,720 draws are retained, with no forced change or replacement song.
Both native outputs preserve 16 tracks, 156 bars, 7,001 notes and all 23,093
MIDI events. The standalone checked-model roundtrip passes on this capture.
These receipts establish bounded representation and honest refusal, not a
fresh creative success or an inference about the recorded guitarist's touch.

Private receipts are under `local-artifacts/palm-mute-control-v1`:
`planner-fresh-qa1.json`, `fresh-independent-audit.json`,
`native-zero-review/review-summary.json`, and the development native audit.
The original run reports remain unchanged; later independent review is
recorded separately rather than rewriting their historical pending fields.

Planner's final `planner-fresh-worker-end.json` independently compares the
actual zero and released no-choice outputs against all 91,443 raw source facts
and rechecks all 667 live/archive hashes. Bounded implementation is accepted;
whole-lever creative generalization and human musical judgment remain open.

## Previous verified checkpoint

Commit `fcf5cd609849aaa9cc5abaeebb90f3477572e657` was pushed to main. Its exact
[Composition Lab CI run](https://github.com/mtch777/Guitar-Learning/actions/runs/40984761613)
completed successfully. That checkpoint contains the development rhythm change,
bounded melody logic, grace-chord repair, and the preserved B.Y.O.B. no-choice
results. This versioned ownership work is subsequent work, not part of that
already completed frozen test.
