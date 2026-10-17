# Songsterr Automation — Usage and Handoff Guide

Repository: https://github.com/mtch777/Guitar-Learning  
Branch: `main`  
Directory: `composition-lab/songsterr_automation/`

## Status (2026-10-16)

**Working and tested:** Search and Songsterr metadata, revision discovery, notation fetching, Songsterr-to-GP5 reconstruction, GP5-to-GP7 conversion/reimport, source-to-GP5 fidelity comparison, and expanded multi-song corpus testing.

**Verified:** `results/source_corpus_report.json` reports 8/8 tracks passing across five song IDs and 5,606 source notes, with zero detected differences under the independent source-vs-GP5 comparator. `results/source_fidelity_report.json` reports 218/218 notes, 81/81 measures, zero differences for Wish You Were Here lead guitar. `results/gp7_roundtrip_report.json` reports 0 mismatched compared events between GP5 and reimported GP7, preserving its counted effects. Note object counts in alphaTab (232) are not directly comparable to PyGuitarPro's 218 without normalization.

**Not yet established:** direct original-JSON-to-GP7 fidelity across the corpus; end-user browser integration; full validation of all configurable downloader input combinations; permanence of generated GP files in Git history; absence of all possible unsupported notation fields.

## Configurable downloader — verified smoke test (2026-10-16)

Workflow: https://github.com/mtch777/Guitar-Learning/actions/workflows/songsterr-download.yml

**Verified on GitHub:** A push-triggered smoke test downloaded song ID `153`, track index `2`, reconstructed GP5 and exported/reopened GP7. The committed `results/configurable_download_selection.json` reports downloader status `ok`, return code `0`, and no errors. The committed `results/configurable_download_exports.json` reports `success: true`, 232/232 alphaTab note objects retained, 81 measures, one track and a 12,209-byte GP7 file.

- Selection report: https://github.com/mtch777/Guitar-Learning/blob/main/composition-lab/songsterr_automation/results/configurable_download_selection.json
- Export report: https://github.com/mtch777/Guitar-Learning/blob/main/composition-lab/songsterr_automation/results/configurable_download_exports.json

### How to use

Open the configurable workflow and choose **Run workflow** on `main`. Supply either an exact `song_id` (number or Songsterr URL) **or** artist and optional song title. Leave `song_id` empty when using artist/title search. Use `song=ALL` to retrieve search matches for an artist (bounded by `max_songs`). The inputs are:

| Input | Usage |
| --- | --- |
| `artist` | Artist name for search |
| `song` | Title substring or `ALL` |
| `song_id` | Songsterr numeric ID or tab URL; overrides search |
| `tracks` | `all`, `guitar`, `bass`, `drums`, `vocals` or zero-based comma-separated indices such as `2,7` |
| `output` | Repository-relative folder under `composition-lab/songsterr_automation/downloads` |
| `existing` | `skip` or `overwrite` |
| `max_songs` | 1–100 results for search |
| `save_to_repo` | Commit generated files to `main` when true; use only with appropriate rights |

Example: `song_id=153`, `tracks=2`, `existing=overwrite`, `save_to_repo=false`. Output: `downloads/153/Pink Floyd - Wish You Were Here.gp5` and `.gp`, accessible from the run's `songsterr-downloaded-scores` Actions artifact, retained for 30 days.

For artist selection, set `artist=Pink Floyd`, `song=Comfortably Numb`, `song_id=` (empty), `tracks=guitar`, `max_songs=10`. This configuration is supported by the code but **not yet individually verified in CI**.

The workflow's push trigger is primarily for smoke testing and uses fixed `153` / track `2` defaults. A manual `workflow_dispatch` uses supplied inputs. The current script uses third-party `songsterr-dl`, installed from its upstream default branch at execution time, and `@coderline/alphatab@1.8.1` for GP7 export. `download_configurable.py` handles selection and GP5 generation; `export_gp7_batch.mjs` converts each resulting GP5 and checks that note and measure counts survive reimport.

### Limits to note before reusing

- The verified configurable smoke test covered one exact song ID and one selected guitar track, **not** every input combination.
- Song/title discovery uses a search request capped at 100 results and then truncates to `max_songs`; `ALL` is therefore **not a proven exhaustive artist catalog crawl**.
- The current batch export validates GP5-vs-GP7 **counts**, not full effect-by-effect fidelity for arbitrary songs. Use the existing dedicated source corpus validator where needed.
- `skip` currently skips an entire song folder if it contains any GP5, not an individual track-specific revision.
- All selected tracks are combined into one score per song by the underlying converter; categorical selection is based on track name/instrument text.
- Generated files live in temporary run artifacts by default. `save_to_repo=true` attempts to commit them into the output folder on `main`.
- Workflow credentials need `contents: write` for optional commits and diagnostic results. Respect transcription copyrights and Songsterr terms.

## Quick links

- Workflow: https://github.com/mtch777/Guitar-Learning/actions/workflows/songsterr-e2e.yml
- API smoke workflow: https://github.com/mtch777/Guitar-Learning/actions/workflows/songsterr-api-smoke.yml
- Latest source corpus report: https://github.com/mtch777/Guitar-Learning/blob/main/composition-lab/songsterr_automation/results/source_corpus_report.json
- GP7 round-trip report: https://github.com/mtch777/Guitar-Learning/blob/main/composition-lab/songsterr_automation/results/gp7_roundtrip_report.json
- Single-track source fidelity report: https://github.com/mtch777/Guitar-Learning/blob/main/composition-lab/songsterr_automation/results/source_fidelity_report.json

## What lives where

- `songsterr_api/test_endpoints.py`: seven basic endpoint probes, optional extras.
- `songsterr_api/inspect_metadata.py`: search response and metadata inventory.
- `songsterr_api/inspect_notation.py`: revision metadata inspection.
- `songsterr_api/validate_conversion.py`: checks generated GP5 measures, beats and notes.
- `songsterr_api/gp7_roundtrip.mjs`: opens generated GP5 with alphaTab, exports a GP7 `.gp`, reopens and compares events and technique counts.
- `songsterr_api/validate_source.py`: directly compares one live Songsterr notation payload against generated GP5, using an independent comparator supplied by upstream `songsterr-dl`.
- `songsterr_api/validate_corpus.py`: performs an eight-track, five-song source-vs-GP5 validation corpus.
- `songsterr_downloader/README.md`: describes the upstream web-based GP7 downloader; it has **not** been vendored or embedded.
- `results/*.json`: committed machine-readable test reports.
- `.github/workflows/songsterr-e2e.yml`: current conversion and validation workflow.
- `.github/workflows/songsterr-api-smoke.yml`: endpoint/connectivity inventory.

## How another ChatGPT chat can use it

Provide the repository URL, branch and this file path. Ask the chat to **read the current files from GitHub first** (not rely on previous conversation summaries), inspect the reports, and make changes/commits through the connected GitHub app when appropriate. If GitHub is not connected in that chat, it will need access to the repository another way. This guide is repo-stored, so it is portable between conversations.

Suggested new-chat message:

> Work on `mtch777/Guitar-Learning`, branch `main`. Read `composition-lab/songsterr_automation/USAGE_GUIDE.md`, the current scripts, `.github/workflows/songsterr-e2e.yml`, and the committed reports. Use the existing working Songsterr pipeline rather than starting over. For new work, implement, commit, trigger through a workflow-file push if needed, fetch run logs/artifacts where possible, and distinguish actual test success from successful commits.

## How to run the existing tests on GitHub

1. Open https://github.com/mtch777/Guitar-Learning/actions/workflows/songsterr-e2e.yml
2. Run the workflow on `main`, or commit an actual edit to `.github/workflows/songsterr-e2e.yml`. Its `push` trigger responds **only to changes to that workflow file**, not to every script change.
3. The workflow checks out the repo, installs Python 3.13, `pyguitarpro` and upstream `songsterr-dl`, downloads a test track, validates GP5, converts to GP7 via `@coderline/alphatab`, checks GP7 round-trip, checks original notation, and runs the expanded corpus.
4. Consult run logs and the `songsterr-e2e-conversion` artifact. Generated GP files are inside workflow artifacts, which expire; the JSON summaries are pushed into `results/`.
5. Check **each named step** and the JSON reports. A workflow commit/push does not itself prove the test passed.

The workflow has fixed cases:
- Primary GP5/GP7 round-trip: Songsterr song `153` (Pink Floyd — Wish You Were Here), zero-based track `2`.
- Corpus: `153` tracks `2,7,10`; `271` tracks `3,6`; `378962` track `0`; `10770` track `0`; `63101` track `0`.

For different songs or tracks, update the scripts or implement workflow inputs; current `workflow_dispatch` has no song/track parameters.

## Using Songsterr APIs

Previously validated Songsterr endpoints:

```text
GET https://www.songsterr.com/api/songs?pattern=Pink+Floyd&size=5
GET https://www.songsterr.com/api/meta/153
GET https://www.songsterr.com/api/meta/153/revisions
```

Metadata yields song ID, artist ID, title, track names, instrument IDs, tuning, difficulty where present, track hash, views, revision IDs, content image/hash, authorship, tags and other available metadata. The current JSON payloads may change.

For per-track notation, the upstream Python client obtains the current `revisionId` and `image` from song metadata and fetches the JSON at:

```text
https://dqsljvtekg760.cloudfront.net/{songId}/{revisionId}/{image}/{trackIndex}.json
```

Indices are zero-based. Do not confuse a Songsterr song ID with an artist ID (for example 79 is the artist ID for Pink Floyd). The CDN is an implementation detail and may change.

Avoid treating failures of older `/a/wa/` and `/a/ra/` routes as proof of failed connectivity: the confirmed modern search and metadata routes returned HTTP 200 on GitHub Actions.

## Downloading a GP5 locally

Requires Python >=3.13 and installation of upstream https://github.com/6801318d8d/songsterr-dl (a third-party dependency, not vendored here). An example in a shell with `songsterr-dl` installed:

```bash
songsterr-dl --search "Comfortably Numb"
songsterr-dl 271 --list-revisions
songsterr-dl 271 --tracks 3 -f gp5 -o tabs --overwrite
songsterr-dl 271 -f gp5 -o tabs --overwrite
```

The last command selects all tracks. Formats provided by that converter are `tg`, `gp5`, `gp4`, `gp3`; it does not directly emit GP7. Review its emitted `*_report.txt` for documented losses.

## GP7 export

The working GitHub pipeline uses `@coderline/alphatab@1.8.1` and `songsterr_api/gp7_roundtrip.mjs` to export the newly created GP5 to Guitar Pro 7 format (`.gp`) and reimport it. It currently finds the first `*.gp5` inside its input directory.

Within the repo root, after installing Node dependencies and placing a GP5 file in `songsterr-e2e/`:

```bash
npm install --no-save @coderline/alphatab@1.8.1
node composition-lab/songsterr_automation/songsterr_api/gp7_roundtrip.mjs songsterr-e2e
```

Its report is written at `results/gp7_roundtrip_report.json`. This is a GP5-vs-GP7 comparison, **not** by itself direct source JSON vs GP7 parity.

## Validation policy and known limitations

- Source-vs-GP5: `validate_source.py` and `validate_corpus.py` use the independent `tests.comparison.compare_track` supplied by the cloned upstream repository at `/tmp/songsterr-dl`. As written, these scripts depend on that exact path and on the upstream implementation being compatible.
- GP7 round-trip: compares note-event fields plus **aggregate** technique counts; it does not check all source fields, bend curves or every effect parameter independently.
- Several source fields are not carried by the GP5 converter, including lyrics, crescendo/diminuendo markings, how tuning flats were spelled, and certain unsupported notation. The corpus reports explicitly show warnings (e.g. dozens of crescendo/diminuendo markings on some tracks) despite zero differences for the comparator's checked fields. Treat zero differences as **zero detected differences in tested fields**, not proof of lossless conversion.
- GP5 writer and alphaTab exporter may have different fidelity and format constraints. GP7 should be source-compared independently if strict losslessness is needed.
- This work generates reconstructed scores, **not original uploader GP files**. Use only with content you have permission to use, in accordance with Songsterr terms and applicable copyright.
- Upstream `songsterr-dl` is cloned from its floating default branch in CI; pin a commit for reproducible validation.
- Results JSON are committed; generated GP5/GP7 score files are uploaded as **temporary Actions artifacts**, not automatically persisted into the GitHub repository.
- The workflow uses `contents: write` because it commits result summaries. Another chat should avoid unnecessary workflow edits, secrets, and unreviewed remote code changes.

## Further improvements

1. Test artist/song discovery and all track-selector categories, and add clearer GP7 fidelity validation to the configurable workflow.
2. Persist an optional user-selected generated score to a GitHub-managed destination instead of only an expiring artifact (subject to rights and repository size policies).
3. Compare **live Songsterr JSON directly to GP7**, field-by-field for pitch, timing, rhythm, tuning, instruments, bends/curves, slides, hammer/pull, grace notes, tremolo, dynamics and structural metadata.
4. Add clear mismatch categories and test a pinned corpus with more unusual rhythmic and expressive features.
5. Pin external converter/tool versions and integrate a configurable frontend or Composition Lab import path only after fidelity requirements are met.


## CSV corpus acquisition (2026-10-17)

Read CORPUS_RESULTS.md and CORPUS_PROGRESS.md for the new private CSV batch adapter and its actual98-entry results. It reuses the existing converter but adds a reversible8-string bridge, exact source-rhythm restoration, native GP7 export, serialized-source and detailed roundtrip checks, and an independent raw-notation technique inventory. The legacy GP5 downloader fails on8-string notes and its count-only GP7 smoke report is insufficient for technique fidelity. Generated scores/raw JSON/CSV stay under ignored local-artifacts; never use save_to_repo for this corpus.74/98 detailed roundtrip passes are not a claim of lossless conversion; all98 regular-note source checks and vanilla GP7 imports pass in their narrower scopes. No new source-derived musical-feel result is claimed.
