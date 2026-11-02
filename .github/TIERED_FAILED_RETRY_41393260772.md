# Retry the twelve failed entries from run 41393260772

## User-authorized scope

Identify the original twelve failed entries and run the current workflow for only those twelve. Save results and diagnostics directly to draft GitHub Releases. Keep the existing validation checks active and preserve the successful 296 entries.

## Acceptance checklist

- [x] Read all four job pages from the original run and verify exactly twelve failed song IDs.
- [x] Identify the current artist and title for all twelve IDs.
- [x] Add a selected-song input to the existing workflow while preserving full-catalog behavior.
- [x] Validate that selected mode contains exactly the requested IDs and does not run the successful pilot.
- [ ] Start a fresh run using current code and Release storage for only the twelve IDs.
- [ ] Verify job counts, results, and zero Actions artifacts for the retry.
- [ ] Record the actual outcome for every selected entry, including persistent validation failures.

## Exact song IDs

`4081672,1817932,6656103,993568,1511882,6028811,3851017,2457200,3956211,4472844,4248474,3165226`

## Identified entries

Live Songsterr metadata and canonical entry pages were checked on 2026-11-02. These are the current upstream artist identities; titles that credit a band do not change the entry's registered artist ID.

| Song ID | Current artist | Current title | Original failure |
|---:|---|---|---|
| 4081672 | Lexi | Unf | Artist identity 122760 is outside the three allowed artists |
| 1817932 | ERRA | gore of being | Added-cycle response-role assertion |
| 6656103 | Misc Covers | Halcyon (drop E) by Invent Animate | Artist identity 86430 is outside the three allowed artists |
| 993568 | ERRA | Eidolon | Added-cycle response-role assertion |
| 1511882 | Currents | My Disguise | Added-cycle response-role assertion |
| 6028811 | ERRA | spiral (of liminal infinity) | Added-cycle response-role assertion |
| 3851017 | misc covers | Cure by Erra (Light Bass) | Artist identity 500784 is outside the three allowed artists |
| 2457200 | ERR | Echo Sonata intro Tapping | Artist identity 485079 is outside the three allowed artists |
| 3956211 | misc covers | further eden by Erra | Artist identity 500784 is outside the three allowed artists |
| 4472844 | yuyayu24 | Black Cloud - ERRA | Artist identity 182939 is outside the three allowed artists |
| 4248474 | ERRA | lucid threshold AI | Added-cycle response-role assertion |
| 3165226 | Currents | My Disguise (Official | Added-cycle response-role assertion |

Metadata source for each entry: `https://www.songsterr.com/api/meta/<song_id>`. The source title for 3165226 has an unclosed parenthesis; the displayed title for 993568 omits an invisible trailing U+200B.

## Progress log — 2026-11-02

- Current main inspected at `2950ac6fb8a100157cb145010b172e11dd2b8ddb`.
- Original run has 309 jobs, including pilot/inventory; exactly twelve song jobs failed. The explicit retry set matches those twelve IDs.
- Six original failures were analysis assertions; six were artist-identity rejections. A retry must report actual results without weakening checks to force success.
- The original run's Re-run button uses its old code and artifact uploads. Use the updated reusable workflow with the exact selection instead.
- Added `song_ids` and `expected_count` inputs for manual and reusable workflow calls. Selected mode validates the requested IDs before analysis, skips the pilot, and avoids a full-catalog download. Empty/default input preserves the original full-catalog behavior.
- Validated the exact embedded selection script against 15 cases, including the exact twelve IDs, singleton, selected pilot once, full 308-entry mode, malformed/duplicate IDs, count mismatch, blank-selection protection, and maximum count. All passed. YAML parsing and shell syntax also passed.
- The dedicated launcher passes the verified twelve IDs and `expected_count: 12`. Its temporary path-scoped push trigger starts one fresh run on current code; remove the push trigger after the run, retaining manual dispatch.
- Next: commit, launch, and inspect the twelve outcomes.
