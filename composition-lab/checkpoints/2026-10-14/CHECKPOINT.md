# Composition Lab — reproducible checkpoint (2026-10-14)

This is an additive checkpoint of the local GP analysis, exact fractional rhythmic timing, learned sequence and structure generation, chord-relative melody transformation, expanded chord vocabulary, harmonic continuity, and conservative contextual inference. Original composition-lab files remain untouched.

## Run tests
`python -m unittest discover -s . -p "test_*.py"`

## Known limitations
- Some GP features remain unsupported; automatic chord inference is uncertain.
- Contextual inference deliberately refuses ambiguous incomplete/rootless voicings; the Chet Baker experiment found no extra qualifying cases.
- Reharmonization is a conservative prototype, not a calibrated 0–100% similarity control.
- The generation model has not passed comprehensive human listening validation.

## Source
Files were copied from the locally tested Step10_Exact_Timing and harmonic_continuity versions, with the newest contextual harmony code taking precedence. This directory is a snapshot, not a replacement of production code.