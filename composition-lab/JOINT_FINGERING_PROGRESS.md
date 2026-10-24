# Joint voicing and physical realization

User authorized developer/ProjectPlanner3000 to choose the next scope on
2026-10-24. Physical string assignments may now be explicitly released; existing
fixed-string experiments remain unchanged. No context matching relaxation.

## Acceptance checklist

- [x] Planner START/MID/END review.
- [x] Physical relationship selects tuning by the owned string variable in BOTH
  directions; old fixed-reference representations remain readable.
- [x] Source-observed joint choices retain musical conditioning, exact pitch-class
  multiplicity, duration, incident endpoints, ties and all unrelated source fields.
- [x] Independent physical control: 0 locks strings; musical0 locks pitches;
  joint release admits only observed joint geometry. 100 never forces change.
- [x] Positive/negative tests and isolated inverse with lower payload removed.
- [x] Frozen new random song, retained failures, independent source/lock audits.
- [ ] GP/audio verification for supported actual changes; no listening claim from
  serialization or waveform difference.
- [x] Full relevant regressions and persistent actual results.

## Development evidence (not fresh-song accuracy)

- `python -m unittest discover -s composition-lab -p test_dynamic_fingering.py`:
  five independent tests PASS, including actual isolated worker and malformed
  string/reference failures. Legacy fixed-index representations remain readable.
- `test_joint_fingering.py`: eight tests PASS; separate musical/physical locks,
  observed joint changes, immutable input, isolated worker, occupied-string guard.
  Initial collision fixture had different musical contexts and could not exercise
  the guard; corrected to hold overlap context equal across observations.
- `test_joint_gp_artifacts.py`: two tests PASS. Wrong GP string, MIDI pitch or
  unrelated fields fail. A physical-only change is allowed identical MIDI audio;
  it is explicitly not reported as a new audible change. A copy of the prior
  native GP/audio artifacts passes the extended checker; original baseline intact.
- Independent `test_check_joint_fingering.py`: seven corruption tests PASS.
- Fixed 60-draw synthetic control contract: independent seeded/source/lock audit
  PASS. 0% changes 0/20; 50% changes 15/20 (release counts 9/9/12); 100% changes
  20/20 in this fixture. Separate repeated-original fixture proves coincidence is
  still permitted at 100%. These are control mechanics, not real-song musical QA.
- `local-artifacts/joint-fingering-development-v1`: Under Pressure and Over The
  Hills actual stripped-worker zero + independent full source check PASS: 52028
  and 82140 captured facts/containers; no source mismatch.
- All three inspected development songs (above plus Satisfaction) still have no
  admissible alternative under unchanged incident context matching. String freedom
  alone does NOT supply missing musical choice evidence. No adaptive relaxation.
- Existing full suite before final oracle additions: 1057 run, one optional skip;
  43 JS tests PASS; Vite build PASS. Final suite pending all new checks.

Current next action: independent whole-choice/lock oracle, freeze unchanged code,
fresh random trial, retain every no-choice/failure result. No new generator,
detector change or manually chosen pitch offset.

## First frozen trial: failures retained, then repair

`local-artifacts/joint-fingering-fresh-v1`: seeds 4179993861100340308 and
7079914199931664039 selected Sound Of Silence (79618, 5 tracks) and Come Together
(62923, 11 tracks). BOTH failed closed before inverse: 11 and 4095 unsupported
source rows. No substitution or post-analysis change to their trial results.

Root cause: finite declaration registry lacked new provider playback fields,
object key signatures, note SPN arrays/courtesy flags, a clef and grand-staff
group declaration. Added only the observed scalar paths/types. Raw declarations
are not promoted to inferred keys, modes, sounding pitches or emotional meaning.
Also corrected generic container registration: a scalar leaf path cannot authorize
an empty object/array of the wrong type. Independent malformed-shape tests follow.

`local-artifacts/joint-fingering-repair-v1`: separately frozen production-only
development replay of those SAME captures, not new-song portability. Both actual
stripped workers, full independent source checks, retained detector parity,
dependency and complete policy-denominator checks PASS: 3821/4575 notes and
28532/59843 facts/containers. Original failures and capture hashes stay intact.
Both still have zero supported alternative choices. The older repair result's
generic PASS status must be read with its explicit DEVELOPMENT_REPAIR manifest;
future runner outputs distinguish repair versus fresh status directly.

## Second frozen trial and final verification

`local-artifacts/joint-fingering-fresh-v2`: all 464 Python/API/client file hashes
frozen before sampling; seeds 2510066751450809547 and 4626837071064606837.

| New song | Notes | Captured facts/containers | Eligible units | Accepted donor links | Distinct alternatives |
|---|---:|---:|---:|---:|---:|
| Rock And Roll All Nite (307) | 4760 | 36376 | 570 | 2550 | 0 |
| Fur Elise (2482) | 929 | 11529 | 67 | 30 | 0 |

Both unchanged frozen runs PASS complete source parity, actual stripped-zero
worker, independent full source comparison, all-target donor/context oracle and
retained execution graph checks. Source timing, identities, ties and technique
metadata remain exact. Total 5689 notes / 47905 facts+containers. Source-supported
alternative and listening gates remain OPEN. No new changed GP/audio is fabricated.

Six independent schema-evolution tests pass: actual isolated full inverse,
provider/display declarations do not affect musical pitch authority, strict leaf
types, valid empty containers, wrong container kinds and scalar impostors.
Full Python suite: 1080 run, 1079 passed, one optional skip (44.664s). 43 JS tests
PASS; Vite build PASS. No website edits or Pages deployment claim.

This second sample tests the repaired source contract; it is not a search for an
easier song or a favorable musical-change demonstration. Next bottleneck is
source-supported musical context/choice abstraction, not further string unlocking.
Planner END independently rehashed all 464 code files and capture hashes, re-ran
the raw-source checker on actual isolated worker outputs and the complete policy
oracle: zero mismatches, both PASS. Private review:
`joint-fingering-fresh-v2/planner-independent-end-review.json`.

Planner accepts bounded fresh portability and exact0. Positive creative, human
physical execution and new audio gates remain OPEN. Recommended next experiment:
source-learned transposition-equivariant voicing families with structural context,
wrong-context negatives and physical witnesses. A bass-relative family must not
be labeled a chord root or known harmonic function without evidence. No more
random draws to fish for an example; no arbitrary matching relaxation.

Delivered commit `6359eb4`, pushed to main. GitHub Actions run `40119958499`
completed SUCCESS. No private source captures, scores or audio were published;
unrelated unfinished work remains unstaged.
