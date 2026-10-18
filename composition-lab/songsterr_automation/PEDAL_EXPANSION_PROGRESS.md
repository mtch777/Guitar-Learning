# Pedal continuation pass

User contract: preserve the current detector. Expand only existing supported
patterns using the exact established anchor. Favor later continuation; require
stronger independent repetition before the start. Combine connected patterns
without counting overlapping phrases twice. Never delete or shorten a seed.

## Checklist and acceptance

- [x] Pull main without overwriting local work; inspect detector, source-review
  builder, tests and workflows. Baseline commit bfce702.
- [x] Implement a separate, deterministic rational-time expansion pass. Detector
  file hash must remain unchanged; original analysis and input rows immutable.
- [x] Test forward, backward, both, merging, no-change and adversarial cases:
  simultaneous voices, changed anchors, arpeggios, silences, ties and boundaries.
- [x] Run the full private corpus. Every original seed must map to exactly one
  output containing its full time range and evidence; no overlapping outputs.
- [x] Investigate the reported continuation with source occurrences. No
  song-specific rules or manual highlight overrides.
- [x] Build all four requested diff categories, with original boundaries visible,
  full-range source notes, unchanged playback and precise marking/export.
- [x] Verify every UI note against source; inspect real browser controls,
  playback and cursor. No synthetic judgments entered as human feedback.
- [x] Run Python/JS tests and build; commit/push verified public code/docs only;
  check CI and existing Pages deployment where triggered.

Only scripted/evidence validation can be completed autonomously. Listening
acceptance of newly connected passages remains a human review, not an inferred
musical verdict. Private score-specific diagnoses stay in local-artifacts.

## Verified local results

- Detector hash unchanged: 4ddb8ebaaf574c5177720812a00b8488c81094eecdce0e972fe4547e110126c2.
- Expansion hash: ce49842e7dc444a5be47136fe8a37ad87f5af64dce30f4149079c3b69f7917fa.
- Evaluation: 310 source tracks, 2,239 original chains in 2,018 original
  disjoint groups; 1,902 outputs. Every original chain maps to exactly one
  containing output. All original members, roles and bounds retained.
- Exclusive diffs: 20 BEFORE, 71 AFTER, 15 BOTH, 72 COMBINED; 400 added
  complete exchanges. No duplicate cycle time triples. No input seed tracks
  have the corpus temporal-ineligibility flag. No new detections or removals.
- Root-cause test: an established terminal return can seed new exchanges without
  independently meeting the detector's two-exchange acceptance threshold again.
  The reported ending now continues through two additional exact source exchanges.
- Initial adversarial QA caught extension into a regular chord walk; reusing the
  existing uniform-arpeggio predicate on local windows blocks it. Final-burst
  and tied-tail tests protect complete endings without inventing extra attacks.
- Full suite: 279 Python tests run, 278 pass, one optional skip; 24 JS tests
  pass; Vite production build and git diff --check pass.
- Release source audit: 178 cases / 426 parts / 19,785 exact source-note
  displays / 57 hash-identical GP copies. 42 unavailable automatic previews
  are explicitly identified, with full notes and GP retained.
- Browser QA: all four category controls populate correct counts and note rolls;
  original/expanded bounds render. Source audio loaded (3.693424 seconds in
  the reported case), playback advanced and cursor moved. Final source-note
  click seeks and inspects; marked occurrence and typed comment survive reload.
- QA feedback is isolated; final human-mode comment and marks verified empty.
  Review screenshot saved privately; local port5196 final release remains running.
- Prior detector outputs, port5195 review and all source GP files preserved.

Remote publication and workflow results are recorded after push. New phrase
connections remain listening candidates; no human musical judgments invented.

## Remote publication

- Implementation 33642217b22d71d702dd215e4f04850d60a467d9 pushed to origin/main
  after pull --rebase confirmed no concurrent changes.
- Composition Lab CI: success, https://github.com/mtch777/Guitar-Learning/actions/runs/39164175767
- Existing Pages workflow: success, https://github.com/mtch777/Guitar-Learning/actions/runs/39164175822
- Live public site HTTP200; prior port5195 catalogue HTTP200/906 cases and new
  port5196 release HTTP200/178 cases. Commercial-source material stays local.
- Final release source audit passed. The source-only implementation, test and
  progress checklist are published; listening acceptance remains open.

## Human acceptance — complete

2026-10-18: user: “nice work. approved. done with pedals”. This closes the pedal
identification and expansion milestone. Preserve the accepted implementation and
regressions; do not request another generic pedal review. This approval does not
close the remaining artist-profile, transfer, lever or composition milestones.
