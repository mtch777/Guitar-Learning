# Pedal criteria audit: acceptance is reopened

The current after-results are register hypotheses, not accepted musical pedal
identifications. The audit did not change pedal_register.py. Raw feedback and
score-specific diagnoses are private in local-artifacts/pedal-feedback-audit-v1.
The three provided feedback exports contain21judgments; later chat corrections
take precedence over conflicting older labels.

## Required distinction

A recurring low note or interval must establish an actual call/response pattern.
Returning to a lower register is not necessarily returning to that pedal. Chord
voices moving in lockstep do not establish an independent response. Successive
different held notes without responses do not become a pedal by being grouped
into a low register band. Continuation of a musical theme can link independently
established pedals; it cannot waive those pedals' qualifying evidence.

## What the live after-method actually checks

- Groups written, positive-duration note attacks at equal rational onset, across
  voices; tied destinations do not count as attacks.
- Tests ascending observed pitch ceilings except the highest pitch.
- An event containing any pitch at/below the ceiling is a call event; an entirely
  higher event is a response. Any unknown pitch makes its event unknown.
- Joins consecutive events of the same kind, without a maximum silence or phrase
  span. Requires at least two consecutive low/high/low cycles.
- Requires one selected call pitch to occur three times somewhere in the support,
  and three standalone call groups with at most two pitches, all below the ceiling.
- Rejects one narrow arpeggio family: at least six monophonic attacks, a fixed
  major/minor/diminished/augmented/sus2/sus4 pitch-class collection, identical note
  durations and onset gaps, and changing pitch at every adjacent attack.
- Picks the first passing ceiling. Does not score independent anchor identities.
- Assigns every selected note below the ceiling to call and every higher note to
  response, including simultaneous upper notes. Transposed dyad shapes seen at
  least three times as standalone low calls can extend membership.
- Retains final return bursts and following answers. Source scopes are not
  established musical phrase boundaries.

## Missing or incorrectly generalized acceptance gates

- Stable local anchor identity and actual return to it; not merely three
  occurrences of some pitch anywhere in a long selected scope.
- Independent timing of call and answer as qualifying evidence; coincident
  upper voices can currently receive response labels without establishing it.
- Relevant local recurrence, silence handling and phrase boundaries; unrelated
  material can supply the few high-only events needed to accept a long scope.
- Contrast in melodic/rhythmic function, beyond crossing a register threshold.
- Lowest valid anchor selection, rather than widening a band until it passes.
- Context-sensitive treatment of occasional lower answering accents.
- General chord/arpeggio discrimination; the narrow triad filter is insufficient.
- Separate measurement of notes/intervals/durations/repetition/rhythm/consistency
  from evidence establishing that the passage is a pedal in the first place.

These gaps require correction and source-based regressions; track-name
blacklists and manual edits to the reported examples would not resolve them.
