# Historical harmony replay and operation trace

## Scope and acceptance

Explain an existing generated accompaniment context before proposing a replacement.
No live generator edit, new candidate, GP export or listening judgment. Consult
ProjectPlanner3000 at start, midpoint and completion; developer owns technical QA.

- Exact recorded generator recovered from Git `202706072f4cb96cb073d15004e8f0f019e066a7`.
- Generator SHA256: `ff1f13a2c2b5831f0f6a74b4741c58216193984dc682bf57fd0bbdefc98a03a2`.
- All four original harmony tracks reproduce exactly using the recorded model,
  comparator/section inputs, seed and accepted retry.
- Equality covers the entire canonical harmony track: notes/voicings, all voices,
  rational onset/duration, tuning, string/fret, program and metadata.
- Imported helper revisions were not fully sealed by the original batch.
  Current reconstructed helpers reproduce these outputs; historical helper
  authenticity is **not** established.

| Generated core | Seed | Accepted retry | Entire harmony track |
|---|---:|---:|---|
| 1 | 10002 | 2 | Exact |
| 2 | 10101 | 1 | Exact |
| 3 | 10200 | 0 | Exact |
| 4 | 10301 | 1 | Exact |

An initial full Python line trace was interrupted because of instrumentation
overhead before any result. Its script is preserved. Narrow instrumentation
turns off after capturing configuration; output assertions remain exact.

## Observed operations: one reproduced core

The instrumented historical generator still reproduces core1's complete harmony.
Every recorded emitted root matches the actual generated event. All rejected
and successful harmony fit attempts are recorded separately.

| Newly sampled harmony attacks | Count |
|---|---:|
| No octave adjustment | 611 |
| Upward octave adjustment | 16 |
| Downward octave adjustment | 31 |
| Total | 658 |
| Targets below the instrument's lowest open note | 14 |
| Upward adjustment although target itself is in range | 2 |

At these **newly sampled attacks only**, sampled step increments sum to+169
semitones and octave-fit adjustments sum to-180. Reused motif transitions/resets
are excluded; these totals are **not a whole-piece drift decomposition**.
Thus the simple explanation that octave fitting only pushes upward is false
for this run. Neither statistic proves the source of the earlier context gap.

The actual first sampled sequence includes jumps+14,+12,-31,-27 applied to new
pitch states. Below-range targets are octave-adjusted for playable fingering.
The code samples from source track-level step counts, without conditioning that
step draw on the current register. This identifies a concrete relationship to
investigate: **where a jump was used in its source versus where it is reused**.
It is not evidence that a particular conditioning method will fix musical feel.
One core's operation trace does not establish prevalence across the corpus.

## Reproduction

`historical_harmony_replay.py PLAN.json ORIGINAL_BATCH.json PRIVATE_OUTPUT.json
--trace-core 1` recovers the exact recorded generator from this repository's Git
history; refuses substitution, changed frozen inputs, ambiguous retry history,
track mismatches and changed dependencies. It exports no GP files. Private plans,
models, event locations and outputs must stay under ignored `local-artifacts`.

Three targeted tests check exact-blob recovery/refusal, accepted-retry ambiguity
and instrumentation preserving output while separating rejected fit attempts.
Private evidence under `local-artifacts/g6-barline-continuity-v1/historical-generator-trace-v1/`
includes both replay records, input/helper seals, all operations, reconciliation
and explicit limitations. No source score or model is included in Git.

## What this closes—and leaves open

Closed: exact reproduction of these four harmony outputs and an observational
account of one run's actual step/refit transformations. Open: the causal source
of the full context mismatch, a remedy that passes controlled tests, joint
artist-style fidelity and musical acceptance. The two previous G6 candidates
remain failed, with their original gates unchanged.

ProjectPlanner3000 reviewed at START, MIDPOINT and END. Bounded investigation accepted, pending publication/CI; planner inspected code/tests/saved evidence and did not rerun them. Developer performed the technical checks.
