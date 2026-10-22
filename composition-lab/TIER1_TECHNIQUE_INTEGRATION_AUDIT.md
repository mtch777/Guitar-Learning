# Tier1 and retained technique integration â€” requirements audit

2026-10-22. Requested by the user; reviewed with ProjectPlanner3000.
This is a source/code audit and ownership plan, not completed implementation.
Corpus/context-factor work is paused. Accepted technique identification is retained.

## Why this gap exists

The rebuilt interface deliberately began with a small field contract so its
forward/backward relationships could be verified. We subsequently extended
harmonic analysis without completing the bridge to retained technique analysis.
That is unfinished integration, not a requirement of reversibility or evidence
that the earlier technique work disappeared. Narrow QA passes do not close it.

Current extraction chain:
`run_reversible_tier_qa.extract` â†’ `source_key_tier1.extract` â†’
`source_tie_tier1.extract`. The active musical core consumes that result.

Exact current schema4 ownership:

- Original non-rest occurrence IDs; part/bar/voice/beat/note addresses;
  base pitch or explicit unknown; rational onset/duration; grace occurrences have
  zero nominal duration but their source grace type is not owned.
- Coverage and timing/layout warnings; source-derived measure geometry/effective
  meter and normalized pickup witnesses; optional exact measure key-signature
  declarations. Original per-part meter/pickup presence is not fully owned here.
- Part fields: `instrumentId`, `tuning`, `capo` when present.
- Note fields: `string`, `fret`, `dead`, `tie` when present, including original
  value/type/presence. Resolved/unresolved ties and continuity are integrated in T2.

Everything else is outside this rebuilt contract unless expressly added. Exact
written duration does not recover its original note value, dots or tuplet spelling.

## Source-fact ownership gaps

| Category | Missing from rebuilt T1 | Existing work / correct owner |
|---|---|---|
| Beat/voice topology | Explicit rests, empty voices, rest placeholders, full grace/beat topology, source grace type/notated duration, duration/type/dots/tuplet and grouping declarations | Original occurrence addresses retain ordering. Retained topology/rhythm/clock modules and source extraction exist. T1 owns declarations and occurrences; T2 owns interpreted timing/continuity. Do not revive retired wrappers wholesale. |
| Note technique declarations | Bend curves; vibrato flags; `hp`; slide; harmonic/harmonicFret; ghost; staccato; accents; tremolo and other note effects | T1 owns exact note-scoped facts and source units, not inferred execution. |
| Beat technique declarations | Palm mute, tapping, let ring, brush/upstroke/pickstroke, fade, tremoloBar, vibrato, tremolo, harmonic and gradual-velocity fields | T1 owns each beat-scoped fact once, with beatâ†’note membership. Never duplicate a shared arm curve onto every note. |
| Dynamics | Explicit beat/note velocity markings and original unknown values | T1 owns markings; T2 owns inheritance/overrides and provenance. |
| Song clock/control flow | Tempo/automation declarations, repeat/endings, triplet-feel and exact per-part meter/pickup presence/type | T1 owns declarations; T2 owns verified clock/control-flow relationships. No assumed repeat traversal or unknown ramp interpolation. |
| Source structure | Track identity/settings beyond the whitelist, source markers/section text, relevant instrument/sound changes | T1 owns source facts; a supplied section label is not a discovered phrase boundary. |
| Unrecognized fields | No exhaustive rebuilt field-ownership ledger or supported extension channel | T0 still preserves captured JSON. Inventory every field/path; distinguish required score facts, provenance/admin fields and unknowns. No claim that every API metadata field belongs in musical analysis. |

## Every requested technique: facts â†’ identification â†’ musical relationships

All rows below remain disconnected from the rebuilt boundary unless marked integrated.

| Requirement | T1: source facts | T2: retained analysis to connect | Above T2: additional meaning / limits |
|---|---|---|---|
| Bends | Exact curve header/points, native positions/tones, point-vibrato flags and note ownership | Shared unit relations; normalized trajectory; initial/peak/final/excursion, arrival, slopes, held-neighbor context. `source_semantics.curve`, `mechanics`, `sustain_context`; GP `bend_analysis` | Gesture placement, repetition/variation and conditional song/artist use. Existing curve interpolation is not performed sound. |
| Vibrato | Distinct note/beat markers and any explicit parameters | Existing GP finger/arm effect distinctions; source flag inventory. Preserve unspecified speed/depth as unknown | Contextual use; do not invent a continuous waveform from a boolean. The user's requested pitch vibrato is not rapid repeated picking. |
| Open-string hammer-ons/pull-offs | Exact `hp` or GP origin/destination markers; source string/fret and continuity facts | Same-string directed transitions, open endpoints, eligibility and unresolved cases. Existing API `hopo` and GP `hopo_pairs` | Repeated gestures and connections to rhythm/melody. Fretted transitions remain detectable, but the user excluded them from current listening priorities. |
| Slides | Exact source type/value and originating occurrence | Existing `source_slides.resolve_slides` plus local timing gates; written targets/direction or explicit unresolved endpoint | Gesture relationships. Entry/exit markings with unspecified pitches stay unspecified. |
| Harmonics | Type/fret and source parameters | Separate base/written pitch from supported sounding-pitch interpretation | Unresolved type/execution remains unknown; base-pitch chord analysis is not complete sounding harmony. |
| Dead/ghost notes | Dead is already owned; ghost and other declarations are missing | Preserve unpitched continuity and dynamics provenance; never invent pitched dead notes or automatic ghost attenuation | Rhythmic/textural role requires contextual support, not a flagâ†’emotion rule. |
| Double stops | Separate-string occurrence identities, simultaneous timing and pitches | Existing `technique_analysis.classify_group`: exactly two notes on different strings; labels may overlap | Contextual accents/recurrence, not an assumed harmonic function. |
| Close-interval texture | Same facts; no fabricated source label | Existing classifier requires exactly two different-string notes one semitone apart | Preserve user's corrected half-step definition; whole-step examples are exclusions. |
| Power chords | Same facts | Existing classifier: lowest root and fifth only, octave duplication allowed | Rhythmic/harmonic role remains contextual. |
| Extended power chords | Same facts | Existing classifier requires root/fifth core plus one additional pitch class; root is the lowest note, so the color lies above it | Preserve this definition and its existing cases during integration; no extra triad or functional label is implied. |
| Palm mute / tapping / let ring | Exact beat/note declarations as supplied | Existing marker inventories and affected-note relationships | Technique combinations and conditional use. Let ring does not establish an otherwise unspecified release time. |
| Other articulation | Staccato, accents, picking, brush/fade and explicit parameters | Existing inventories/normalization; preserve unverified brush native units | Contextual density/placement, not a loudness or emotion estimate. |
| Approved pedals | Complete source occurrences, timing, rests, physical facts and declarations used by the detector | Connect the accepted `pedal_evidence` â†’ support-region â†’ `pedal_expansion` path unchanged; exact anchor/call/response IDs and continuation/merge evidence | Recurrence, variation and call/response measurements belong above the local identification layer. Identification remains closed; analysis/recreation is not declared complete. |

Pedal warning: `analyze_relationships.pedal_candidates` calls the older
`pedal_patterns.detect_bursts`; it is NOT the complete approved identification and
continuation path. Do not substitute that convenient field for the approved result.
Existing `pedal_dialogue` alone also does not validate the anchor or override later
call/response timing corrections.

## Actual example: current gap is visible in source data

Frozen Cliffs of Dover, Songsterr6701/rev9071983, has 3,842 non-rest occurrences.
The following are source-field presence counts, not distinct affected-note totals
or performed-technique judgments:

| Source declaration | Present | Rebuilt T1 |
|---|---:|---|
| bend | 41 notes | Missing |
| leftHandVibrato | 94 notes | Missing |
| hp | 53 notes | Missing |
| slide | 116 notes | Missing |
| harmonic / harmonicFret | 5 / 5 notes | Missing |
| ghost | 21 notes | Missing |
| dead / tie | 3 / 323 notes | Integrated |
| palmMute / letRing | 101 / 108 beats | Missing |
| pickStroke / velocity | 255 / 103 beats | Missing |

T0 retains all these values. Their absence from rebuilt T1 means T2 cannot legally
read them from T0 to compensate: that would violate isolated preceding-tier inputs.
This one-song inventory illustrates the gap; it is not exhaustive corpus coverage.

## Integration acceptance â€” not more technique research

1. Make an exhaustive source-path ownership ledger and explicit supported scope.
   Preserve absent/null/false/zero distinctions and original note/beat ownership.
2. Extend T1 facts/topology before exposing higher analysis. Preserve unknowns and
   provenance; no report dumps or parallel raw-note streams in higher tiers.
3. Adapt retained pure analysis to T1 inputs; no higher-tier raw-file reads.
   Keep accepted detectors unchanged, including the approved pedal path.
4. Differential-test occurrence IDs, measurements, positive/negative results,
   unresolved statuses and boundaries against retained outputs on fixed sources.
5. Apply all three gates: new frozen song; stripped-lower same-relationship inverse
   for every newly owned fact; source-backed musical distinctions and Planner review.
   Exact serialization alone is not technique execution or meaningful abstraction.

No new detector, corpus model, generation engine, UI or percentage lever is needed
to establish this missing connection. Higher tiers' eventual numbering remains a
design decision; source facts versus local relationships versus recurring patterns
must remain separate regardless of those numbers.

## Audit verification

- [x] Read actual schema4 extraction and the rebuilt interface.
- [x] Trace retained API/GP analysis and the approved pedal continuation path.
- [x] Count actual source field presence on one frozen capture without changing it.
- [x] Map every requested technique plus known structural ownership gaps.
- [x] Existing targeted suites: technique analysis13; source semantics16; pedal
  expansion15; slides7; dynamics5; local relationship details5 â€” **61 passed**.
  Commands: `.venv/Scripts/python.exe -m unittest discover -s composition-lab -p`
  followed respectively by `test_technique_analysis.py`, `test_source_semantics.py`,
  `test_pedal_expansion.py`, `test_source_slides.py`, `test_source_dynamics.py`,
  `test_source_relationship_details.py`.
- [x] Planner final document review and user report-out; meter/pickup/grace wording
  corrected as requested. The user subsequently authorized implementation;
  current work is tracked in TECHNIQUE_INTEGRATION_PROGRESS.md.

These tests confirm retained components still pass their existing checks. They do
not prove the missing rebuilt-tier integration, full GP fidelity or listening quality.
