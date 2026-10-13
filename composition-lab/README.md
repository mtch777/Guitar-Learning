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


## Phase 2d: ensemble pitch context and structural novelty

Run:

```bash
python harmony_boundaries.py "Cloud Cascade (Tuned Down).gp" "Nocturne_ Lost Faith (Tuned Down).gp" "Immolation of Night (Tuned Down).gp" --output harmony_boundary_report.json
python -m unittest discover -s . -p 'test_*.py' -v
```

This script reads pitches from all guitar and bass tracks, deduplicates *exactly identical* guitar tracks, and reports pitch-class presence weighted by duration for every measure. If an explicit bass track exists, its lowest note provides only a possible harmonic root (not a verified chord label).

It also finds potential structural changes from differences in pitch-class distribution and guitar note density over neighboring four-measure windows. Labeled song-section changes are used **only to count candidates and inspect in-sample agreement**. Do not interpret overlap as independent model accuracy.

**Initial three-song observations:** Cloud Cascade: 5/13 candidate cues within ±1 bar of a tab section start; Nocturne: 8/11; Immolation of Night: 7/8. Only Cloud Cascade has a separate bass track. No automatic chord-progressions or validated phrase boundaries are claimed.

**Next:** human-audited boundary labels and chord/root annotations, held-out evaluation without using source boundary counts, robust double-tracking suppression, and proper drum analysis. The instrument tracks and proprietary music inputs are not committed to GitHub.


## Phase 2e — boundary validation and harmonic hypotheses (2026-10-09)

`validate_structure.py` addresses an important evaluation flaw in the earlier section detector: the number of boundary candidates is now based ONLY on song length (one per 12 measures), rather than the number of source section labels. Candidate locations use changes in pitch distribution and guitar event density, then source labels are consulted afterward for evaluation. This remains an **in-sample annotation comparison**, not held-out validation or verified phrase detection.

It also fits ranked **chord hypotheses** per measure from guitar and available bass pitch-class counts. These are not authoritative chord progressions; melody notes, unclear roots, doubled parts and missing bass can skew the results.

Usage:
```bash
python validate_structure.py "Cloud Cascade (Tuned Down).gp" "Nocturne_ Lost Faith (Tuned Down).gp" "Immolation of Night (Tuned Down).gp" --output structure_harmony_validation.json --audit-csv structure_boundary_audit.csv
python -m unittest discover -s . -p 'test_*.py' -v
```

Three-song in-sample section overlap (±1 bar):
- Cloud Cascade: 4/9 candidates near labels; 4/13 labels recalled.
- Nocturne: Lost Faith: 6/9 candidates near labels; 6/11 labels recalled.
- Immolation of Night: 7/8 candidates near labels; 7/8 labels recalled.

The audit CSV includes predicted measures with blank fields for human review; original songs and analysis exports are not committed. Next: human-verified section and phrase labels, selected chord-reference annotations, and held-out tests before fitting a credible style model.


## Phase 2f — human-validation workflow

This step does **not** claim that a motif/chord/section candidate is musically correct. Before training a style model on these labels, a reviewer should inspect and listen to representative examples.

Use the existing local JSON artifacts from `phrase_analysis.py` and `validate_structure.py`:

```bash
python review_candidates.py create --motifs phrase_analysis_report.json --structure structure_harmony_validation.json --output composition_review_audit.csv
python review_candidates.py score composition_review_audit.csv
```

The CSV includes song, guitar track, measure(s), hypothesis, supporting measurements, plus blank `review_label` and `reviewer_notes` fields.

Human review label options: `confirmed`, `rejected`, `uncertain`. Do not treat blank or uncertain rows as accepted training data. The scoring command reports reviewed/unreviewed counts and the confirmed fraction **among decisive human reviews only**. It cannot produce ground truth on its own.

Review guidelines:
- **Motif:** Listen to both excerpts; confirm if they are meaningfully related despite variation, and reject superficial coincidences.
- **Section boundary:** Confirm whether the proposed measure begins a musically distinct section or phrase (these are different annotation tasks).
- **Chord:** Verify whether the nominated chord/root fits the arrangement; pitch-class coverage alone may confuse melody notes with chord tones.

The first three-song audit dataset contains 79 rows: 30 motifs, 26 boundary candidates, 23 chord hypotheses. All are initially **unreviewed**. Source tab files remain outside GitHub.

**Before any accuracy or learning claim:** Check that test fixtures and Github Actions pass, audit the parser's rhythm and track interpretation, and reserve at least one song for evaluation separate from parameter selection. Source annotations should not be treated as independent human-verified ground truth.


## Interactive listening review (independent browser page)

Open `https://mtch777.github.io/Guitar-Learning/composition-review/` after GitHub Pages deploys. This is **not** a new lesson or an extension of the existing guitar trainer: its UI, JavaScript, and candidate data reside exclusively in `public/composition-review/`. No imports from `src/`, `training/`, or the existing audio/classifier stack. The existing Vite build only copies the standalone public assets to the Pages output.

- Choose the three original GP files when first opening. They remain **local** to your browser; IndexedDB stores copies on the same device when allowed.
- The 79 candidates are sourced from the previous `composition_review_audit.csv` (30 riff comparisons, 26 section changes, 23 chord hypotheses); the code repository contains **metadata only, not any original music**.
- For riffs, play A and B separately using alphaTab 1.8.4 score rendering and the player `playbackRange` of the specified measures.
- For section changes, compare the four measures before and after a candidate boundary.
- For chord questions, play the measure with its complete arrangement (rather than assuming one guitar part establishes a chord).
- Choose relevant guitar vs full band (except chords, always full), speed 50%-125%, and Confirm/Reject/Unsure, optionally adding notes.
- Feedback automatically persists in browser localStorage; **Export feedback JSON** is the portable record to share with the researcher. "Forget local song files" clears IndexedDB only, not feedback.
- No requests are made to any custom upload server; alphaTab's JavaScript, worker assets and soundfont load from its public jsDelivr CDN.

**Verification:** Static JavaScript syntax and JSON case-count validation passed locally. Browser rendering, playback ranges, deployment, and GitHub Actions must still be confirmed on the published site/device. If the original files include repeats, player tick positions may follow playback-order semantics rather than the notation bar-number order, which should be audited with listening tests.

## Phase 2g — candidate phrase boundaries and riff development

Use the verified three-song GP files as local inputs (never commit them):

```bash
python phrase_development.py "Cloud Cascade (Tuned Down).gp" "Nocturne_ Lost Faith (Tuned Down).gp" "Immolation of Night (Tuned Down).gp" --output phrase_development_report.json
python -m unittest test_phrase_development -v
```

The phrase analyzer partitions each track at **tab-annotated section boundaries**, then uses dynamic programming and local pitch/rhythm activity to propose smaller 1/2/3/4/6/8-bar phrases. It groups earlier phrases by relative melodic intervals and note timing (limited edit-distance changes), identifying candidate **repeat / transposed exact / varied / new material** relationships. It exports a per-track chronological phrase map including bars, section labels, motif-family IDs, prior phrase references, and comparison distance.

Local checks: 7 new tests passed; analysis completed on all three original tuned-down GP files. Sample predictions:
- Cloud Cascade, Leads I: phrase 1–4 recurs exactly at 9–12 and 17–20, and phrase 5–8 at 13–16 and 21–24; measures 29–32 appear as a variant of 25–28.
- Nocturne, rhythm left: bars 30–33 recur at 34–37.
- Immolation, Guitar 1: bars 20–23 appear as a variant of 16–19, then 24–27 recur.

**Interpretation limits:** This is *candidate* phrase segmentation, not human-verified phrase boundaries. The prior riff listening review supported candidate similarity but did not validate the new boundary algorithm. Section annotations force hard breaks, the model compares the first voice's lowest note (not harmony/chord voicings), and double-tracked parts that differ slightly can still be double-counted. The motif family assignment is greedy and may be nontransitive. Phrase complexity varies; the length prior often favors four bars. These results are descriptive, **not yet a trained generative style model**.

Next: build a section-to-phrase development grammar / arrangement model; compare repeated motif sequences across songs while holding at least one out for evaluation; prepare constrained 16-bar generation.


## Phase 3a — phrase-development structure model

`structure_model.py` builds empirical high-level transition counts from the provisional phrase families produced by `phrase_development.py`. It selects one representative (preferably rhythm) guitar track per source song to avoid interpreting two doubled rhythm guitars as two independent training songs. Actions are `introduce`, `repeat`, `vary`, `transpose`, and `return`.

```bash
python structure_model.py "Cloud Cascade (Tuned Down).gp" "Nocturne_ Lost Faith (Tuned Down).gp" "Immolation of Night (Tuned Down).gp" --bars 16 --seed 17 --output structure_model_report.json
python -m unittest discover -s . -p "test_*.py" -v
```

The 16-bar planner samples learned transition frequencies with smoothing and adds explicit coherence constraints (at least two phrase families and a final return when the length permits). Repeated/varied phrases reference earlier phrase IDs. Output is a **plan only**; no new note sequence or playable GP file has yet been generated. The user's earlier positive listening feedback supports motif *similarity*, not the correctness of these learned composition decisions.

Observed representative-track phrase counts: Cloud Cascade 22, Nocturne 21, Immolation of Night 18 (61 total). Leave-one-song-out coverage of transition TYPES, not musical fidelity: Cloud Cascade 14/21, Nocturne 19/20, Immolation of Night 7/17. These counts are small, source-dependent, and are not accuracy scores.

Seed 17 example: measures 1–4 introduce A; 5–8 repeat A; 9–12 introduce B; 13–16 return to A. That coherent plan is partly enforced by constraints, not solely discovered. The next milestone is to **generate new notes and rhythms into playable modern .gp**, validate originality, and test musical results by ear.


## Phase 3b — first generated playable guitar study

`generate_composition.py` is the first original-score generator. It learns distributions of rhythmic durations, relative melodic leaps, and pitch classes from supplied .gp scores. Then it generates two independent four-bar phrases, makes a small pitched variation of A, and reprises A as the final phrase.

```bash
python generate_composition.py \
  --template "Cloud Cascade (Tuned Down).gp" \
  --sources "Cloud Cascade (Tuned Down).gp" "Nocturne_ Lost Faith (Tuned Down).gp" "Immolation of Night (Tuned Down).gp" \
  --output "Original_16_Bar_Guitar_Study.gp" --seed 17
```

**A (bars 1–4) → varied A (5–8) → B (9–12) → return to A (13–16).**

The script preserves one compatible 8-string source track *configuration* and ZIP packaging but replaces all original master bars, bars, voices, beats, rhythms and notes with newly authored material. It creates 16 measures of 4/4 music, writes a single 8-string guitar track, and reopens the resulting .gp XML for structural validation. A deterministic seed allows exact reproduction. No copyrighted source song or generated file is committed to this public repository.

Local trial with the three source songs: **153 newly authored notes in 16 measures**. The existing `phrase_development.parse` parser successfully re-imported the result. Five source-independent generator smoke tests and three source-dependent local checks passed. **Manual alphaTab/Guitar Pro playback remains unverified.**

Important limits: this is a *first experimental sketch*, not a high-quality style-transfer composition. Rhythm and note/interval choice are informed by corpus distributions, but melodic coherence, harmonic development, fretboard technique and natural phrasing need significant improvement. The long-range A/A-var/B/A structure is explicitly constructed, not autonomously learned. No polyphonic guitar chords or other instruments yet.

**Next: audition the generated .gp**, diagnose timing/tone/playability issues in the song player, compare against copied-source and random baselines, and improve composition grammar before expanding to other instruments.


## Phase 3b — reusable tonal-center and mode inference

`infer_tonality.py` analyzes each modern GP source independently, with the same configurable, explainable rules across songs. It is a **hypothesis generator**, not a trained or validated key detector.

```bash
python infer_tonality.py "Cloud Cascade (Tuned Down).gp" "Nocturne_ Lost Faith (Tuned Down).gp" "Immolation of Night (Tuned Down).gp" --output tonality_inference_report.json
python -m unittest test_infer_tonality -v
```

Optional repeatable weights: place any subset of `Settings` field names and numeric weights in a JSON file and run `--settings weights.json`. Unknown fields and negative weights fail fast. Tune weights on a **held-out manually labeled** corpus, not on these three songs.

Steps:
1. Read pitched events by song/track/measure; exclude percussion and exact doubled guitar tracks.
2. Extract bass pitch-duration counts, explicit simultaneous guitar pitch clusters, melody endings at **annotated section boundaries**, and pitch-class distribution.
3. For explicit chords, evaluate root/quality along with potential bass-root agreement, inversions, or non-chord/pedal bass. Agreement adds evidence; disagreement **does not reject** a chord.
4. Rank 12 tonal centers using multiple evidence sources; compare the seven diatonic modes and their pitch coverage for every tonic; rerank tonic + mode jointly.
5. Analyze annotated sections separately for possible changes. Preserve ambiguity and return scores, alternative interpretations, and evidence contributions.

Caveats: GP written key signatures are not parsed by this module (never silently treated as tonic). It uses an upstream simplified event parser that does not preserve every rest/tie, and treats score-provided section boundaries as structural evidence. Mode coverage and tonal-center rankings are **heuristic scores, not calibrated probabilities**; missing drums and ambiguous chord-root vs pedal interpretation can change results. There is no independently validated ground truth.

First run's leading candidates (unconfirmed): Cloud Cascade D Aeolian; Nocturne C# Aeolian; Immolation C Lydian. These are **not** established musical keys. Review them against the actual music before allowing inferred harmonic labels to influence generation.
