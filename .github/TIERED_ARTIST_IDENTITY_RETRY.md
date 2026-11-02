# Resolve Songsterr artist mismatches and retry only those six entries

## Authorized scope

Resolve the six Songsterr artist-name mismatches, then rerun **only those six entries**. The user explicitly clarified that the six existing analysis failures are a separate task. Keep the existing musical analysis and its validation unchanged for the subsequent discussion. Save output directly to encrypted draft Release assets.

## Acceptance checklist

- [x] Compare current main with the previous retry and read repository instructions.
- [x] Verify the same six song IDs in both the search catalog and metadata endpoint.
- [x] Add narrow per-song reconciliation with explicit catalog/source provenance and untouched raw metadata.
- [x] Verify matching song IDs and track identities before admitting a known mismatch.
- [x] Test exact known matches, unexpected identities, changed tracks, missing/duplicate search rows, and unchanged normal capture behavior.
- [x] Commit on current main without changing analysis code.
- [x] Run only the six reconciled entries and inspect every outcome.
- [x] Verify Release delivery, integrity metadata, and zero Actions artifacts.
- [x] Record the separate six-analysis-failure scope and make the launcher manual-only.

## Completed corrected run

- [Run 41487355735](https://github.com/mtch777/Guitar-Learning/actions/runs/41487355735), attempt 1, commit `575c087433504b66621dc2bb7590827bef112fd9`: **SUCCESS**. Created 2026-11-02 17:02:59 UTC; completed 17:06:31 UTC.
- Exactly six song jobs executed, and all six passed capture, analysis, and independent verification. Each final status reports `verified` and `verified_catalog_metadata_reconciliation`. Inventory passed; the pilot was skipped.
- The separate existing analysis-failure IDs `1817932,993568,1511882,6028811,4248474,3165226` are absent from this corrected run. Their analysis code was not changed; that work remains explicitly deferred.
- [Draft Release 431730564](https://github.com/mtch777/Guitar-Learning/releases/tag/untagged-bf51480090715601947e) contains exactly seven assets: the six encrypted song/output ZIPs and the selected-ID manifest, totaling **53,860,257 bytes**. All assets are uploaded, nonempty, and have SHA-256 digests. Every song asset's size and digest match its verified upload log.
- Corrected run Actions artifacts: **0**. No extra song or pilot asset exists in its Release.
- The launcher is manual-only, selects exactly these six reconciled IDs, and retains `expected_count: 6`. Its temporary cancellation setting is restored to `false`.
- Local identity regression tests: 17/17 passed. The separate automatically triggered isolated repository CI run `41487073758` was still in progress when this end-to-end run completed; it is not represented as completed testing.

## Progress log — 2026-11-02

- Starting main: `0b0e3e9b3f34e69db6a4f8cb06ea90a3f6a5e608`. Previous retry: `41475864505` at `52cbaf208a40951f51b3adaf5a4439c3dae5f66c`.
- All six are same-ID catalog/metadata discrepancies, rather than evidence that the alternate artist profiles are global aliases. Keep each reconciliation tied to the specific song and verified catalog/source identities.
- The two ambiguous cases have additional source-video evidence: catalog ID 4081672 is Currents, `Unf (Drop C#)`; its linked label video is Currents, `Unfamiliar`. Catalog ID 2457200 is ERRA, `Echo Sonata intro Tapping`; its linked label video is ERRA, `echo sonata`.
- Added six explicit rules in `composition-lab/songsterr_identity_reconciliations.json`. A known discrepancy is accepted only when the requested song ID, reviewed metadata identity, unique live catalog row, catalog identity, and complete ordered track fingerprints match the reviewed records. The ordinary artist allowlist remains unchanged.
- Preserved raw metadata including original artist/title and all source flags. Wrote catalog attribution and reconciliation evidence separately in `identity-reconciliation.json`, outside `capture/`, with a copy of the verified catalog record, source endpoints, revisions, and SHA-256 of the track fingerprint. Status retains original source labels and exposes a separate `catalog_identity`.
- Verified all six independently fetched public API records through the actual resolver: six passes, with input metadata unchanged. Python compilation passes. Analysis files and musical validation remain untouched.
- `cd composition-lab && python -m unittest -v test_tiered_catalog_identity`: **17/17 tests passed**, including parameterized cases for all six rules, changed identities and track evidence, normal artist behavior, unchanged source data, correct audit placement, and preservation of downstream failure status. These tests mock musical analysis only to verify runner boundaries; they do not establish musical-analysis success.
- Independent review passed: rules match separately fetched API evidence, the exception remains song-specific, source fields and analysis inputs remain unchanged, and the audit is encrypted with the full result.
- The launcher still contains exactly the original twelve IDs with `expected_count: 12`; only its temporary path-scoped push trigger was restored for this authorized fresh run.
- Committed the identity-only change as `1555b64e38fa44cc30343125161330c9e92dd389`. It initially launched run `41487073742` with the prior twelve-ID selection. The user corrected this scope: only six former identity failures should run. This initial twelve-entry retry was a selection mistake, not authorization to work on the six analysis failures.
- Corrected the launcher to exactly `4081672,6656103,3851017,2457200,3956211,4472844` with `expected_count: 6`. Temporarily enabled cancellation within the existing dedicated retry concurrency group so the corrected six-entry run supersedes the mistaken run if it is still active. Existing diagnostics are retained.
- Correction committed as `575c087433504b66621dc2bb7590827bef112fd9`. The mistaken run `41487073742` completed with conclusion **cancelled**. It is retained as an audit record and is not the corrected run's result.
- Started the corrected [six-entry run 41487355735](https://github.com/mtch777/Guitar-Learning/actions/runs/41487355735). The live job API confirms exactly the six intended analysis jobs, inventory success, and a skipped pilot. None of the six separate analysis-failure IDs appears in this run.
- Draft Release [431730564](https://github.com/mtch777/Guitar-Learning/releases/tag/untagged-bf51480090715601947e) was created for tag `tiered-analysis-run-41487355735-attempt-1`; it is receiving the six-entry run's outputs directly.
- Inspected all six completed job logs: every identity reconciliation, capture, build, and verifier passed. Matched all six upload sizes and digests against the Release asset API; independently checked the exact seven-asset set and zero Actions artifacts.
- Recorded the mistaken twelve-entry run as cancelled and kept its audit history. Saved the corrected six-only outcome and restored the launcher to manual-only operation.

## Verified song-level reconciliation

| Song ID | Catalog artist and title | Metadata artist and title | Matching tracks | Corrected run result |
|---:|---|---|---:|---|
| 4081672 | Currents — Unf (Drop C#) | Lexi — Unf | 5/5 | [Verified](https://github.com/mtch777/Guitar-Learning/actions/runs/41487355735/job/125421727033) |
| 6656103 | Invent Animate — Halcyon (drop E) | Misc Covers — Halcyon (drop E) by Invent Animate | 2/2 | [Verified](https://github.com/mtch777/Guitar-Learning/actions/runs/41487355735/job/125421726561) |
| 3851017 | ERRA — Cure (Light Bass) | misc covers — Cure by Erra (Light Bass) | 4/4 | [Verified](https://github.com/mtch777/Guitar-Learning/actions/runs/41487355735/job/125421726506) |
| 2457200 | ERRA — Echo Sonata intro Tapping | ERR — Echo Sonata intro Tapping | 1/1 | [Verified](https://github.com/mtch777/Guitar-Learning/actions/runs/41487355735/job/125421726422) |
| 3956211 | ERRA — further eden (Bass in Drop Eb) | misc covers — further eden by Erra | 5/5 | [Verified](https://github.com/mtch777/Guitar-Learning/actions/runs/41487355735/job/125421726497) |
| 4472844 | ERRA — Black Cloud (Guitar · 7-string) | yuyayu24 — Black Cloud - ERRA | 2/2 | [Verified](https://github.com/mtch777/Guitar-Learning/actions/runs/41487355735/job/125421726352) |

Evidence: exact song IDs from `https://www.songsterr.com/api/meta/<song_id>` and `https://www.songsterr.com/api/songs?pattern=<catalog_artist>&size=250`. Each rule stores its source URLs and the reviewed track identifiers. Metadata's linked label videos additionally confirm [Currents — Unfamiliar](https://www.youtube.com/watch?v=QeVRtCXbkhs) and [ERRA — echo sonata](https://www.youtube.com/watch?v=iNW1aZughso). Original source quality flags, including `isJunk`, remain preserved; this identity reconciliation makes no musical quality claim.
