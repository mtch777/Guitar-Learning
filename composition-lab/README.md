# Composition Lab — isolated Guitar Pro composition research

**Scope:** Guitar Pro (.gp) input → music analysis → guitarist-style composition → new Guitar Pro (.gp) output.

This is an **independent Python project** inside Guitar-Learning. It does not import from or modify `src/`, `training/`, the guitar trainer, the audio ML pipeline, or the web app. Python standard library only for the current compatibility tests.

## Phase 1: GP7 archive compatibility

Modern `.gp` files supplied for this project are GP7 ZIP archives containing `VERSION` and `Content/score.gpif`. `gp_io.py` currently:

- checks a file's container/version and parses its GPIF XML;
- reports count of tracks, master bars, notes, beats, and track names;
- writes a **lossless archive round-trip** to another `.gp` file;
- verifies *every* original ZIP member has exactly the same uncompressed bytes in the output.

Run from the `composition-lab/` directory:

```bash
python gp_io.py inspect "song1.gp" "song2.gp"
python gp_io.py roundtrip "song1.gp" "roundtrip.gp"
python -m unittest discover -s . -p 'test_*.py' -v
```

**Important distinction:** This verifies archive reconstruction, NOT authoring new musical notes. Exact score-data preservation is a prerequisite only. The output may not be byte-for-byte the same ZIP because compression metadata can differ. A separate GP7 score-writing implementation and an alphaTab/Guitar Pro open-and-render test are required before claiming editable new composition support.

## Development plan

1. **GP file compatibility**: archive inspection and lossless repackaging (first milestone); then validate with Guitar Pro and alphaTab.
2. **Semantic GPIF reading/writing**: extract and reconstruct linked tracks, measures, voices, beats, rhythms, notes, tunings and techniques. Verify score round-trip after reserialization; reject unsupported features rather than drop them silently.
3. **Style analysis**: rhythmic patterns, melodic intervals, riff/motif reuse, techniques, fretboard choices and song structure.
4. **Generator**: 16-bar original guitar composition conditioned on learned style; use guitar-playability and timing constraints.
5. **Evaluation**: compare to held-out music and generic baseline; test novelty, structural coherence, valid export and human-listening impressions.

Source songs remain local/test inputs and are **not committed** to the repository by default. The three initial test songs are Cloud Cascade, Nocturne: Lost Faith and Immolation of Night.

## Phase 1b: real note editing and verified score re-import

`edit_gp.py` now provides a **narrow, safe first musical edit** to a GP7/GP8-style archive. It shifts one un-tied, non-bent fretted guitar note by one semitone, updating its fret, MIDI number, ConcertPitch and TransposedPitch simultaneously. After writing, it re-opens the output and checks that the new note values persisted and that only `Content/score.gpif` changed. Unsupported notes are skipped rather than silently altered.

```bash
python edit_gp.py "input.gp" "note-up.gp"
python edit_gp.py "input.gp" "note-down.gp" --semitones -1
python -m unittest discover -s . -p "test_*.py" -v
```

**Evidence:** Manual local tests on all three supplied source files succeeded for one-note changes and XML re-import. Automated GitHub tests use an independently generated fixture; source songs are not stored in the repository.

**Still required:** Open the edited exports in Guitar Pro and alphaTab to confirm rendering/playback; implement generalized GPIF score generation (new notes, beats, measures and musical composition), not merely modifying an existing score.

## Phase 2: First symbolic style-analysis milestone

Run independently from the `composition-lab/` directory:

```bash
python analyze_style.py "Cloud Cascade (Tuned Down).gp" "Nocturne_ Lost Faith (Tuned Down).gp" "Immolation of Night (Tuned Down).gp" --output analysis.json
python -m unittest discover -s . -p 'test_*.py' -v
```

`analyze_style.py` extracts **source-annotated section boundaries**, time signatures, pitched-fretted-note distributions, rhythmic note values, playing-technique markings, fret/string preferences, and exact 1- and 2-measure tab repetitions. The tool produces inspectable JSON, not generated music. Files and derived user-specific analyses stay out of the repo by default.

**Honest limits:** Sections come from GPIF annotations, not automatic section inference. Exact riff fingerprints do not match transposed or varied phrases. Naive intervals may include simultaneous chord notes, tied notes are counted as written, and pitch histograms alone do not determine harmonic function or key. Percussion groove modeling and general learned guitarist-style models remain future work. Duplicate doubled rhythm tracks must be de-duplicated before deriving band-level statistics.

Next: reconstruct timing and rests rigorously, recognize transposed/varied motifs and phrase boundaries, analyze harmony with appropriate uncertainty, compare against held-out songs or a contrasting guitarist.

## Phase 2b: transposition-invariant motif analysis

`analyze_motifs.py` extends the original feature report without interacting with the existing web/audio application.

```bash
python analyze_motifs.py "Cloud Cascade (Tuned Down).gp" "Nocturne_ Lost Faith (Tuned Down).gp" "Immolation of Night (Tuned Down).gp" --output motif_harmony_report.json
python -m unittest discover -s . -p 'test_*.py' -v
```

- Parses linked measures, voices, beats and MIDI pitches from GP7.
- Builds **transposition-invariant signatures** (relative pitch with beat timing).
- Finds same relative-pitch motifs when rhythms change (rhythm-flexible signature).
- Finds repeated *two-bar* relative-pitch/rhythm sequences.
- Reports pitch-class counts, unambiguous monophonic note-to-note leaps and simultaneous pitch-class sets.
- Includes regression tests for transposition, rhythm changes, sparse measures and different interval patterns.

**Limits:** Source section labels are not automatic segmentation. These are exact relative-interval signatures rather than general similarity search, transposition-equivalent motifs can include identical originals, and chord pitch-class groups are not functional harmonic analysis. Scores with unknown rhythmic values are rejected rather than misread. Tuplet and grace-note handling needs more rigorous validation.

Next: avoid double-counting doubled guitar tracks; align phrases across sections; detect insertions/deletions and motif transformations; infer harmony cautiously from all parts; evaluate against held-out songs.


## Phase 2c: approximate riff variants and phrase *candidates*

Run:

```bash
python phrase_analysis.py "Cloud Cascade (Tuned Down).gp" "Nocturne_ Lost Faith (Tuned Down).gp" "Immolation of Night (Tuned Down).gp" --output phrases.json
python -m unittest discover -s . -p 'test_*.py' -v
```

`phrase_analysis.py` compares 2- and 4-measure windows with dynamic-programming edit distance after normalizing starting pitch. It tolerates limited changes in notes, insertions, deletions and timing, and outputs ranked candidate pairs for inspection. Song section start points come directly from existing Guitar Pro labels; silence in the primary voice is flagged as another structural cue. The actual style model and genuine phrase segmentation **are not implemented yet**.

The initial three-song run found approximate variant pairs (examples):
- Cloud Cascade, lead I: measures 8 and 100 (4-bar windows, distance 0.0476).
- Nocturne, lead: measures 31 and 35 (4-bar windows, distance 0.1484).
- Immolation of Night, guitar 1: measures 37 and 80 (4-bar windows, distance 0.0228).

These are **candidate similarities**, not automatically confirmed musically meaningful transformations. Doubled guitar tracks can produce duplicate evidence. The metric reads the principal voice and lowest note from a chord, and it does not compare harmony, orchestration, drum interaction, or expressive techniques. It treats source tab labels as provided metadata. Validate candidate pairs aurally/visually and evaluate the similarity metric against manually labeled examples before trusting it to drive generation.

Next: annotation-assisted phrase-boundary validation, motif transformations across phrase lengths, accompaniment-conditioned harmony, and de-duplication of doubled tracks.
