# V14: independent similarity-control groundwork

`similarity_controls.py` introduces three independently settable controls (`chords`, `melody`, and `rhythm`), each in the range 0–100.

- **0:** exact lock. Source chords, source harmonic-relative melody, and/or original onset and duration are preserved, as applicable.
- **Above 0:** probability of attempting an allowed transformation—not a calibrated measure of musical difference.
- **Chord changes:** use supplied/observed chords, changing roots or qualities while remapping note pitches to retain verified chord-degree function and octave displacement.
- **Melody changes:** currently semitone-offset variants, configurable by caller. **Not yet an expressive, learned melody generator.**
- **Rhythm changes:** currently caller-supplied onset/duration variants, preserving exact fractions and rejecting shifts outside the source harmonic window. **Not yet a learned rhythm generator.**
- **No chord evidence:** notes are not arbitrarily assigned a chord. Unsupported cases are counted.
- **Safety:** unknown harmony is not fabricated; conflicting rhythm shifts are reported; metadata is carried through.

This is a **symbolic event transformation layer**, not yet integrated into GP export or user-facing sliders. Existing GP reharmonization remains in `automatic_harmony_control.py`. No claims of fully independent full-song arrangement reconstruction should be made at this stage.

Run: `python -m unittest discover -p 'test_*.py' -q` from the checkpoint directory. Validation here: 40 tests passed.