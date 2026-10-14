# V21 — music-interpretation validation baseline

This is an **evaluation harness**, not a claim that chord or phrase accuracy has been verified. It operates on the first 20 measures of five source scores, automatically choosing the pitched track with the most events (recording its actual identity).

## What is actually measured
- Attack count and the share of sonorities that exactly match a unique chord template. A template match is **NOT** a verified chord.
- Fraction of explicitly labeled GP section starts, *when coincident with attacks*, also detected as a candidate boundary. Section starts are an **imperfect positive-only proxy** for phrase boundaries.
- Model-hypothesis scores and unresolved passages; the scores have NOT been calibrated to empirical accuracy.
- A balanced 60-row sample for manual chord/phrase labeling. Review fields are deliberately blank; neither correctness nor precision/recall against true human phrases can be stated yet.

## Evaluation across first 20 measures

| Score | Attacks | Exact-template matches | Section-start boundary proxy (at attacks) |
|---|---:|---:|---:|
| Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp | 126 | 48 | 0/1 |
| Sweet Child O' Mine.gp | 160 | 0 | 2/2 |
| Cloud Cascade (Tuned Down).gp | 137 | 10 | 0/1 |
| Nocturne_ Lost Faith (Tuned Down).gp | 216 | 56 | 0/2 |
| Immolation of Night (Tuned Down).gp | 128 | 0 | 1/1 |

## Next
1. Open `V21_human_review.csv` and label chords and phrase boundaries while listening to the source. Blank labels are not negatives.
2. Evaluate precision/recall on these reviewed examples with explicit criteria, then expand the reviewed corpus.
3. Compare parameter ablations and instruments under held-out files to avoid overfitting these five scores.
4. Fix mistaken labels/segmentation only after measurable failure modes are known.

## Reproduction
`python evaluate_v21.py <input1.gp> ... --out-dir output_dir --max-measures 20 --samples 12`

Requires the V20 checkpoint's `extract.py`, `joint_interpretation_v20.py`, etc. All prior V20 generation code is unchanged.