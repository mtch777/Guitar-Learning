# One bounded relationship contract: interval changes between parts

**Record and candidate validator only. No GP consumer, new generator, completed
lever, learned-support result or musical acceptance.**

Feature: within-bar, main-voice, written-minimum signed melody-minus-harmony
interval **changes**, measured at identical jointly active rational clocks.
Use the existing shared digest, score validation and dimension checks.

| Requirement | Exact behavior |
|---|---|
| 0% | Same signed change on every existing edge, literally; not a lock of absolute interval or MIDI |
| Harmony fixed | Only selected-bar melody MIDI/string/fret may change; this can preserve melody motion while shifting its register |
| Rest gaps | No connecting edge is invented; disconnected components can have independent offsets where no edge constrains them |
| 100% | Proposal view contains role, tuning, meter, duration/cardinality topology only; no original played pitches, intervals, deltas, evidence digest or support/provenance payload |
| Unlocked coincidence | Same resulting relationship is allowed; difference is never forced |
| Other dimensions | Harmony, bass, rhythm, form, instrumentation, performance, tempo/metadata and other bars remain protected |
| Literal melody pitch lock | At 0%, candidate must also preserve that literal dimension; at 100%, refuse the target-determined conflict |
| Function/octave controls | Explicit refusal; no unsupported claim of compatibility |
| Intermediate percentages | Explicit refusal; no invented perceptual calibration |
| No eligible transition | Known `not_applicable`, not missing data |
| Invalid/unknown pitch or clock | `unknown`; no relationship-lock claim |

With harmony fixed, a constant melody shift may preserve 0% changes. Parallel
movement of both parts still violates the harmony lock. A single changed melody
motion fails the 0% relationship lock even when the rest of the score is valid.

The protected original stays in the validator. It is never a proposal payload.
Independent training aggregates/support metadata are a separate evidence input;
the proposal view does not echo arbitrary support fields. Tuning is permitted
instrument context, not a copy of original played notes.

Five unit tests cover those distinctions, target perturbation, supported refusal
paths, rest gaps, other-bar edits and tempo/metadata. Self-QA found that existing
dimension facets omit tempo; an additional full protected-object comparison now
permits only the three selected melody-note fields, preserving all other data.

Archived-cell exercises use explicit **engineering fixture support**, not fitted
model evidence. Their outcomes do not authorize generation or establish artist
style. An executable recreation/transfer consumer and real source-derived versus
learned-generation studies remain separate work.
