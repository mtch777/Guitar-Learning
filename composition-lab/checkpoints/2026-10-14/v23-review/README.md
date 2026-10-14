# V23 — Offline listening-based musical review

Open **V23_Music_Review_Player.html** in a browser. It contains all 60 V21/V22 review samples and symbolic surrounding parts from the five `.gp` scores. No server or internet required.

## Controls
- Previous/Next review case; listen to all parts or the selected track; adjustable tempo (default **100 BPM**, not extracted original tempo) and context length.
- Piano-roll display of nearby note pitches from all GP tracks. Gold line marks the reviewed attack.
- Write an independent chord label (`D minor7`, etc.), chord certainty, phrase-boundary yes/no/unknown, and notes. Predictions are hidden until deliberately revealed.
- Judgments persist locally in the browser when storage is available; **Export V22-compatible CSV** to keep an independent durable copy.

## Playback limitations
Web Audio plays synthesized pitches/durations, not original guitar tone or source recording. It does not reproduce GP tempo changes, dynamics, tuning bends, articulations, palm mutes, drum samples, or original mixing. The UI is for symbolic musical context and preliminary listening review, not a high-fidelity rendering or professionally verified transcription. Other tracks may contain notes that are not directly relevant to harmony.

## Evaluate
Run the existing `reference_validation_v22.py` on the downloaded CSV. Blank/unknown answers do not count as correct or incorrect. All 60 cases initially have **no human labels**.

## Rebuild from original scores
Place this folder's `build_review.py` and `player_template.html` alongside your composition-lab Python modules (`extract.py`, `music_events.py`), then run:

```
python build_review.py --source-dir /path/to/GP/scores --review-csv V21_human_review.csv
```

Requires Python standard library and the project `extract.py`/`music_events.py` only. No third-party frontend packages.

## Tests
`python -m unittest test_review_player.py` verifies all case IDs, track+onset mapping, V22 evaluator compatibility, embedded player data, and JS syntax (requires Node.js for the syntax test). Original GP files are necessary to rerun generation tests.

## Accuracy claim
Seven tests passed locally. Browser interaction/playback have not been independently tested in a graphical browser here. No human labels have been collected, so chord and boundary accuracy remain unknown.