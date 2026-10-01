# Live lesson pilot recordings — September 30, 2026 (Denver)

23 unmodified Float32 WAV recordings from the user's live pilot, normal picking, all eight strings at frets 0/12/24 except string 7 fret 12. The entire S7/F12 trial is excluded at the user's request because they accidentally plucked another string. Its audio is not present here.

These six-second files include silence before and after the note. Preserve originals; select the intended onset/capture before extracting training features. The manifest contains intended labels, source file hashes, session grouping, and recorded hybrid detections. It intentionally omits device identifiers and does not use predicted labels as training truth.

The session has not been fitted into the deployed model. Keep recordings from this session grouped when splitting future experiments; do not claim a held-out live score after training on these same recordings. The original 384-recording dataset remains separate.

Validation: `node training/check_lesson_pipeline.mjs` checks that the lesson engine reproduces the archived hybrid predictions and capture times for all 23 recordings, and verifies the accidental-pluck trial is absent.
