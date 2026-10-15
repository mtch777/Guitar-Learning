# Audible phrase passages

The first pitch-only experiment was reported too subtle to judge. No forced preference is inferred. This follow-up intentionally changes more dimensions and presents short labelled before/after comparisons rather than another blind full-sketch battery.

## Design

Four passages: Cloud and Sweet bars 1-4 and 13-16 (8 seconds each at the fixed 120 BPM generation tempo). A is the same earlier roles/motif baseline. B offers two choices: rhythm/breathing using pitches from that lead; or rhythm plus shared-contour development, inversion/contraction across sections and held accompaniment-tone answers. Both retain rhythm-guitar and bass events exactly. The second also reduces the lead to one note per attack, so changes in polyphony are a confound, not attributed solely to phrase understanding. The rhythm-only variant resamples existing local chord events onto the authored rhythm grid; it does not preserve their original order/counts exactly.

Explicit authored 4/4 patterns include pickups, gaps, variable attack durations and longer answers. They are demonstration hypotheses, not learned boundaries or a solution to genre-agnostic composition. Original generated 16-bar scores are preserved; source songs and private feedback are not published. All 12 full/solo GP files passed alphaTab pitch/timing/tuning/program checks and MIDI export. Developed lead counts are 60 notes per family versus baseline 96/176. More/less notes are not quality scores.

## Audio and review

`phrase_passages.py` creates fresh ignored per-family directories. Independently verify/export MIDI with `verify_gp.mjs`, then `build_passage_review.py` writes the generated-only public package. The renderer undoes independent peak normalization and applies one common gain across conditions per family/mode, then slices exact 8-second clips. Solo and full modes have different common gains; compare A/B within a mode. No per-excerpt normalization. Downloaded GP files contain the full 16 bars, including separate lead-only exports.

Review allows synchronized A/B switching and solo/full selection, loop, separate passage/experiment feedback and export. Browser autoplay restrictions may require pressing Play after changing mode. Feedback includes difference audibility, preference, connecting thread and breathing/endings. This review is labelled, not blind; it is for diagnosing perceptibility and mechanism before estimating preference. Older review storage is unchanged; QA uses a separate namespace. No listening quality claim has been made.

Regression: 84 source-free Python tests, 10 JS tests and production build passed. Media hashes and 8-second PCM lengths verified. Human audibility and musical judgments remain open. This narrows the comparison; it does not establish originality or held-out generalization.
