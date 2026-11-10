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
- [x] Confirm publication and served assets separately from local code/build checks.

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

## Original format limits (bend routing superseded below)

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

Published implementation: 00147fb6fc130d97a56444f6ca001cb521efa0ce, confirmed on
remote main. Pages workflow 42330749440 completed successfully for that exact SHA:
https://github.com/mtch777/Guitar-Learning/actions/runs/42330749440

Public page: https://mtch777.github.io/Guitar-Learning/riff-builder.html
Verified MIDI Export in public HTML. Served riffBuilder-C18vlrm8.js and
riffBuilder-D275nU2N.css match the local production build byte-for-byte.

Additional smoke: the public composer with Invent Animate / Aeolian / seed 606
produced 128 events, 150 BPM, 32 beats. Export produced a deterministic 1,744-byte
MThd file. An extra optional mido cross-check could not run because that package
was absent; the independent binary-parser tests above passed.

Remaining verification limit: an actual browser click/download and visual layout
check remain unperformed, as recorded above. No musical listening claim.


## Bend mismatch investigation - 2026-11-07

User reports bends differ between player and exported MIDI. Confirmed defect:
the native score's primary/secondary channels are both zero. Player per-note
pitch wheels are converted to channel-wide wheels by the standard exporter.
An unrelated attack resets an ongoing bend, and held notes inherit each other's
curves. Separate issue: the native range is +/-16 semitones; receiving instruments
that ignore the MIDI RPN range need that setting configured manually.

- [x] Inspect native per-note vs standard channel-bend semantics independently.
- [x] Reproduce original pitch contamination with parsed MIDI and actual examples.
- [x] Route export-only notes, ties and slides to separate string channels/tracks.
- [x] Verify every channel's range, native pitch paths, clocks and live-player isolation.
- [x] Run full regressions and independent review.
- [x] Deploy and verify served assets (November 10 verification below).

Current implementation uses the pinned native generator's channel hook only on
the export instance, not on its shared prototype. The original score adapter,
source data, player and composition remain unchanged.

The first per-string implementation exposed a second conversion edge case in the
fixed Currents / Dorian / seed 606 case. Native prebend setup can target a future
key one tick early; converting it directly still bent the preceding different
key. The exporter now records native events, checks actual sounding key windows,
and omits only preparation events addressed to a non-sounding key while that
string sounds a different key. All other events replay in original order. The
new note's attack-time prebend, silence preparation, same-key behavior and legato
root curves remain verified. No rounding or note-clock change is involved.

Fixed actual coverage: three artists x six modes, seed 606 declared before
generation. All 18 generated and exported, including two cases containing bends
and seven containing slides. The original conversion had eight wrong sounding
pitch samples in Currents/Dorian; repaired exports match every checked native
sounding pitch path in all 18 cases. Artificial overlapping-bend and independent
unison tests also pass. This is technical event verification, not a listening
comparison in the user's DAW.

Receiver requirement remains: preserve the separate tracks/channels and honor
the exported +/-16-semitone RPN bend range, or set each receiving instrument to
that range. Guitar timbre depends on the instrument. Previously downloaded MIDI
files are unchanged and should be re-exported after publication.


## MPE addition - 2026-11-07

User requested MPE. Added separate MPE Export; conventional MIDI remains fallback.

- [x] Check official MPE v1.0 specification and emit actual RPN6 configuration.
- [x] SMF0: lower manager channel 1, eight members on channels 2-9; upper zone off.
- [x] Set manager +/-2 and each member +/-48 after zones; rescale native +/-16 curves.
- [x] Allocate one free member per sounding voice, preferring released matching-key
  members, otherwise longest-idle members. Do not steal an active voice.
- [x] Preserve native clocks, legato roots, initial bend, and voice-owned curves.
- [x] Put program, bank, volume, pan and expression on manager. Do not invent
  pressure/timbre expression that is absent from source.
- [x] Test RPN bytes, opposing bends/unisons, eight members, reuse, same-key preference,
  early prebends, old endpoints, slides, and interrupted/repeated button flows.
- [x] Compare both formats against native playback for 18 fixed generated riffs.
- [x] Independent review identified an endpoint omission not covered by sounding-
  window tests: terminal bend preceding native Note Off must remain for release.
  Preserve terminal events using original call indices, before Note Off and before
  any new attack/reset. Added isolated, same-key and different-key regression cases.
- [x] Full regression and final independent review.
- [x] Push and live asset verification (November 10 verification below).

Receiver: import MPE into one MPE-enabled instrument with channel expression
preserved, lower zone, manager 1, members 2-9, member range +/-48. Some importers
flatten channels or discard RPN setup; manual configuration may be needed. No
specific DAW/plugin has been tested. MPE does not reproduce the player sample tone.
Standard MIDI requires separate string tracks/channels and +/-16 instruments.

Source: https://d30pueezughrda.cloudfront.net/campaigns/mpe/mpespec.pdf
MPE v1.0 sections 2.1, 2.3, 2.4, 3.2-3.3. All tests are silent, not listening QA.
The browser click/download and visual layout remain unverified due the previously
recorded browser-tool stop. No workaround was used.


Final local verification: 115 JavaScript tests passed, no skips; production build
passed. Python browser suites: 19 passed and one existing optional corpus test
skipped (test_riff_browser, test_riff_pattern_browser, test_procedural_riff_browser).
Independent reviewer reran all 19 native MIDI tests after the endpoint fix and
reported no remaining blocking findings. A subsequent static HTML test checks
that both export modes show their different receiver requirements.
Two mistakenly named Python discovery patterns found no tests; the correct suites
were then run as listed above. No composer asset was changed or staged.

## Release verification - 2026-11-10

The user subsequently authorized project publication. Released only the five
previously staged MIDI/MPE files; unrelated working-tree changes were preserved.
Implementation commit: ec44c751211547cede2b8a05fc4bd8d0d8f04faf, verified on main.
Fresh local checks: 115/115 JavaScript tests, zero skips; Python 19 passed,
one existing optional corpus skip; production build and staged whitespace check passed.
Build and publish run 42811746417 succeeded for the implementation commit.
Pages deployment run 42811834460 succeeded for gh-pages
33121867b2b30cd62d2d1907a6982a4f878503dc.

Live riff-builder.html contains MIDI Export and MPE Export and loads
assets/riffBuilder-Do7p3Qb4.js. Its 31,088 served bytes exactly match the local
production build, SHA-256
496262df151e0f363472c6467806f14a61b3afec9ca045ab51fbfbfbbeba2d31.
The existing /riff-audit/ page still returns HTTP 200.

Actual browser click/download, DAW import and listening remain unverified.
Automated button-flow and binary MIDI tests are not substitutes for those checks.