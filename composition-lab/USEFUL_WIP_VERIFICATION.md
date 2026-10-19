# G2 — descriptive profiles and sequence-muting experiment

Technical verification is complete locally. Planner scope review accepted the
bounded content, subject to the reporting clarifications included below.
Delivery is pending. No artist-feel or musical-quality acceptance is claimed.

## Requirements checked

| Requirement | Result | Limit |
|---|---|---|
| Individual-note percentages | 10 marker families; separate written segments, fresh attacks and duration mass | Not occupied time or gesture counts |
| Song/local/artist totals | Reconciled both development and held-out inventories against frozen eligible rows | Marker classifier reused; not detector recall validation |
| Family weighting | Pooled, equal-score and equal-family rates independently recomputed for 21 group features | Group positives are not note percentages |
| Missingness | Explicit unknown marker/tie/duration coverage; note vibrato distinct from beat vibrato | Known absent notation does not prove absent performance |
| Preserve music while editing muting | All 36 GP files preserve other GPIF fields and archive members | Only declared muting fields may change |
| Native interpretation | 36/36 import/timing/pitch/mute-flag checks; bend curves on all three tracks and directed links/vibrato agree | These are native-reader checks, not listening |
| Controls/state | Existing eight sequence tests pass: resets, coattack exclusions, partition separation, 0% byte identity, 100% annotation independence, actual-output state at intermediate freedom | Opt-in method; defaults unchanged |
| Source/model identity | Frozen analysis/code/model seals checked; exact model refit reproduced saved model | Musical interpretation still requires later gates |

`artist_note_summaries.py` inventories ten marker families. Structural chord,
dyad and other group relationships remain in the separate 21-feature profile;
they are not copied onto individual notes. Neither summary adds missing
performed endpoints, acoustic muting depth, harmonic function or artistic intent.

Malformed binary-float durations are now refused rather than silently converted
to binary fractions. Response comparison summaries reject non-Boolean labels and
negative/non-integer counts. These are input-validation changes, not detector edits.

## What the comparison establishes

There are **12 matched inputs × three conditions = 36 GP files**:

- **Legacy static:** prior model/cohort; descriptive baseline only.
- **New static:** current model, no previous-output conditioning.
- **Stateful:** same current model, previous-output conditioning enabled.

The last two isolate statefulness. Legacy-static and new-static GPIFs differ;
their models/cohorts differ, so equality is not a valid null expectation. The
original batch and its false equality field are preserved, not rewritten.

The Invent Animate cohort contains 70 development scores in 54 families and
eight held-out scores in six families. This **previously examined holdout**
contributes 13,130 eligible notation events, with no held-out fitting. It is not
a pristine new test set. Exact replay of the saved fit matched its model. Independently
recomputed family-balanced results:

| Metric | New static | Stateful |
|---|---:|---:|
| Negative log likelihood; lower is better | 0.216591 | 0.115799 |
| Brier error; lower is better | 0.065893 | 0.031518 |

NLL improved in all six held-out families. Stateful prediction used a supported
state table on 13,128 events and static backoff on two. This is teacher-forced
prediction of written annotation; it does not establish generation quality.
Separate free-running context rollouts over three seeds produced muted-after-muted
rates of about 0.400–0.425 for static and 0.761–0.791 for stateful. This shows
changed sequence behavior, not closer source fidelity: no matched source
conditional baseline was compared here. These are rollout diagnostics on frozen
source contexts, separate from native GP generation and listening.
Marginal muting percentage is not a promotion criterion.

## What the previews establish

Before rendering, froze three matched contexts: generated pieces 1, 7 and 11,
seed 17, bars 1–4, track 0. Nine WAVs include the legacy baseline; these are three
contexts, not nine independent trials. Same reader, SF2, gain, playback profile,
tempo and window within each context. All are finite, nonzero and unclipped.

| Same-model comparison | Changed mute-note flags | Audio result |
|---|---:|---|
| Piece 1 | 24 | Byte-identical; all changed notes last 78.125 ms |
| Piece 7 | 6 | Different PCM; changed notes last 156.25 ms |
| Piece 11 | 16 | Different PCM; 14 short notes and two longer notes |

Reader-code inspection explains the negative case: alphaTab applies a capped
static duration to palm-muted notes, taking the minimum with written duration.
It does not provide a physical palm-muting timbre model. Short notes can retain
identical audio despite correct changed flags. Do not present that case as an
informative listening test, failed edit, or musical equivalence.

The passage renderer now reads adjacent `.playback.json`, as the full instrument
renderer already did, so approved vibrato settings are preserved in previews.
No synthesizer behavior was changed. No listening preference was invented.

## Commands and retained evidence

- Python discovery: **492 run, 491 passed, one optional skip**. This includes
  the still-uncommitted rejected tuning candidate's tests, not its acceptance.
- JS tests: **39 passed**. Vite production build passed.
- `verify_profile_summaries.py --report REPORT --model MODEL --artist ARTIST
  --output NEW_PRIVATE_PATH`: repeatable denominator/rate reconciliation.
- Existing native verifiers: `verify_gp.mjs`, `verify_note_flags.mjs`,
  `verify_bend_curves.mjs` for tracks 0–2, `verify_technique_links.mjs` on all36.
- Private `local-artifacts/g2-useful-wip-v1/`: frozen preview plan/jobs/results,
  nine WAVs, output-preservation, held-out and preview reconciliation.
- Private `artist-pipeline-v1/g2-summary-reconciliation-v2.json`: full note
  inventories and aggregate checks. Source-located data stays outside Git.
- Original 36 GP files and native-check JSONL remain in
  `local-artifacts/overnight-palm-sequence-gps-v3/`.

Tuning-relative candidate remains rejected and unpromoted. No approved pedal
identification, source-score repairs, generator defaults or website UI changed.
G3 recreation/transfer and genuine listening acceptance remain separate gates.
