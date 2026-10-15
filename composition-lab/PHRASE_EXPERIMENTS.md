# Phrase-development experiment 1

This experiment follows private listening feedback from the first ten-sketch
review: role interaction was useful, while statements lacked continuity,
development and resolution. Private annotations remain local.

## Predeclared comparison

For each family, freeze the existing seed-17 `roles-phrases` output. Cross two
factors: (1) shared melodic contour with contracted answer, reversed development
and returning contour; (2) target the final melodic attack of each authored
phrase to a pitch class present in that bar's accompaniment. The four cells are
unchanged baseline, contour only, endings only, and combined. V2 is a fifth
historical reference, **not** a controlled cell (its instrumentation differs).

The spans 3/5/3/5 bars are explicit experimental scaffolding, not learned phrase
boundaries. Transformations reuse the first two generated bars, never commercial
source notes. Octave placement favors the preceding melodic attack. This tests
an authored heuristic, not an external model or learned narrative structure.

All four controlled cells preserve accompaniment exactly, all note counts,
rests, onsets/durations, tuning, programs and form. Thus unequal phrase spans do
not yet change rhythmic breathing. Baseline GP and audio are copied byte for
byte from the previous review. Old review/feedback storage remains intact; the
new dataset uses a different version and independently shuffled sketch order.

## Actual measurements

Mean absolute interval between successive first pitches of melodic attacks:

| Family | Baseline | Contour | Endings | Combined |
|---|---:|---:|---:|---:|
| Cloud | 3.40 | 2.24 | 3.09 | 2.13 |
| Sweet | 10.94 | 2.75 | 10.85 | 2.56 |

Phrase-end first pitches belonging to that bar's accompaniment pitch classes:
Cloud 0/4, 0/4, 4/4, 4/4; Sweet 0/4, 1/4, 4/4, 4/4 respectively.
Melody-note changes: Cloud 0/96, 80/96, 8/96, 82/96; Sweet 0/176,
172/176, 4/176, 168/176. Melody includes polyphonic attacks; the ending metric
concerns its first pitch, not all voices.

Smaller leaps and accompaniment membership are manipulation checks, **not
musical-quality scores**. Smoothing may remove the pitch spread that the first
review liked; ending on accompaniment tones may still lack tonal resolution.
The accompaniment progression and rhythmic repetition remain unchanged.

## Reproduction and validation

`python composition-lab/phrase_experiments.py` creates fresh ignored directories
`local-artifacts/{cloud,sweet}-phrase-experiments` (refuses overwrite). Each holds
GP, canonical expected events and metrics/copying reports. Run `verify_gp.mjs`
with alphaTab on all eight GP files to independently compare exact pitch,
notation timing, tuning/programs, note counts and tracks, and export MIDI.
`python composition-lab/build_phrase_review.py` then packages generated-only
GP/audio/note timelines into `public/composition-phrase-review` (fresh directory).
Baseline/reference copies must match original hashes.

All eight GP files passed independent alphaTab checks. Python suite: 82 passed.
Public copying-window reports compare transformations against their generated
parent locally; intentional motif reuse is expected. This does not establish
originality against commercial sources. A separate check against both private
original scores found 0% exact relative eight-event matches for every Cloud
case; Sweet retained the baseline's 1.3746% against Sweet in all four cells,
and 0% against Cloud. Unchanged accompaniment can retain existing matches.
Use repeated `--reference <private.gp>` arguments to reproduce those checks.
These are two baseline-conditioned
cases, not a new held-out evaluation or a preference estimate.

## Listening gate

Open `composition-ablation-review.html?study=phrases`. Judge blind before reveal:
does a recognizable thread persist without becoming monotonous? Do answers
develop it? Do endings feel earned? Does smoothing flatten useful contrast?
Use notes for timestamps and “Cannot judge” where the preview is insufficient.
No human preferences for this set have yet been collected. This narrow test
precedes changes to rhythm/breathing and learned harmonic/form planning.
