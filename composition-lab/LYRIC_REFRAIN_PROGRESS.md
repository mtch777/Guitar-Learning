# Optional lyric-refrain evidence: implementation and acceptance

## Checklist
- [x] Add an opt-in evidence layer without modifying existing musical hypotheses or labels.
- [x] Preserve missing-lyrics/no-option fallback exactly.
- [x] Retain alternatives including verse, chorus, intro, outro and other refrain functions.
- [x] Do not copy raw lyrics or text hashes into outputs.
- [x] Validate source-feature identity before attaching evidence.
- [x] Reject overlapping pair occurrences as independent recurrence.
- [x] Require usable timing for both lines and every supporting occurrence, with caller-declared lyric timing error and recording alignment error allowances.
- [x] Require caller-selected maximum line-pair gap; preserve actual gaps.
- [x] Preserve unknown confidence: a supplied distribution is a global uncalibrated reference prior, not occurrence-specific certainty.
- [x] Run real fitting-held-out tests and retain reduced coverage.
- [ ] Reliable whole-song verse/chorus classifier: NOT achieved or claimed.

## API
`analyze_functions(..., lyric_evidence=None)` remains unchanged when omitted.
`lyric_refrain_evidence(events, bar_times, source_fingerprint=feature_fingerprint(features), maximum_pair_gap_seconds=..., maximum_alignment_error=..., candidate_distribution=...)` builds optional evidence.
Events need start_seconds, text, timestamp_error_seconds. Bar times need bar, start_seconds, end_seconds, verified, max_error_seconds. Verification and error allowances are caller declarations; the module cannot certify recording alignment. Unknown timing produces no positive evidence. The caller must not invent certified bounds.

Repeated adjacent transcript lines are a candidate, not proof of contiguous singing or function. Pair gap is caller controlled, not a fixed musical form rule. No absence-to-verse inference. No forced labels, no propagation of the same functional role across recurrences.

## Independent review and corrections
Review found overlapping matches, unverified second/matching onsets, missing lyric timestamp uncertainty, wrong-song attachment risk, and omitted verse alternative. All corrected and regression-tested. Timing basis now distinguishes unverified input. Distribution explicitly marked global prior.

## Evidence and limitations
Earlier exploratory lyric model used line-to-next-line spans and checked only target-bar alignment. It yielded9/10chorus bars across36qualified bars on Secret Sun/Cloud Cascade, but overstated usable coverage.
Strict integrated onset-only check with both pair occurrences verified: Secret Sun0/6chorus anchors, Cloud Cascade2/4, zero false positives among26nonchorus reference bars. Combined2true anchors,0false,8chorus bars without anchor. This is20%bar-anchor recall, NOT a successful full classifier. Declared test allowances: up to1second automatic clock diagnostic lag,0.1second assumed lyric onset error,10second maximum pair gap. These are test parameters, not certified timing errors or musical requirements. Different allowance choices must be audited, not tuned against labels.

References were held out from lyric-model fitting but inspected during earlier musical-model development; no pristine blind claim. No licensed lyrics, recordings or reference annotations are included here. More reliable synchronization is needed before expecting useful broad coverage. No full-corpus run or UI changes.

Tests:18new lyric tests,12section-function regressions,19repeat regressions passed. Source-only optional API remains experimental; publication does not establish classifier accuracy.


## Core-envelope increment
Added a separate opt-in `lyric_refrain_core_evidence` API. It finds maximal verified repeated lyric subruns, and represents only their first-to-last onset envelopes with endpoint uncertainty removed. It does not guess the end of the final sung line. Full bars must fit after expanding their own timing uncertainty. Intervening instrumental gaps and possible functional changes remain explicit: `continuous_singing_verified=False`; all alternative roles and unknown labels remain.

Controlled five-song test, SAME original timing checks with timed references remapped and uncertainty containment: onset-only evidence2/30chorus bars; core envelopes16/30. No disagreements among77labeled nonchorus bars, but9additional positive bars have no reference label. Do not call this100%general precision. These are inspected development songs, not a pristine blind benchmark.

Separate modeled-landmark interpolation experiment reaches23/34chorus bars with1known nonchorus disagreement (bridge), and20unlabeled positive bars. This uses a different timing gate and denominator, is not locally certified alignment, and is NOT implemented as automatic verification in this API.

Positive verse evidence from changed lyrics over recurring instrumental material was also tested and did not discriminate reliably. Absence of a refrain remains unknown, never verse.

Tests after core increment:27lyric tests,12function regressions,19repeat regressions. Core envelopes are useful refrain candidates, not complete musical sections or a finished verse/chorus classifier.

