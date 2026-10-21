# Rhythm relationships replace onset data

Experimental higher operator over the existing written-clock representation. This is part of the same mathematical analysis/inverse chain, not a separate music generator.

## Contract

| Item | Exact behavior |
|---|---|
| Input | Only the preceding `shared-written-clock/1` representation |
| Removed | The entire beat onset channel: masks, parameters and anchors; old onset-dependent definition hashes are not retained |
| Retained | Ordered beat membership, duration parameters, source symbols, voice units and the preceding clock dependencies |
| Relationship | `next_onset = current_onset + duration`; voice origin comes from the shared written frame |
| Reverse | The same affine advance relation plus existing numeric factoring rebuilds the exact canonical preceding clock model |
| Unsupported parent | Refuse a nonchronological/noncanonical parent rather than silently repair it |
| Validation | Restore the parent, then run its complete inverse validation; a partial numeric view is not parent validation |

## Acceptance

- [x] No source path or source access above extraction; input and protected fields unchanged.
- [x] No onset stream, copied onset-dependent hashes or residual onset cache in the new beat representation.
- [x] Five source-free tests: exact parent; grace/rest/empty voice/overflow; whole-bar rest and pickup; cache/wrong-tier refusal; nonchronological parent refusal.
- [x] Feasibility diagnostic: all 98 source-derived models, all 318,888 beat onsets recovered after removing every onset channel/mask/parameter/anchor. This diagnostic alone is NOT the production inverse gate.
- [x] NEW frozen random v13: Limp Bizkit, Behind Blue Eyes (The Who Cover), song63892 revision8791578; seed8074848681717012820/queryb. Selection preceded analysis; previous corpus/captures excluded. All prior nine raw gates pass3,286note occurrences. With file reads denied, the new highest-only representation restores the entire clock model and the entire owned model;134raw frames/eight tempo addresses match. Source/operator hashes unchanged. No reroll.
- [x] Frozen all98 canonical-parent inverse run: all98 pass, every original case accounted exactly once across four fixed partitions. All onset fields removed; entire previous canonical clock model restored. Source/model/case-set and12operator hashes unchanged. Merged evidence retained.
- [x] Copied-module guarded worker integration and all98replays pass. Entire reconstructed facts equal the sealed independently source-checked baseline; direct raw EVENT oracle rerun for every capture. All25execution/source/model/baseline-fact/directory checks unchanged; all98unique cases accounted, no omissions.
- [ ] Planner assessment. Unavailable due collaborator usage error; no final approval claimed.

This removes redundant written-time observations. It does not interpret phrases, harmony, artist style, performed microtiming or emotional meaning. It does not establish full GP reconstruction or nonzero-lever musical quality. Duration changes can conflict with existing tie/voicing constraints; those conflicts must be solved or refused, not hidden by a separate recreation engine.


## Integrated worker checkpoint
Same existing runner/worker/corpus now accepts `--rhythm` above `--clock`; no separate recreation engine. Six rhythm tests and seven batch tests pass; full local suite734run733pass1optional skip. NEWv15 frozen before analysis: Nirvana Breed10779rev9174728,seed10706751401765792086/queryb.5,117note occurrences,121frames/four tempo addresses; all10raw checks and exact rhythm/clock/owned parent identities pass in copied-module guarded worker.
Final98guarded replay passed98/98. It compares WHOLE reconstructed owned facts against a sealed baseline that already passed independent field oracles; source hashes remain frozen. Direct raw EVENT checks are rerun. This uses exact transitive field equality and does NOT pretend to rerun all10oracles in that final replay. Every successful inverse read is restricted to the highest JSON, copied operators and Python runtime; bytecode-cache reads remain denied. No inferred source repair or guessed notes.

Final closure17:59UTC:98/98guarded PASS,420119note occurrences. Source deliveredf60e95395541b4f1d09f92bcfa6351f060b2b27d; CI39648497937SUCCESS verified. FinalPlannerassessment remainsPENDING.
