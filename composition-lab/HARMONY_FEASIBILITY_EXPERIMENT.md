# Feasible actions: separate conditional harmony experiment

**Mechanically valid output; failed the frozen musical-distance/refit gate.**
The original unmasked pilot remains failed. No generator default changed.

## Frozen change

Before the new candidate, freeze an exact 255-step feasibility mask, using the
same source voicing, tuning, previous fingering, span limit 4 and octave shifts
-5 through +5. Remove only actions that cannot fit; normalize remaining mass
once before the original common-uniform draw. Refuse zero mass; never reroll.
Keep the smoothing floor, priors, category order, initial/gap backoff, recurrence
and all original gates. The mask changes the probability distribution; sharing
a uniform does **not** preserve the selected step.

ProjectPlanner3000 reviewed START, fixed-state MIDPOINT and the new-pair plan.
This is mechanical permission, not a learned musical preference.

## Verification and acceptance

| Requirement | Evidence / result |
|---|---|
| Audit both priors at the same old fixed states | 540 states, 163 unique root/voicing states; 41,565 independent action checks |
| Check new candidate states too | All 658 decisions, 197 unique states; **50,235 action checks, zero disagreements or invalid witnesses** |
| Historical null stays exact | All 658 draws and complete original harmony including fingering |
| 100% target hiding | Same proposal/audit after replacing reference harmony with same-string open notes; proposal accepts only pitch-redacted skeleton |
| 0% literal identity | Original baseline GP copied byte-for-byte |
| Preserve non-harmony dimensions | Exact canonical facets; occurrence transaction changes only harmony pitch/fingering properties |
| No stale history | Actual exported predecessor material ID, pitch, fingering and contiguity reconcile: 618 active decisions, 557 copied attacks; 40 sampled decisions not exported |
| Valid GP and MIDI | Both 131-bar scores pass alphaTab expected pitch/timing/tuning verification; MIDI emitted |
| Equal render conditions | Both 271.0349 seconds, fixed gain .5; finite, nonzero, unclipped; no listening judgments |
| Broad experiment acceptance | **Failed:** three frozen guardrails regress, below |

| Frozen metric | Historical baseline | Masked candidate | Gate |
|---|---:|---:|---|
| Harmony-register TV, lower better | 0.785523 | 0.757972 | Pass |
| Melody-minus-harmony TV, lower better | 0.603601 | 0.661674 | **Fail** |
| Sampled targets below lowest open | 14/658 | 28/658 | **Fail** |
| Octave-refitted sampled attacks | 47/658 | 66/658 | **Fail** |

The same 107 generated eligible boundaries were measured; 8 lack active harmony.
Source comparison remains 1,311 known boundaries; 953 unknowns are excluded
explicitly. These are written-minimum/heuristic-role relationships, not functional
harmony or artist-fidelity ratings.

Backoffs among all 658 decisions: 1 initial, 55 post-gap, 177 missing exact keys;
425 supported. Among 618 exported active decisions: 1 initial, 52 post-gap,
161 missing keys, 404 supported. Reused/copied attacks are constrained material,
not 557 fresh model predictions.

## What changed versus the failed pilot

On its 540 fixed prefix states, historical prior infeasible mass was only
floating-point roundoff; conditional mean removed mass was 0.000785535.
At the new candidate's states, historical mean removed mass was 0.000008321
(four states nonzero), conditional 0.000797160. Neither is a whole-rollout failure
probability. This demonstrates why the old fixed-state audit cannot certify a
changed rollout.

The mask resolves this bounded action-validity failure. It does **not** make the
profile a successful harmony generator: register motion and melody/harmony
relationships still regress. Preserve the rejected GP and baseline for review;
do not tune tolerances or promote a default from this result.

Private plans, audits, scores, MIDI and WAVs:
`local-artifacts/source-transition-context-v1/actual-context-support-v1/`.
No private source or media is published.
