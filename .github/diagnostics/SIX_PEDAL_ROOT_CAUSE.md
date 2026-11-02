# Six pedal-expansion failures: confirmed root cause

Investigation only, 2026-11-02. No fix applied to main or production analysis/workflow files.

## Execution and scope

[Diagnostic run 41536992120](https://github.com/mtch777/Guitar-Learning/actions/runs/41536992120) completed successfully at 22:25:47 UTC on diagnostic/pedal-six-20261102, commit d366a2e06afa309e1c5a21e4b2179d879146be55. Exactly six diagnostic jobs ran. Base production commit: f9ca4fc6e9c97227d0cc70e9be1d78028a8d6463. The diagnostic launcher was made manual-only in 227d7ac670bd4dcc4e72dbc2d7fdbaece5cc8906.

Fresh captures matched the same revision IDs as the failed retry. This was not a decryption or byte-identical replay of the historical encrypted archives. Fresh captured bytes and production expander bytes stayed unchanged during every test.

## Cause

In composition-lab/pedal_expansion.py:184, backward expansion reads `preceding=original[i-1] if i else None`. That is the previous phrase's pre-expansion state, although that phrase has already expanded. Neighboring differently anchored phrases can therefore expand into the same gap. The final `_merge` overwrites overlapping roles via `target['roles'].update(region['roles'])` at line31 while retaining added cycle records at line33. The retained records then contradict the final role map. The evaluator correctly fails the response-membership assertion at evaluate_pedal_expansion.py:42.

Both implicated blobs match the earlier failed retry commit 52cbaf208a40951f51b3adaf5a4439c3dae5f66c: expander dbd90c8e280df81001e3120f66860306e07d7bc9; evaluator 58d0a2cf513fcdbd7baacd7460ec3542ad1b0720.

## Actual song results

Part IDs are zero-based. Contradictions count added-cycle memberships, not distinct bad notes. Every affected track had zero contradictions before the final merge, and every final contradictory membership involved a role overwritten by that merge.

| ID | Entry | Revision | Affected parts | Role overwrite operations | Contradictory memberships | Candidate expansion validation |
|---:|---|---:|---|---:|---:|---|
| 1817932 | ERRA — gore of being | 9885745 | 2,3,4 | 18 | 15 | [PASS](https://github.com/mtch777/Guitar-Learning/actions/runs/41536992120/job/125591246615) |
| 993568 | ERRA — Eidolon | 1320385 | 5 | 4 | 2 | [PASS](https://github.com/mtch777/Guitar-Learning/actions/runs/41536992120/job/125591246703) |
| 1511882 | Currents — My Disguise | 4540687 | 0 | 3 | 2 | [PASS](https://github.com/mtch777/Guitar-Learning/actions/runs/41536992120/job/125591246659) |
| 6028811 | ERRA — spiral (of liminal infinity) | 8322146 | 2 | 10 | 8 | [PASS](https://github.com/mtch777/Guitar-Learning/actions/runs/41536992120/job/125591246651) |
| 4248474 | ERRA — lucid threshold AI | 5561199 | 0 | 14 | 8 | [PASS](https://github.com/mtch777/Guitar-Learning/actions/runs/41536992120/job/125591246217) |
| 3165226 | Currents — My Disguise (Official | 4189601 | 2 | 3 | 2 | [PASS](https://github.com/mtch777/Guitar-Learning/actions/runs/41536992120/job/125591246699) |

All eight affected tracks reproduced the original line42 assertion. Total: 52 role overwrite operations and 37 contradictory added-cycle memberships.

## Candidate, tested only in memory

```diff
- preceding=original[i-1] if i else None
+ preceding=phrases[i-1] if i else None
```

All six songs pass the existing pedal-expansion evaluator with this candidate and all original assertions active. This is not a full build_tiered_song.py + verify_tiered_song.py rerun; later-stage failures have not been ruled out.

A local authored 16-event reproducer yields overlapping bounds [0,11) and [5,16), four conflicting role overwrites, and the same line42 failure. The candidate yields [0,11) and [11,16) and passes. All 15 existing expansion tests pass on both original and candidate code. The missing regression is differently anchored neighboring phrases expanding toward each other across a gap; existing helper checks do not validate every added-cycle role.

## Storage

All six upload steps succeeded using the existing verifying uploader and reported verified size/SHA-256. [Draft Release](https://github.com/mtch777/Guitar-Learning/releases/tag/untagged-19855ee0b1383f7b601a): six diagnostic ZIP uploads totaling 235893 bytes according to logs; raw captures are CMS encrypted. The run artifacts API reports zero Actions artifacts. A separate post-run release-list lookup did not surface the new draft, so independent post-run asset-list comparison is not claimed.

## Next implementation gate

Add a permanent regression for the reproduced collision, retain the consistency assertions, guard merges against silent incompatible-role overwrites, apply the bounded boundary correction, and then run the full pipeline for only these six IDs. Broader corpus regression is still needed before claiming globally unchanged successful behavior or musical correctness.
