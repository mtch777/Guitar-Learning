# Voicing/register: software decisions, frozen-song tests

2026-10-24. User correction: plan generic logic, then use songs to TEST it.
ProjectPlanner3000 reviews start/middle/end. Satisfaction is development/regression
only. Earlier pooled/declared-geometry proof remains historical, not suitability.

## Musical contract

Question: which other observed spacing/register realization of the SAME note
pitch-class multiplicities has evidence in this part and local musical context,
and can be realized without changing separately locked dimensions?

- Sole musical input: preceding complete T1. Upper coordinate owners stay unchanged.
- Relationships: pitch class + rank within repeated class; bass register anchor;
  directed member intervals; tuning + capo + fret; timed overlap and neighboring
  PC context; occurrence-linked notation/execution witnesses.
- SAME equations forward/backward. No AI chooses a note, musical offset or donor.
- All other source values lock, including strings. No implied permission to move
  strings or add tapping. Source observations are not anatomical certifications.
- Missing contextual support yields an explicit refusal, never automatic pooling.
- Candidate physical evidence must match the actual proposed fixed-string shape,
  not merely the donor's pitches or a track's maximum played fret.
- No key, emotional purpose, phrase role or artist suitability inferred from this
  bounded matching model. Those are missing musical context, not validated claims.

## Acceptance checklist (freeze before fresh selection)

- [x] Planner START contract challenge reconciled before implementation.
- [x] Add opt-in `source_witnessed_fixed_strings`; retain legacy policies unchanged.
- [x] Before sampling: filter candidate choices by musical-context full/local policy
  and direct donor witness of proposed per-member pitches/strings/frets. Retain
  rejection reasons, IDs and all denominators. No empirical range as anatomy.
- Musical conditioning whitelist: part/instrument, member PC multiplicities,
  duration, source meter and metrical offset, nominal timed overlap PC context.
  Full adds preceding/following part PC vectors; local omits those two neighbors.
  Prefer full when it has a supported alternative, otherwise declared local.
  Literal target notation is locked, but not a donor-conditioning feature.
- Independent checker enumerates expected units, eligibility, musical context,
  complete joint witnesses and accepted/rejected donor links from source facts.
  Producer output omission must fail; empty choices cannot pass by vacuity.
- [x] Positive, negative, repeated-PC, missing-witness, lock and 0/50/100 tests.
- [x] Freeze code/config/test hashes, sampling rule and two case slots BEFORE
  selection. Existing random search sampler; exclude all prior selections and
  existing corpus. Biased search pool, not uniform catalog sampling. No rerolls.
- [x] QA1: run both cases unchanged; independent raw source relationship checks,
  complete source coverage and technique parity; keep capture/analysis failures.
- [x] QA2: ALWAYS attempt stripped exact-zero isolated worker, even no alternatives.
  Nonzero worker and independent locked-fact comparison only if supported edit.
- [x] QA3: source-linked pitch/register/interval/witness checks; negative/ambiguous
  cases. Distinguish mechanically checked relationships from musical suitability.
- [x] Every case records all-unit eligibility/context/physical support, first
  eligible alternative by source order, seeds9427..9446 at0/50/100 plus separate
  100/0 and0/100; retain every refusal/coincidence. Never optimize change rate.
- [ ] If actual fresh nonzero change: GP/audio verification before audible delivery.
  If none: nonzero musical acceptance stays OPEN; don't alter rules on test songs.
- [x] Planner MID/END, regressions and persistent results.
- [x] Commit/push/CI: implementation b03e9d3, Actions40105066469 SUCCESS.

Outcomes in VOICING_GENERALIZATION_RESULTS.md. Completed attempts above are not
all passing gates: fresh case2 failed source registration; positive musical
variation was not exercised in either case. Both same-case development replays
now pass source/inverse after generic arpeggio ownership repair. No new fresh
accuracy claim and no Tier2 promotion.

## Dependencies and completion

Changing voicing/register releases selected octave/spacing coordinates; source
pitch classes, rhythm, techniques, accompaniment and strings remain exact. If all
observed alternatives require other strings, report a physical-lock conflict.
Any future string/position freedom needs its own explicit control contract.
Ordinary instrument equations are general constraints, not handpicked musical
rules. Learned observations supply musical choices; source/context evidence
limits claims. Passing math and source portability does not complete Tier2.

An authored counterexample exposed outgoing tie dependencies beyond the unit's
half-open nominal overlap. Existing accepted tie relations now pin incident
endpoint pitches before sampling and are recomputed after every intervention;
raw flag equality alone is insufficient. Positive regression permits untied
members to change while the tied member remains fixed. Full slide/HOPO/gesture
dependency closure remains OPEN, as does positive fresh musical choice evidence.
