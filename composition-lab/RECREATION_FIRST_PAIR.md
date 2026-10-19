# G3 first-pair checkpoint — not the completed eight-case gate

One four-bar Invent Animate window from the previously examined holdout was
selected before generating proposals. It contains 55 regular note occurrences.
The song and family are excluded from fitting. Private source identities,
annotations and GP outputs remain in `local-artifacts/g3-recreation-v1/`.

## Actual results

| Requirement | Evidence |
|---|---|
| Source join | 55/55 pitch, onset, duration and fret matches; normalized string coordinates match |
| Coordinate proof | Actual API tuning reverses GPIF tuning; map uses string count, not a fixed seven-string exception |
| Raw annotation join | All 55 known API mute markers match GP notation; zero unknown markers in this window |
| Source replay | Removed and reapplied only declared mute properties; original target XML restored; other fields preserved |
| Hidden-target reconstruction | Proposals run on a target-redacted GP; eligible fields overlaid onto original GP, preserving ineligible notes |
| Population | 33 eligible coattacks / 49 notes; six ineligible notes retain exact original XML |
| Target perturbation | Setting every window target flag on versus off leaves all 100% proposal decisions identical |
| Window state | Starts with no previous state; subsequently uses generated output state |
| Native interpretation | Replay, learned and static-control mute flags checked against actual native imports |

The initial naive join failed on all55 string indices. That failed report is
preserved. These were coordinate-convention differences, not lost notes:
`GPIF_string = len(raw_tuning) - 1 - API_string`. Actual raw/GPIF tuning arrays
confirm reversal. This proves the selected window, not the whole corpus.

## Same-model comparison

Both methods use the same hidden-target input, window, model, seed and reset
policy. Actual source annotations are consulted by the evaluator, not by the
learned proposal branch. Source replay is explicitly a separate non-learning branch.

| On 33 eligible coattacks | Static | Stateful |
|---|---:|---:|
| Negative log likelihood | 0.185545 | 0.037313 |
| Brier error | 0.061620 | 0.010543 |
| Sampled annotation mismatches | 5 | 1 |

Stateful confusion counts: **7 true positives, 1 false negative, 0 false positives,
25 true negatives**. Source population:8positive/25negative groups. These are
one selected window/seed's diagnostic counts, not population accuracy or
artist-feel acceptance. Wrong predictions are preserved.

## Implementation and limits

The sequence method now accepts an optional `(track, first_bar, last_bar)` window.
This avoids a lossy source-score extraction. It locks surrounding material and
resets state at the window boundary. Existing unscoped behavior is retained.
Nine sequence tests pass, including the new window/boundary/invalid-bound tests.
Full local discovery:493run,492passed,one optional skip, including the still
uncommitted rejected tuning candidate's tests.

ProjectPlanner3000 accepted the first-pair requirements/scope checkpoint.
Developer self-QA supplies engineering verification; no independent technical or
listening acceptance is claimed. No new detector, original source repair, pedal
change or generator default promotion occurred.

G3 remains open: build a reusable guarded replay/overlay runner, freeze eight
representative passages across at least four families, include directed and
continuous techniques, verify each and account for refusals/misses. Do not expand
this single muting success into eight muting-only cases.
