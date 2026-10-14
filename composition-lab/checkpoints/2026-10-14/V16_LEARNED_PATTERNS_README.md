# V16: source-derived phrase substitutions (experimental)

`gp_similarity_export.py --learned` enables phrase-level substitutions sampled from observed GP events rather than V15's hardcoded pitch offsets and duration swaps.

- Melody: learns chord-relative note-role / octave sequences spanning 2–4 consecutive events. Requires an unambiguous chord at every event onset; maps roles to each **target** chord. Never guesses a chord where none is known. Fretted results must be playable and GP note definitions must be safely editable.
- Rhythm: learns 2–4-event duration sequences from source measures, then substitutes only sequences with identical event count, note cardinality/rest signature and exact total duration. A candidate is rejected if any moved event changes its inferred chord-window association. GP beat definitions must be unique across the whole score.
- 0% lock: passes through to identical GP bytes if all controls are zero; melody 0 and rhythm 0 protect those symbolic dimensions independently.
- Nonzero percentages: **sampling attempt probabilities**, not calibrated perceptual distances or guarantees of change.
- No genre-specific assumptions; note articulation, parallel voices, and track routing preserved.

## Reproduction

`python gp_similarity_export.py '/mnt/data/Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp' --output /mnt/data/Chet_Baker_V16_rhythm.gp --rhythm 100 --learned`

`python -m unittest discover -q` in the source directory; 52 local tests pass.

## Real file result

Chet Baker: 6 learned rhythm substitutions; 0 learned melody substitutions. This is **not** proof of complete melodic-learning functionality on real music. Its chord detector does not provide sufficient consecutive event-level harmonic evidence in this source. The melody transformer is exercised on explicit synthetic chord-annotated phrases. Next improvement should infer robust passage harmony, or accept an explicit chord track/lead sheet, then evaluate learned melody on unseen full GP songs.

The source score is not overwritten. This is an additive experimental V16 checkpoint; existing V15 `--learned`-off behavior remains.