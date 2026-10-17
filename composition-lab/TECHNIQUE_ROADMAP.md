# Current goal: performance techniques and guitar patterns

Started 2026-10-16. Status: active; scripted controls and engineering review delivered; human musical acceptance pending. This extends, rather than replaces, the verified bend baseline. Authoritative branch: origin/main. Private scores, annotations, rendered source excerpts and checkpoints remain outside Git.

## Contract

Analysis and musical decisions use repeatable scripts, not AI-filled labels. Observations, inferred patterns and listening judgments remain separate. Analyze corpus/song/section/phrase/event levels where evidence permits; denominators, annotation coverage and uncertainty are mandatory. No missing label becomes a negative training example by default.

0% = literal lock of the selected data. 100% = unlocked from direct reference values for that feature, not forced difference. Methods and constraints are separate from freedom. Performance and arrangement are separate. Techniques affect sound differently: a HOPO changes the articulation between discrete notes; it is not a continuous bend. New intermediate notes, changed pitches/durations, voice allocation or fingering require explicit declared edit permissions and conflict checks. Start by annotating eligible existing note pairs before inserting notes. Keep fretted observations and sounding-pitch goals distinct.

## Feature definitions

| Family | Initial definition | Status / caveat |
|---|---|---|
| Fretted hammer-ons | Directed same-string lower-to-higher fret transitions, destination fretted; distinguish explicit HOPO marking from inferred eligibility | High-neck location is a contextual descriptor, not a hardcoded fret cutoff |
| Fretted pull-offs | Directed same-string higher-to-lower fret transitions, both fretted | User confirmed higher neck positions; report positions rather than impose a universal fret cutoff |
| Hammer-ons from open | Same-string fret 0 to a positive fret | Separate occurrence/transition rates |
| Pull-offs to open | Same-string positive fret to 0 | Separate occurrence/transition rates |
| Vibrato | Oscillating pitch on a sustain; distinguish finger and arm notation | Preserve source type; encoded width/rate may be absent |
| “Tremolo” as requested | User clarified bending-based vibrato | Rapid tremolo picking is outside the requested generation scope; recognize its notation to avoid misclassification |
| Pedal-note patterns | Recurring mid/low anchor interleaved with contrasting notes, with recurring temporal organization | Detect recurring anchors/patterns, not just most frequent pitch; include lower accents, register changes and cross-phrase/section recurrence |
| Close-interval texture | Exactly two notes on distinct strings sounding simultaneously, absolute pitch separation exactly 1 or 2 semitones | “Inharmonic” is user's category name; measurable observation is a close dyad, not acoustic inharmonicity. Distinguish co-attack from incidental sustain overlap |
| Power chords | At least two simultaneous notes; lowest pitch defines root; pitch classes are exactly root and perfect fifth, both present; octave doublings allowed | Root+octave alone is excluded; no third/extra pitch class |
| Extended power chords | Power-chord core plus one distinct color pitch class, neither root nor fifth, above the lowest root | Track color occurrences/doublings separately; this exact-class interpretation is explicit and can be revised |
| Double stops | Exactly two simultaneous notes on distinct strings, any interval | Plain user-facing definition. Internal descriptions may also name their interval/chord content; user need not choose exclusive labels |

## Execution steps and acceptance criteria

- [ ] **1. Finalize schema and definitions.** Scope questions resolved 2026-10-16 as above; finish positive/negative fixtures for every family, including ties, grace events, polyphony, alternate tuning and ambiguous markers. No additional double-stop terminology decision required.
- [x] **2a. Initial private-source inventory.** Inspect Time, Cloud Cascade and Sweet Child for source technique encodings; retain aggregate counts only publicly.
- [ ] **2b. Complete extraction/notation coverage audit.** Read note properties, note tags, beat properties, beat tags, staff effects and linked transitions; preserve exact rational timing, occurrences, fret/string/tuning. Every detected effect is mapped or explicitly unsupported. Audit parser/independent-import agreement. This is necessary before interpreting absence.
- [x] **3. Implement directed HOPO relationship analysis.** Match explicit origins/destinations in same track/voice/string using timing and source links; classify upward/downward and open/fretted pairs; report unmatched/ambiguous markers. Tests ensure no cross-string, cross-track or arbitrary skipped-note links. Measures report attacks/transitions separately from tied segments. Evidence below; higher-neck naming remains provisional.
- [ ] **4. Implement vibrato and tremolo analysis.** Separate finger vibrato, arm effects, tremolo picking and any volume effect; preserve available speed/width/rate/subdivision and report unknowns. Do not infer a performed waveform from a generic marker. Validate synthetic examples plus available annotated sources; absence of corpus examples does not count as validated detection.
- [ ] **5. Implement simultaneous-note vocabulary.** Exact rational sounding groups with string identity; classify dyads, power and extended power chords using definitions above. Tests cover inversions, octaves, extra thirds, held overlaps, cross-voice groups and duplicate unisons. Labels may overlap; report exclusions and co-attack versus overlap.
- [ ] **6. Implement recurring pedal-pattern analysis.** Identify anchor/contrast alternation, relative register, rhythm signatures, repetitions and transformations within/across sections. Include counterexamples: isolated repeated pitch, chord root frequency, unrelated open strings. Threshold sensitivity and evidence links required; no automatic emotional/function claims.
- [ ] **7. Produce unified reference reports.** For each family: counts/rates, song/track/section coverage, distributions, conditional relationships and inspectable occurrences. Phrase/corpus reports only where validated boundaries/multiple relevant songs exist. New analyzer results must reconcile with original occurrence totals and preserve unknowns.
- [ ] **8. Extend exact-lock edit contracts.** Separate toggles for HOPO articulation, finger vibrato, pedal pattern and dyad/chord construction. Declare permitted fields and downstream sounding consequences. Zero = literal identity; 100 = proposal invariant to perturbing hidden original feature annotations. Reject incompatible requests; no whole-score serialization that erases unsupported effects.
- [ ] **9. Build isolated performance experiments.** First existing eligible fretted HOPO pairs, then open-string HOPO, then finger vibrato. Keep other dimensions locked; use authored diagnostic notes when no real example exists. Independently import GP; verify audible articulation/oscillation. Sine previews that cannot distinguish picking/HOPO timbre are insufficient. Preserve all bend baselines.
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

## Performance edits, effects and pedal bursts

User scope clarification received: fretted pull-offs at higher positions confirmed; requested “tremolo” is bending-based vibrato, not rapid picking. Double stops mean two notes played together; internal interval descriptions need not be user-facing exclusive categories. Do not repeat the abstract category question.

`technique_effects.py` separates finger/arm vibrato, arm curve components, picking direction, trill and tremolo-picking notation. Generic marker strength does not establish a physical rate or width; these remain null. Unknown effects retain XML and unsupported status. Tremolo-picking parsing prevents confusion but its generation is outside requested scope.

`technique_edits.py` adds reusable fail-closed note/beat property and tag transactions. Existing HOPO pairs can be selected by scripted short-interval or longer-arrival rules; no notes/pitches/timing are inserted or moved. Origin/destination flags are independently owned at shared chain nodes. End-of-tie origin location is respected. 100% proposals redact both valid and malformed reference HOPO labels before selection. 0% copies bytes literally. Intermediate strengths explicitly unsupported. Finger vibrato edits only `<Vibrato>` on eligible fretted single-note segments; open strings excluded, qualitative Slight/Wide only.

Actual source benchmark `local-artifacts/technique-edits-v2`: 30 nonempty variants across Time/Cloud/Sweet; all locks and independent directed-link/note-vibrato mappings pass. Twelve HOPO zero cases are byte-identical; 24 source HOPO perturbations and three source vibrato-width perturbations pass. Public aggregate only: `benchmarks/technique_edit_results.json`. Original partial batch v1 retained after profiling and intentionally stopped for an indexed-lookup optimization; v2 completed. No baseline files overwritten.

Reproduce source cases: `python composition-lab/benchmarks/technique_edit_benchmark.py SOURCE1.gp SOURCE2.gp SOURCE3.gp --out NEW_PRIVATE_DIRECTORY`. CLI for individual levers: `python composition-lab/technique_edits.py SOURCE.gp --out NEW.gp --track INDEX --family FAMILY --strength 0|100`. Fretted and open-string HOPO are separate families; `finger_vibrato` accepts `--width Slight|Wide`.

Reproducible authored diagnostics: `python composition-lab/build_technique_diagnostics.py --out NEW_PRIVATE_DIRECTORY`. Seven GP files (reference diagnostic plus four HOPO/two vibrato variants), not a musical review set. `render_gp_instrument.mjs` exports native alphaTab internal MIDI to bundled Sonivox SF2 at 44.1kHz, fixed gain; finite/clipping/duration limits enforced. Seven instrument WAVs verified finite, nonzero and unclipped. The bundled font license was read separately; it remains in installed dependencies, not copied into Git. Font SHA256 in aggregate report.

`verify_technique_playback.mjs` verifies unchanged synth note pitches/on/off times. Four HOPO diagnostic variants alter 8/8/6/5 destination dynamics respectively. Slight/Wide diagnostics create noncenter pitch events; both expose 24 note vibrato markers independently. **Authentic legato timbre remains unverified:** this GM engine primarily adjusts HOPO dynamics, so these are engine diagnostics, not a sufficient human hammer-on quality review. No original/no-technique control was presented to the user. No human listening judgments fabricated; step 9 remains open.

`pedal_patterns.py` adds co-attack-group and repeated-anchor-burst queries. Repeated chugs before fills no longer require strict single-note alternation. Cloud source now yields 48/23/58/58/3 burst candidates across its five pitched guitar/bass tracks, versus zero under the earlier monophonic rule. These are overlapping candidates under a stated period tolerance, not adjudicated musical roles. Constant roots without contrasting returns are excluded; section boundaries respected; source evidence retained. Recurrence/variation validation and pattern generation remain open.

Verification at this milestone: 158 Python tests, 16 JS tests, Vite build; independent imports for all 30 real-score variants plus six authored modified scores. No website changes, no Pages deployment required. Remaining: full effect coverage, broader pedal/phrase validation, arrangement-pattern edit levers, physical/authentic playback and human review. Goal stays active.


## 2026-10-16 — construction controls and consolidated review

Acceptance evidence and reproduction commands: TECHNIQUE_RESULTS.md. Earlier endpoint-only statements above are historical.

- [x] Integer 0–100 release for HOPO/vibrato; paired flags, literal zero copies, actual/proposed selection reporting.
- [x] Separately authorized pedal/dyad/power/extended-power/double-stop construction; immutable original definitions, occurrence clones, exact timing, untouched-occurrence and archive checks. Incompatible locks reject.
- [x] Full-freedom reference-pitch perturbation tests in two tunings; all five construction families and nested release subsets checked.
- [x] Thirty real-score guitar-only cases; independent written stringed pitch/string/fret verification on all thirty.
- [x] Multiscale descriptive reports with section/track denominators and conditional distributions; artist/phrase truth unknown; staff inventory retained. Time arm-vibrato independently checked.
- [x] Eighty authored GP/audio probes including higher-neck positions; all independently imported and rendered finite/nonzero/unclipped. Final review offers 35 distinct A/B pairs across ten families; empty/identical pairs withheld.
- [x] Browser-check ten groups/both rolls, playback, saved QA feedback and exported JSON. Range-server fix verified synchronized A/B seeking. QA isolated from musical judgments.
- [ ] Human musical/physical acceptance, authentic HOPO tone, validated pedal/phrase function and learned artist-conditioned transfer remain open.

Final private review: local-artifacts/technique-review-v6 at http://127.0.0.1:5180/. Guitar batch: pattern-edits-v3. Earlier diagnostic rounds retained: review v1/v4 failed family coverage, v2/v5 exposed identical methods, v3 valid lower-position bundle; v6 includes higher positions and passes final gate. Pattern v2 selected bass where it maximized coverage; v3 deliberately selects guitars. No original/no-technique listening control offered. 169 Python tests, 16 JS tests, build pass. No public website changes.
