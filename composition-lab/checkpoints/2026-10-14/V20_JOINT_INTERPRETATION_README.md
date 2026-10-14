# V20 — Coupled harmony/phrase evidence (experimental)

This is **not** a fully trained joint probabilistic model. It is an opt-in analysis/refinement layer. Raw GP observations stay unchanged, exact candidate-chord labels remain mandatory for destructive reharmonization, and uncertain notes remain available for interval learning.

## Implementation
- `joint_interpretation_v20.py` collects sounding pitch classes at note attacks, including sustaining notes and concurrent voices; ranks chord alternatives using the existing expanded shared `CHORDS` vocabulary, with forward/backward temporal smoothing; keeps probabilities as hypotheses (not verified confidence calibration).
- Phrase-boundary evidence joins V19 rest/jump/section gesture starts, repeated interval+duration motifs, and differences between adjacent **independently verified** chord sonorities. Broad chord posteriors cannot by themselves assert changes. Scores are heuristics, not probability-calibrated boundaries.
- `joint_phrase_windows` splits V19 candidate gestures on strong combined evidence and emits compatible variable-length training windows; melody learning remains usable without identified chords.
- `relational_learning_v17.py` supports opt-in `joint=True` in `observed_windows`, `learn_relations`, and `plan_intervals`.
- `gp_similarity_export.py` supports opt-in `joint=True` (`--joint` CLI) with learned mode. Default V19 behavior remains unchanged; zero-strength stays a byte-identical file copy.

## Validation (2026-10-14)
- 79/79 local regression/unit tests passed.
- Chet Baker (track 0): 248 observed attacks; 97 verified chord sonorities; 151 unresolved; 40 motif-supported boundary points; 35 adjacent verified harmonic changes; 23 candidate boundary points; joint learner 344 windows (vs. V19 387); melody-only export changed 97 note occurrences. Note this is not a claim of better perceptual phrase segmentation.
- Sweet Child (first pitched track, vocal/sax): 401 attacks; 1 verified sonority, 400 unresolved. This does **not** validate guitar harmony accuracy; select an intended instrument track for meaningful evaluation.
- Cloud Cascade (first pitched track): 285 attacks; 32 verified sonorities, 253 unresolved.
- No ground-truth chord/phrase annotations yet. No measured improvement in chord identification, only additional connected interpretation and control-respecting GP output.

## Limitations / next
- Temporal probabilities use finite candidate sets and a generic continuity penalty, not corpus-trained transition probabilities. Confidence is not calibrated.
- Candidate partial/rootless chords are retained as hypotheses, not promoted to verified chord identities.
- Independent note attacks and repeated motifs supply evidence but accompaniment or multi-track harmony still needs explicit voice/instrument-role selection and annotation.
- Evaluation next needs manually annotated examples and recall/precision of boundary and chord identification.