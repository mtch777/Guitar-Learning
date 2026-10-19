# Barline continuity: two controlled experiments

Experimental tooling only. Neither candidate passed the predeclared whole-piece gate. Existing generation defaults are unchanged.

## Requirement and method

Improve melody continuity across bars without changing harmony, bass, rhythm, form, instrumentation or performance. Use actual final preceding notes after explicit theme-return constraints. Hide original target melody pitches at 100%; preserve literal data at 0%. Intermediate values are explicitly unsupported by this experimental live-history method.

The existing model and consumer both reset per bar: this was a new context hypothesis, not a contract bug. Accepted source analysis supplies exact clocks, written minimum pitches and known section instances. Source role labels and written harmony minima remain proxies, not validated musical functions.

- Reset: existing within-bar method, with explicit generated-theme returns preserved.
- Carry: retain actual previous melody context at a contiguous bar boundary within the same supplied section instance. Rest/gap/section changes reset it.
- Register carry: same method, plus one fixed source-learned relative-register factor at eligible boundaries. Family/song weighting; alpha 0.0001; no tuning after results.

Source prerequisite: 2,264 development melody boundaries across 43 families/55 songs; 392 previously examined held-out boundaries across five families/seven songs. The held-out material is not fresh. Unknown sections, part changes, unknown pitches/tie destinations and gaps are excluded.

## Frozen whole-piece comparison

Four preserved generated cores, three seeds, identical inputs: 24 reset/carry GP files and 12 register-carry GP files. Both alternatives must improve signed interval distance in at least three of four core means, without worsening aggregate register distance, written harmony-offset distance or large-jump-share error. Lower numbers below are better.

| Diagnostic | Reset | Carry | Register carry |
|---|---:|---:|---:|
| Signed interval TV | 0.607107 | 0.360429 | 0.389068 |
| Relative register TV | 0.494069 | **0.550078: worse** | 0.305512 |
| Written harmony-offset TV | 0.631630 | 0.618131 | **0.636692: worse** |
| Large-jump-share error | 0.348141 | 0.036037 | 0.058357 |
| Cores with better interval distance | — | 4/4 | 4/4 |
| Full acceptance gate | Baseline | **Failed** | **Failed** |

The first method improves interval behavior but shifts register. The second corrects register while slightly worsening written harmony-offset distance. No tolerance was added after seeing results; neither is promoted. These distances do not establish artist feel, emotional meaning, originality or musical quality.

## Reproduce with private data

`barline_continuity.py` provides `observe`, `fit-register` and `generate` subcommands (`--help`). Outputs must be under ignored `local-artifacts`; source scores and model weights stay private. Supply the exact accepted relationship report, composer, role-pitch model, plain generated GP core/adjacent `.expected.json`, and explicit section/return plan. Generation supports `--mode bar_reset`, `carry`, or `register_carry`; the latter requires `--register-model`. Never use commercial source scores as generated cores.

The public implementation uses the same frozen math. Model provenance, literal nonmelody locks, actual final history, exact returns and unsupported inputs are checked. Export changes only melody pitch/fingering properties in the original GP archive. Shared note definitions are refused rather than accidentally changing other occurrences.

## Evidence and limits

All 36 original experimental GP files independently import with expected pitch/rhythm/tuning/fingering and export MIDI. Actual-history checks and literal unrelated-facet/archive checks pass. Twelve representative full instrument WAVs are finite, non-silent and unclipped; paired durations agree. Rendering is alphaTab/Sonivox, not physical guitar or Guitar Pro RSE. Listening judgments remain unknown.

Private artifacts: `local-artifacts/g6-barline-continuity-v1/`, including frozen plans, source observations, metrics, original GPs/MIDI/audio and code seals. Public packaging replay and final regression evidence are recorded in `ENGINE_EXECUTION_PROGRESS.md`. Developer self-QA is not independent musical acceptance. ProjectPlanner3000 could not complete the final review because its usage limit was reached; no substitute agent was created.


Known-corpus check across all 36 pieces: zero exact relative 32-attack matches;
90 varied 16-attack matches, all in locked harmony (30 per method), none in melody.
Short varied 8-attack matches: reset 565, carry 566, register carry 566 across all
tracks. This is a supplied-corpus window audit, not an originality verdict.
No two full generated scores are identical. The 12 shared eight-attack melody
opening groups each contain the three matched methods on the same core/seed;
none span distinct core/seed contexts. Identical opening material before the
first affected boundary is expected by the experiment, not a diversity result.


## Follow-up: register and harmony are coupled

A read-only audit uses the exact identity `R - D = H`, where R is melody pitch
minus its lowest open string, D is melody pitch minus the written harmony minimum,
and H is that harmony minimum minus the melody track's lowest open string.
All three measurements use the same known-harmony boundary subset and weights.

| Joint-context diagnostic | Observed source | Locked generated context |
|---|---:|---:|
| Mean H, semitones | 8.8573 | 23.9217 |
| Source leave-one-family-out mean H range | 8.6766–9.0796 | — |
| Known-harmony source support | 1,311 boundaries;35families;42songs | — |
| Unknown-harmony source boundaries | 953 of2,264 | Explicitly excluded |
| Exact H values absent from source support | — | 24.3%–36.7%, depending on core |

The fixed-context mean shift is15.0644semitones. Consequently, at least one of
register-mean error and harmony-distance-mean error must be at least7.5322semitones
on this matched cohort while H stays fixed. This is an exact first-moment bound,
**not proof that no better joint distribution or passing TV result exists**.
The original frozen TV gates remain failed and unchanged. Missing harmony is
not a negative observation; these results do not cover the953unknown boundaries.

`joint_register_harmony_audit.py` reproduces the support/identity/coverage check
from accepted observations and an explicit comparison manifest, with input seals,
family/song weighting, duplicate checks and locked-context refusal. No model
fitted or third candidate generated. Existing composer code does resynthesize
harmony roots using first-order steps and octave feasibility; that is a plausible
place to investigate context drift, not an experimentally proven cause here.
The next separate study should examine source-supported joint role contexts and
conditional evaluation; it must not silently retune this failed cycle.
