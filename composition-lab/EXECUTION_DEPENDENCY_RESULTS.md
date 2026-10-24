# Incident dependencies: implementation and frozen tests

2026-10-24. ProjectPlanner3000 start/middle/end reviewed. Current scope is
voicing/register safety and written context, not a complete creative lever.

## What changed

- Tier2 now exposes a recomputable execution-dependency view: source occurrence
  references, HP/slide relationships and statuses, roll/ringing declarations,
  conservative endpoint pins and explicit unknowns. No extra note-pitch stream.
- Target execution uncertainty and same-part uncertain overlap still refuse edits.
  Unchanged OTHER parts' uncertainty is recorded as timed nominal context, not
  automatically treated as a physical dependency on the selected notes.
- Donor conditioning retains uncertainty descriptors; unknown/nonintegral pitches
  are UNKNOWN in the twelve-class representation. Raw fractions remain exact.
- Whole-shape source geometry, string/PC/time/other source locks and tie guards
  remain. Incident HP/slide pins filter proposals before sampling; global stable
  signatures catch changed unresolved reasons/new relationships afterward.
- SAME anchor/interval and tuning/capo/fret equations realize changes. Derived
  dependency caches are stripped before inverse; tampered views fail validation.
- Independent oracle uses retained track analysis and source-fact roots, not the
  dependency producer. Full policy oracle checks all units/donors/refusals.
- Existing technique/pedal detectors and JSON/GP conversion are unchanged.

## Development findings (inspected sources, NOT fresh proof)

| Existing song | Eligible units before / after | New alternatives |
|---|---:|---:|
| The Less I Know The Better | 0 /35 | 0 |
| Never Meant | 2 /340 | 0 |

Initial independent checks caught differently ordered uncertainty evidence lists.
Canonical occurrence-reference ordering fixes the representation; source data and
donor conditioning are unchanged. Failed reports retained. A staggered three-part
regression covers it. Fractional context pitches now remain UNKNOWN rather than
masquerading as twelve-class categories; raw0.5 source facts reconstruct exactly.

## Frozen new-song trial

Policy `incident_dependencies`,458 code/client files and two seeds frozen BEFORE
sampling. Seeds18247268428019499102 /3455124642796440520. Prior captures and failed
selections excluded. Existing seeded-letter first100 search-pool sampler; NOT a
uniform catalog sample. Both songs retained; no policy changes or replacements.

| Song | Raw note occurrences | Typed facts/containers | Eligible units | Alternative choices |
|---|---:|---:|---:|---:|
| Queen/David Bowie - Under Pressure,17042 | 5831 | 52028 | 57 | 0 |
| Led Zeppelin - Over The Hills And Far Away,11714 | 9713 | 82140 | 1131 | 0 |

QA1 PASS: both complete source checks and unchanged accepted-detector parity.
QA2 PASS: both actual isolated stripped-zero workers recover all134168typed facts
and15544occurrences exactly. Source/derived caches and expected answers absent
from worker input. Python read/network/process audit is not an OS sandbox or
resource quota.
QA3 bounded dependency/context abstraction PASS: independent source relationship,
all-unit/donor denominator, unknown-status and execution graph checks. This is
NOT positive fresh creative-change validation. Both controls0/50/100 and separate
100/0,0/100 were tested with retained fixed draws; no changed draw occurred.

Under Pressure:413dependency edges/506pins;327resolved ties,0unresolved.
Over The Hills:383edges/659pins;906resolved ties,1unresolved preserved. No invented
repair to source ambiguity. Original sources/code unchanged during both runs.

There is no changed GP/audio demonstration because neither source supports a
different realization under this policy. Rendering an unchanged or handpicked
replacement would not demonstrate this lever.

## Verification and acceptance

Local full suite:1052tests,1051PASS/1optional skip.43JS tests PASS; Vite build PASS.
Eight incident contrasts include actual stripped-worker nonzero on AUTHORED data,
same-part refusal, unknown/fractional pitch, evidence order and cache corruption.
Seven dependency tests and four independent-oracle tests cover HP/slide endpoints,
grace/timing exclusions, roll/ringing unknowns and omitted/fabricated graph data.

Private evidence:local-artifacts/execution-dependency-fresh-v1 (freeze, selections,
captures, complete QA and Planner independent end review); development failures
and rechecks remain in execution-dependency-development-v1. No source scores,
captures, private annotations, media or licensed weights published.

Closed: this bounded incident-versus-context distinction and its source/inverse
tests. OPEN: full creative voicing/register acceptance, human execution/listening,
musical function/artist context and supported fresh nonzero changes. No Tier2 pass.
Further source-family scoping is read-only; do not weaken the frozen policy to
force a listening example.

## Planner's follow-up diagnosis

Independent458file/source freeze check PASS. Family diagnostics reject the simple
hypothesis that pitch normalization alone unlocks this trial: Under Pressure has
no distinct alternatives; Over The Hills has alternatives but none meets the
current fixed-string whole-shape evidence rule. See VOICING_FINGERING_DESIGN.md
for the proposed joint voicing/fingering relationship and separate-lock contract.
No physical control was silently released and no trial policy was changed.
