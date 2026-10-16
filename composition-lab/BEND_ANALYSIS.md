# Scripted bend analysis

No model inference or AI-assigned musical labels. Private scores and occurrence reports stay outside Git.

Acceptance checklist:
- [x] Read the supplied Time GP archive; record its hash and extraction validation.
- [x] Count note occurrences separately from attacks; report track denominators, encoded sections, bend shapes and rational timing.
- [x] Query local relationships and expose heuristic rest-gap grouping with sensitivity thresholds, without claiming musical phrase truth.
- [x] Test bend decoding, tie handling and contextual denominators; run relevant regression tests.
- [x] Run the actual file, inspect results, preserve private JSON and publish only code and source-free findings.

Definition: GPIF bend values / 50 are semitones (alphaTab GPIF parser uses /25 quarter tones). Offsets /100 are fractions of the notated segment. They are notation, not measured performance timing. A bend-bearing tied destination is an occurrence but not a new attack. Duration summaries below use notated segments unless explicitly called a tie-chain duration. Track names and section labels come from the file, not role inference. Rest-gap groups are sensitivity probes, not adjudicated phrases. No artist-wide estimate is possible from one song.

## 2026-10-16 test results

Command: `.venv/Scripts/python.exe composition-lab/bend_analysis.py C:/Users/User/Downloads/time.gp --output composition-lab/local-artifacts/time-bends/report.json`.

Source SHA256: `bd656f927c89b00fbc366b8659879d606937e4ff33fef60367023802c53aa89b`. 209 written bars, 15 tracks, 6,442 note occurrences, 5,520 attacks, no voice/meter discrepancies. Independent alphaTab 1.8.4 import agrees with occurrence, attack and bend-segment counts on every track. No unresolved explicit tie destinations or unmatched origins.

- Source-named guitar-solo track: 204 segments, 153 attacks, 69 bend-flagged segments. 36 attacks start with a bend annotation, but **37 sustained notes contain a bend somewhere in their tied chain (24.183%)**. This distinction prevents losing delayed bends.
- Median bent sustain: 2 quarter beats; unbent: 2/3 quarter beat. Bent sustains account for 44.365% of this track's summed notated note-time, including the entire bent sustain, not just active pitch movement.
- Peak displacement per bent sustain: 24 at two semitones, seven at one, three at three, two at one-half, one at one-and-one-half. Peaks are relative to the written base pitch, not necessarily excursion from a pre-bent starting position.
- All solo-track bend segments occur within source section Guitar Solo, bars 96–138 (section begins bar 95). Rhythm-guitar track: 14/1,099 sustains contain bends (1.274%). Vocal track: 25/277 (9.025%); do not conflate vocal pitch notation with guitar technique.
- No vibrato XML tags found. Solo track has no explicit rest events and no gap qualifying under 1/2, 1 or 2 quarter-beat thresholds. Therefore this score cannot establish the previously proposed bend-to-silence/phrase-ending hypothesis using rest gaps. No AI labels substituted.
- Conditional tables retain bend and nonbend denominators by pitch, string, fret, onset within bar and duration. Neighboring groups and complete occurrence IDs remain private in JSON. Musical phrase boundaries, chord-relative resolution, fast/slow performance labels and artist-wide rates remain unestablished.

Private reports: `composition-lab/local-artifacts/time-bends/report.json` and `report.md`; source remains in Downloads. No source notes or per-occurrence report committed.

Verification: 112 Python tests pass (including six new bend tests); 16 JS tests pass; Vite build passes. Initial import-path collision exposed two different historical extractors; resolved using an isolated package namespace, then reran actual CLI and suite. No website files changed, so this task does not trigger a new Pages deployment.

Next: add explicit phrase/harmony annotations or independently validated deterministic estimators before testing their relationships to bends; run the same queries over additional authorized artist scores for corpus-level distributions. No learned or model-inferred relationships claimed here.
