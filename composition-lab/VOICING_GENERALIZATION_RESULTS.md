# Frozen tests of generic voicing/register logic

2026-10-24. ProjectPlanner3000 start/middle/end reviewed. No AI-selected notes,
offsets or donors. Satisfaction remains a development/regression song.

## Original fresh tests: retained, not overwritten

Policy/code451files and two seeds frozen BEFORE selection. Existing sampler chose
from first100 search results for a seeded alphabet letter, excluding prior captures
and prior failed selections. This is NOT uniform sampling of the Songsterr catalog.
No replacement song or changed policy after viewing either result.

| Frozen case | Coverage / exact reversal | Musical-change evidence |
|---|---|---|
| Tame Impala - The Less I Know The Better,411169 | 3758 occurrences,43993 source facts/containers; independent source and actual stripped-worker exact0 PASS; approved technique parity PASS | 2552 units,0 eligible. Positive nonzero/QA3 musical evidence NOT EXERCISED. |
| American Football - Never Meant,25202 | FAIL_RETAINED:16 unsupported source paths,4 arpeggio objects. T2 inverse NOT RUN; no false pass or replacement. | NOT RUN. |

Case1:35 otherwise-plain target units are blocked by unresolved overlap execution.
Other candidates are excluded for single-note, instrument, unknown pitch/string,
slide, grace, tie or ringing dependencies. Counts overlap; not additive percentages.
Case2: rolled-attack markings carry direction/duration/shift in four beats. The
registry lacked an owner for these source fields. No timing/sound inference made.

Original artifacts: private local-artifacts/voicing-generalization-v1. freeze.json,
capture-results.json, both selections/captures, QA results and independent Planner
end review remain intact. Original case1 result's PASS_BOUNDED_SOURCE_WITNESSES
means a consistent refusal/denominator check, NOT positive musical validation.
Original runner completed both cases before the subsequent development edits.

## General implementation changes

- Musical conditioning separated from literal target notation: part/instrument,
  PC multiplicities, duration, meter/metrical position, nominal overlap PC context;
  full context adds neighboring part PC vectors, local omits those two neighbors.
- Fixed strings stay locked. Whole simultaneous pitch/string/fret shape requires
  direct source witness with same tuning/capo/instrument, before sampling.
- No maximum-played-fret anatomy heuristic; no declared-fret-bound playability claim.
- Independent checker rebuilds complete unit/context/accepted/rejected donor sets.
  Omitted valid choices cannot pass by vacuity. Source clock/membership authenticated.
- Same pitch=anchor+interval and pitch=tuning+capo+fret relationships remain both ways.
- All original legacy policies retained for regression, not fresh policy shopping.

## Development repair/replay (NOT a fresh benchmark)

After both frozen tests: add explicit typed arpeggio declaration ownership and
preserve its direction/duration/shift using the existing shared scalar relations.
Reject arpeggio/brush-stroke-dependent units in this plain simultaneous-voicing
experiment. No approved detector edits, guessed performed timing or arpeggio engine.
Replay the SAME captures under separately hashed development code; keep original
failure history. Never relabel these songs untouched.

| Development replay | Exact stripped reconstruction | Musical change |
|---|---|---|
| The Less I Know The Better | 43993 typed facts/containers,3758 notes:PASS; complete source and unchanged approved-detector parity PASS | 0 eligible units; no proposals. |
| Never Meant | 66483 typed facts/containers,6037 notes:PASS; all4 arpeggio objects preserved exactly, complete source and detector parity PASS | 2 eligible units,0 supported donors; all62fixed control draws unchanged/refused. |

Both separate audited workers use the SAME relationship code, with lower/source
and derived-cache payloads removed. Python read/network/process audit is not an
OS sandbox or memory/disk quota. All capture files and code hashes unchanged
during each replay. Private evidence:local-artifacts/voicing-generalization-development-v2.
The original frozen case2 failure is not replaced by this development replay.
Total replay boundary:9795note occurrences /110476typed facts and containers.
No changed GP/audio is manufactured when no supported nonzero result exists.

## Acceptance

No finished voicing/register creative lever or Tier2 pass. Source-backed geometry
is not a human execution certificate. Exact equality and refusal correctness are
necessary but do not prove artistic choice. Missing gesture/overlap/harmonic
understanding remains explicit; do not lower evidence requirements to force audio.

Tests before original freeze:1022 Python tests,1021PASS/1optional skip;43JS PASS.
After generic source repair:1028 Python tests,1027PASS/1optional skip. Fourteen
voicing tests include a positive authored nonzero example and actual isolated
worker; seven independent policy tests reject omissions/corruptions; six arpeggio
tests verify types/presence/shape, independent source joins and isolated inverse.

## Additional authored semantic-lock defect and repair

Planner constructed a regression with an explicit tied continuation starting at
the exact end of the selected chord. Original code could change the origin pitch
while leaving the continuation fret/tie flag unchanged: source field locks passed,
but the accepted tie became unresolved. This is NOT attributed to either fresh song.

The policy now consumes the existing accepted written-tie graph, identifies
incident selected members, and filters donor choices changing locked endpoint
pitches BEFORE sampling. Untied members can still change when the tied member
stays fixed. Independent oracle authenticates complete links/unresolved states
and the endpoint pins from raw source clocks/lanes/positions using the accepted
written-tie predicate. All policies also recompute and compare the complete tie
graph after realization, refusing any changed resolved/unresolved relationship.
Corrupting the candidate filter cannot bypass this final guard.

This does not claim complete dependency closure for every slide/HOPO/gesture.
Those relationships and unresolved expressive overlap context remain OPEN.
Final development-v3 replays/results are recorded separately below.

Final development-v3:444source files frozen before replay, both cases PASS
complete stripped exact0/source parity and independent policy checks. Same
9795occurrences/110476typed facts exact. Independent accepted tie graphs contain
316resolved links (Tame) and427 (American Football), no unresolved declarations.
Eligibility/draw outcomes remain0/2eligible,0supported alternatives,0changes.
No positive musical/nonzero claim. Final local regressions:1033Python tests,
1032PASS/1optional skip;43JS tests PASS. Code/captures/audit inputs frozen and
unchanged during each execution; snapshots from older versions stay preserved.

Delivery:implementation b03e9d3 pushed to main; GitHub Actions40105066469 SUCCESS.
Vite production build PASS. Planner finalv3 independent review accepts bounded
source-ownership/tie-safety repairs only. Positive fresh musical variation remains
OPEN. Next:edit-incident technique dependencies versus context-only uncertainty,
with contrast tests before further fresh sampling; no threshold tuning for demos.
