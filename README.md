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
