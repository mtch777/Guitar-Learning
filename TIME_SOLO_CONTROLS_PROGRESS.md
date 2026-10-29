# Time Solo controls — 2026-10-29

- [x] Include the user-provided `time.gp` in the public site and load it on the Time Solo (with Chords) lesson without upload. Acceptance: built asset hash equals uploaded score; fresh lesson loads the score and solo range.
- [x] Up/Down move through every available speed, preserving the current score tick. Acceptance: transport test checks both directions while playing.
- [x] Chord timeline click seeks by proportional score tick through the solo transport. Acceptance: transport test checks a tick seek and relative time; deployed UI click check pending.
- [x] Interval Type switches sounding-note labels between Base Key and Current Chord. Acceptance: test checks E changes from R in E major to b7 in F# minor and back.
- [x] Run JavaScript tests and production build. `node --test tests/*.test.mjs`: 28 passed, 0 failed. `npm run build`: passed. `sha256sum public/time.gp dist/time.gp`: both `bd656f927c89b00fbc366b8659879d606937e4ff33fef60367023802c53aa89b`.
- [x] Verify published page in a fresh browser session. Commit `ac86497`: score loaded automatically, Guitar Solo track selected, solo duration 1:31, 23 score-timed chord sections. Clicking midpoint of chord strip sought to 0:45 / progress 493; Up changed 1× to 1.1×, Down restored 1× without changing position; Space paused playback; switching Interval Type on the same held pitch changed its displayed interval from 6 (Current Chord) to 5 (Base Key).
- [ ] Default Interval Type to Base Key in the public lesson. Acceptance: a fresh page has Base Key selected before playback, and Current Chord remains selectable.

Next action: user review on the public site.
