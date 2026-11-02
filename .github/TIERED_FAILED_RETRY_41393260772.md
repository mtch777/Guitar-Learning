# Retry the twelve failed entries from run 41393260772

## User-authorized scope

Identify the original twelve failed entries and run the current workflow for only those twelve. Save results and diagnostics directly to draft GitHub Releases. Keep the existing validation checks active and preserve the successful 296 entries.

## Acceptance checklist

- [x] Read all four job pages from the original run and verify exactly twelve failed song IDs.
- [x] Identify the current artist and title for all twelve IDs.
- [x] Add a selected-song input to the existing workflow while preserving full-catalog behavior.
- [x] Validate that selected mode contains exactly the requested IDs and does not run the successful pilot.
- [x] Start a fresh run using current code and Release storage for only the twelve IDs.
- [x] Verify job counts, results, and zero Actions artifacts for the retry.
- [x] Record the actual outcome for every selected entry, including persistent validation failures.

## Exact song IDs

`4081672,1817932,6656103,993568,1511882,6028811,3851017,2457200,3956211,4472844,4248474,3165226`

## Identified entries

Live Songsterr metadata and canonical entry pages were checked on 2026-11-02. These are the current upstream artist identities; titles that credit a band do not change the entry's registered artist ID.

| Song ID | Current artist | Current title | Failure reproduced in targeted retry |
|---:|---|---|---|
| 4081672 | Lexi | Unf | [Rejected artist identity 122760](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290341) |
| 1817932 | ERRA | gore of being | [Added-cycle response-role assertion](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290168) |
| 6656103 | Misc Covers | Halcyon (drop E) by Invent Animate | [Rejected artist identity 86430](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290196) |
| 993568 | ERRA | Eidolon | [Added-cycle response-role assertion](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290157) |
| 1511882 | Currents | My Disguise | [Added-cycle response-role assertion](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290552) |
| 6028811 | ERRA | spiral (of liminal infinity) | [Added-cycle response-role assertion](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290248) |
| 3851017 | misc covers | Cure by Erra (Light Bass) | [Rejected artist identity 500784](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290437) |
| 2457200 | ERR | Echo Sonata intro Tapping | [Rejected artist identity 485079](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290234) |
| 3956211 | misc covers | further eden by Erra | [Rejected artist identity 500784](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290254) |
| 4472844 | yuyayu24 | Black Cloud - ERRA | [Rejected artist identity 182939](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290280) |
| 4248474 | ERRA | lucid threshold AI | [Added-cycle response-role assertion](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290311) |
| 3165226 | Currents | My Disguise (Official | [Added-cycle response-role assertion](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505/job/125381290250) |

Metadata source for each entry: `https://www.songsterr.com/api/meta/<song_id>`. The source title for 3165226 has an unclosed parenthesis; the displayed title for 993568 omits an invisible trailing U+200B.

## Completed retry result

- Run: [41475864505](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505), attempt 1, commit `52cbaf208a40951f51b3adaf5a4439c3dae5f66c`.
- Started 2026-11-02 15:52:28 UTC; completed 15:53:59 UTC. Overall conclusion: **failure**.
- Exactly twelve analysis jobs executed: **0 succeeded, 12 failed**. Inventory succeeded; the pilot was skipped. All twelve reproduced their original failure category.
- Six jobs were rejected by the artist identity guard. The other six reached `evaluate_pedal_expansion.py:42` and failed the assertion that every added response-cycle member retains the `response` role. These are unresolved source-identity and analysis-validation failures.
- [Draft Release 431655978](https://github.com/mtch777/Guitar-Learning/releases/tag/untagged-bc06f9a0ad835244df48), tag `tiered-analysis-run-41475864505-attempt-1`, contains exactly **13 assets: twelve diagnostic/output ZIPs and one selection manifest**, totaling **210,384 bytes**. Every asset is uploaded, nonempty, and has a SHA-256 digest. Every song asset's server digest and size match its verified upload log.
- Retry Actions artifacts: **0**, confirmed through the run artifacts API after completion. The Release contains no pilot asset or unexpected song ID.
- The launcher is now manual-only. The reusable workflow keeps the selected-ID inputs for future targeted runs. The retry did not produce any newly verified song analyses.

## Progress log — 2026-11-02

- Current main inspected at `2950ac6fb8a100157cb145010b172e11dd2b8ddb`.
- Original run has 309 jobs, including pilot/inventory; exactly twelve song jobs failed. The explicit retry set matches those twelve IDs.
- Six original failures were analysis assertions; six were artist-identity rejections. A retry must report actual results without weakening checks to force success.
- The original run's Re-run button uses its old code and artifact uploads. Use the updated reusable workflow with the exact selection instead.
- Added `song_ids` and `expected_count` inputs for manual and reusable workflow calls. Selected mode validates the requested IDs before analysis, skips the pilot, and avoids a full-catalog download. Empty/default input preserves the original full-catalog behavior.
- Validated the exact embedded selection script against 15 cases, including the exact twelve IDs, singleton, selected pilot once, full 308-entry mode, malformed/duplicate IDs, count mismatch, blank-selection protection, and maximum count. All passed. YAML parsing and shell syntax also passed.
- The dedicated launcher passes the verified twelve IDs and `expected_count: 12`. Its temporary path-scoped push trigger starts one fresh run on current code; remove the push trigger after the run, retaining manual dispatch.
- Launched [run 41475864505](https://github.com/mtch777/Guitar-Learning/actions/runs/41475864505) from commit `52cbaf208a40951f51b3adaf5a4439c3dae5f66c` at 15:52:28 UTC. Inventory succeeded and emitted the exact twelve-ID selection, with `pilot_song_id: null` and `total_songs_to_process: 12`.
- GitHub expanded exactly twelve analysis jobs; the Cloud Cascade pilot was skipped. The selection manifest was saved to the new draft Release as a 942-byte ZIP with SHA-256 `e0dfed1301fcfbfeb0246c45c0583d67470b87fb4ae1e0288e0464b1e91e1be8`.
- Inspected all twelve completed job logs and matched each failure to its original category. Verified every Release upload against the asset API, with no missing or unexpected outputs and zero Actions artifacts.
- Removed the launcher's temporary push trigger; retained manual dispatch with the same fixed twelve IDs and `expected_count: 12`.
