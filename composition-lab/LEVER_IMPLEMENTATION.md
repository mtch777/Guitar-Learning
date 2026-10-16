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
