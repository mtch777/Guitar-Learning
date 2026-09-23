# Model training

## Current retraining dataset

- 8 physical strings
- all frets 0–24 represented
- ringing notes only
- muted recordings excluded
- original anchor frets include soft / normal / hard takes
- newly mapped fret positions include the additional recordings collected across the fretboard
- pitch is used to eliminate physically impossible string/fret positions
- classifier distinguishes the remaining physical candidates from acoustic/timbral features

## Baseline

The current production extractor is the original **107-feature** definition:

- attack: 13 MFCC mean/std + centroid/bandwidth/rolloff/flatness/ZCR statistics
- sustain: same feature family
- 5 amplitude/energy features

This baseline is intentionally preserved so the retraining experiments can measure the value of each new feature family rather than changing everything at once.

## Retraining plan

Run the same candidate-constrained evaluation after each feature addition:

1. 107-feature baseline
2. + explicit H2/H1 through H8/H1
3. + time-resolved harmonics (attack / early sustain / late sustain)
4. + harmonic decay/change features
5. + harmonic peak shape / inharmonicity / surrounding-noise features

Primary validation is **leave-one-pitch-out**. This holds an entire MIDI pitch out of training, then candidate-masks predictions using the tuning and 24-fret physical limits.

Track:

- overall exact physical-string accuracy
- accuracy by number of physically possible candidates
- accuracy by pitch
- accuracy by string/fret
- confidence and confusion for the hardest same-pitch candidate pairs

Amplitude should remain available as weak evidence, not the primary discriminator.

The browser feature extractor must match the final trained model's feature definition and ordering exactly before deployment.
