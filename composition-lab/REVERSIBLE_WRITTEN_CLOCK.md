# Next connection: shared written-bar clock

Isolated prototype under validation. Not yet integrated into the guarded worker; no playback-seconds claim. Existing frozen owned-engine files remain unchanged during their batch.

## Goal
Replace redundant absolute voice onset anchors with relationships to a shared written-measure clock. Connect meter, beat occurrences and tempo source addresses using exact rationals. This consumes existing structural/temporal/control facts; it is not another unrelated flag codec.

## Source evidence
- All495 captured parts have an explicit initial meter; none is empty. Existing shared layout has no meter conflicts in98captures.
- Ten anacrusisTrue flags all belong to ONEcapture552415. All10first bars have no independent occupied-duration evidence after whole-measure-rest sentinels are excluded. Explicit first meter5/8; accepted normalized clock uses span5/2 and does not shorten it. This is NOT positive real pickup-duration validation.
- Future conflicting/missing declarations cannot borrow the historical implicit4/4 default.

## Relationships and ownership
- Shared written ordinal comes from ordered source measure memberships across parts, never parsed IDs.
- Preserve every sparse meter declaration and provenance. Agreeing declarations constrain the same frame; contradictions stay explicit, with no sorted-first winner.
- nominal_span_q=4*numerator/denominator; next_bar_start=current_start+selected_span.
- Observed short pickup occupancy may use exact contributor voice/beat references, exclusion of grace0 and whole-bar-rest sentinels, and a declared maximum of independent occupied extents. Require0<occupied<nominal. Do not call this uniquely proven intended duration.
- Derive occupancy from retained duration parameters where possible. Do not retain a duplicate numeric gauge merely to avoid evaluating the shared equations.
- Preserve source-normalized anchors where clock constraints are unresolved; no source repair or guessed shortening. Flag-present/no-independent-occupancy remains distinct from supported observed pickup evidence.
- Automation address links its source part and zero-based source measure index to the shared written frame; event_q=frame_start+4*source_position. Unknown/out-of-range/missing addresses are different from a valid literal BPM observation.
- Beat-local tempo links an existing beat occurrence. Do not merge away explicit redundant declarations; stateful repeat execution may need them later.
- Written time, performed visits and seconds stay separate.

## Gates before integration
- [x] Source-free poly-part short pickup with differing voice fills and whole-rest sentinels; zero-duration grace does not inflate extent.
- [x] Missing/conflicting meter and source overflows are explicit; overflow does not move later nominal frames or group different source bars.
- [x] SAME constraint declarations validate forward anchors and restore removed anchors; no source access or guessed note/timing stream.
- [x] No redundant occupancy cache; demonstrate concrete dependency if a generic partial numeric view is needed.
- [x] Remove only owned onset anchors; all other fields/protected slots unchanged. Recompute constraints after inverse.
- [ ] Independent raw frame/address/anchor comparison; all earlier gates; NEWfrozenrandom capture; failures retained.
- [ ] Planner start/mid/end, source-only commit/push/CI. No musical meter-control, repeated-performance or fullGP claim.


## Prototype evidence — 2026-10-21
- reversible_written_clock.py accepts only the previous owned-song-stages/2 control-stage representation. Its output stores that representation with voice onset anchors removed; no additional source payload, copied onset list, occupancy gauge or performed timeline.
- Existing numeric channel projection solves retained duration/written-duration parameters without requiring removed onset origins. A derived cross-part frame walks source measure memberships; explicit meter consensus and SAME affine advance/origin equations validate forward and restore reverse.
- timing_view derives frame/tempo links on demand. Beat-local tempo references existing beat identity; automation source part/measure/position map to a written frame. Missing, unsupported and out-of-range addresses remain distinct; no missing-position default. Literal BPM conversion is separate from address validity.
-10unit tests pass. Whole-parent validation after restoring anchors rejects malformed unselected channels, duplicate retained origins and arbitrary cache fields. Independent raw oracle is corruption-tested against a fabricated frame result.
- Actual1047444:127frames/2addresses match raw capture; whole previous representation equal with file reads denied.
- NEWfrozenrandomv11: Queens of the Stone Age 3's & 7's23343rev9111270,6tracks,seed11554982870898547229/queryq. All previous9raw gates pass7376note occurrences. Clock removes702origins and restores the entire previous representation;117frames/6addresses independently match raw capture; source/shared-code/clock hashes unchanged. Zero repeat regions retained, no positive-repeat claim.
- Private written-clock-v1/qa.json explicitly marks isolated_clock_worker PENDING. In-process file-read denial is not the stronger copied-module guarded-worker gate.
- ALL98 clock regression queued AFTER the prerequisite control batch completes. Freeze source/model/code hashes before the first clock analysis; retain every failure. Do not edit declared clock or shared execution files once it begins.
- Planner notified at start/middle; final integration review unavailable due collaborator usage error. No approval claimed.


Boundary: this lift removes voice origins only. Within-voice relative onset parameters still exist in the lower numeric representation. A later cumulative-rhythm relationship can eliminate that further redundancy; this prototype is not complete rhythmic abstraction, phrase analysis or artist-level analysis.


Self-QA correction: non-boolean/non-null pickup flags (including complex unsupported flags) now REFUSE the clock lift rather than silently treating them as false. Control observations remain preserved. Priorv11 code snapshot retained privately before changing execution code; no overwritten evidence.11clock tests pass after this correction.
Freshv12 selected before analysis under revised clock: Alice in Chains Man In The Box355rev9688679,seed12419867621476503713/querym.5265notes,1045origins removed/restored,130raw frames and104tempo addresses match. All underlying9raw gates and whole previous representation pass; source/shared/clock code unchanged. Isolated clock worker remainsPENDING. This is not performed playback or listening evidence.


Full pure-operator regression CLOSED: all 98 captures pass; 59,021 origins restored, 11,137 written frames and 687 tempo addresses independently match source. The complete preceding model matches for every capture; source, baseline, operator files and case directory set unchanged. Guarded-worker integration has12clock tests and6batch tests passing; NEWv14 source261rev9416539,seed15354381497671256283/querye, passes3,450notes/all10raw checks and exact clock-parent/owned-model identities. Full local suite732run731pass1optional skip (includes experimental rhythm tests). Source-read policy correctly blocks attempted bytecode-cache reads; successful reads are limited to copied modules, highest JSON and Python runtime. No guard was loosened to make a test pass.
Guarded all98 replay is in progress across four fixed index-modulo4 partitions. The earlier serial replay is retained with its interruption record; no case or gate was dropped. Final integration assessment remains pending.


Guarded replay CLOSED: all98captures pass all10direct raw gates and whole owned-fact equality; successful reads limited to highest JSON/copied operators/runtime. Four deterministic partitions merged: complete original case set, no duplicates/omissions; original sources, baseline models and24declared execution files unchanged. Earlier serial partial run retained; no gate/case removed. Source delivery follows. Planner assessment remains pending; no fullGP/performed/style claim.
