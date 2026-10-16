# Current goal: performance techniques and guitar patterns

Started 2026-10-16. Status: active; specification and preflight in progress. This extends, rather than replaces, the verified bend baseline. Authoritative branch: origin/main. Private scores, annotations, rendered source excerpts and checkpoints remain outside Git.

## Contract

Analysis and musical decisions use repeatable scripts, not AI-filled labels. Observations, inferred patterns and listening judgments remain separate. Analyze corpus/song/section/phrase/event levels where evidence permits; denominators, annotation coverage and uncertainty are mandatory. No missing label becomes a negative training example by default.

0% = literal lock of the selected data. 100% = unlocked from direct reference values for that feature, not forced difference. Methods and constraints are separate from freedom. Performance and arrangement are separate. Techniques affect sound differently: a HOPO changes the articulation between discrete notes; it is not a continuous bend. New intermediate notes, changed pitches/durations, voice allocation or fingering require explicit declared edit permissions and conflict checks. Start by annotating eligible existing note pairs before inserting notes. Keep fretted observations and sounding-pitch goals distinct.

## Feature definitions

| Family | Initial definition | Status / caveat |
|---|---|---|
| Fretted hammer-ons | Directed same-string lower-to-higher fret transitions, destination fretted; distinguish explicit HOPO marking from inferred eligibility | High-neck location is a contextual descriptor, not a hardcoded fret cutoff |
| Fretted pull-offs | Directed same-string higher-to-lower fret transitions, both fretted | Proposed interpretation of “up-the-neck”; user clarification pending |
| Hammer-ons from open | Same-string fret 0 to a positive fret | Separate occurrence/transition rates |
| Pull-offs to open | Same-string positive fret to 0 | Separate occurrence/transition rates |
| Vibrato | Oscillating pitch on a sustain; distinguish finger and arm notation | Preserve source type; encoded width/rate may be absent |
| Tremolo | Picking repetition and/or arm pitch movement | Scope pending user clarification; do not conflate with vibrato or volume tremolo |
| Pedal-note patterns | Recurring mid/low anchor interleaved with contrasting notes, with recurring temporal organization | Detect recurring anchors/patterns, not just most frequent pitch; include lower accents, register changes and cross-phrase/section recurrence |
| Close-interval texture | Exactly two notes on distinct strings sounding simultaneously, absolute pitch separation exactly 1 or 2 semitones | “Inharmonic” is user's category name; measurable observation is a close dyad, not acoustic inharmonicity. Distinguish co-attack from incidental sustain overlap |
| Power chords | At least two simultaneous notes; lowest pitch defines root; pitch classes are exactly root and perfect fifth, both present; octave doublings allowed | Root+octave alone is excluded; no third/extra pitch class |
| Extended power chords | Power-chord core plus one distinct color pitch class, neither root nor fifth, above the lowest root | Track color occurrences/doublings separately; this exact-class interpretation is explicit and can be revised |
| Double stops | Exactly two simultaneous notes on distinct strings, any interval | Proposed overlapping category: may also qualify as power/close dyad; user clarification pending |

## Execution steps and acceptance criteria

- [ ] **1. Finalize schema and definitions.** Resolve the three scoped questions; version all definitions. Positive/negative fixtures for every family, including ties, grace events, polyphony, alternate tuning and ambiguous markers. Defaults remain labeled until confirmed.
- [x] **2a. Initial private-source inventory.** Inspect Time, Cloud Cascade and Sweet Child for source technique encodings; retain aggregate counts only publicly.
- [ ] **2b. Complete extraction/notation coverage audit.** Read note properties, note tags, beat properties, beat tags, staff effects and linked transitions; preserve exact rational timing, occurrences, fret/string/tuning. Every detected effect is mapped or explicitly unsupported. Audit parser/independent-import agreement. This is necessary before interpreting absence.
- [x] **3. Implement directed HOPO relationship analysis.** Match explicit origins/destinations in same track/voice/string using timing and source links; classify upward/downward and open/fretted pairs; report unmatched/ambiguous markers. Tests ensure no cross-string, cross-track or arbitrary skipped-note links. Measures report attacks/transitions separately from tied segments. Evidence below; higher-neck naming remains provisional.
- [ ] **4. Implement vibrato and tremolo analysis.** Separate finger vibrato, arm effects, tremolo picking and any volume effect; preserve available speed/width/rate/subdivision and report unknowns. Do not infer a performed waveform from a generic marker. Validate synthetic examples plus available annotated sources; absence of corpus examples does not count as validated detection.
- [ ] **5. Implement simultaneous-note vocabulary.** Exact rational sounding groups with string identity; classify dyads, power and extended power chords using definitions above. Tests cover inversions, octaves, extra thirds, held overlaps, cross-voice groups and duplicate unisons. Labels may overlap; report exclusions and co-attack versus overlap.
- [ ] **6. Implement recurring pedal-pattern analysis.** Identify anchor/contrast alternation, relative register, rhythm signatures, repetitions and transformations within/across sections. Include counterexamples: isolated repeated pitch, chord root frequency, unrelated open strings. Threshold sensitivity and evidence links required; no automatic emotional/function claims.
- [ ] **7. Produce unified reference reports.** For each family: counts/rates, song/track/section coverage, distributions, conditional relationships and inspectable occurrences. Phrase/corpus reports only where validated boundaries/multiple relevant songs exist. New analyzer results must reconcile with original occurrence totals and preserve unknowns.
- [ ] **8. Extend exact-lock edit contracts.** Separate toggles for HOPO articulation, vibrato, tremolo picking, pedal pattern and dyad/chord construction. Declare permitted fields and downstream sounding consequences. Zero = literal identity; 100 = proposal invariant to perturbing hidden original feature annotations. Reject incompatible requests; no whole-score serialization that erases unsupported effects.
- [ ] **9. Build isolated performance experiments.** First existing eligible fretted HOPO pairs, then open-string HOPO, then vibrato/tremolo. Keep other dimensions locked; use authored diagnostic notes when no real example exists. Independently import GP; verify audible articulation/oscillation/repetition. Sine previews that cannot distinguish picking/HOPO timbre are insufficient. Preserve all bend baselines.
- [ ] **10. Build pattern/arrangement experiments.** Pedal patterns and dyad/power-chord voicings need explicitly unlocked pitch/rhythm/voicing dimensions; do not masquerade as articulation-only edits. Compare generated methods with controlled differences and complete edit manifests. Physical playability is independently checked and limitations reported.
- [ ] **11. Validate transfer and review.** Cross-song/section tests with leakage checks; corpus licensing separate; held-out exact metrics and source-copy checks. No claim of artist generality from a single track. Human listening gates assess musical function; original/no-technique controls stay out of user review unless requested. Preserve them privately for diagnostics.
- [ ] **12. Deliver and persist.** Tested code/aggregate findings committed/pushed to origin/main; private GP/audio and versioned review bundles retained locally; GitHub CI verified; Pages verified if public website changes. Record actual evidence and unresolved limitations per step. Goal remains active until achievable execution is complete or essential input blocks it.

Order: steps 1–3 first; then 4–7, moving independent work forward when data/definitions are blocked; then 8–12. Each experiment must verify sound rendering before requesting judgments. We will not ask the user to assess an effect the player does not reproduce.

## Preflight evidence

Main pulled ff-only; no incoming changes at start. Existing code: analyze_style.py counts HOPO property presence but does not reconstruct directional pairs; historical extractor preserves raw note/beat XML and property names. Exact graph and shared reference_levers property transaction are reusable, but do not implement these new features yet.

Raw XML property inventory (counts are definitions containing the property, not certified techniques/attacks):

| Private score | HopoOrigin | HopoDestination | Beat VibratoWTremBar |
|---|---:|---:|---:|
| Time | 87 | 87 | 1 |
| Cloud Cascade | 50 | 50 | 0 |
| Sweet Child | 154 | 154 | 1 |

Equal origin/destination totals do not prove pair linkage. Earlier “no vibrato tags” observation concerned note tags; it did not establish absence of beat-level arm vibrato. This coverage gap must be corrected in the unified analysis. No completed implementation or listening quality is claimed by this roadmap.

## First analysis implementation

`technique_analysis.py` now reports occurrence-level note/beat inventories, explicitly paired and eligible-but-unmarked HOPO, directional/open/fretted counts, source-section counts, effect XML, simultaneous vocabulary groups and alternating-return pedal candidates. Guitar/bass MIDI programs are distinguished from notation-only tracks; e.g. vocal HOPO/slurs are not silently called guitar technique. Beat arm-vibrato is retained. Summarized marker absence still does not establish performance absence.

Independent `verify_technique_links.mjs` agrees with every directed alphaTab HOPO link: Time 87, Cloud 50, Sweet 154. No unmatched markers, zero source timing discrepancies. Guitar/bass-only observed transitions:

| Source | Fretted hammer-on | Fretted pull-off | Hammer-on from open | Pull-off to open |
|---|---:|---:|---:|---:|
| Time | 6 | 12 | 25 | 1 |
| Cloud | 26 | 4 | 16 | 4 |
| Sweet | 36 | 116 | 1 | 1 |

Private reports: `local-artifacts/techniques-v1/{time,cloud,sweet}.json`. Public source-free aggregates: `benchmarks/technique_analysis_results.json`. CLI: `python composition-lab/technique_analysis.py SOURCE.gp --output PRIVATE_REPORT.json`; independent linkage check: `node composition-lab/verify_technique_links.mjs ALPHATAB_MODULE SOURCE.gp PRIVATE_REPORT.json`.

Simultaneous classification uses rational onset AND end boundaries, not just attacks, and excludes percussion; it distinguishes co-attacks from sustained overlap. Labels describe notated base pitches, flag bend/harmonic/beat-pitch effects for further resolution, and do not establish acoustic dissonance. Pattern counts are intervals, not distinct riffs. Extended power follows the user definition and can include ordinary major/minor triads as root/fifth/one-color collections. Exact alternating six-event pedal windows are exploratory, overlap each other, and are not verified pedal roles. Cloud currently has zero under this narrow monophonic detector; this is not evidence Cloud has no pedal material. Steps 4–7 remain partial; no new technique generation/playback acceptance yet.

Verification: 142 Python tests (13 new technique tests), 16 JS tests and Vite build pass. No website changes. Next: broaden notation-effect mapping and pedal-pattern coverage, then controlled performance edits with a renderer that can audibly distinguish legato from picking.
