# V15 — Guitar Pro similarity-controls export

`gp_similarity_export.py` connects V14 independent chord/melody/rhythm controls to a GP7 `.gp` writer using the original file's GPIF score as source. It preserves existing song structure, voices, tracks, and unknown note properties.

Run:

```bash
python gp_similarity_export.py source.gp --output result.gp --track 0 --chords 100 --melody 0 --rhythm 0 --seed 17
```

- `0` is an exact lock: all three controls at zero copy the source file byte-for-byte.
- Chords are selected from harmonies confidently observed in the score, retaining chord-relative role and octave of affected notes.
- Melody currently uses semitone offsets from V14; **these are basic, not yet corpus-learned alternatives**.
- Rhythm changes are limited to adjacent beats in the same measure/voice, with different durations, no ties, unique beat definitions, and a single sufficiently supported harmonic window. Swapping durations preserves measure length, but does not generate arbitrary onset/duration changes.
- Candidate pitch changes are applied only if playable on the guitar and if every occurrence of a shared GP note definition agrees. Unsupported notes, ambiguous chords and unplayable edits are preserved.
- Percentages over zero are probabilities of variation, **not measured distances**.
- This is a command-line export pipeline, not the browser Song Player UI.

Validation: `python -m unittest discover -p 'test_*.py' -q` from the checkpoint folder; V15 local run: 47 passed including seven GP exporter tests.

Chet Baker illustrative run (track index 0, seed 17): chord-only 45 changed note definitions; melody-only 52; rhythm-only 2 safe beat-duration exchanges; combined (100/70/80) 46 changed definitions and 2 exchanges. These counts do not measure musical similarity.