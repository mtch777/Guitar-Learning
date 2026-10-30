# Palm-muting opportunity census

Initial scope: source opportunity census. Planner/root subsequently approved a
bounded optional palm-mute owner and source-observed control using these exact
unchanged census predicates. Approved technique detectors are untouched.

## Acceptance checklist

- [x] Preregister exact source set, matching conditions and source/code hashes before counts.
- [x] Reuse the same five development captures; label previously seen B.Y.O.B. separately.
- [x] Count every complete same-part written coattack, all source exclusions and unlocated notes.
- [x] Preserve absent/false/true palm-mute declarations and refuse other types.
- [x] Compare only identical pitch, physical shape, duration, metrical position and known dynamics, with other source markings held fixed.
- [x] Exclude linked execution and overlapping/dependent source witnesses.
- [x] Report independent on/off pairs separately from leave-target-out opportunities.
- [x] Ask Planner to review counts/limits; obtain implementation scope before proceeding.

Absence means an absent source declaration, not verified unmuted physical playing.
No musical-fit, native-playback or fresh-random acceptance is claimed by a census.

## Preregistered census result

Private evidence: `local-artifacts/palm-mute-census-v1/protocol.json`,
`census/result.json`, and per-capture inventories. Protocol and source/code hashes
were recorded before counts; all matched at census completion. These are fixed
development captures, including B.Y.O.B. (already seen by the melody/rhythm work).

| Capture | Complete coattacks | Eligible | Independent on/off pairs | Targets with two independent on/off witnesses |
|---|---:|---:|---:|---:|
| Sweet Child | 5,791 | 1,443 | 10 | 8 |
| All the Small Things | 3,794 | 1,266 | 0 | 0 |
| Queen capture | 2,186 | 512 | 56 | 25 |
| Knockin' | 4,158 | 1,167 | 15 | 15 |
| Leper Messiah | 6,418 | 3,088 | 256 | 91 |
| B.Y.O.B., previously seen | 6,069 | 1,983 | 0 | 0 |

Original five: **337 independent pairs; 139 eligible target opportunities**.
Every raw note occurrence was located. Real captures used absent/true flags;
explicit false, unknown typed values, mixed coattacks and linked-execution
exclusions are covered by authored tests. No matching condition was relaxed after
these counts. B.Y.O.B. has both muted and unmuted events but no matching context
with independent on/off witnesses under this policy.

## Implementation acceptance

- [x] One optional beat owner preserves absent / explicit false / explicit true
  and original field order at zero. Unknown types remain unclaimed.
- [x] Whole same-part coattack changes all participating beat declarations using
  their ordered source correspondence. One source coattack supplies one vote.
- [x] Source-only alternatives retain pitch, physical shape, duration, position,
  known dynamics, other notation and non-overlapping dependency closures.
- [x] Zero is literal lock; 50 releases with probability 0.5; 100 releases without
  forcing difference. Literal absent/false changes are distinct from mute changes.
- [x] Actual source-denied workers tested at 0/50/100 on authored fixtures.
- [x] Optional accents and structural timing ownership compose; mutation does not
  grant permission to change an otherwise ineligible rhythm group.
- [x] Full inverse rejects missing owner plus its rule, duplicated old technique
  owner, forged child, unknown state, stale flag and contradictory ownership.
- [x] Complete fixed-source inverse and every coattack/alternative/draw audit.
- [x] Independent actual GP, MIDI and PCM checks; retain unchanged PCM if observed.
- [x] One fresh random capture after code freeze, unchanged policy, no replacements.
- [x] Planner reviewed the bounded implementation, all development alternatives/draws,
  actual workers and the fresh frozen selection. Human fit and authentic mute
  timbre are not claimed; root confirmed this bounded batch complete.

Files: `optional_palm_mute_slots.py`, `local_palm_mutes.py`,
`run_palm_mute_qa.py` and corresponding tests. Root owns the v3 integration and
structural timing representation. Melody's wrapper recognition now accepts that
representation without changing its pitch or timing authority.

Intermediate verification: 30 focused integration tests passed; the added full-inverse
corruption cases brought the local policy suite to 11 passing tests. Two actual
runner tests pass (positive source alternatives and honest all-no-choice).
The runner's first test initially expected a no-choice worker in a fixture whose
every coattack had alternatives; corrected that test expectation, with no-choice
worker coverage explicitly verified in the second fixture. Initial log retained.

Completed real-source run: `run_palm_mute_qa.py
local-artifacts/context-membership-v1/frozen-v1/fresh/capture
local-artifacts/palm-mute-control-v1/development-first`. Sweet Child was the first
preregistered source with opportunities; the first source-ordered actual mute
change was selected, never a manually chosen note or a replacement for unchanged PCM.

## Completed fixed-source execution

`development-first/result.json`: **102,106 source facts**, exact zero inverse;
actual zero, no-choice, 50% and 100% source-denied workers all passed. Every raw
captured fact was independently compared, and both actual changed outputs passed
the native reviewer's independent source-scope check.

All **5,791 coattacks** were retained: 1,443 eligible, 4,348 refused, 1,435 eligible
but without independent on/off alternatives, and **8 choice targets**. This matches
the pre-implementation census exactly. The **555,936 draws** are saved:

| Release | Draws | Released | Actual mute changes |
|---|---:|---:|---:|
| 0% | 185,312 | 0 | 0 |
| 50% | 185,312 | 92,656 | 72 |
| 100% | 185,312 | 185,312 | 136 |

Release is permission to choose from source alternatives; it is not a promise to
change an unsupported event. Full release can select the same observed state.

Private independent `audit_development_votes.py` imported no owner, selector,
census builder or sampler. It compared every inventory row to the immutable
pre-implementation census, independently recomputed all alternatives, witness
separation, refusals, weighted votes, draws and first selection: **PASS**.
Planner separately checked the same complete inventory/draws and actual workers.
This proves the approved source rules were applied, not a second theory of musical
admission or a human listening judgment.

The first source-ordered real change was Sweet Child, part 4, bar 128,
`coattack:4:1017/2`, seed 1: **three-note chord, palm-mute true → absent**. Both 50%
and 100% released that same choice for this seed. Pitches, attack times, written
durations, dynamics, other declarations and all other source events stayed fixed.

Independent `native-preview/palm-mute-artifact-audit.json`:
**PASS_NATIVE_PALM_MUTE_PCM_CHANGED**. Exactly three native palm flags changed;
only their three MIDI release durations changed **166 → 480 ticks**. Original and
zero PCM matched exactly; changed focused and ensemble PCM differed. No target
replacement was used. The player changes sustain duration, not a verified muted
guitar timbre. No listening/artist-fit claim is made.

Artifact scope remains **GP plus hash-bound exact-model bends**. The pre-existing
standalone GP bend discrepancy remains in source, zero and changed outputs;
paired checked fields pass. Palm-muting work did not repair or hide that limit.

Before the fresh freeze, the focused suite:
`python -m unittest test_palm_mute_opportunity_census
test_optional_palm_mute_slots test_local_palm_mutes test_run_palm_mute_qa
test_melodic_contour_choices -q` — **38 passed** before adding the frozen-protocol
failure-retention test. Runner suite afterward: **3 passed**. Root's final complete
Python regression: **1,556 run; 1,555 passed; 1 optional skip**. Source/tests
remained frozen throughout acquisition, execution and independent review.

## Fresh random gate

Root froze 667 dependencies before selecting **Queen — Innuendo**, Songsterr
24056, revision 6955102, 16 parts, seed `16432599566745286866`. Planner independently verified the
selection receipt and all 667 live/archive hashes. Archive SHA-256:
`3be629b5384e7f00088e0b0d8769086d9cd1c73b43de4ad7714a1695d85feab3`.
Source: `frozen-v1/fresh/capture`;
actual run: `local-artifacts/palm-mute-control-v1/fresh`.

Result: **91,443 source facts** reconstructed exactly. Actual zero and released
no-choice workers passed. **7,001 raw note occurrences**, zero unlocated notes,
**4,320 complete coattacks**: 1,303 otherwise eligible, 3,017 refused, **zero
independent on/off alternatives**. Every coattack lacked an active palm-mute
declaration, so this input cannot supply an observed on/off contrast. This is a
source-coverage limit; absence does not prove how the recorded guitarist played.

All **414,720 draws** were retained: at 0%, none released; at 50%, 69,120 of
138,240 released; at 100%, all released. **Zero changes at every percentage**.
No replacement song, forced state or changed-audio demonstration was selected.

Private `audit_fresh_palm.py` rebuilt the complete source coattacks directly from
captured JSON and checked every identity, literal state, context, refusal,
neighbor closure, option, witness and draw. It imports no palm census, optional
owner, selector or sampler. Shared dependencies are explicitly the accepted
event/clock parser, execution-link definitions and existing independent dynamic
and clock oracle. **PASS_RAW_SOURCE_ALL_OPPORTUNITIES_ALL_DRAWS**;
`fresh-independent-audit.json`. Source hashes and frozen code hashes still match.

Fresh original/zero native check also passed:
`native-zero-review/review-summary.json`,
**PASS_EXISTING_SOURCE_CODEC_AND_ZERO_NATIVE_EQUALITY**. All 16 tracks / 156 bars
were exported. Native checked models and all **23,093 MIDI events per version**
matched; normalized GPIF, archive assets and bound bend payloads matched. Direct
source alignment found zero differences across 5,454 regular pitched notes and
6,960 beats; percussion mapping is outside that alignment scope. This song passes
the checked standalone roundtrip, and 13 exact-model bend curves are additionally
bound to each GP. That does not establish universal standalone bend fidelity.
No redundant PCM render, changed-song result, listening or artist-fit claim was
made for the no-choice input.

Development demonstrates one **measured playback change**; the fresh gate demonstrates
honest refusal when the new input has no source-supported contrast. Neither is
universal style validation or human approval of palm-muting feel.

## Closure and remaining limits

No known remaining defect in this bounded palm-mute operation requires another
code change. The source evidence, exact reverse, release behavior and actual
native effect have been checked within the declared scope. No new implementation
is planned while Planner selects the next musical operation.

Remaining limits are explicit: no human listening/artist-fit approval; no verified
physically authentic muted-guitar timbre; no change where the source lacks an
independent on/off contrast; linked/unknown execution remains excluded. Existing
standalone GP bend limits remain separate. These checks do not close every
musical use of a full palm-mute lever.

All captured scores, audio, inventories and private audit scripts remain under
ignored `local-artifacts/`; only implementation, tests and this aggregate progress
document belong in source staging. `git check-ignore` confirmed the private fresh
audit is ignored. This worker has not staged or committed private material.
