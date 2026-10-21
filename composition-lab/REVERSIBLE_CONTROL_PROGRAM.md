# Repeat-region operator: contract and integration

Optional owned version2 integration is under frozen98 regression. No playback visits or seconds.

## Evidence and grammar

Read-only98captures:495parts;397exactTrue repeatStart declarations and397positive integer repeat ends, all explicitly paired;0unmatched/nested observed.355alternateEnding declarations:182inside explicit regions,173outside.10anacrusisTrue declarations. Outside endings are NOT invalid; their musical attachment is unknown.

Supported relation: per-source-part ordered written-measure list, exactTrue starts and positive integral numeric repeat values. At a measure process its start BEFORE its end (start-of-bar vs end-of-bar). Pair ends with the most recent open start. Same-measure and nested cases require synthetic tests. No implicit first-bar start. Unmatched/invalid/null/nonboolean controls remain explicit observations plus unresolved reasons.

A supported pair replaces its two source fields with ONEregion:source part, start reference, inclusive measure span, literal source repeat count and numeric source type. SAME equation in both directions:end_index-start_index-measure_span+1=0. Do not call count the number of performed passes. Source startTrue is restored through its format binding; source end/count comes from the region. Endpoint copies must not survive underneath.

Ending labels remain typed source declarations at their source measure. Only geometric containment in explicit regions is derived; musical attachment is UNKNOWN until independently established, including all173outside cases. Pickup flag is a source flag; no pickup duration inferred here.

## Acceptance

- [x] Prior-facts-only encode/decode; no source access above extraction.
- [x] Region parameters use shared relationship/factoring operators, no bespoke note recreation.
- [x] Strict part/measure ownership, endpoint uniqueness, span bounds, no arbitrary fields/caches or retained endpoint copies.
- [x] Exact missing/False/null/zero/invalid controls and all ending declarations retained in declared scope.
- [x] Recompute region set/reasons from restored observations; compare complete model.
- [x] Independent direct-source eligible-region recall, unresolved reasons and declaration equality; not merely codec self-agreement.
- [x] Same-measure/nested/unmatched/conflict/corruption/unknown shapes and source-free reversal tests.
- [x] ALL98 plus currentrandomv8, failures retained; no grammar simplification to cherry-pick cases.
- [ ] Planner start/mid/end; source-only delivery+CI. Integration into owned pipeline is a later gate after its freeze closes.

Markers/double-barline preservation and automations-container presence remain fidelity work. They are deliberately not mixed into this first control-relationship operator. Current495parts all have automations{tempo:array}; absent/null/empty container distinctions remain an explicit future requirement.


## Isolated prototype acceptance checkpoint
- Eight source-free tests pass, including strict contradictory field/inventory refusal and independent-oracle corruption tests (missing declaration/region, changed count, wrong reason). Producer decode is patched only in oracle tests to prove the raw comparison is genuinely independent.
- Independent direct-source audit:99 actual uppers,397 explicit regions and355 ending declarations, exact recognized source declarations/owners/missingness/reasons. All173 outside endings retained; attachment unknown everywhere.
- NEW frozen randomv9:Nirvana song39 revision8551137,8tracks,seed12160368037485629014/querym; original98+prior8 excluded before capture. Zero repeat regions/ending declarations was KEPT. Pure highest-only control reverse succeeds with file opens forbidden; direct raw oracle passes; input/code hashes unchanged. This is negative-case evidence, not new positive-repeat evidence.
- Planner independently approved8tests,99artifact audit and actualv9 reversal/hash checks. Private artifacts:local-artifacts/reversible-control-prototype-v1/ and reversible-tier-qa-v9/control-v1/.
- Full local suite706run,705pass,1optional skip. No integrated owned-worker/control/visits/seconds/GP claim. Production owned19-file freeze remains untouched.


## Owned integration acceptance (local; final review pending)
- [x] owned-song-stages/2 owns control observations at extraction, lifts them only after the music/temporal stages, reverses control before the earlier operators. Version1 remains supported/default.
- [x] Part and ordered measure references must exactly match the song registry; wrong ownership/extent/schema/stage/cache cases refused. Each transform preserves every protected slot.
- [x] Existing isolated worker dispatches /1 and /2; control source endpoint observations do not enter its highest-only input. Same operators and9independent source gates, no separate music recreation path.
- [x] Source-free positive integrated one-measure repeat test;9owned tests and5batch tests pass; full714run713pass1optional skip; Node7pass.
- [x] Freshv10 frozen before analysis passes6408notes/all9raw gates. Zero repeats preserved as a negative case, not swapped out.
- [x] ALL 98 frozen production cases pass: 420,119 note occurrences, 397 regions, 355 ending declarations. Entire music models unchanged; all sources/baselines/directories and 21 declared execution files unchanged. End-integrity recorded.
- [ ] Planner final integration assessment; collaborator currently unavailable due usage error. Earlier isolated approval does not automatically approve the integration.
- [ ] Source-only commit/push and verified CI.
