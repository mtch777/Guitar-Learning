# V19 — Evidence-based candidate gesture discovery

Changes:
- `phrase_discovery_v19.py`: score-event-based segmentation using rests, silence, pitch discontinuity, explicitly marked section starts, and ties. Crosses measures when evidence supports continuity; no chord label required.
- `relational_learning_v17.py`: uses variable-length training windows (2–8 events) inside inferred gesture boundaries instead of fixed 2–4-event windows crossing all boundaries.
- `test_phrase_discovery_v19.py`: eight targeted boundary, exact-time, validation, and no-chord tests.

Chet Baker track 0: 50 candidate gesture segments, 387 eligible learned windows, 202 distinct interval patterns, 109 changed note occurrences in a melody-only GP export (seed 17). Total local tests: 68/68.

IMPORTANT: These are candidate gestures, not reliably discovered human musical phrases. 2–8 is a training window length, not a fixed phrase length. There is no joint probabilistic harmony/phrase inference, no learned rhythmic phrase boundary model, and variation percentage is still stochastic probability, not calibrated musical distance. Transforms preserve exact rhythmic timing when the rhythm control is zero. Existing GP writer and all other repository code are unchanged.