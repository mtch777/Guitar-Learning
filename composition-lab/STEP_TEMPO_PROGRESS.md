# Component-conditioned passage speed

## Musical scope

The accepted experiment asks whether an exactly recurring guitar rhythm has
independent source examples at different speeds. It changes the whole band's
speed over the existing tempo event's interval, with written notes, rhythms,
expression markings, and the next tempo event fixed. Other parts can lack
matching source examples. That remains PARTIAL evidence, not band consensus,
transition suitability, whole-passage suitability or artist approval.

Planner approved this preregistered component stratum after reviewing B.Y.O.B.
bars 95 and 144. The observed alternatives are 153 and 162 BPM. These numbers
are source observations, not constants in the algorithm. No source replacement
or weakened matching rule is permitted if an execution check fails.

## Acceptance checklist

- [x] Preserve the complete A/B/component census, missingness and native limits.
- [x] Planner START decision based on the actual source, not a desired result.
- [x] One global speed parameter replaces all agreeing source BPM copies.
- [x] Same equation in both directions: seconds per quarter multiplied by BPM
  equals 60; source alias types, membership and time intervals are checked.
- [x] Exact written-pass seconds derived from those same parameters; no invented
  initial tempo or interpolation. Performed repeats require a separate ledger.
- [x] Exact zero and typed/corrupt/unknown owner tests; actual source-denied zero.
- [x] Independent MID review of owner and context choices; 8 owner and 8 policy
  tests independently rerun. Exact source fact order needs its own audit guard.
- [x] Actual development 0/50/100 inverse and independent raw-path expected
  source comparison. Complete source-context/draw review is still separate.
- [x] Development native GP, performed tempo/seconds, expression consequences
  and audio. Fresh no-choice source/zero path is being completed before freeze.
- [x] Freeze before one new random source; retain every result and failure.
- [x] Record all three QA verdicts and obtain independent END review.
- [ ] Source-only commit, push and verified CI.

## Current implementation

`step_tempo_relations.py` stores each global event's quarter duration, written
influence interval and source BPM references. It stores no original BPM backup.
`connected_tier2` owns it explicitly with `step_tempos=True`; prior defaults
remain unchanged. Optional accents, palm mutes and written-time ownership still
compose. The inverse recomputes the source clock to reject missing, conflicting
or falsely linked tempo aliases. Unknown declarations retain literal ownership
and cannot silently become a qualified clock.

Data-only temporal adapters were replayed against all seven saved censuses:
every original result remains equal. A previously untested beat-local branch
had a duplicate argument; its fix is covered by an unsupported-map refusal test.
No original source candidate or matching condition changed.

Commands so far: owner/default/written-time subset **23 passed**; updated
owner/census/policy subset **21 passed**. These are development checks, not
completed real-song or fresh-source acceptance.

Private evidence remains under `local-artifacts/tempo-census-v1`,
`local-artifacts/tempo-native-semantics-v1`, and the upcoming
`local-artifacts/step-tempo-control-v1`.

## First actual development result

`run_step_tempo_qa.py` on the frozen B.Y.O.B. capture:
**92,617 facts**, **128 component opportunities**, **12,288 draws**.
Two components have observed alternatives; 126 cannot change. All zero,
no-choice, 50% and 100% source-denied workers pass. The first source-ordered
changed draw is bar 95, part 3 voice 0, seed 0: **153 to 162 BPM**, all seven
source aliases together, written interval **376 to 392 quarter notes** fixed.
0%: zero changes; 50%: 2,048/4,096 releases and 14 actual changes;
100%: 4,096 releases and 30 actual changes. Release includes no-choice cases;
it is not the percentage of notes actually changed.

`python -m unittest discover -s . -p 'test_*.py' -q`:
**1,583 run, 1,582 passed, 1 optional skip**, 245.746 seconds. This checkout
contains unrelated retained WIP tests; this is a local result, not a published
CI count. Source/native freeze and independent playback proof are still open.

The same retained development artifacts now pass the hardened native audit:
8,767 written notes; 8,681 MIDI attacks in each case; complete actual MIDI and
origin streams equal the one-BPM validation reference. All 1,180 native dead/
palm-mute duration caps per case satisfy the independent equations. Only bars
95–98 change speed; bar 99 resets. Original and zero PCM match exactly; both
focused and whole-band changed PCM differ. Source-bar-aligned duration falls
by 160/459 seconds (about 0.349 seconds), allowing renderer buffer rounding.

The initial full-model comparison failed on regenerated chord-diagram UUIDs.
That failure is retained. Only declared IDs and their references are now
canonicalized, with orphan references rejected; complete GP XML remains
compared independently. No musical field or converter was changed for this.

## Frozen new-song gate

Seed **5918555136526282279**, frozen before acquisition, selected Franz
Ferdinand **Take Me Out**, song **7648**, revision **9282703**, nine tracks.
682 dependencies were hashed, archived and reread. Planner independently
replayed the selection from 94 eligible IDs and verified the exclusions and
archive; the pool is a letter-search result, not the complete Songsterr catalog.

`run_step_tempo_qa.py .../frozen-v1/fresh/capture .../fresh-first --freeze ...`:
**74,381 source facts exact**, actual source-denied zero and no-choice workers
pass. All **54 components** are refused by the native tempo-map gate. All
**5,184 draws** remain unchanged. No source, seed, candidate or failure replaced.

The song explicitly declares gradual tempo and four linear tempo marks. The
frozen **step-only native checker fails/refuses** that unsupported execution
scope. This is retained as a real limitation, not converted to a passing ramp
test. Separate read-only verification proves original/zero full GP/MIDI
equality and source/native quarter geometry: **9 tracks, 109 bars, 8,578 notes,
26,341 MIDI events**. Equality does not establish faithful ramp playback.

Final local frozen regression: **1,599 tests run, 1,598 passed, 1 optional
skip**, 305.999 seconds; **48 JS tests passed**; Vite build passed. This includes
unrelated retained WIP tests and is not the eventual published CI count.

Planner independently verified every fresh option/refusal and all 5,184 draws,
both actual workers and all 682 live/archive hashes before closing the freeze.
QA1 selection and exact source reconstruction pass; QA2 exact zero/no-choice
passes; QA3 preserves conditional musical evidence and correct refusal, but
does not validate a changed fresh passage or ramp performance.

After that freeze closed, the native worker promoted the independently checked
source/native quarter geometry assertion into the reusable zero checker.
**35 targeted tests passed** (17 tempo, 10 palm mute, 8 rhythm). New receipts
under `post-freeze-geometry-review` verify the same development zero and retain
the same fresh ramp refusal. Original frozen reports and archive are untouched.

The converter currently drops the source gradual/linear fields; toggling them
leaves its complete model unchanged. The native renderer also ignores its
linear flag for MIDI timing. `TEMPO_RAMP_NATIVE_PROGRESS.md` records the proof.
The next bounded check must establish Songsterr's actual clock semantics before
any interpolation repair. The tempo lever remains partial.

Remaining for this bounded delivery: source-only commit/push and verified CI.
