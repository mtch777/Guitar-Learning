# Songsterr tonal analysis

An isolated, standard-library Python tool that ranks tonal centers and scale/mode interpretations from captured Songsterr notation. It reports evidence, competing explanations and unresolved outcomes instead of forcing every song into one major/minor key.

This directory does not change the guitar-learning UI, existing Composition Lab analysis, accepted technique detectors, GP conversion or source scores. It requires Python 3.10 or newer and no pip dependencies. It reads local captures; it does not download songs or need credentials.

## Run it

From the repository root:

```sh
# Original synthetic examples: major, minor, Dorian, ambiguous power chords,
# a dominant pedal, chromatic passing material, silence and a section change.
python -B tonal-analysis/analyze.py examples --output .local/tonal-demo

# A complete raw capture: metadata.json and track-0.json ... track-N.json.
python -B tonal-analysis/analyze.py analyze /path/to/capture --output .local/tonal-song --window-bars 4 --top 8

# Extraction integrity alone, without interpreting the key.
python -B tonal-analysis/analyze.py check-capture /path/to/capture --output .local/tonal-source-check

# Tests (run from tonal-analysis/).
cd tonal-analysis
python -B -m unittest discover -s tests -v
```

Use a **new output directory for each run**. Existing outputs and source files are never overwritten. Source-derived outputs require an ancestor named `.local` or `local-artifacts`, and cannot be inside the capture. Prefer the documented `.local` paths, which the repository ignores. Never publish source-derived reports, normalized commercial scores, or private annotations. Synthetic examples may be shared.

Each analysis writes:

- `events.json`: every non-rest occurrence, exact timing, pitch eligibility, original note/beat witnesses, tuning, ties, source declarations and exclusions.
- `report.json`: global analysis, overlapping windows, declared section instances, candidate section-center changes, all 12 center scores, top tonic/mode candidates and evidence.
- `verification.json`: independently traversed source occurrence identities, raw-witness equality, eligible pitches and within-voice timing checks; source-byte preservation.
- `manifest.json`: input byte hashes, analysis module hashes and scoring configuration.

Only a compact summary prints to the terminal. `check-capture` writes the verification and manifest. `examples` writes a subdirectory per original fixture plus `summary.json`.

## What the logic actually does

The pipeline is `raw capture -> exact normalized events -> observations -> ranked hypotheses`. Source metadata such as song title, artist and declared key never enters scoring. A normalized score is also available to Python callers through `tonal_analysis.engine.analyze(score)`; this is an explicit contract, not an arbitrary MIDI import.

| Evidence family | Implemented calculation | Boundary |
|---|---|---|
| Notes/scales | Unique pitch classes, separate attack and occupied-duration histograms, metric/accent weighting, 108 tonic/collection fits | Missing degrees preserve ambiguity; out-of-scale notes reduce fit without deleting the candidate |
| Chords | Every exact matching triad/seventh/add9/sixth/suspended/power template at each actual overlap cell; inversions retain bass separately | Incomplete or rootless chords and arpeggiated harmony remain unresolved; notes in an entire bar are never pooled into a chord |
| Chord order | Contiguous dominant-to-tonic, leading-chord and plagal/modal-return patterns with both source sonorities | These are pattern candidates, not independently established cadences; ambiguous chord interpretations share the evidence weight |
| Bass | Time-weighted lowest eligible active pitch, with exact cells and note witnesses | Not called a chord root; bass/chord evidence is suppressed if unresolved pitched material overlaps |
| Melody | Same-voice monophonic interval transitions, upward semitone destinations, returns after excursions | Polyphonic overlaps, rests and uncertain pitched material break the relevant sequential evidence |
| Arrivals | Actual voice endings and notes before at least one quarter-note of source silence | Structural proxies, not inferred phrase truth; window boundaries never manufacture endings |
| Chromatic context | Passing/neighbor candidates with three-note witnesses, candidate-specific outside notes, mixed-third notice | Borrowed chords, secondary dominants, substitutions and blues functions are not automatically adjudicated |
| Mode | Seven diatonic modes plus harmonic minor and ascending melodic minor as pitch collections | Minor collections can coexist in one minor key; this does not declare three different keys |
| Structure | Whole score, one-bar-stride windows, source marker instances, candidate center changes between sections | A changed window/section label is not proof of modulation; repeated identical marker text still starts a new instance |
| Annotations | Source key/signature, repeat and marker declarations retained separately | Undocumented key encodings are not guessed or used as truth |
| Baseline | Krumhansl-Kessler major/minor profile correlations on occupied-duration histogram | Diagnostic comparison only; correlation is neither an ensemble vote nor a probability |

The result can be `no_pitched_evidence`, `center_unresolved`, `mode_unresolved`, or `ranked_hypothesis`. A ranked hypothesis is still unvalidated musical interpretation. The `centers` array exposes every tonic even if a small `--top` list happens to contain several modes of the same tonic.

## Reproducible scoring

`engine.py` and the report's `configuration` disclose the complete heuristic. Each channel is independently normalized over 12 pitch classes. Missing channels contribute zero, rather than silently redistributing their weights.

| Channel | Weight |
|---|---:|
| Pitch-class time occupancy | 0.10 |
| Attack positions | 0.04 |
| Metric/accent prominence | 0.08 |
| Bass time occupancy | 0.14 |
| Candidate chord-root duration | 0.14 |
| Ending/rest-arrival pitches | 0.14 |
| Melodic returns | 0.06 |
| Upward semitone destinations | 0.08 |
| Harmonic resolution patterns | 0.22 |

For tonic `t`, `support[t]` is the weighted sum of those channels. Collection membership uses a normalized blend of 0.60 occupancy, 0.25 metric and 0.15 attacks. `fit[t, mode]` is its mass inside the candidate collection, with no penalty for unobserved notes.

```text
center_score[t] = 0.85 * support[t] + 0.15 * best_collection_fit[t]
candidate_score[t, mode] = center_score[t] - 0.20 * (1 - fit[t, mode])
```

A selected center requires at least two observed pitch classes, three attack positions and a leading-center margin of 0.035. Mode stays unresolved unless exactly one mode is within 0.025 of the best fit and that fit is at least 0.90. These are initial, deliberately disclosed engineering thresholds, **not empirically calibrated musical confidence**. The features overlap; they are not independent votes. There is no training or weight fitting in this version.

Exact duplicate complete eligible tracks are collapsed for scoring, with original occurrences retained in `events.json` and duplicate groups reported. Tracks with excluded events are not assumed identical. Coattacked octave/unison duplicates contribute once to attack statistics. Occupancy counts a pitch class once at any instant. Ties retain separate source occurrences, but verified continuations do not create attacks or artificial melodic boundaries.

Source-level observations are computed before window slicing. Window cells have exact overlap witnesses. Transitions may use the immediate preceding source context; such records explicitly carry `uses_preceding_context`, so they are not presented as entirely inside the window.

## Raw-data contract and limitations

- Metadata tracks are index-addressed. All indexed track files and matching identities/revisions are required. Missing/conflicting initial meter fails closed; no 4/4 is invented.
- Fractions remain rational quarter-note units. Songsterr duration fractions already include dot/tuplet duration. Pickups and the explicit whole-measure-rest sentinel receive their own handling.
- Ordinary base pitch is tuning[string] + fret + capo. Drum IDs 1024/128, dead notes, malformed pitch, unsupported transposition settings and untyped non-fretted pitches are excluded.
- Bends, slides, harmonics, whammy and grace events remain in the data with explicit exclusions. This version does not model their sounding pitch. Unknown material cannot become an invented rest or a complete chord.
- Invalid timing preserves occurrences and warnings; affected positions are excluded. An uncertain empty/rest beat also creates a timing barrier even when it has no note event.
- Written durations are not measured acoustic sustain. Let-ring, staccato performance length and instrument decay are not acoustically modeled.
- The written form is analyzed once. Repeat declarations are preserved but playback order is not expanded.
- Some songs have incomplete transcriptions, mixed modes, several centers or no stable center. A 12-tonic/9-collection vocabulary is not a universal model of all musical systems.
- Current source verification independently checks raw occurrences, witnesses, eligible pitches and within-voice accumulation. It uses the adapter's shared bar geometry; it is not a second independent global timing oracle.

This is additive analysis, not a reversible tier. It leaves source files unchanged, supplies no GP inverse and generates no audio. The normalized event file is not a lossless replacement for the entire raw capture. Existing source scores and listening baselines are untouched. Synthetic tests and capture preservation do not establish human musical correctness. An accuracy benchmark needs independent local/global key annotations, ambiguity labels, held-out songs and evaluation of both predictions and abstentions. No such corpus-accuracy or listening claim is made here.

## Files and validation

| File | Responsibility |
|---|---|
| `tonal_analysis/songsterr.py` | Conservative raw-capture adapter |
| `tonal_analysis/engine.py` | Observations, exact chord alternatives, ranking and local analysis |
| `tonal_analysis/examples.py` | Original synthetic examples and invariance transforms |
| `tonal_analysis/cli.py`, `analyze.py` | CLI, source-preservation checks and private output |
| `tests/` | Adversarial source, inference, invariance and subprocess tests |
| `../.github/workflows/tonal-analysis.yml` | Python 3.10/3.12 CI plus demo execution |
| `PROGRESS.md` | Acceptance checklist, commands, actual results and unresolved validation |

Tests distinguish shared pitch collections with different centers; preserve all 108 scores under transposition, exact track duplication and tied subdivision; test dominant pedals, power-chord ambiguity, chromatic notes and section changes; and guard against fabricated notes/chords/arrivals at exclusions and window edges. Source capture runs stay private; public documentation contains aggregate results only.

Theory/research references: [music21 key analysis](https://music21.org/music21docs/usersGuide/usersGuide_15_key.html), [Temperley and de Clercq on harmony/melody in rock](https://davidtemperley.com/wp-content/uploads/2015/11/temperley-declercq-jnmr.pdf), [Open Music Theory on diatonic modes](https://viva.pressbooks.pub/openmusictheory/chapter/diatonic-modes/). This implementation's combined weights and abstention thresholds are our disclosed prototype choices, not values validated by those publications.
