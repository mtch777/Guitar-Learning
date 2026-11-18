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
- [x] Build, publish through the existing Pages workflow and inspect live output
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
- Live baseline: old build `ec67ab24a7e9` had fill `#D6D9DF`, white 30px checks
  and low-contrast translucent borders.
- Source release `a85edec5646f085199f33dcfefa01acba8c4aa25` is on main.
  Build/regression/publish run 44226766439 and Pages deployment 44226853447 both
  succeeded. Published branch commit: `683a95580d449bd8d348555ddd24787523348865`.
- Live browser confirmed build `a85edec5646f` on all three quizzes. Each has
  12 dark sectors, border `rgb(102, 112, 133)`, check fill `rgb(74, 222, 128)`,
  check font size 40px and dark check stroke `rgb(16, 38, 26)`.
- Color → Key at a 337px CSS viewport has a 295px-wide circle and no horizontal
  page overflow. The 40px SVG check size scales to about 19.7px at that width.
  Narrow inspection used normal browser zoom at 400%; zoom restored to 100%.
  Live screenshot captured and the Color → Key tab retained for review.
- Browser verified deployed appearance/CSS; wrong-input and solved-state behavior
  was verified through actual page scripts with simulated MIDI. No physical
  MIDI device or audio was used. No remaining blocker for the requested changes.

## Feedback scope and MIDI failure diagnosis — 2026-11-17

Latest user correction supersedes the earlier all-three-quiz feedback scope:
only Color → Key should highlight the incorrect guessed pitch on the circle.
Accidentals Count should flash the submitted numbered input tile red or green;
Accidentals Order should keep its existing sequence feedback without a red
circle sector. The user also reports another generic MIDI access failure and
asks what its failure logs say.

- [x] Limit wrong-pitch circle highlighting to Color → Key; preserve dark
  interiors, green solved checks, prompt colors and Order sequence behavior.
- [x] Flash Count's existing submitted number tile red/green and clear it on
  timeout/reset without stale feedback affecting the next question.
- [x] Make the existing MIDI status show the actual access/setup exception;
  preserve a bounded local failure history without a debug panel or telemetry.
- [x] Prevent unavailable preference storage from breaking a successful MIDI
  connection or stopping a page at startup.
- [ ] Run scoped silent regression checks/build, publish and verify the deployed
  release; distinguish simulated input evidence from physical hardware testing.

Initial diagnosis at `2155bafd6ded442972636711e99b81a51862c423`:

- The circle and keyboard-shape catches discard their exception. There is no
  existing persistent or remote MIDI failure log to retrieve for this occurrence.
  Learning Songs logs to its current browser console only and incorrectly labels
  every caught failure as permission denial. Note Reading displays error.message.
- Actual three-circle-script VM reproductions: request rejection yields the
  generic message and zero console records; successful access followed by a
  throwing preference save yields the same message and clears the access object;
  an empty input list correctly yields No MIDI keyboard connected.
- This proves an error-reporting/storage defect, not the user's device cause.
  Do not infer permission, cable, OS or keyboard failure from discarded evidence.

Counterexamples: Count's MIDI note encodes a number rather than a key guess;
black keys have no numbered tile; reset during a pulse must clear old feedback;
a blocked localStorage write is not a failed MIDI permission request; no connected
input is distinct from access rejection. Scope excludes musical source changes,
song layout changes, remote logging and new visible debug controls.

Implementation and local verification:

- Count's mapped input tile flashes red for 300ms or green for 450ms. Wrong
  Count/Order input never changes a circle sector. Color → Key retains its
  actual guessed-pitch flash. Black-key count input has no mapped number tile.
- Shared MIDI preferences now tolerate blocked storage and keep the current
  value in memory. All seven MIDI pages distinguish access-request failures
  from subsequent setup failures and show the actual exception name/message.
- The latest 20 failure records are stored locally under
  `practiceAppMidiFailuresV1` and printed to the browser console. Records contain
  time, access/setup stage, name/message, pathname and build. No device identifiers,
  played notes, query strings, stack traces, network collector or debug panel.
  Storage/console failures cannot mask the original exception. This cannot
  reconstruct previously discarded failures from the user's device.
- `node --test tests/piano-*.test.mjs`: 99/99 passed, including 18 circle feedback
  cases and 8 new MIDI preference/diagnostic cases. Covers all pitch classes in
  two octaves, all seven correct number tiles, wrong/repeated/unmapped input,
  reset/lock/timeout behavior, solved checks and Order's shared F#/Gb questions.
- Independent actual-circle-script + real-shared-helper integration: 18 checks
  passed (3 pages × 6 scenarios). Access rejection and input-binding exceptions
  produce exact access/setup status and records. Blocked preference read, write,
  or both retain the connected handler and can still grade a correct answer,
  with no failure record. Empty inputs remain No MIDI keyboard connected.
- `npm run build` and `git diff --check` passed. Independent source review found
  no blocking issue. All checks were silent and used simulated MIDI; the user's
  current physical-device failure is not diagnosed by those simulations.
