# Next operator contract: source temporal context

PLANNING ONLY until the frozen98-case regression finishes. Do not modify the frozen engine. This closes missing musical timing/form, not artist interpretation.

## Source ownership

| Observation | Required owner / representation | Preserve |
|---|---|---|
| Sparse meter declarations | Source part + measure occurrence | Absent/inherited vs explicit signature; agreeing cross-track declarations remain individually identified |
| Pickup flag | Source part; occupied first-bar span grounded in contents | Flag presence/value, nominal vs occupied span; unresolved empty/inconsistent pickup evidence |
| Repeat starts/ends/counts, alternate endings | Source measure occurrences + interpreted control-flow relations | Original instructions, absent flags and explicit values; visits alone cannot invert notation uniquely |
| Markers/double barlines | Source measure boundary | Source labels/fields; no inferred phrase/mode/function presented as source |
| Tempo automations | Source part + automation ordinal, linked measure | measure/position/bpm/type, visible/linear/text field states; agreeing duplicate declarations remain distinct |
| Beat-local tempo objects | Source beat occurrence, independently of track automation | All49 observed bpm/type objects; preserve agreeing duplicates and conflicts, do not silently fold away source presence |
| Global interpreted clock | Song-level merged evidence | Explicit conflicts/unknowns; never manufacture initial120BPM |

## Shared relationships

- tempo_event_q = measure_start_q +4*source_position_whole.
- quarter_BPM = source_BPM*4/source_beat_unit, ONLY under a verified source-unit contract. Current98cohort only proves type4; new types require explicit supported/unknown status.
- nominal_measure_span_q =4*numerator/denominator; pickup occupied span remains distinct.
- seconds_delta =60*quarter_span/quarter_BPM for supported step-tempo intervals. Keep rational values internally.
- Source field bindings, anchors, presence and instruction identities are required witnesses, not inferred musical meaning. SAME equations recover transformed values; no source/cache fallback.

## Three clocks

1. Written q: source bar/beat positions, including exact rational durations.
2. Playback q: repeat-expanded visit identity/order. Never overwrite written occurrence IDs or count a repeated visit as another source note.
3. Seconds: stateful tempo execution over playback visits under an explicitly selected renderer policy. Unsupported ramps/conflicts/missing initial tempo remain unknown.

A static written-q tempo lookup is NOT sufficient after a repeat jump. Process explicit tempo instructions in visit order; preserve their presence even when their written value appears redundant.

## Observed contract evidence

Private read-only98caseaudit:638tempoentries,ALLtype4;525linearfieldsabsent,113explicitFalse,0true ramps. All98haveexplicitinitialmeter and initialtempoatq0. Acceptedlayout/timeline reports0warnings. This does not prove every future source shape is covered.

Private primary-library experiment:installedalphaTab1.8.4, synthetic3bars4/4.120BPMbar1, repeatbars2..3 twice,90BPMbar3:

| Bar2 declaration | Visits | Exact step-tempo duration | Observed renderer duration |
|---|---|---|---|
| None | 1,2,3,2,3 | 12s | 11.998s |
| Explicit120BPM | 1,2,3,2,3 | 34/3s | 11.332s |

On the secondbar2 visit, the inherited state is90; the explicit120instruction in the control then resets it. Millisecond rounding differs from exact arithmetic. Evidence applies to this installed renderer, not generic Songsterr/GP-app behavior or listening quality. Preserve both probe scripts/results in the frozenbatchroot.

## Acceptance gates

- [ ] Synthetic meter changes, pickups, empty voices, whole-measure rests and duplicate agreeing/conflicting track declarations.
- [ ] Step-tempo changes, missing initial tempo, unfamiliar units and linearTrue all have explicit supported/unknown/refused status; no silent flattening/defaults.
- [ ] Repeats, endings, source visits and the paired redundant-tempo instruction experiment; exact source instructions reconstruct, not guessed from visits.
- [ ] Strip source temporal payloads; same parameter/equation declarations restore all claimed source fields, with source identities and presence intact.
- [ ] Independently compare all original source declarations and each supported derived clock. Do not compare exact rationals to renderer-rounded milliseconds as identical representations.
- [ ] Keep every existing mathematical/physical/annotation/tie/voicing regression passing. No detector changes or generation work.
- [ ] Frozen existing corpus plus a NEWpreselectedrandomcapture through unchangedlogic; failures retained. Planner start/mid/end review; source-onlydelivery+CI.


## Follow-up source-shape evidence (read-only, after v2)
The98captures additionally contain49beat.tempo objects, each withbpm/type fields. These MUST enter temporal ownership alongside638track tempo automations; current reversible annotation slice inventories them as unsupported. Accepted historical timeline logic reads both sources, but its merged output alone is not a lossless owner.
Other still-unsupported complex observations:442note.tremolo and368beat.tremolo two-element arrays (observed examples1/16),132brushStroke objects (direction/duration/shift),529beat.text objects. Those require their own typed meaning/relationships; do not relabel tremolo picking as vibrato or claim raw array preservation equals interpreted execution. Counts are observations, not proof of a universal schema.


## Isolated prototype checkpoint (not integrated)
New reversible_temporal.py/test_reversible_temporal.py are NOT imported by the frozen pipeline. Only explicit meter and tempo declarations enter this bounded slice. Typed pure observations â†’ normalized shared parameters â†’ the same observations; no repeats, pickup interpretation, merged precedence or seconds yet.
- Normalized coordinates:nominal_span_q,quarter_bpm,position_q. Original source numeric types/presence/owner identities are witnesses; original transformed numeric values are removed. Denominator/unit witnesses keep the equations invertible.
- Only source tempo type4 is currently verified/supported. Other types remain literal observations with unsupported-conversion status, not invented unit interpretation. Nonpositive meter/BPM values remain unnormalized. linearTrue reports unresolved ramp execution. Playback status is always not_implemented.
- Unsupported complex data accepts descriptor inventory only; nested/raw-score payload injection is refused. Bindings cannot carry arbitrary caches.
- ALL98 factâ†’parameterâ†’fact checks pass:1769meter+49beat-tempo+638automation declarations. This is prototype equality, separate from independent source audit and isolated integrated worker gates.
- Ten source-free tests cover fractional meter spans, numeric types, absence/false/null, unknown units, invalid values, ramp status, agreeing/conflicting/redundant declarations, both source owners, corruption, and inverse parameter edits with file reads prohibited.
- Planner identified unsupported-inventory cache injection and unverified tempo-unit claims; both corrected before approval. Planner independently approved10tests and99raw declaration audits (2474declarations). Production source oracle check_reversible_temporal.py imports decode only; it rejects omitted declarations and type changes. No completed temporal/playback tier claim.


Prototype limits include container presence: absent/empty/null automations containers are not yet individually owned. Exact claims cover declared record fields and unsupported descriptors, not whole raw source objects or byte spelling. No producer aliases may masquerade as supported normalized coordinates, nor eligible source coordinates bypass normalization; corruption regressions enforce both directions.

## Agreed integration contract (after frozen v3 closure)
One typed source-reading envelope; no source reads above extraction. Fixed schema/version and explicit owned slots; no arbitrary extension blob. Each lift consumes/replaces its owned slot and hash-protects untouched slots. Temporal observations are carried until the temporal lift REPLACES them with parameters. Reverse uses the same equations. Validate owner-reference closure against actual part/measure/beat identities without parsing IDs. Do not retain both raw observations and their normalized copy. Highest-only isolated reverse must pass all existing source gates plus the temporal oracle; deletion/tampering/cross-song references must fail. Meter declarations remain distinct from topology timing until shared clock constraints are integrated; changing meter is NOT yet a supported musical lever.
