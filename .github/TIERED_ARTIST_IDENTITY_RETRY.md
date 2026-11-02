# Resolve Songsterr artist mismatches and retry the failed entries

## Authorized scope

Resolve the six Songsterr artist-name mismatches, then rerun **only those six entries**. The user explicitly clarified that the six existing analysis failures are a separate task. Keep the existing musical analysis and its validation unchanged for the subsequent discussion. Save output directly to encrypted draft Release assets.

## Acceptance checklist

- [x] Compare current main with the previous retry and read repository instructions.
- [x] Verify the same six song IDs in both the search catalog and metadata endpoint.
- [x] Add narrow per-song reconciliation with explicit catalog/source provenance and untouched raw metadata.
- [x] Verify matching song IDs and track identities before admitting a known mismatch.
- [x] Test exact known matches, unexpected identities, changed tracks, missing/duplicate search rows, and unchanged normal capture behavior.
- [x] Commit on current main without changing analysis code.
- [ ] Run only the six reconciled entries and inspect every outcome.
- [ ] Verify Release delivery, integrity metadata, and zero Actions artifacts.
- [ ] Record actual remaining analysis failures and make the launcher manual-only.

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
- Next: verify the corrected six-entry run, its identities/outcomes, and seven Release assets with zero Actions artifacts.

## Verified song-level reconciliation

| Song ID | Catalog artist and title | Metadata artist and title | Matching tracks |
|---:|---|---|---:|
| 4081672 | Currents — Unf (Drop C#) | Lexi — Unf | 5/5 |
| 6656103 | Invent Animate — Halcyon (drop E) | Misc Covers — Halcyon (drop E) by Invent Animate | 2/2 |
| 3851017 | ERRA — Cure (Light Bass) | misc covers — Cure by Erra (Light Bass) | 4/4 |
| 2457200 | ERRA — Echo Sonata intro Tapping | ERR — Echo Sonata intro Tapping | 1/1 |
| 3956211 | ERRA — further eden (Bass in Drop Eb) | misc covers — further eden by Erra | 5/5 |
| 4472844 | ERRA — Black Cloud (Guitar · 7-string) | yuyayu24 — Black Cloud - ERRA | 2/2 |

Evidence: exact song IDs from `https://www.songsterr.com/api/meta/<song_id>` and `https://www.songsterr.com/api/songs?pattern=<catalog_artist>&size=250`. Each rule stores its source URLs and the reviewed track identifiers. Metadata's linked label videos additionally confirm [Currents — Unfamiliar](https://www.youtube.com/watch?v=QeVRtCXbkhs) and [ERRA — echo sonata](https://www.youtube.com/watch?v=iNW1aZughso). Original source quality flags, including `isJunk`, remain preserved; this identity reconciliation makes no musical quality claim.
