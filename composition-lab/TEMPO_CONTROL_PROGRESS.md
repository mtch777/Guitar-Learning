# Component-conditioned passage speed: bounded execution

## Scope approved after the census

Planner approved an **opt-in PARTIAL experiment**: an explicitly named rhythmic
component supplies the observed speed choices; the whole band follows that speed
over the existing written tempo interval. This does not assert agreement from
the other parts, transition suitability, whole-interval musical fit or an artist
preference. The stricter incoming-tempo and full-ensemble strata remain visible
with their original empty results.

Private decision: `local-artifacts/tempo-census-v1/planner-tempo-gate-decision.json`.
The earlier census and its empty/unknown rows are preserved.

## Acceptance checklist

- [x] Pure-data temporal/census entry points. No file access in policy analysis.
- [x] Every field of the seven saved census outputs remains exactly unchanged
  through their capture wrappers after the refactor. The independent file oracle
  remains outside the data-only entry point.
- [x] Source observations alone supply candidate BPMs. Each original global
  event supplies one sampling vote. Target and witness closures remain disjoint.
- [x] Use the existing 0/50/100 release sampler. 100% permits an observed
  coincidence; it does not force a different speed.
- [x] Use root's sole reciprocal quarter-seconds owner to change every alias of
  the selected global event; lock all other typed written source facts.
- [x] Keep partial evidence, missing component support, incoming/outgoing risk
  and fixed written lifetime in every decision.
- [x] Refuse unsupported full native maps rather than ignoring extra tempo
  fields, unsafe units/positions, ramps or contradictory declarations.
- [x] Synthetic actual isolated workers prove zero, half, changed and no-choice
  behavior. A stale donor edit is reanalyzed; it cannot reuse previous support.
- [x] Run every actual B.Y.O.B. component and draw; keep all refusals and choose
  the first actual changed 100% draw in original source order.
- [ ] Independent source/all-options review and exact native performed-tempo,
  expression and source-position-aligned audio checks on that first result.
- [ ] Root freezes one genuinely new random capture before the next QA run.
- [ ] Retain new-song exact source reconstruction and all choices/no-choices;
  independently audit complete evidence and native zero/changed results.
- [ ] End review with Planner. No full tempo-lever or human-fit claim without
  the corresponding evidence.

## Implementation and verification

`local_step_tempos.py` reads only the preceding packet reconstructed by the same
inverse. `run_step_tempo_qa.py` records every event/part/voice and every seed at
0/50/100. The parent creates its expected source by updating the original JSON
paths; the actual source-denied worker receives only the stripped representation,
controls and frozen code.

Development tests cover duplicate aliases, all-remaining-fact locks, donor
mutation, absent extra metadata, beat-local unknown tempo, ramp/contradictory
maps, typed controls, false forced-difference assumptions, original no-choice
retention and complete actual worker output. A beat-local adversarial case found
and fixed a duplicate `position_q` argument in the census constructor; the seven
actual samples contain no beat-local tempo declarations and keep the same
observations and opportunities.

Commands:

- `python -m unittest test_local_step_tempos test_run_step_tempo_qa test_tempo_source_census test_reversible_temporal -v`
- `python tempo_source_census.py local-artifacts/tempo-census-v1/protocol-v2.json local-artifacts/tempo-census-v1/census-data-only-adapter --opportunities`

The combined command ran **28 tests: all passed**. Planner's later exact fact-row
order check and its reordered-row regression passed in the 11 policy/runner
tests. The runner then gained the separate native reviewer's independent raw
alias/source-scope checker; its three actual-worker tests passed again.

## First actual experiment

`python run_step_tempo_qa.py local-artifacts/parallel-levers-v1/frozen-v1/recovery-same-seed/capture local-artifacts/step-tempo-control-v1/development-first`

- **92,617 source facts:** exact reconstruction from the stripped packet.
- **128 components, 12,288 draws:** complete inventory and all 32 seeds at each
  strength. Two components had choices; 63 had no rhythmic attacks, 62 had no
  independent contrasting BPMs and one had unresolved execution.
- **0%:** zero releases and zero changes across 4,096 draws.
- **50%:** 2,048 releases; 14 changed outputs across 4,096 draws.
- **100%:** 4,096 releases; 30 changed outputs across 4,096 draws. Empty choice
  sets and observed coincidences remain unchanged.
- Actual isolated zero, no-choice, 50% and 100% workers passed against all typed
  source facts. The selected seed's 50% trial retained the original, as permitted
  by the probability control.
- First actual change, without replacement: **B.Y.O.B., bar 95, guitar part 3 /
  voice 0, seed 0: 153 to 162 BPM**. All seven source aliases change together;
  written interval **q376–392** and every other written source fact stay fixed.
- The independent raw source checker passed the actual worker result. A separate
  private script, importing no policy/owner/census/sampler, checked all 128 option
  rows and 12,288 draws against the preserved preregistration output and raw
  source aliases. Both receipts are retained beside the development result.

This is previously seen development material, **not QA #1 on a new song**.
Its native performed-time/expression/audio review subsequently passed. The new
frozen Take Me Out test preserved all 74,381 facts and refused all 54 components
because its gradual/linear tempo behavior is outside the proved step scope.
The native step audit's failure is retained; separate source/zero equality is
not ramp-playback fidelity. See `STEP_TEMPO_PROGRESS.md` for the independently
reviewed final receipts. No listening or full-tempo acceptance is claimed.

No source capture, failed result or baseline was replaced. All private source
documents, exact outputs and native media remain under ignored `local-artifacts`.
