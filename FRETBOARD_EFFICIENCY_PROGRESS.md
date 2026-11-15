# Drop E fretboard efficiency — two-riff pilot

## Current delivery: existing training lesson — 2026-11-15

The user explicitly approved the GitHub upload, then requested a new lesson in the existing lesson/guitar-training HTML UI, conversion of both results to that fretboard, file upload, and actual playback validation before handoff. The previous portable review is supporting evidence; it is not the requested final surface.

- [x] Publish the approved optimizer, original fixtures and mappings on `codex/drop-e-fretboard-efficiency`. GitHub checkpoint `f30b088a0c8a20cf358053c32481134b16ecea21`; tree `9867b54b5ffe5d8b73b2efba5e0dc16793fc5ec4`.
- [x] Convert both mappings into the existing native player format with exact source occurrences, pitches, timing and string/fret contacts.
- [x] Add Fretboard Efficiency to `index.html` / the existing trainer; use existing fretboard and transport with A/B selection and direct lesson URLs.
- [x] Verify native playback clocks and the low/high string conversion, duplicate B3, sustained-note seek, stop/pause/end, and 0.75 speed in native/unit integration checks; live browser checks remain below.
- [x] Verify relevant existing lesson regressions and production build with pinned native alphaTab installed, without skips caused by its absence.
- [ ] Publish the lesson files and app through the existing Pages deployment, verifying served bytes and completed deployment.
- [ ] Exercise the live fretboard/player for both riffs, inspect the responsive view, and hand off the verified lesson URL only after these checks pass.

The terminal had no GitHub credential after approval. The connected GitHub API published the approved Git tree and updated the branch with a guarded fast-forward. This is a completed upload, not an unresolved authorization issue. Pinned native alphaTab 1.8.4 is installed at `.local/qa` for exact playback verification. Root owns integration/deployment/browser evidence; independent agents own the lesson UI, native adapter, and independent playback tests respectively.

Pre-publication verification: all 131 JavaScript tests pass, zero skipped; all 32 optimizer/shape Python tests pass; the three existing Python Pages checks pass (6/7 with one pre-existing optional fixture skip, 9/9, 4/4). Build passes. Full trainer DOM harness checks 524 frames and exact active contacts with a silent mocked transport; this is separate from actual native conversion and from pending live browser playback. Native conversion preserves all 164/191 source occurrences, 61,920 ticks and 32.25 seconds. All 5,472 Time score events remain unchanged after mapped-note velocity registration. A delayed callback could previously restore paused highlights; a targeted counterexample now verifies the explicit seek-preview state and stopped-display guard.

## Current user contract

Use the user-selected `cfa029a2` and `da80eca9` generated MIDI files as the frozen inputs and tests. Source branch commit: `b86db9f73d1adf8a5552dc81a475437a36b4ae2c`. Preserve note occurrences, pitches, octave, velocity and exact onset/release ticks, including duplicated unisons. Assign to 8-string Drop E (high-to-low MIDI 64,59,55,50,45,40,35,28), 24 frets.

Ordered priorities within valid fingerings: (1) maximize exact-pitch open-string occurrences; (2) minimize rapid changes of hand position along the neck; (3) minimize remaining travel and fretting effort; (4) reduce picking travel/skips; (5) prefer explicit familiar shape fragments. Lower priorities never override higher priorities.

This is a new, isolated task. Earlier composition generation, classifier and listening milestones are unchanged.

## Acceptance checklist

- [x] Freeze both actual user-selected MIDI inputs and independently inspect their notes.
- [x] Implement reusable whole-sequence fingering search with ordered objectives and sustained-note constraints.
- [x] Preserve every source occurrence in both mapped outputs and MIDI exports.
- [x] Retain the four duplicate B3 occurrences per riff on different strings; prove maximum feasible open counts of 82/86 and 73/77.
- [x] Compare to a physically valid greedy baseline using the same notes and declared constraints.
- [x] Independently verify geometry, overlap, note preservation, open counts, and meaningful adversarial examples.
- [x] Reuse the existing riff-builder surface for both fixtures and both mapping versions; verify all 496 attack states in a DOM harness, without sound.
- [ ] Inspect actual desktop and phone rendering. Blocked in this environment: local Chromium cannot start through Playwright, native text entry lacks an accessibility provider, and cloud browser cannot reach the local server. DOM verification is not a visual-render claim.
- [x] Produce the portable offline review, reporting actual metrics and model limitations; source is ready for an isolated branch checkpoint.

## Model boundaries

Positive-fret span is at most four, with at most four fretting contacts; open strings do not force a hand position of zero. Hand positions are discrete reachable five-fret windows. Rapid-shift risk uses the released-fretting gap plus a bounded 125ms transition allowance (capped by attack spacing), and an adjustable default threshold of eight fret positions per second. Time spent sustaining a fretted chord is not free travel time. This is not a measured physical-speed or human-comfort certificate. Picking is a string-travel/selective-picking proxy, not recovered original pick direction.

## Progress

- 2026-11-15: Created isolated branch from main `bdcec7e`. Read current instructions and relevant existing adapters/contact-coverage model. Independent agents confirmed 164/191 source occurrences, 124 attacks each, no cross-onset held notes in these fixtures, and four duplicate-unison groups per fixture (2,10,18,26 seconds). Generic holds require separate adversarial tests.
- First pass used attack spacing and reported 0/3 rapid moves. Independent review disproved that proxy with a chord held until a 12-fret jump: it incorrectly scored zero. Replaced with release-aware timing; those initial movement figures are superseded, not final acceptance evidence.
- Final release-aware results: cfa rapid flags 19→1, total fret travel 96→12, largest jump 14→2; da80 rapid flags 34→10, travel 204→84, largest jump 14→5. Both reach the maximum feasible open counts. Picking costs worsen 433→524 and 475→686; shape costs worsen 916→976 and 892→952, consistently with the priority order. The second riff makes 45 smaller shifts versus the baseline's 43; distance/risk, not count alone, is the Tier 2 objective.
- Independent raw-MIDI oracle passes both sources, all four mappings, and all four string-channel MIDI exports. Focused Python suite: 32 passing, none skipped. Existing relevant JavaScript suite: 49 passed, 38 native-alphaTab cases skipped because that optional package is absent; no failures. Production build passes. No audio was played.
- Portable HTML bundles the same UI, CSS and current measured data. Embedded-data and provided-data routes work under file://; existing fetched-data route still passes. All 496 attack states and controls pass in the actual offline bundle; zero automatic fetches or external script/style/audio/video tags. Reproduce with `python composition-lab/export_fretboard_efficiency_review.py`.
- Implementation checkpoint committed locally as `f46d1c7ba5bad89d68ec8853c4bbe03ebfa4b41f` on `codex/drop-e-fretboard-efficiency`. Automatic approval review rejected the GitHub push: the current user request authorizes processing/testing, but publication and destination sharing authorization were not established. No alternate upload or bypass was attempted. Explicit user approval is needed before pushing this branch.

## Next useful refinement

Review the actual assigned contacts on the user's guitar, especially the remaining high-dyad transitions in fixture B. Calibrate the provisional transition allowance and reach model from that feedback. Complete phrase-level 2/3-NPS and arpeggio recognition remains a Tier 5 extension. Actual phone/desktop rendering needs a browser that can reach the preview; this has not been silently counted as passed.
