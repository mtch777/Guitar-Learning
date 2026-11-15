# Drop E fretboard efficiency — two-riff pilot

## Current delivery: existing training lesson — 2026-11-15

The user explicitly approved the GitHub upload, then requested a new lesson in the existing lesson/guitar-training HTML UI, conversion of both results to that fretboard, file upload, and actual playback validation before handoff. The previous portable review is supporting evidence; it is not the requested final surface.

- [x] Publish the approved optimizer, original fixtures and mappings on `codex/drop-e-fretboard-efficiency`. GitHub checkpoint `f30b088a0c8a20cf358053c32481134b16ecea21`; tree `9867b54b5ffe5d8b73b2efba5e0dc16793fc5ec4`.
- [x] Convert both mappings into the existing native player format with exact source occurrences, pitches, timing and string/fret contacts.
- [x] Add Fretboard Efficiency to `index.html` / the existing trainer; use existing fretboard and transport with A/B selection and direct lesson URLs.
- [x] Verify native playback clocks and the low/high string conversion, duplicate B3, sustained-note seek, stop/pause/end, and 0.75 speed in native/unit integration checks; live browser checks remain below.
- [x] Verify relevant existing lesson regressions and production build with pinned native alphaTab installed, without skips caused by its absence.
- [x] Publish the lesson files and app through the existing Pages deployment, verifying served bytes and completed deployment.
- [x] Exercise the live fretboard/player for both riffs, inspect the deployed desktop view, upload the mapping through the existing file chooser, and leave the verified lesson ready at its start.

The terminal had no GitHub credential after approval. The connected GitHub API published the approved Git tree and updated the branch with a guarded fast-forward. This is a completed upload, not an unresolved authorization issue. Pinned native alphaTab 1.8.4 is installed at `.local/qa` for exact playback verification. Root owns integration/deployment/browser evidence; independent agents own the lesson UI, native adapter, and independent playback tests respectively.

Pre-publication verification: all 131 JavaScript tests pass, zero skipped; all 32 optimizer/shape Python tests pass; the three existing Python Pages checks pass (6/7 with one pre-existing optional fixture skip, 9/9, 4/4). Build passes. Full trainer DOM harness checks 524 frames and exact active contacts with a silent mocked transport; this is separate from actual native conversion and from pending live browser playback. Native conversion preserves all 164/191 source occurrences, 61,920 ticks and 32.25 seconds. All 5,472 Time score events remain unchanged after mapped-note velocity registration. A delayed callback could previously restore paused highlights; a targeted counterexample now verifies the explicit seek-preview state and stopped-display guard.

First publication: source commit `7f1f0d5b0d5315247d75f7e3b6a0a3517b5ad46a`, Pages source run `43755042104` and deployment `43755120032` succeeded. Live index and fixture bytes matched the tested build. Actual browser use then found that `alphaTab.min.js` omits the named MIDI generator APIs used by the existing playback bridge. The player now loads the pinned `alphaTab.js` browser distribution, already used by Riff Builder. Regression checks execute that actual UMD distribution and assert both the inserted CDN script and player worker URL. No API guard was bypassed. Live playback remains an open acceptance gate until this correction is deployed and exercised.

The independent microphone preflight first failed while installing Playwright 1.51.1 on the newly changed `ubuntu-latest` runner. Commit `4c29a685ba44c0798295ff04c4f88ed8703ab234` pins its supported Ubuntu 24.04 runner. The next run reached the real acoustic test and correctly detected the recorded D#1, but the default Time lesson is in Drop E and has no MIDI 27 fret. The harness now explicitly selects the existing Intervals lesson and verifies its lowest open pitch is MIDI 27 before starting the test. Browser inspection independently confirmed that setup. All original detection, completed-note, click and timing assertions remain; no audio classifier or signal processing was changed.

Corrected-distribution verification: the complete JavaScript suite passes 132 tests with zero skips; production build and whitespace checks pass. Native browser-bundle checks retain exact source events and the unrelated Time score. The corrected public main asset is `main-xrin7cvB.js`; deployment and actual playback are the remaining checks.

Live verification of `f640c21b1a9df6ad6581ff9bed4f212f5d52bf7d`: Pages source run `43756330292` and deployment `43756390770` succeeded; public index, `main-xrin7cvB.js`, and fixture bytes match the local build. Both optimized riffs completed native playback at tick 61,920 with zero active contacts (A at 0.75x, B at 1x). Actual UI seeks at tick 6,192 show both B3 occurrences and all four sustained chord contacts; tick 8,173 shows only the lowest open E1/B1; B tick 12,694 shows S4 fret 21 / B4 and S3 fret 17 / C5 in a seven-fret window. Pause and Stop clear active occurrence markers, and Stop resets tick zero. Full neck and comparison controls work. The existing decorative `timeSoloSelectedNote` class can remain on empty cells; actual sounding contacts are identified by `data-note-id`, and the paused screenshot confirms no note markers.

The corrected main microphone preflight `43756330356` passed, but its identical-SHA feature-branch run exposed a genuine race: bundled Time checked the selected lesson before waiting for the player script, then loaded after the user had switched to Intervals. A new deferred-script regression fails before the fix and passes after it. Only bundled Time now rechecks lesson/score/upload state after `ensureApi()`; explicit uploads remain unchanged. The preflight path filter now includes Song Player and this regression so the corrected head gets a real browser check. All 133 JavaScript tests pass with zero skips; production build passes with `main-BR2GQeSp.js`. This final lifecycle correction still needs publication and live confirmation. Composition run `43755042025` also completed successfully for the initial lesson integration.

### Final acceptance — completed

Final application source: `c49a261a148e06a78ed6d6469bb09892a0baafe9`. Published gh-pages commit: `7dced718ff7bb9994f3c047f12ee00389c0ddaaa`. Pages source build `43757011718`, deployment `43757069742`, main live preflight `43757011705`, and feature live preflight `43757009448` all succeeded. The live index, `main-BR2GQeSp.js`, and fixture JSON match local bytes exactly. The source bundle SHA-256 is `0eeb3880c0d30fcdbbf8f5ff97aeda7da2b947a79e369e94e3f21863ebbe5bfe`; fixture SHA-256 is `94a2fbfd849692ac40ed122cf889c18be673182f74a511e231e45de36686f076`.

Actual final-deployment browser verification completed full native playback of both A and B, each ending at 61,920 ticks / 32.25 seconds with no active contacts. A separate full A run at 0.75x also finished correctly; two live playing samples measured approximately 0.751x source-time advancement. The existing Song Player file chooser accepted the exact 384,330-byte mapping bundle and played it with advancing native ticks and matching contacts. Switching from that uploaded score back to Time loaded its original solo track and enabled its transport. Returning to the new lesson restored Drop E, E-relative intervals, and the selected optimized mapping.

The retained browser receipt is `composition-lab/fretboard-efficiency-live-validation.json`: 33 observations, including 23 exact active-contact snapshots independently joined against source occurrence IDs and assignments, 20 checks that active contacts fit the visible fret range, and 8 empty-contact states. Both duplicated B3 occurrences, the lowest open E1/B1 power chord, and B's S4:21 / S3:17 high dyad are verified in the real fretboard. Pause/Stop/end, seeking, speed, comparison selection, and full-neck/follow controls passed. The final handoff tab is A / Optimized / Follow hand at tick zero, ready to play. Desktop rendering was inspected; phone rendering is not claimed.

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
- [x] Inspect the actual published desktop trainer and playback. This supersedes the earlier local-preview browser limitation. Phone rendering remains outside the verified scope.
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

Review the actual assigned contacts on the user's guitar, especially the remaining high-dyad transitions in fixture B. Calibrate the provisional transition allowance and reach model from that feedback. Complete phrase-level 2/3-NPS and arpeggio recognition remains a Tier 5 extension. The deployed desktop UI and native playback are verified; a dedicated phone-rendering check remains a separate future refinement.
