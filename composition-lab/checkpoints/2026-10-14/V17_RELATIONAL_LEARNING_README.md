# V17 — Chord-independent melodic relationship learning

This is the **first implemented layer** of the proposed multi-view architecture, **not** joint probabilistic harmonic inference or full phrase segmentation.

## Changes
- `relational_learning_v17.py` learns intervals between adjacent single-note events across bar boundaries, independently of detected chords.
- Existing chord-relative phrase variations remain highest priority; interval-pattern variation is used when chord-relative patterns are unavailable.
- Existing 0% locks, source GP file and other tracks remain untouched.
- Fixed a V16 integration bug: learned-mode melody strength was being set to 0 when disabling the old per-note random pitch shift.
- The learner produces candidate pitch changes; export still rejects unplayable notes and conflicting reused GP note definitions.

## Chet Baker baseline test
- 275 source-observed melodic windows; 110 distinct interval patterns (sizes 2,3,4).
- Seed 17, melody 100, chords 0, rhythm 0: 8 harmonic phrase attempts + 45 interval-pattern phrases planned, but **only 4 GP note definitions actually changed**; 6 unplayable events rejected and 40 shared note definitions skipped.
- Seed 23: 8 note definitions changed.
- These numbers are planning/GP output metrics, not a musical-quality evaluation.

## Important remaining blockers
1. Reused GPIF note definitions cause conflicting edits; make a safe GPIF clone-and-rewire writer to support independent occurrences.
2. Interval-sequence learning is not harmonic-function preservation. With melody changed, roles may change intentionally; with melody locked, role-preservation still relies on known harmony.
3. No multi-hypothesis joint harmony inference, hierarchical boundary learning, chord-independent polyphonic motif generation, or calibrated similarity distances yet.
4. A requested 100% remains an attempt probability, not measured difference.