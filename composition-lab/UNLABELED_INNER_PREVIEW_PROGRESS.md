# Unlabeled inner-voicing integration

2026-10-28. Parent checkpoint: `8e92d34`. START contract:
`UNLABELED_INNER_PREVIEW_START.md`. Private outputs:
`local-artifacts/unlabeled-inner-preview-v1/`.

## Acceptance

- [x] Planner START: reuse existing harmonic evidence and source patterns;
  preserve every assumption and existing lock. No new chord/key detector.
- [x] Existing plain, declared-degree and spacing owners realize the same
  conditional source components through the connected inverse.
- [x] Written-label masking leaves available layouts and source-group weights
  unchanged. Multiple chord interpretations do not multiply donor votes.
- [x] C6/Am7 fixture: both interpretations support one actual changed layout;
  missing one retained interpretation's mapping refuses the proposal.
- [x] Recovered degrees match the proposal under every retained interpretation.
  Caller pitches, incomplete support and stale resolved pitches are rejected.
- [x] Temporal support excludes the entire edited set together. Tests cover
  held notes crossing a context change, empty support and unknown support.
- [x] Actual isolated zero/changed fixture workers use the same module sources.
- [x] Planner MID: adapter retains one pitch owner; all-fit agreement is finite
  vocabulary compatibility, not proof of a true chord or intended note role.
- [x] New frozen random capture, retained failures/no-choice, unchanged code.
- [x] Independent native inventory, every candidate/refusal and actual output
  checked on complete real captures, including previous development cases.
- [x] Whole-source, owner-pair and explicit operation-zero workers pass;
  actual changed worker, GP and PCM checks where a change is available.
- [x] Full relevant regression suite and independent Planner END review.
- [x] Actual browser checks: playback, source/change switching, cue, keyboard
  seek, zero-speed pause, 10% and 100% speed, guitar and full ensemble.
- [x] Complete old Queen policy rerun matches its frozen baseline.
- [ ] Verified source committed/pushed; exact-commit CI checked.

## Commands/results

- `..\.venv\Scripts\python.exe -m unittest test_unlabeled_inner_voicing test_nominal_harmony -q`:
  26 passed, 9.121s.
- Targeted new/old inner, independent, temporal and ledger suites:
  38 passed, 47.195s.
- Planner found a missing formula argument in the new degree roundtrip before
  freezing. Fixed by using the original retained hypothesis, not guessing one.
- Full Python discovery: 1,342 tests run, 1,341 passed, one optional skip,
  160.225s. The two subsequently added runner tests passed separately; Planner's
  supplemental 19-test suite also passed. No sum of overlapping suites is claimed.
- Existing JS checks: 19 passed. `node --test test_source_preview_notes.mjs`:
  two passed. Vite build passed (1.00s). Syntax checks passed.
- `..\.venv\Scripts\python.exe local-artifacts/unlabeled-inner-preview-v1/prepare.py`:
  froze 541 project Python files, 266 native files, nine client modules and 32
  sampling seeds before the new draw. Fresh seed `6044710712646952877`, query
  `s`, 97 eligible search results after 171 exclusions. This is a reproducible
  search-result draw, not a uniform draw from Songsterr's entire catalogue.
- `..\.venv\Scripts\python.exe local-artifacts/unlabeled-inner-preview-v1/run_frozen.py fresh`:
  completed the fresh capture without a reroll or logic change.
- The same runner with `queen departure legacy-queen`: Queen and Departure
  complete. The old-policy rerun also passed: all counts, the complete choices
  ledger, actual zero output and actual changed output exactly match its old
  frozen Queen baseline (47 targets, 16 eligible, four changed layouts, six
  rejected, 20 independently checked changed pairs). Frozen Python/native
  hashes remained unchanged. See `frozen-v1/legacy-default-regression.json`.
- `node build_contact_preview.mjs` with the Queen/fresh result directories,
  private backend and pinned alphaTab/soundfont produced source, exact-zero and
  changed GP files plus focused/ensemble WAVs. Native note/audio checks passed.

## Results against the three gates

| Capture | Complete source recovery | Complete candidate audit | Changed output |
| --- | --- | --- | --- |
| Fresh: All The Small Things | 6,513 notes; 60,358 facts | 3,794/3,794 groups; 364 eligible, including 324 without a written chord label | None. All available placements equal the source under current locks. |
| Queen development case | 3,384 notes; 37,953 facts | 2,186/2,186 groups; 78 eligible; four changed layouts accepted and ten rejected | Four changed layouts, all on already labeled groups. Actual isolated preview equals the previously approved change. |
| Departure development case | 778 notes; 12,114 facts | 778/778 groups; no exact harmonic fit | None; retained as a no-choice outcome. |

**QA1:** frozen logic ran on the preregistered new capture. No omitted targets
or new capture chosen to obtain an audible success.

**QA2:** actual complete-source, owner-pair and operation-zero workers passed.
Queen's actual changed worker passed the independent raw/native oracle. All
six new Queen WAVs are byte-identical to the previous experiment. The old
human-fit pass therefore applies once to the same audio, not to a new example.

**QA3:** existing conditional chord degrees now drive real choices without
requiring a written label. Every retained interpretation must support the
same proposed placement. Edited notes cannot certify one another's context.
This establishes finite-vocabulary compatibility and exact equations, not
correct key/function/intent, comfortable fingering or artist-wide fidelity.
The broader creative gateway remains open: no new unlabeled audible change.

## Independent review and UI

Planner START/MID/END passed within this scope. Independent END replay checked
every fresh/Queen/Departure candidate and refusal, all 121,408 fresh and 69,952
Queen seeded draws, actual isolated outputs, native GP/PCM and frozen hashes.
Evidence lives under `frozen-v1/planner-*-review.json` and associated private
audit scripts; native UI evidence is in `queen-qa/native-preview/ui-review.json`
and its two screenshots. No private scores, annotations or audio are published.

The browser test exposed a serving issue: generic `python -m http.server`
loaded audio but did not seek correctly. Reusing `serve_private_review.py`
with byte-range responses fixed it. Retest verified the 2.730357s chord cue,
live source/changed switching, 10% playback, 0% pause, 100% speed, guitar and
ensemble playback, and keyboard seeking from 2.730357s to 2.980357s. No console
warnings/errors or visible error remained. The previously approved phone
viewer and its frozen assets were left intact.

Planner's next recommendation: connect the already-tested canonical
root/register-frame relationship to this label-independent source pool. This
would test observed same-quality placements across roots under every retained
target interpretation. Preserve outer notes, pitch-class/formula coverage,
execution and provisional contact guards; first enumerate the fixed existing
source population and retain no-choice. It is a proposed next endeavor, not an
implemented or accepted cross-root creative result.

Next: publish only verified source and check exact-commit CI.
