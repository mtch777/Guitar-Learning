> Superseded analysis: see MUSICAL_FIELDS_RESULTS.md for v2. Historical v1 raw bend semitone labels were doubled; GP conversion/audio was unaffected. Preserve these historical measurements as v1.

# Source-grounded relational analysis

The analyzer reads cached Songsterr notation directly. It does not infer labels with AI, train a model, or modify the acquired GP files.

## What is implemented

- Revision-level provenance; separate AI/junk cohorts with no silent exclusions. Artist summaries use the exact supplied artist label, not an assumed identity for collaborations or adaptations.
- Exact representation hashes and conservative title-family candidates. Neither is proof of independent compositions. Provisional development/held-out partitions keep connected candidate families and exact duplicates together; no held-out prediction accuracy is claimed.
- Corpus, artist-label, song, track and source-section-instance summaries. Marker percentages explicitly use regular written note segments; note attacks are reported separately. Repeated section names retain separate instances.
- Marked/unmarked comparisons for written duration, relative register, bar-start placement and the next monophonic attack interval in the same voice. Polyphony, unknown pitches and section crossings leave that interval unknown. The interval describes written base pitches, not a harmonic resolution judgment.
- Pairwise marker co-occurrence and technique placement in section quartiles. Section positions are not phrase boundaries. Register is relative to the scope being summarized, not a fixed pitch cutoff.
- Coattack groups across voices within a track, excluding tied continuations. Shared chord definitions require distinct strings: exactly one semitone for close texture, root/fifth pitch classes only for power chords, and exactly one additional color pitch class for extended power chords. They describe written pitches, not bend-adjusted sounding harmony. Sustained sonorities remain outside this analyzer's classification scope.
- Contiguous same-string source-`hp` transition candidates, with direction, open-string context and fret distance. The origin-marker interpretation follows the pinned upstream converter's GP convention. It is not independently adjudicated technique truth. Ties extend eligibility, gaps/grace/unknown pitch block it.
- Existing pedal-burst detector applied to raw notation, with source-derived burst lengths. Overlapping windows remain candidates, not independent phrases or verified call-and-response.
- Private source-located examples, whole-step counterexamples, duration-matched unmarked controls and exact raw-note/beat readback verification. The evidence pack contains no authored listening substitutes.

## Fidelity and interpretation limits

Written notation is the observation. Missing markers do not prove a performer omitted a technique. Bend/vibrato annotation does not establish performed emotional purpose, physical vibrato rate or timing. Counts are score order; repeat playback is not expanded. Duration comparisons are written note segments, not tied gesture lengths. Provisional title families need adjudication; catalog flags do not establish transcription accuracy. Pooled note-weighted, equal-song and candidate-family-balanced rates answer different questions; none estimates the artist's entire catalog.

Malformed or overflowing source timing is reported. Affected tracks retain raw notes and marker counts but are conservatively excluded from temporal relationship candidates. Timing is not silently repaired. Existing GP conversion warnings remain in the acquisition reports: this analysis does not repair unsupported GP bend/whammy curves.

## Reproduction

From the repository root, using the isolated corpus Python environment:

```powershell
.\.local\songsterr-venv\Scripts\python.exe composition-lab/songsterr_automation/songsterr_api/analyze_relationships.py composition-lab/local-artifacts/invent-animate-corpus-v1/songs --out composition-lab/local-artifacts/invent-animate-corpus-v1/relationships.json --aggregate composition-lab/songsterr_automation/results/corpus_relationships.json
.\.local\songsterr-venv\Scripts\python.exe composition-lab/songsterr_automation/songsterr_api/build_analysis_evidence.py composition-lab/local-artifacts/invent-animate-corpus-v1 --aggregate composition-lab/songsterr_automation/results/corpus_relationships.json
```

Private outputs: `relationships.json` (full observations/relationships), `ANALYSIS.md` (readable index), `analysis-evidence.json` (source context/controls). Only the source-free aggregate JSON is committed.

Next musical gate: inspect genuine source passages and resolve ambiguous annotations before using these distributions to condition generation. Exact recreation, controlled contextual transfer and creative generation require separate export/constraint tests and listening evidence; this analysis does not mark those gates passed.

## Verified run — 2026-10-17

- 98 entries / 495 tracks / 415 guitar-bass tracks. Counts reconcile independently with the earlier raw inventory: 339,385 regular written note segments and 316,030 attacks.
- 11 AI-flagged and 4 junk-flagged entries; both flags remain provenance, not accuracy judgments. Eighteen candidate title families span 42 entries; no identical complete notation hashes were found. Different hashes do not prove independent compositions.
- 55 overflowing voice/bar observations across 25 tracks, including 20 guitar/bass tracks. All remain in notation summaries; temporal relationship candidates exclude those tracks conservatively.
- On eligible tracks: 28,187 double-stop groups, 2,933 exact half-step dyads, 17,683 power-chord groups and 11,091 extended-power-chord groups. Labels overlap. These differ from the first inventory because this analyzer excludes tied continuations from coattacks, combines voices, and quarantines timing conflicts.
- 2,937 from-open hammer-on and 1,961 to-open pull-off transition candidates; 2,891 fretted hammer-on and 1,918 fretted pull-off candidates. Eight marked transitions remain unresolved because of timing gaps/overlaps. Fretted HOPO observations are retained for analysis, without reviving the rejected MIDI listening exercise.
- 29,447 overlapping pedal-burst candidates, not independent phrases or verified pedal roles. Thirty-seven retained whole-step near-miss examples challenge the half-step classifier.
- Private evidence pack: 88 examples across 31 labels; 2,904 contextual/control occurrences checked against raw source note and beat fields. Rare eligible markers have fewer than three distinct candidate families. Selected examples and self-consistency tests do not measure identification accuracy.
- Descriptive pooled duration result: bend-marked segments average 0.801 quarter beats vs 0.468 unmarked; HP-marked segments 0.268 vs 0.475 unmarked. These are written-segment associations, confounded by song/track/section and notation coverage, not causal or listening claims.
- Raw-value summaries include slide/harmonic/accent values, explicit velocity without imputation, and exact bend initial/peak/final displacement and first-peak segment fraction. Bend units follow the pinned upstream interpretation: tone/25 semitones and position/60 of the written segment; no integer rounding or performed-speed inference. Peak values include zero and up to eight semitones, so marker totals must not be mistaken for verified performed bends.

Verification commands/results:

- `python -m unittest discover -s composition-lab -p 'test_*.py' -q` in the main venv: **183 tests, 182 passed, 1 optional PyGuitarPro skip**.
- Same corpus-specific discovery with `-p 'test_songsterr*.py'` in the isolated Python3.13/PyGuitarPro environment: **14 passed**, including the optional eight-string serialization test.
- Native Node `--test` over `tests/*.test.mjs`: **16 passed**.
- Native Node `node_modules/vite/bin/vite.js build`: **passed**. `npm` was absent from the shell PATH; direct Vite invocation used the installed runtime.
- Corpus analyzer and evidence builder completed with exit0; aggregate totals reconciled against the earlier independent inventory. Evidence builder uses `--aggregate composition-lab/songsterr_automation/results/corpus_relationships.json` to persist source-free validation counts.
- Windows sandbox temp-directory creation initially failed; rerunning tests with TEMP/TMP set to ignored `.local/test-temp` succeeded. No source mutation or baseline regeneration occurred.

No public website files changed; Pages deployment is outside this change. GitHub CI delivery is recorded in ANALYSIS_PROGRESS.md.
