# Voicing/register: requirements, experiments and acceptance

User authorized planning with ProjectPlanner3000, then execution on the frozen
random song; same relationships, all other dimensions locked, all three QA gates.
Approved detectors/codecs and unrelated work remain unchanged.

## Persistent acceptance checklist

- [x] Planner start/middle/end reviews and independent source/lock/audio audit.
- [x] Retain frozen capture; generic candidate rules, failures and all seeded draws.
- [x] Shared-relation intervention; strict control interface; isolated worker.
- [x] QA1 source population and coverage (development-inspected, not held-out accuracy).
- [x] QA2 stripped-source/cache exact-zero reversal and independent nonzero locks.
- [x] QA3 bounded musical relationship and donor evidence; limitations explicit.
- [x] Source/zero/changed native GP exports, imports and independent comparison.
- [x] Audio renders and independent PCM comparison; actual browser UI/control QA.
- [x] Python/JS regressions.
- [ ] Commit/push and remote CI verification.
- [ ] Human musical listening and physical execution acceptance; full lever OPEN.

## Frozen source and locks

Rolling Stones, (I Can't Get No) Satisfaction, Songsterr16453/revision7421771.
Seed9084737611129534236, query c; prior corpus/captures excluded before selection.
Six tracks,126bars,7605 note occurrences,59514 typed source facts/containers.
Input: complete preceding T1 only. Candidate: first eligible source coattack unit,
at least two known integral pitches, equal positive duration, distinct fixed guitar
strings, no unresolved timing/grace/tie/pitch/sustain dependencies. Unknown or
expressive cases retained with refusals. GM guitar/bass range24..39.
Only selected voicing/register coordinates unlocked. Per-member pitch class and
multiplicity, note cardinality, strings, time, techniques, dynamics, all other
parts/notes/source fields stay locked. Selected octave/spacing are released.

## Historical contracts and experiments (not retroactive claims)

V1: predeclared full/local exact context, ordered physical member/string matching,
same part, notation/effects, PC/duration, meter/offset, nominal overlap ensemble;
full additionally preceding/following PC vectors. Fixed seed9427.3685 units,
538 eligible, no alternatives. Planner raw-checked42notes in18units: two aggregate
PC families had alternatives. Physical serialization order was the wrong musical
correspondence. V1 evidence remains retained, not relabeled as corrected.

V2: data-informed PC plus low-to-high rank within PC correspondence, preserving
repeated pitch classes and target strings. Still no exact-context alternatives.
Planner inspected all25cross-realization pairs: every pair differed in overlapping
ensemble context. Removing notation alone could not solve this.

V3: explicitly weaker source pooling, same part/instrument, PC multiplicities and
written duration. Target markings, accompaniment and every other lock retained;
donor contexts need not match. No exact moment/artist suitability claim. Empirical
max played fret11/span2 used as screen: no eligible alternative. Planner checked
all18paired choices:15require negative frets;3fit source-declared24frets, span10.
Observed maximum played fret is not instrument limit.

V4: pooled_declared_geometry uses explicit source fret-count, nonnegative integral
frets, no guessed default. Observed range/span retained as diagnostics. Does not
certify a ten-fret shape playable, invent tapping or silently move strings.
Data-informed revisions on SAME frozen song, not pristine held-out generalization.
No handpicked chord, interval, direction, transposition or easier replacement song.

## Same relationships and intervention

Member correspondence by pitch class/register rank; source-supported conditional
choices exclude target and retain donor IDs/count weights. At100 no preference for
original register and no forced difference; equal observed outcomes are allowed.
Change existing coattack bass-register anchor and member voicing intervals only.
Recompute musical context and constraints; realize with the SAME equations:
pitch=anchor+interval; pitch=tuning+capo+fret. No raw patch, cached note stream or
separate generation engine. Strict typed voicing/register,target_ref,seed,policy
controls. Nonzero worker purpose separate from exact-zero QA, same audit denials.
Python audit is NOT an OS sandbox or resource quota.

## Actual bounded result: 2026-10-24

Target event:16453:2:17:0:2:0, track2/bar17/local onset1quarter. E2/E3/B3 becomes
E3/E4/B3. Anchor40 ->52; intervals[0,12,19] ->[0,12,7]. Alternative observed five
times in bars47/48/53. Fixed strings yield frets12/19/9, simultaneous span10.
Donor realization uses different strings, frets7/9/9, span2. Target ghost marking
remains on its original occurrence, not copied from donor. Physical execution and
musical suitability OPEN. No whole-song key/function/emotion/style claim.

Only source changes:track-2 measures/16/voices/0/beats/2 notes/1 fret7 ->19 and
notes/2 fret0 ->12. All other field types/topology/order/values independently checked.

62 preregistered draws:seeds9427..9446, both strengths0/50/100, plus two single-
control100tests.0%=0/20changed;50%=6/20;100%=20/20. Both coordinates must release
for this alternative; each independent probability.5 gives joint.25, not50%audible
change. Single-control100tests correctly refuse. All refusals retained; first
changed draw50/50seed9428 is displayed, not selected for quality.

QA1 PASS population/coverage; development inspection disclosed.
QA2 PASS:actual stripped exact-zero worker recovers59514paths; actual nonzero
worker matches direct shared-equation result, independent lock comparison PASS.
QA3 PASS bounded source-supported PC/voicing/register relationships only; weaker
pooling and physical/listening unknowns remain explicit. No full Tier2 PASS.
Retained detector parity checked; detectors not modified.

All3GP7 exports/imports7605notes; model comparison zero differences. Source/zero
GPIF identical after generated chord-ID/reference normalization; other ZIP assets
byte-identical. Changed only two notes' dependent fret/pitch leaves (8leaves).
GP binary-byte identity is NOT claimed.
Source/zero focused and ensemble WAV sample-identical. Changed waveform differs
2.20444..2.62088s within5.29415s bars16..18;44100Hz mono. No subjective quality claim.
Planner independently checked raw source, donors,62draws and PCM:PASS.

Actual UI at localhost5221:populated notes, both cue players, focused/ensemble,
half-speed,zero pause,loop,mutual exclusion tested. Fixed async loading/seek race
found during actual browser QA and retested. Defaults restored, playback paused.

## Commands/results and artifacts

- python -m unittest discover -s composition-lab -p test_voicing_register.py:11PASS.
- same discovery test_qa_isolation_harness.py:8PASS.
- full test_*.py discovery:1010run,1009PASS,1optional skip.
- node --test tests/*.test.mjs:24PASS.
- run_voicing_register_qa.py:PASS_EXACT_AND_SCOPED_SYMBOLIC_INTERVENTION.
- check_voicing_artifacts.py:PASS_NATIVE_GP_AND_AUDIO_CHANGE.

Private local-artifacts/voicing-register-qa-v1 retains all versioned inventories,
contracts, worker inputs/outputs/audits, all draws, complete T2 and lock comparison.
Private local-artifacts/voicing-register-gp-v1 retains GP/audio/review and independent
checks. Commercial scores/captures/audio remain ignored and unpublished.

Next: optional user approval to reassign only affected strings to actual observed
donor fingering; current all-other-dimensions-locked scope cannot silently permit
that. Musical listening is a separate judgment. Other Tier2 levers remain open.
