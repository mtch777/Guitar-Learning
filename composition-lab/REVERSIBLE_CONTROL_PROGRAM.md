# Repeat-region operator: isolated contract

Not imported into the frozen owned-corpus pipeline. No playback visits or seconds.

## Evidence and grammar

Read-only98captures:495parts;397exactTrue repeatStart declarations and397positive integer repeat ends, all explicitly paired;0unmatched/nested observed.355alternateEnding declarations:182inside explicit regions,173outside.10anacrusisTrue declarations. Outside endings are NOT invalid; their musical attachment is unknown.

Supported relation: per-source-part ordered written-measure list, exactTrue starts and positive integral numeric repeat values. At a measure process its start BEFORE its end (start-of-bar vs end-of-bar). Pair ends with the most recent open start. Same-measure and nested cases require synthetic tests. No implicit first-bar start. Unmatched/invalid/null/nonboolean controls remain explicit observations plus unresolved reasons.

A supported pair replaces its two source fields with ONEregion:source part, start reference, inclusive measure span, literal source repeat count and numeric source type. SAME equation in both directions:end_index-start_index-measure_span+1=0. Do not call count the number of performed passes. Source startTrue is restored through its format binding; source end/count comes from the region. Endpoint copies must not survive underneath.

Ending labels remain typed source declarations at their source measure. Only geometric containment in explicit regions is derived; musical attachment is UNKNOWN until independently established, including all173outside cases. Pickup flag is a source flag; no pickup duration inferred here.

## Acceptance

- [ ] Prior-facts-only encode/decode; no source access above extraction.
- [ ] Region parameters use shared relationship/factoring operators, no bespoke note recreation.
- [ ] Strict part/measure ownership, endpoint uniqueness, span bounds, no arbitrary fields/caches or retained endpoint copies.
- [ ] Exact missing/False/null/zero/invalid controls and all ending declarations retained in declared scope.
- [ ] Recompute region set/reasons from restored observations; compare complete model.
- [ ] Independent direct-source eligible-region recall, unresolved reasons and declaration equality; not merely codec self-agreement.
- [ ] Same-measure/nested/unmatched/conflict/corruption/unknown shapes and source-free reversal tests.
- [ ] ALL98 plus currentrandomv8, failures retained; no grammar simplification to cherry-pick cases.
- [ ] Planner start/mid/end; source-only delivery+CI. Integration into owned pipeline is a later gate after its freeze closes.

Markers/double-barline preservation and automations-container presence remain fidelity work. They are deliberately not mixed into this first control-relationship operator. Current495parts all have automations{tempo:array}; absent/null/empty container distinctions remain an explicit future requirement.


## Isolated prototype acceptance checkpoint
- Eight source-free tests pass, including strict contradictory field/inventory refusal and independent-oracle corruption tests (missing declaration/region, changed count, wrong reason). Producer decode is patched only in oracle tests to prove the raw comparison is genuinely independent.
- Independent direct-source audit:99 actual uppers,397 explicit regions and355 ending declarations, exact recognized source declarations/owners/missingness/reasons. All173 outside endings retained; attachment unknown everywhere.
- NEW frozen randomv9:Nirvana song39 revision8551137,8tracks,seed12160368037485629014/querym; original98+prior8 excluded before capture. Zero repeat regions/ending declarations was KEPT. Pure highest-only control reverse succeeds with file opens forbidden; direct raw oracle passes; input/code hashes unchanged. This is negative-case evidence, not new positive-repeat evidence.
- Planner independently approved8tests,99artifact audit and actualv9 reversal/hash checks. Private artifacts:local-artifacts/reversible-control-prototype-v1/ and reversible-tier-qa-v9/control-v1/.
- Full local suite706run,705pass,1optional skip. No integrated owned-worker/control/visits/seconds/GP claim. Production owned19-file freeze remains untouched.
