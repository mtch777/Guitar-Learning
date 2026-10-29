# Songsterr tonal analysis implementation

Authorized 2026-10-29: a separate GitHub section/scripts to implement and test data-driven key analysis. Base: `19d4f65` on origin/main. Existing working-copy changes and all Composition Lab engines, detectors, source scores and baselines are outside this change.

## Checklist and acceptance criteria

- [x] Raw input: accept a captured Songsterr directory; preserve exact occurrence/time/track/voice and raw technique evidence; reject or quarantine unsupported input without guessing.
- [x] Evidence: separate pitch distribution, bass, chord candidates, ordered resolutions, melodic movement and structural arrival proxies; link observations to source occurrences.
- [x] Inference: rank tonic and mode separately, retain scale-compatible alternatives, and abstain for empty/insufficient input. Scores must not claim calibrated probabilities.
- [x] Scope: analyze whole song, source sections and overlapping windows without creating attacks or phrase endings at window edges.
- [x] Reproducibility: CLI, synthetic examples, documented formulas/limitations, standard-library tests, dedicated GitHub Actions job.
- [x] Verification: adversarial synthetic and transposition/doubling tests; unchanged private capture smoke with independent occurrence check; existing applicable Python tests, JS tests and UI build.
- [ ] Delivery: isolate staged files, publish branch/PR, inspect remote CI. No private source or derived song report enters Git.

## Design contract

This is an additive analysis tool, not a new reversible tier or composition engine. It does not remove or regenerate source data; exact tier reversal and GP/playback quality gates are not applicable. Musical correctness on commercial songs and human listening acceptance are untested until independently annotated review. Synthetic fixtures validate bounded logic and invariants, not corpus accuracy.

Raw source -> normalized immutable-by-convention events -> measurable evidence -> heuristic tonic/mode rankings and a local timeline. Bass is an observed minimum, chord roots are template candidates, and source keys are declarations, never training/evaluation truth. All scoring weights and abstention rules are versioned, disclosed and uncalibrated. Evidence includes contradictions and missing distinguishing scale degrees.

## Log

- Read HANDOFF.md then CODEX_CONTEXT.md; inspected current source, tests, workflows, AGENTS.md and the musical reset/three-gate requirements. Current request authorizes this isolated implementation.
- `git fetch origin main` succeeded after filesystem escalation; origin/main and local main are `19d4f65413825c2ca9acf416ad31ef22f8e3e70b`.
- Created managed worktree `songsterr-key-analysis`; separate agents own raw adapter and synthetic regressions, with an independent read-only reviewer.
- Implemented the independent adapter, evidence engine, CLI, original fixtures, 63 tests and dedicated CI. No imports from Composition Lab's engines or third-party packages.
- Independent review reproduced excluded notes becoming rests, stale window witnesses and overlapping voices becoming false monophonic transitions. All repaired with regression tests. Also guarded malformed rest timing, identical section-marker instances, normalized input geometry, unequal-duration landing witnesses and pickup metric positions.
- Initial temporary-file tests and `npm ci` encountered sandbox write denials. Scoped escalated reruns passed; no permissions workaround or source replacement.

## Local verification (2026-10-29)

| Command / scope | Actual result |
|---|---|
| `cd tonal-analysis; python -B -m unittest discover -s tests -q` | 63 passed on Python 3.12.14; 63 passed on Python 3.10.9 |
| `cd composition-lab; python -B -m unittest test_songsterr_relationships test_source_semantics test_source_timing_regions test_tonal_source_stream -q` | 38 passed |
| `node --test tests/*.test.mjs` | 28 passed |
| `npm ci --ignore-scripts` | Locked dependencies installed; lockfile unchanged. npm reported two existing high-severity advisories; dependency upgrades are outside this isolated change |
| `npm run build` | Passed, Vite 7.3.6; existing UI production bundle built |
| CLI subprocess tests | Fresh outputs, private-path guard, no overwrite/source writes, malformed input and examples all passed |

Used three fixed existing private capture directories selected before running inference. They are regression/portability checks, not newly sampled songs or an independently labeled benchmark. Every run pins code and source hashes; original and final reports are preserved under ignored `.local/tonal-qa-20261029/` and `.local/tonal-qa-20261029-final/`.

| Private case | Raw non-rest occurrences | Retained | Eligible | Verification |
|---|---:|---:|---:|---|
| A | 7,605 | 7,605 | 5,173 | PASS |
| B | 9,031 | 9,031 | 6,227 | PASS |
| C | 6,749 | 6,749 | 4,692 | PASS |
| Total | 23,385 | 23,385 | 16,092 | Source byte hashes unchanged |

Commands: `python -B tonal-analysis/analyze.py analyze <fixed-private-capture> --output .local/tonal-qa-20261029-final/capture-<a|b|c>`. Full identities and hashes remain in private manifests. Verification independently traverses raw note witnesses, eligible pitch, and within-voice timing; shared bar geometry comes from the adapter. No private score, result or source identifier is published. Case C returned an unresolved center; no forced answer was substituted.

## Remaining limits / next action

- Musical prediction accuracy, calibration and human listening agreement are NOT TESTED. Independent annotated held-out evaluation is the next research gate.
- Sounding-pitch techniques, physical sustain, expanded repeat order, arpeggiated/rootless harmony, reliable borrowed/applied-chord labels and additional scale systems remain explicit limits, not claimed implementations.
- Same-relationships inverse/GP/playback gates are NOT APPLICABLE to this additive read-only tool; it is not promoted into the existing tier engine.
- Next delivery action: inspect staged paths, commit/push the isolated branch, create the PR and verify its remote checks.
