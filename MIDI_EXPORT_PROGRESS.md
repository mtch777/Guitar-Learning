# MIDI export - 2026-11-07

Scope: add a standard .mid download to the current riff builder without changing
composition, playback, or parallel local work. Base: 4b00f350.

Acceptance checklist:
- [x] Inspect source, player, tests and workflow; isolate changes on a feature branch.
- [x] Reuse the native score adapter and slide correction used by playback.
- [x] Export the complete accepted riff at original tempo, not preview speed.
- [x] Add MIDI Export beside JSON with timestamped filenames and wrapping controls.
- [x] Parse real MIDI bytes: header, tempo/meter, pitches, clocks, rests, ties, end and bends.
- [x] Test repeated export, busy/failed/new generation, source immutability and URL cleanup.
- [x] Independent final code review and all 101 JS tests passed, no skipped tests.
- [x] Run the production build and Python browser-composer regression suites.
- [ ] Actual browser download and visual layout verification: blocked by browser access.
- [ ] Confirm publication and served assets separately from local code/build checks.

## Verification

- `node --test tests/*.test.mjs`: 101 passed, including six new MIDI tests.
- `python -B -m unittest discover -s composition-lab -p test_riff_browser.py`:
  7 run, 6 passed, one existing optional corpus test skipped.
- `python -B -m unittest discover -s composition-lab -p test_riff_pattern_browser.py`:
  9 passed. First run failed the existing content hash because Windows Git expanded
  pattern_engine.py to CRLF. Rechecking exact committed LF bytes passed; no source
  or manifest change is included for that checkout-only issue.
- `python -B -m unittest discover -s composition-lab -p test_procedural_riff_browser.py`:
  4 passed.
- `npm run build`: passed. Existing rake guards and `git diff --check` passed.
- Independent review reran six MIDI tests and all 101 JS tests successfully.
- Browser verification could not run: no browser tab provider was available and
  Windows Computer Use could not safely determine the browser URL. No audible
  playback was started. Automated DOM tests do not establish visual/browser QA.

## Format limits

Standard MIDI stores instrument instructions, not the sampled guitar audio.
AlphaTab's standard export uses channel-wide pitch bends, so simultaneous independent
note bends cannot be guaranteed. Preserve JSON for the complete guitar-specific data.
No new composer or musical-quality acceptance is claimed. Export uses the full
currently displayed accepted result, even after a later generation failure.

## Progress and remaining checks

The original dirty checkout was left untouched. A filtered clone isolated the feature.
The full clone attempt was stopped after no progress. Locked Vite dependencies and
existing pinned alphaTab 1.8.4 were used. Dependency installation reports two existing
high-severity findings; this feature adds no dependency or lockfile changes.

Next: push the isolated fast-forward commit under the user's existing live-site
workflow, check the exact commit's Pages build, and compare served assets to the build.
