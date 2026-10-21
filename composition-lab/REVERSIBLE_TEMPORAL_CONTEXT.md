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
