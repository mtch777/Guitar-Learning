# Technique analysis contract and acceptance

Scope: repeatable scripting on notation, not AI-filled interpretation. Source GP,
API captures, annotated occurrences and review judgments stay private. No source
marker absence establishes absence in the actual performance.

## Shared representation

Immutable song/revision/part/bar/voice/beat/note identity; exact rational written
onset/duration; grace notation separate from metrical time; tuning/capo/string/fret;
ties; raw note and beat properties; source section labels separate from inferred
phrases. Written occurrences, attacks, sustained gestures and playback visits have
different denominators. Bad timing excludes temporal relationships, not raw counts.

## Family contracts

| Family | Literal evidence and properties | Relationships and denominator | Unknown / validation gate |
|---|---|---|---|
| Bend | Explicit note curve; raw tone/50 semitones; precisePosition/100, fallback position/60; rise/hold/release, peak, excursion, slope, point vibrato | Written segment share separately from tied gestures; duration, register, section position, neighboring intervals and held pitches | No emotional purpose, physical execution or phrase-end truth inferred |
| Open-string HOPO | Source origin flag, same-string/voice contiguous transition through matching ties; fret rise/fall, from/to open | Candidate transition count; gaps/grace/ties unresolved explicitly | API candidates distinct from GP paired-marker/independent-reader evidence; audible legato timbre not certified |
| Fretted HOPO | Same notation logic, fretted endpoints | Retained in analysis; not a requested listening study | MIDI articulation does not prove technique reproduction |
| Finger vibrato | Explicit note flags and qualitative strength; curve-point flags separate | Marked segments, durations and contexts | Physical oscillation rate/depth unavailable; arm effects separate |
| Double stop | Exactly two coattacking notes on different strings | Eligible onset groups; absolute written interval | Sustained overlap separate; effects can alter sounding pitch |
| Close texture | Double stop with exactly one semitone absolute separation | Eligible groups; whole-step and octave-displaced negatives | No general dissonance/intent claim |
| Power chord | Lowest written pitch is root; pitch classes exactly root/fifth, octave duplicates allowed | Eligible coattack groups; root, voicing, register | No functional harmonic-root inference |
| Extended power | Root/fifth plus exactly one additional pitch class above lowest root | Same group scope; color interval recorded in source evidence | May include familiar triads by the user definition |
| Pedal pattern | Repeated anchor/chug-return candidates with contrasting events and explicit rhythmic tolerance | Candidate windows/bursts, not independent phrases; overlap and recurrence disclosed | Function, meaningful call/response and phrase scope need adjudication |
| Arm/brush/picking | Exact arm curves, native brush duration/shift and effective direction, tremolo fraction | Note-scope histograms explicitly differ from beat counts | Brush native units unresolved; tremolo picking is distinct from requested finger vibrato |

## Validation levels

1. Preservation: independently read raw files; reconcile all occurrences, raw notes,
   string/fret/ties, written pitch and durations, including grace occurrences.
2. Rule conformance: independent interval/set oracle checks every eligible attack
   group, including negatives and missed detections. This is not musical accuracy.
3. Independent reader: existing GP/alphaTab timing, HOPO, curves and roundtrip checks.
   Corpus conversion has 74 passing and 24 flagged entries; do not hide that cohort.
4. Semantic accuracy: independently adjudicated positive/negative source examples
   before reporting precision/recall of pedal function, phrase, role or resolution.
5. Listening: only where notation cannot answer; no synthetic playback state may
   be substituted for a human judgment.

Deterministic private strata include marked/unmarked notes and positive/negative
construction groups. Twelve source-located samples per stratum are retained as an
inspection seed, not a statistically representative accuracy estimate. Earlier 88
source-located evidence cases and 2904 context/control occurrences remain preserved.

## Persistent checklist

- [x] Define family semantics, denominators, exclusions and uncertainty.
- [x] Extend shared exact-time source observations and retain raw data.
- [x] Run all 98 entries / 495 tracks; reconcile source occurrences.
- [x] Strict field audit: no unreviewed observed paths.
- [x] Independent all-group rule audit, including negatives and injected-failure tests.
- [x] Private stratified review evidence, source-free published validation counts.
- [ ] Independently adjudicated musical-function labels and measured semantic accuracy.
- [ ] Validate pedal recurrence/function and phrase-level placement beyond candidates.
- [ ] Human listening acceptance for context transfer (separate from analysis correctness).
- [ ] Verified main delivery and CI/Pages: recorded in MUSICAL_FIELDS_PROGRESS.md.

Future unknown fields fail the strict coverage gate. Do not add invented phrase,
artist, emotional or performance annotations to fill missing evidence.
