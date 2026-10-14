# V22 — Ground-truth music validation

## Purpose
V21 generated **unlabeled** review candidates. V22 evaluates **human-entered** chord and phrase-boundary labels. It does not pretend automatic chord template matching is accurate ground truth.

## Label workflow
1. Open `V21_human_review.csv` in a spreadsheet. Keep `source_file`, `track_index`, and `onset_q` intact: together they uniquely identify the sampled attack.
2. Listen to the song or inspect the Guitar Pro score **with surrounding bars and other relevant instruments**; the candidate MIDI list alone is insufficient to determine harmonic context.
3. Fill `human_chord_label` with a confident chord label, e.g. `D minor`, `F major7`, `G dom7`, including slash bass if understood. Use `unknown` when there is not enough musical evidence. Do **not** copy model predictions as answers.
4. Fill `human_phrase_boundary` with `yes`, `no`, or `unknown`, meaning **a new musical phrase begins at this onset**. A section start is not automatically a phrase start.
5. Keep `human_chord_confidence` and `human_notes` for your audit trail. Ideally have a second independent reviewer label overlapping examples; adjudicate disagreements before using them as a reference set.
6. Run `python reference_validation_v22.py V21_human_review.csv --out V22_scored_review.json`.

## Scoring rules
- Only explicit human labels count. Missing/unknown labels are excluded; null accuracy means no labeled samples, not failure.
- Chord top-1 match compares pitch-class root plus chord quality. Enharmonic roots normalize (Db = C#), chord quality must agree. Existing model output does not have a reliable complete inversion representation, so slash bass is **not scored separately** in V22.
- Phrase boundary precision/recall/F1 are calculated only where a reviewer entered `yes` or `no`.
- The 60 examples were intentionally sampled across confidence/boundary groups, not at random from all musical events. Metrics apply only to reviewed examples, not to an entire song or corpus.
- Predicted probabilities are uncalibrated; the optional score-bin table is descriptive only and not a confidence calibration claim.

## Next engineering steps
Implement review playback with bar-level multi-track context, independent reviewer IDs, disagreement adjudication, and an immutable held-out split before tuning chord and phrase scorers. Expand annotation coverage across roles and genres; avoid automatically labeling unreviewed predictions as truth.

## Reproducibility
Code: `reference_validation_v22.py` and `test_reference_validation_v22.py`.
Baseline: `V22_review_baseline.json` (60 valid rows, **zero** chord/phrase labels; accuracy null).
Tests: 90/90 unittest suite passing locally on 2026-10-14.