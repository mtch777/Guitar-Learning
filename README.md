# Guitar Learning

8-string guitar learning ecosystem.

## Current architecture

- `src/guitar/` — shared tuning, notes, fret/string calculations
- `src/audio/` — microphone, pitch detection, feature extraction
- `src/classifier/` — physical-string classifier and candidate masking
- `src/lessons/` — interval and 2/3-NPS lesson logic
- `src/input/` — fretboard-click and live-guitar input adapters
- `src/ui/` — browser UI
- `training/` — Python training/evaluation/export pipeline
- `legacy/codepen/` — references to the original prototypes

## Source prototypes

- Interval & 2/3 NPS: https://codepen.io/mtch77/pen/KwWamLQ
- Audio/string detector: https://codepen.io/mtch77/pen/VYpmrxW

## Classifier MVP

Live pipeline:

microphone → pitch → candidate strings → audio features → ringing-only classifier → physical string → fret

Muted recordings are excluded from the current MVP.

## Songsterr tonal analysis

[Independent key/mode analysis, CLI and tests](tonal-analysis/README.md): ranks tonal centers and collections from raw Songsterr captures using pitch, harmony, bass, melody and timing evidence. Reports ambiguous results and local changes; keeps private source-derived reports out of Git. This is a separate research tool with uncalibrated heuristic scores.

## Composition Lab — current handoff (2026-10-14)

- [Handoff: architecture, latest V24 results, limitations, next steps](composition-lab/checkpoints/2026-10-14/HANDOFF_2026-10-14.md)
- [Research checkpoint, source and tests](composition-lab/checkpoints/2026-10-14/)
- [Listening review (GitHub Pages)](https://mtch777.github.io/Guitar-Learning/composition-review.html) ([HTML source](composition-review.html))
- [V23 offline review app generator and tests](composition-lab/checkpoints/2026-10-14/v23-review/)
- [V24 source-annotation results and review CSV](composition-lab/checkpoints/2026-10-14/V24_README.md)

**Research caveat:** Source chord labels and chord-template matches are not verified ground truth; 60 review examples are unlabelled by humans. Similarity controls above zero are not yet calibrated musical-distance percentages. The trainer and research composition engine are separate features.
