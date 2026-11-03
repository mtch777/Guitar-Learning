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

## Composition Lab

Start with [HANDOFF.md](composition-lab/HANDOFF.md), then
[CODEX_CONTEXT.md](composition-lab/CODEX_CONTEXT.md),
[PROJECT_COMPLETION_PLAN.md](composition-lab/PROJECT_COMPLETION_PLAN.md) and
[DEVELOPMENT_OPERATING_RULES.md](composition-lab/DEVELOPMENT_OPERATING_RULES.md).
The plan governs current requirements, acceptance and execution order;
[THEMATIC_RETURN_PROGRESS.md](composition-lab/THEMATIC_RETURN_PROGRESS.md) records
the active implementation contract and next action. The guitar trainer and
Composition Lab are separate features.

Current listening reviews follow
[LISTENING_REVIEW_TEMPLATE.md](composition-lab/LISTENING_REVIEW_TEMPLATE.md): reuse
the existing page and serving URL, preserve the untouched original, show changed
notes and keep four context bars on either side by default.

### Historical checkpoint — 2026-10-14

This checkpoint preserves V13–V24 experiments, tests and review artifacts. Its
milestone labels and next actions do not override the current documents above.

- [Historical handoff: architecture, V24 results and recorded limitations](composition-lab/checkpoints/2026-10-14/HANDOFF_2026-10-14.md)
- [Research checkpoint, source and tests](composition-lab/checkpoints/2026-10-14/)
- [Historical listening review (GitHub Pages)](https://mtch777.github.io/Guitar-Learning/composition-review.html) ([HTML source](composition-review.html))
- [V23 offline review app generator and tests](composition-lab/checkpoints/2026-10-14/v23-review/)
- [V24 source-annotation results and review CSV](composition-lab/checkpoints/2026-10-14/V24_README.md)

**Checkpoint caveat:** Source chord labels and chord-template matches were not verified ground truth; 60 review examples were unlabelled by humans. These historical controls did not establish calibrated musical-distance percentages.
