# Tiered analysis output storage

## Authorized task

Move the outputs of GitHub Actions run `41393260772` out of Actions artifact storage. Preserve every file and its encryption, verify durable replacement copies, and then remove the corresponding Actions artifacts. Future tiered analysis runs must write directly to Release storage.

## Acceptance checklist

- [x] Inspect current repository instructions, workflow, and completed source run.
- [x] Freeze scope: 309 artifacts, 8,741,137,087 bytes, run `41393260772` only.
- [x] Test source checksum, destination verification, conflict, and partial-resume safeguards.
- [ ] Move all 309 original ZIP archives unchanged to a draft Release.
- [ ] Verify every destination SHA-256 and size before deleting its source artifact.
- [ ] Confirm the source run has zero remaining Actions artifacts.
- [x] Replace all three upload-artifact steps in the tiered analysis workflow with direct draft Release uploads (prepared and verified locally).
- [x] Verify the storage patch does not automatically rerun the 308-song analysis (manual-only trigger verified locally).

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
