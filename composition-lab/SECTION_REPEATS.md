# Bar-level repeated passage pilot

Scope: discover repeated passage candidates across a song using actual source bars, independently of riff boundaries. No verse/chorus labels, production integration, full-corpus processing, or invented chord labels.

## API
`build_bar_features(bars, notes, channels, pitch_notes=None, harmony=None)` accepts tie-merged original attacks and optionally existing technique-aware pitch projection and bar-harmony rows. It reads no files and changes no input. `analyze_repeats(features)` returns paired source-bar ranges, complete-link occurrence groups, separate feature scores, adjacent-bar boundary novelty and uncertainty diagnostics. Coordinates describe the written source; explicit repeat playback is separate metadata, not independent recurrence evidence.

Five adjustable similarity weights: rhythm .30, pitch .25, local contour .15, harmony .15, arrangement .15. Available dimensions are renormalized. Scores are not confidence probabilities. Channel coverage and unknown pitch mass accompany scores; a score of 1 with partial data is not full identity. Exact observed identity is a separate flag and excludes unknown pitch.

Defaults: .82 match threshold, .55 per-bar floor, one weak internal bar allowed, minimum one bar. No fixed maximum length or 4/8-bar assumption. Strong endpoints anchor the matched core; an eligible weaker following bar is exposed as an ending-variation alternative, not silently omitted. Contained matches on the same diagonal collapse. Each paired occurrence is nonoverlapping. Occurrence groups require every pair to match. Internal repetition of at least two cycles is flagged as motif/loop evidence, not proof of song function.

## Checks and results
Run `python -B -m unittest test_section_repeats` from this folder. Synthetic checks cover unusual lengths/meters, order, silence, unknown pitch, note sustain vs attack, added channels, changed endings, pedal/accompaniment false identity, mixed harmony bases and no mutation.

Pilot: three rounds of three newly randomly chosen Invent Animate captures; frozen selection seed 2026111601. All nine rechecked after review fixes, with .78/.82/.86 sensitivity. Local corpus outputs stay outside git. Source original-pitch timing, existing technique-aware projection, tonal estimator and bar-harmony analyzer reused. No user session changed.

## Boundaries and limits
This is a repeat-candidate layer, not final structural segmentation. Overlapping alternatives remain and short motifs are retained explicitly. Similarity thresholds are engineering settings, not calibrated accuracy. Local contour does not establish constant transposition across a passage. Inserted/deleted bars, shifted sub-bar material and melodic reassignment between channels are not aligned. Track IDs are song-local; channels are compared within the same song. No ground-truth structural labels or accuracy percentage is claimed. Fresh songs are separate captures, not guaranteed independent compositions (alternate versions exist).

## Problems caught in iteration
- Source population used capture_artist, not artist; corrected metadata adapter.
- False periodicity when only first/last bars matched; require two full cycles.
- Sustains mistakenly omitted from attack comparison; known zero attacks now differ from reattacks.
- Candidate chord-root vectors compared against pitch-duration fallback; mixed bases now unavailable.
- Partial-pitch exactness and differing channel coverage now explicit.
