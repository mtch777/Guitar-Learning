# Complete source-group rhythm control

Active implementation with ProjectPlanner3000, 2026-10-29. Private sources and
earlier failures stay untouched. No detector changes or guessed phrase boundaries.

## Musical change
Use a complete rhythmic group explicitly bracketed in the source. Change the
relative note lengths using another observed group in the same context. Keep
the group's start, total length, notes, physical positions and expression fixed.
The current development evidence is narrow: Leper Messiah has long-short-short
and short-short-long in the same repeated-note bass context, with one donor for
the latter. This is not a learned artist style or a complete rhythm lever.

## Acceptance
- [x] Planner START reviewed same-equation ownership, exact zero and dependencies.
- [x] One positive rational duration-share relation owns source notation lengths
  AND corresponding musical onsets/durations; no old duration-vector backup.
- [x] Complete source-bracket discovery, explicit reasons for excluded groups,
  source-derived choices and disjoint supporting occurrences.
- [x] Compose the representation with existing chord/voicing and optional-accent
  owners. Joint nonzero-policy combinations remain OPEN.
- [x] Exact zero; invalid shares, duplicate owners and unsupported notation fail.
- [x] Changed source timing and musical timing agree; all other source facts,
  outside clocks and nominal pitch contribution remain fixed. Recompute views.
- [x] Independently check 0/50/100 release vs actual-change counts; preserve
  no-choice outcomes. At100 no original-target-value preference.
- [x] Actual inverse with source/lower/cache unavailable; independent comparison.
- [x] Development source GP/MIDI/audio checks, then new frozen random source;
  preserve failures and distinguish reconstruction from a supported new change.
- [x] Planner MID/END and relevant regressions.
- [ ] Commit/push and exact-head CI.

## Fixed scope
Single ordinary pitched note per beat, repeated identical pitch/string/fret,
flat undotted non-tuplet notation, complete explicit source bracket, clear clock,
constant known dynamic and no execution dependencies. Initially refuse other
active same-part voices and shared coattacks. Different attack alignment against
other instruments is an expected consequence, not a claim of unchanged note role.

## Progress
Starting from published82c7bc8 (CI40943360261 success). Existing five-source
inventory and independent census are private under source-beam-boundaries-v1 and
source-beam-opportunity-v1. Existing pair-only approach found no choices; complete
groups have69 development opportunities. These cover TWO contexts:39at offset1q
(changed donorbar166) and30at offset2q (changed donorbar162). Earlier prose pooled
them incorrectly; source ledgers were correct and are preserved.

## Implemented and measured
`source_rhythm_groups.py` reads complete source brackets and records every
exclusion. Planner independently matched all6,170groups across the five fixed
captures. `group_rhythm_relations.py` owns span/shares once, deriving BOTH source
type/fraction notation and musical onset/duration; selected old scalar/time
owners are absent. Original nonreduced fraction encoding is preserved. The
wrapper composes plain, voicing-family, declared-chord and optional-accent data.

`local_group_rhythm.py` chooses complete observed vectors using the existing
release mechanism. Input notes never come from external musical material or AI.
100% ignores the original target vector in selecting among donor occurrences;
same-value outcomes remain possible. Every unaffected captured fact is checked.

Leper development (`run_group_rhythm_qa.py`):94,113facts exact;1,829groups,
150eligible,69with changed choices.117,056draws perstrength.0%:0release/0change;
50%:62,186release/60change;100%:117,056release/60change. Shared64seed schedule has
53.125% releases at50%; changed outcome counts are not release probabilities.
Actual source-denied zero/no-choice/changed workers allPASS. First changed draw:
bassbar39,offset2q,seed25,shares1/2+1/4+1/4 ->1/4+1/4+1/2,donorbar162.
No manual target or alternative selection; not a fresh-song result.

Native GP/MIDI/PCM nowPASS on the same actual inverse outputs. Exactly two GP
length references change; three MIDI notes have the expected start/end changes,
with pitches, velocities and all other notes fixed. Source/zero PCM is exact;
5.294second focused/ensemble clips differ by RMS0.0114387. Human fit unjudged.
Initial native build failed an auditor assumption requiring a preexport recovery
file even when standalone roundtrip passed. The original failure/log remain.
Follow-up exposed unbound center-pitch resets moving with attacks. Independent
actual MIDI regeneration binds them to their generating note; only unchanged
center resets at that note's verified attack may move. Arbitrary controllers,
pitch bends and unrelated events remain prohibited. Recovered audit is separate
from the original failed invocation; no native/audio files regenerated to hide it.

Native reviewer added8corruption tests. They caught and prompted checks for full
capture/archive contents, runtime bindings, actual GP note lengths, all six audio
job/result bindings and unowned MIDI controls.24focused rhythm tests pass.
## Fresh-song verification

The unchanged logic was tested on the same new random song as melody:
**B.Y.O.B., System of a Down, Songsterr 6699, revision 6668952, seven parts.**
The seed and 653 dependency hashes were saved before selection. The first
download attempt failed before requesting the candidate pool because the
analysis environment lacked `httpx`. Its failure remains intact. Replaying the
same seed, query and exclusions with the existing download environment selected
the song; Planner independently reproduced the selection and verified every
archived dependency.

- All **92,617 captured facts** reconstruct exactly in actual source-denied
  zero and no-choice workers.
- All **1,846 complete rhythmic groups** were independently checked; 63 qualify,
  but none has independent alternative rhythms under the declared locks.
- All 354,432 draws reproduce independently: zero changes at every strength.
  This is a portability and preservation pass, **not a fresh creative pass**.
- Original and reconstructed GP archives match, as do all 47,099 MIDI events.
  Existing source/model and native checks pass within their declared scope;
  four percussion grace notes are outside the pitched-grace oracle.
- The earlier Leper changed example remains the actual audible development
  proof. Its native review independently reproduces 9,233 notes and 31,378 MIDI
  events per version; the original failed audit remains preserved separately.

## Integration checks and limits

`python -m unittest discover -s . -p 'test_*.py' -q`: **1,519 run, 1,518 passed,
one optional skip** in 216.232 seconds. Relevant Node checks: **48 passed**.
Vite production build passes after safely incorporating main's unrelated Time
solo UI changes through `712411f`.

Three combination tests verify exact zero across the four local controls,
disjoint rhythm/accent changes at all nine 0/50/100 pairs in either order, and
atomic refusal of an accent inside a plain rhythm group. These are synthetic
relationship tests, not a global control interface or combined musical approval.

Full rhythm remains open: broader patterns, global scheduling and human fit are
not proven. The next evidence check is contextual palm muting. It must show
actual source alternatives and renderer behavior before implementation; the
melody branch stops at its observed no-choice result.
