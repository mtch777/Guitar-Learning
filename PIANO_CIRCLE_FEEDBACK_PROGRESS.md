# Circle of fifths feedback — 2026-11-17

User request: darken the interiors of the circle outlines, flash the played
note's location red for wrong input, and make correct checkmarks clearly green.
Scope: the existing Color → Key, Accidentals Count and Accidentals Order quizzes.

- [x] Give neutral sectors dark interiors and visible boundaries; make solved
  checks larger and green, including at narrow widths.
- [x] Map wrong MIDI input to its actual pitch-class sector and restore that
  sector's prior appearance after the flash.
- [x] Preserve solved checks, prompt colors, count/sequence grading, MIDI state
  and reset behavior; verify shared enharmonic positions and delayed callbacks.
- [ ] Build, publish through the existing Pages workflow and inspect live output
  silently. Record deployed commit and actual evidence below.

Counterexamples: F#/Gb shares one visual sector despite two order questions;
wrong input can hit an already solved sector or the current prompt's tonic;
reset during a flash must not allow a stale timeout to change the new question.
No changes to the reference diagram, song lessons or composition/guitar logic.

Independent scope review confirms all three quizzes need the same change.
No audio is required or permitted during assistant QA.

## Verification

- All three quiz scripts now use neutral fill `#202833`. Each wrong-input
  handler selects the played pitch's sector and restores its actual prior fill.
  Reset cancels pending wrong/correct feedback timers.
- All three styles use clearer sector borders (`#667085`) and 40px green checks
  (`#4ade80`) with a dark stroke, replacing 30px white checks.
- `node --test tests/piano-circle-feedback.test.mjs`: 16/16 pass using the actual
  page scripts and fake MIDI input. Covers all 12 pitch classes in two octaves,
  already solved sectors, prompt-tonic wrong input, note-offs, feedback locks,
  reset during both delays, sequence reset and shared F#/Gb completion.
- The initial harness run found a callback passing its array index as MIDI
  velocity; corrected the harness wrapper. No corresponding production defect.
- `node --check` passes for all three scripts; `git diff --check` passes.
- `npm run build`: passes. Independent source/CSS review reports no blocker.
- Live baseline: old build `ec67ab24a7e9` has fill `#D6D9DF`, white 30px checks
  and low-contrast translucent borders. Publication/live inspection pending.
