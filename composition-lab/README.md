# Composition Lab — isolated Guitar Pro composition research

**Scope:** Guitar Pro (.gp) input → music analysis → guitarist-style composition → new Guitar Pro (.gp) output.

This is an **independent Python project** inside Guitar-Learning. It does not import from or modify `src/`, `training/`, the guitar trainer, the audio ML pipeline, or the web app. Python standard library only for the current compatibility tests.

## Phase 1: GP7 archive compatibility

Modern `.gp` files supplied for this project are GP7 ZIP archives containing `VERSION` and `Content/score.gpif`. `gp_io.py` currently:

- checks a file's container/version and parses its GPIF XML;
- reports count of tracks, master bars, notes, beats, and track names;
- writes a **lossless archive round-trip** to another `.gp` file;
- verifies *every* original ZIP member has exactly the same uncompressed bytes in the output.

Run from the `composition-lab/` directory:

```bash
python gp_io.py inspect "song1.gp" "song2.gp"
python gp_io.py roundtrip "song1.gp" "roundtrip.gp"
python -m unittest discover -s . -p 'test_*.py' -v
```

**Important distinction:** This verifies archive reconstruction, NOT authoring new musical notes. Exact score-data preservation is a prerequisite only. The output may not be byte-for-byte the same ZIP because compression metadata can differ. A separate GP7 score-writing implementation and an alphaTab/Guitar Pro open-and-render test are required before claiming editable new composition support.

## Development plan

1. **GP file compatibility**: archive inspection and lossless repackaging (first milestone); then validate with Guitar Pro and alphaTab.
2. **Semantic GPIF reading/writing**: extract and reconstruct linked tracks, measures, voices, beats, rhythms, notes, tunings and techniques. Verify score round-trip after reserialization; reject unsupported features rather than drop them silently.
3. **Style analysis**: rhythmic patterns, melodic intervals, riff/motif reuse, techniques, fretboard choices and song structure.
4. **Generator**: 16-bar original guitar composition conditioned on learned style; use guitar-playability and timing constraints.
5. **Evaluation**: compare to held-out music and generic baseline; test novelty, structural coherence, valid export and human-listening impressions.

Source songs remain local/test inputs and are **not committed** to the repository by default. The three initial test songs are Cloud Cascade, Nocturne: Lost Faith and Immolation of Night.
