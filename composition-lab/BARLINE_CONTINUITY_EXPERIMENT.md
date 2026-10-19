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
