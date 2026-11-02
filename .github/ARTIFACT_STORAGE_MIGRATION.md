# Tiered analysis output storage

## Authorized task

Move the outputs of GitHub Actions run `41393260772` out of Actions artifact storage. Preserve every file and its encryption, verify durable replacement copies, and then remove the corresponding Actions artifacts. Future tiered analysis runs must write directly to Release storage.

## Acceptance checklist

- [x] Inspect current repository instructions, workflow, and completed source run.
- [x] Freeze scope: 309 artifacts, 8,741,137,087 bytes, run `41393260772` only.
- [x] Test source checksum, destination verification, conflict, and partial-resume safeguards.
- [x] Move all 309 original ZIP archives unchanged to a draft Release.
- [x] Verify every destination SHA-256 and size before deleting its source artifact.
- [x] Confirm the source run has zero remaining Actions artifacts.
- [x] Replace all three upload-artifact steps in the tiered analysis workflow with direct draft Release uploads.
- [x] Verify the storage patch does not automatically rerun the 308-song analysis.

## Storage contract

- Destination: draft Release `tiered-analysis-run-41393260772` in this same repository.
- Keep the Release in draft state; do not publish source notation or decrypted results.
- Copy original artifact ZIP bytes without extraction or repackaging.
- Store the original artifact inventory/checksums in the Release before any source deletion.
- Delete an individual Actions artifact only after independently verifying its matching Release asset.
- If download, upload, or validation fails, preserve the affected source artifact and fail visibly.
- Reruns resume from the saved inventory and verified Release copies; mismatched existing assets are never overwritten.
- Future analysis outputs contain only explicit encrypted CMS files and status/catalog metadata.
- Future analysis runs are manually dispatched. Updating the storage workflow must not launch another full catalog analysis.

## Progress log

### 2026-11-02 — preparation

- Current main inspected at `e3f21d53ba22933842e87207ff92e818978af376`.
- Source run completed with 296 successful song entries and 12 failed entries; preserve both results and failure diagnostics.
- The three existing artifact uploads retained outputs for 30 days and consumed 8.74 GB for this run.
- Identified automatic push trigger on the analysis workflow itself; remove that trigger in the same commit as the storage change.
- Migration uses GitHub's existing per-job token with contents/actions write permissions. No private credentials or decryption keys are requested.
- Next: run safety tests, commit the bounded storage changes, execute migration, and record independently verified final counts.

### 2026-11-02 — validation before execution

- `python -m unittest discover -s .github/scripts -p 'test_release_storage.py' -v`: 18 tests PASS. Checks cover source corruption, destination corruption, failed upload, durable inventory ordering, wrong-run rejection, non-draft rejection, conflicting assets, partial resume, missing prior destination, digest readback fallback, explicit-file packaging, draft discovery, interrupted downloads, token removal on cross-host redirects, and secondary-rate-limit retry.
- Parsed both workflow YAML files and checked every shell step with `bash -n`: PASS.
- Compared the updated analysis workflow to the current source: all analysis/encryption steps, jobs, matrices, dependencies, and diagnostic `always()` conditions preserved; all three Actions artifact uploads replaced.
- Migration enumerates all source pages, validates all source identities, and verifies a durable checksum inventory before starting any deletions.
- Next: commit the five storage files, let the bounded migration run, and independently compare all Release copies with the original inventory.

### 2026-11-02 — first execution and bounded correction

- Storage patch committed as `0838517ca6bb4cc095a123c32ffc13ccf2352468`.
- Migration run `41468478310` passed all 18 tests on the hosted runner, then GitHub rejected draft Release creation with HTTP 403 before any source deletion.
- Runner explicitly received Actions write and Contents write permissions. No Release or migrated asset was created.
- Adjust the Release container to target the current migration commit; keep the historical source commit in the immutable source inventory. Add sanitized API error messages for precise diagnosis if GitHub still rejects creation.
- All 309 source artifacts remain preserved while this correction is applied.

### 2026-11-02 — API download correction

- Commit `6e4db2be24c471ddb8e2d5520669f8b39c1a9802` resolved Release creation. Draft Release `431609715` exists and its source inventory was uploaded and verified.
- Run `41468929388` exposed the API distinction: Actions artifact archive endpoints reject the octet-stream Accept header with HTTP 415; Release asset downloads require it. All 309 source files were preserved.
- Corrected endpoint-specific Accept headers and added a transport regression test; retain all checksum/deletion gates.

### 2026-11-02 — completed and independently verified

- Successful migration: [run 41469306782](https://github.com/mtch777/Guitar-Learning/actions/runs/41469306782), commit `c95ad1e5cba5e91522b85ce1310c1c9f200b6e59`. Finished at 15:21:27 UTC (08:21:27 MST).
- [Draft Release](https://github.com/mtch777/Guitar-Learning/releases/tag/untagged-c2911c4c07760f2b952a), ID `431609715`, tag `tiered-analysis-run-41393260772`.
- 309 original ZIP archives preserved: exactly **8,741,137,087 bytes**.
- Independently fetched all four Release asset pages and compared every ZIP to the original inventory: **309/309 names, sizes, and SHA-256 digests matched; zero mismatches**.
- Release contains 310 assets: the 309 unchanged ZIP archives plus `source-artifacts.json` (84,462 bytes; SHA-256 `449e8f9f48c444c07121c3776397dbb507fe42094308e5a1b89be4d7660ce959`).
- Migration log reports 309 moved, zero errors, zero remaining artifacts, and zero remaining source bytes. Independent source-run API query confirms **0 artifacts**.
- Final repository inventory: 151 artifacts from other runs, totaling 391,223,971 bytes. These are outside this task's original-run scope.
- Final transport/safety suite: `python -m unittest discover -s .github/scripts -p 'test_release_storage.py' -v` — **21 tests passed**, including the endpoint-specific download header regression.
- Future tiered analysis writes directly to draft Releases, preserves CMS encryption, and has no Actions artifact upload step.
- The one-time migration workflow is now manual-only; editing it will not automatically restart migration.
- `AGENTS.md` records the instruction to keep bulk song/analysis outputs out of Actions artifact storage.
- Storage migration is complete. The original 12 song-analysis failures are separate and were not rerun by this storage task.
