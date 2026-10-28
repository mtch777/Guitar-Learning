# Temporal texture continuity: proposed bounded START contract

2026-10-28. **PARKED** pending the common harmonic-evidence interface in
`HARMONIC_EVIDENCE_INTERFACE_START.md`. Design only. No inference implementation
or creative policy is accepted here.
Current source checkpoint inspected: `dc8f71e`. Frame experiment closure and
its fresh-source gates remain separate. Preserve all literal outer-note locks.

## Missing musical relationship

The current system owns source occurrences, written ties, chord-degree/register
coordinates and physical string paths. `note_motion_evidence` requires an
unambiguous source sequence; it does not associate notes inside successive
chords. A notation voice can contain a chord. A string identifies physical
execution, not a musical line. A highest note is a literal boundary, not an
identified melody. No existing owner should be renamed to imply otherwise.

The smallest useful experiment is an explicit **minimum written pitch-motion
correspondence hypothesis** between complete consecutive coattacks. It is a
testable association model, not a claim about the composer's actual voices.
Its purpose is to distinguish invariant temporal motion from uncertainty across
competing assignments, instead of demanding copied physical-string triplets.

## Fixed experimental scope

- Input: complete preceding-tier source facts and existing authoritative musical
  groups, with original IDs, rational clocks/durations and source provenance.
- Enumerate all consecutive group pairs within each part and notation-voice
  scope. The container limits this experiment's population; it does not certify
  that members belong to one musical line. Do not skip refused intervening groups.
- Initial admission requires equal cardinality, positive known timing, complete
  known integer written pitches and no ambiguous source grouping. Retain every
  refused pair and reason. No births/deaths, rest bridging or voice merging in
  this experiment. Unknown execution/grace/timing remains explicit refusal.
- Preserve accepted written tie constraints as hard links where both endpoints
  are represented. A tie is an exact source relationship, not picked-attack or
  acoustic-duration evidence. Unresolved or external incident links refuse an
  unsupported scope; never silently remove a tied occurrence.
- For admitted groups A and B, retain **every** feasible bijection attaining
  `sum(abs(pitch_B[j] - pitch_A[i]))` minimum, subject to hard links. Use exact
  arithmetic. No string, top/bass, crossing, chord-root, learned-style or cadence
  bonus. No birth/death penalties or test-selected weights.
- Resource limits fail explicitly; never truncate hypotheses to get a winner.
  A deterministic serialization witness is not a preferred musical assignment.

This is an intentionally limited model. Crossed or registrally displaced true
voices can lose under minimum motion. Equal optimal costs need not mean equal
musical plausibility; a unique optimum need not be the actual voice assignment.

## Owned outputs and SAME relationships

The existing degree/family owner remains the sole pitch authority. Do not copy
absolute pitches, note streams or source payloads into a second temporal owner.

The checked relation stores/references original group and occurrence IDs,
scope, hard-link provenance, model version, complete optimal correspondence
structure, objective value, ambiguity and support/refusal status. Motion is
`next_pitch = prior_pitch + signed_interval`; chord-degree coordinates continue
to use the existing root/degree/octave equation. Intervals are recomputed from
the authoritative pitches and are not an independent conflicting pitch stream.

The SAME pure relation function must run during forward analysis and after
stripped inverse reconstruction, rejecting stale assignments, omitted optima,
fabricated edges and changed objective/support. Reverse reconstruction still
uses the existing authoritative source owners. Do not describe this as a new
pitch-ownership replacement or invertibility of inferred musical truth.

This becomes useful through joint queries over all compatible correspondence
paths: measured chromatic motion and conditional chord-degree membership along
an associated strand, with universal versus assignment-dependent outcomes.
Existing chord alternatives must remain jointly compatible; no Cartesian
mixture of mutually exclusive hypotheses. Do not add a second harmonic solver.

## Acceptance checklist

- [ ] START challenge agrees on scope/model limitations before implementation.
- [ ] Independent exhaustive permutation oracle verifies all optima, hard links,
  costs, complete occurrence coverage and ambiguity on small authored cases.
- [ ] Contrasts: parallel triads; repeated/unison notes; equally optimal
  assignments; accepted tie anchoring; changed physical strings with identical
  musical observations; chordal notation voice; unequal cardinality; intervening
  rest/grace/unknown; and crossed authored lines that the model cannot identify.
- [ ] Global transposition preserves correspondence possibilities and intervals.
  Reordering serialized notes preserves source-ID-linked results. Changing a
  source string alone cannot create a musical preference.
- [ ] Every stored assignment/interval/cost/support corruption fails through the
  SAME reconstruction-time check. Actual source-denied worker reconstructs full
  T1 exactly at zero and recomputes the relation without original files/caches.
- [ ] Freeze a complete denominator on existing development material before
  measuring outcomes: raw pairs, admission/refusals, cardinalities, ties,
  unique/ambiguous optimum counts and path-dependent versus invariant queries.
- [ ] MID review before a preregistered fresh-source portability gate. Keep
  failures and zero-coverage cases; no reroll until a desired example appears.
- [ ] END compares raw source membership/time/ties and every claimed strand
  interval against an independent oracle. Mathematical model agreement is not
  actual voice-identity accuracy. Without independent voice annotations, report
  that accuracy as unmeasured rather than call uniqueness validation.

## What this can and cannot establish

Without human taste, software can verify exact source facts, model completeness,
joint consistency, invariances, uncertainty, stale refusal and full inverse.
Independent authored/annotated voice material can later measure whether this
model agrees with actual line assignments; it must stay outside inference input.

This contract does not authorize a voicing edit, relax a protected outer note,
identify melody/bass/inner roles, establish artist fit or pass an audible lever.
If the model yields no useful invariant continuity on the fixed sample, retain
that outcome and close this bounded experiment rather than extend penalties,
categories or sampling until it looks successful. Creative permissions need a
separate tested contract; source chords and motion costs alone do not grant them.
