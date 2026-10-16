# Reference-freedom levers

Current user contract supersedes older difference-target proposals: 0 means literal lock; 100 means no direct reference values for the unlocked feature, not maximum difference. Intermediate values control reference preference, not a promised perceptual distance. Performance and arrangement are separate.

Acceptance checklist:
- [x] Shared, fail-closed GP property edit boundary; archive/locked data verified.
- [x] Bend lever: 0 produces byte-identical GP; 100 proposals invariant to hidden reference bends.
- [x] Deterministic method/strength comparisons on actual Time score; all other score data locked.
- [x] Independent GP import and pitch-curve preview verification; no invented listening judgments.
- [x] Private review artifacts, regression tests, committed source and pushed main.

First implementation supports note-level bend properties only. Other dimensions remain locked, not advertised as implemented generation levers. At intermediate strength, candidate log weights receive a reference-equality bonus of 4*(100-strength)/strength. At 100 the reference is not supplied to the proposal method; accidental agreement is allowed. This is an explicit engineering interpolation, not calibrated perception. Methods are transparent scripted baselines, not an artist-trained model.

## Actual Time experiment, 2026-10-16

Command: `.venv/Scripts/python.exe composition-lab/bend_lever_experiment.py C:/Users/User/Downloads/time.gp --out composition-lab/local-artifacts/time-bend-levers-v1 --track 3`.

Seven full-source GP variants: original (0), removal, frequency prior (100), contextual prior (25/50/75/100). Generic priors are not fitted to Time: frequency .25; contextual .45 for sustains at least one quarter beat, .10 for shorter sustains, zero for polyphonic onset groups. New bends are one/two semitones, rise then hold through ties. These are explicit experimental rules, not recovered artist style. Base pitches stay locked; original bend-target preservation is not promised. Physical bend playability is not certified.

All seven outputs pass locked-XML and non-score archive-member comparisons; 0 is byte-identical. All independently import with alphaTab. Full-freedom contextual output is invariant when all original source bends are removed. Shared note definitions and unresolved ties are rejected. Locked comparisons preserve parsed XML, not modified score XML byte formatting.

Private review uses bars 95–110, isolated solo track, original tempo map: 28.657 seconds plus .1-second tail. Seven GP/WAV pairs preserved; six unique previews shown because 25% equals original at this seed. Intermediate percentages do not promise linear edit counts. Fixed-gain continuous-phase sine preview renders piecewise-linear bends and tied sustains; other effects/guitar timbre not synthesized. Full GP files retain all original tracks. No human musical judgments invented.

Verification: 120 Python tests pass locally, including authored-GP endpoint/perturbation tests and FFT verification of 440 Hz bending to approximately 493.88 Hz. Optional NumPy signal test skips when NumPy is absent; lock tests are standard-library only. 16 JS tests and Vite build pass. Browser audio progressed without media errors. No public website edits: review HTML and commercial source-bearing artifacts stay local, so no Pages deployment required.

Next: human comparison, then fit/validate richer contextual methods and extend the shared edit boundary to other feature families. Other generation levers remain unimplemented.

## Bend-only follow-up, 2026-10-16

User: ignore weak final resolution; generated bend versions only, no original/no-bend controls.

Acceptance checklist:
- [x] Scripted destination scores use surrounding pitched accompaniment and following solo note; source bend annotations excluded from proposal context.
- [x] Reject overlapping solo sustains; vary whole-sustain curves and split exactly over ties.
- [x] Generate three distinct nonempty bend previews and independently import all GP outputs.
- [x] Verify locked data and full-freedom reference perturbation; run tests/build.
- [x] Private review ready; code/progress pushed to main. Human quality remains unjudged.

Implementation: contextual_bends.py and build_bend_v2.py. Priors are engineering heuristics, not learned artist technique. Accompaniment selection uses explicit MIDI program ranges for piano, organ, guitar and bass; pitch support is not verified harmonic function. Selection budget and spacing are transparent experimental parameters. Only bends change; base pitches, rhythm, arrangement, ties and all other techniques stay locked. Bends are 1/2 semitone choices; this limits stylistic variety and does not certify physical execution. Curve encoding rejects unrepresentable interior shapes; any fallback is counted. No phrase-end quality objective is used. Existing v1 feedback stays private and v1 outputs are preserved.

Bend v2 completion evidence: three distinct previews with 6/9/9 bent sustains; 18/34/34 selected across the full solo track. Zero curve fallbacks. All three GP files independently imported; all locked-data checks pass. Running each method on the bend-removed source yields identical bend-property output. Actual verification: 124 Python tests, 16 JS tests, Vite build pass. Browser preview advances without media errors. Private comparison: local-artifacts/time-bend-levers-v2, loopback port5178. No public website changes or Pages deployment needed. Human musical quality remains unjudged. Earlier unchecked bend-v2 acceptance items are satisfied by this evidence and the associated main commit/push.

## Bend timing follow-up, 2026-10-16

Acceptance checklist:
- [x] Keep generated bend selections/peak displacements fixed across three modes; no original/no-bend cases.
- [x] Script explicit start/arrival/hold/release times using meter and accompanying pitches at arrival. No reference bend annotations in proposal context.
- [x] Encode delayed origins and early finishes exactly; avoid fractional-pitch tie seams.
- [x] Generate distinct private GP/audio, verify locked data, independent curve fidelity and reference perturbation.
- [x] Run regression/build, verify review UI, commit/push and check CI. Musical quality awaits user feedback.

Research basis: Patrick Brennan, https://www.guitarplayer.com/lessons/unlock-the-secrets-of-expressive-melody-playing (immediate, delayed, held, released and multistage gestures); Mike Stringer, https://www.guitarworld.com/lessons/artist-lessons/mike-stringer-spiritbox-syncopated-bending (rhythmic and tied-note bend placement); D'Hooge et al., https://arxiv.org/html/2308.12307v1 (short-term pitch/rhythm context and bend-direction distinctions). Principles inform transparent scripts; no external ML classifier, pretrained model or AI inference is used. Human advice is not converted to universal musical rules.

The timing comparison retains v2 destination-aware selections and one/two-semitone peaks, then varies pulse arrival, delayed arrival, and contextual release. Harmonic support is normalized by active track, avoiding domination by dense chord notation. It remains observed pitch support, not verified harmony. No final-resolution objective, fretted-pitch edits, pre-bend re-fingering, vibrato changes, or claimed artist fitting. Curve rise/release occurs within a single written segment so quarter-tone-limited independent import does not alter a fractional pitch at a tie seam. No score rhythm is changed. Source preservation and musical melody preservation remain distinct: base pitches are literal locks, bend-induced sounding changes are intentional.

Timing v3 results: three distinct generated-only previews, nine bent sustains each in the excerpt; all 34 full-track selected notes and peak displacements identical across modes. All locked XML/archive comparisons and reference-bend-removal perturbation checks pass. Independent alphaTab sampling verifies every solo note curve in all three outputs: maximum deviation below 1.4e-15 semitone, 204 notes per case, 61 bend-bearing segments. No fractional tie-seam pitch loss. Audio playback verified mechanically; no human quality verdict. 129 Python tests, 16 JS tests and Vite build pass. Review version675391ec9a09b75b, private directory local-artifacts/time-bend-levers-v3, loopback port5179. Remaining timing checklist items satisfied; source code/progress published in associated main commit. No website assets changed, no Pages deployment required.

Reproduce: python composition-lab/build_bend_v2.py SOURCE.gp --out NEW_PRIVATE_DIRECTORY --track 3 --round 3; node composition-lab/verify_bend_curves.mjs ALPHATAB_MODULE 3 NEW_PRIVATE_DIRECTORY/bend-01.gp ... . Private curve expectations are exported alongside GP files. All earlier comparison artifacts remain preserved.
