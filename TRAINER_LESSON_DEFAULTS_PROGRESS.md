# Trainer lesson defaults — 2026-11-01

- [x] Daily Practice resets all eight strings to Drop D# when selected or initialized on page load. All other non-Time lessons reset to Drop D# when selected; Time Solo and Time Solo (with Chords) retain Drop E. Acceptance: switching from Time Solo to any other lesson presents D#1, A#1, D#2, G#2, C#3, F#3, A#3, D#4 while keeping the Daily Practice base root D#.
- [x] Both CAGED pentatonic and Identify Pentatonic CAGED by Shape offer only E and A shapes, including their Daily Practice pairs. Acceptance: shape filter and identification answer choices use E and A; the Shapes control lists E and A.
- [x] Verify the source changes, full JS tests, and build. `node --check src/trainer.js` passed; `node --test tests/*.test.mjs` passed 28/28; `npm run build` passed; `git diff --check` passed. The existing JS tests do not exercise the Daily Practice selection UI, so live UI verification remains below.
- [ ] Publish to main and verify the live UI. Send the updated cache-busted URL immediately after commit.
