# Musical-field implementation and source comparisons

- [x] Timing/identity: normalize marker text; validate song/revision/part identity and metadata vocal/empty flags; shared meter/pickup layout; explicit rest spans and bounded repeat/ending playback order. Acceptance: exact rational written occurrences retained; malformed/conflicting observations reported, no silent repair.
- [x] Technique values: exact source bend/whammy curves including precise positions and point vibrato; tremolo fractions and brush native values. Acceptance: correct quarter-tone/semitone units independently checked; unknown native units remain explicit.
- [x] Relationships: tie-aware sustained gestures, overlaps and technique-to-neighbor/context measurements; tempo/sound timelines. Acceptance: observations distinguish written/sounding hypotheses; no invented phrase/function labels.
- [x] Run corpus and refresh field-coverage matrix. Acceptance: all98 entries/495tracks processed, note counts reconciled, prior outputs preserved privately, unmapped fields fail strict audit.
- [x] Source comparisons: actual existing source GP passages, selected technique changes only, literal zero byte locks and all unrelated XML/archive members locked. Acceptance: actual GP outputs independently reopen; render nonzero variants with source/track/bar context and measurable audio differences; no authored riff or fretted-HOPO listening substitute.
- [x] Tests/build, persistent results, commit/push main and verify CI. Listening/feel acceptance remains for the user; do not mark it passed from serialization or synthetic audio.

2026-10-17: main0713557 clean/up to date; read handoff/context/current analyzer, audit and exporter/transaction tools. Found previous raw-source bend summaries mislabeled tone/25 quarter-tone units as semitones. Correct raw semitone scale is tone/50, consistent with alphaTab quarter-tone model and GPIF analysis. Existing GP conversion preserves raw tone units; no claim that existing audio was doubled. Correction will be versioned and old private outputs retained. Captured precisePosition uses0..100 versus coarse position0..60;25/216 points differ from the coarse fractional position. Corpus tempo.linear is absent/false throughout; unsupported ramp conventions must not be invented. Brush duration/shift remain native until units can be independently established.

## Verification 2026-10-17

- Fresh ff-only origin/main pull: already current; local work preserved.
- Corpus rerun completed: 98 entries / 495 tracks; independent validator: 420119 raw occurrences, 190890 attack groups, 9707 HP-pair invariants, zero failed checks. 180 private inspection seeds / 15 strata. See results/technique_validation.json.
- Rebuilt evidence: 88 cases / 2904 raw-readback occurrences. Strict API audit: 218 paths, zero unmapped.
- Main environment: 207 Python tests, 206 pass / 1 optional dependency skip. Isolated converter environment: 21 songsterr + 16 source + 2 validator tests pass. JS: 18 pass. Vite build pass.
- New validator fault-injection tests detect missing groups and corrupted durations. No model inference or fabricated labels used.
- New results and family contract: MUSICAL_FIELDS_RESULTS.md and TECHNIQUE_ANALYSIS_CONTRACT.md. Outstanding: independent semantic truth, pedal function, phrase interpretation and musical listening acceptance. Earlier 24 source GP roundtrip flags remain.
- Delivery: source/aggregate commit and CI/Pages verification pending below. No private source, raw evidence, audio or feedback will be staged.

## Verified delivery

- Source release 83e6eb0dc647e0cec7994961e6c28afa8c17f0b6 pushed to origin/main.
- Composition CI https://github.com/mtch777/Guitar-Learning/actions/runs/39094575874 success.
- Build/publish https://github.com/mtch777/Guitar-Learning/actions/runs/39094575869 success.
- Public assets unchanged; gh-pages remains 92b8731484b14f0fa44ee75d0f9b830a02a385c5. Existing deployment 7109164021 status success; live site HTTP200. No new source-bearing review was published.
- Private loopback review restarted and HTTP200 verified at port5183.
- Follow-up validator adds full exact onset readback, 866 bend/469 arm curve/range audits and 29447 pedal structural invariant checks; all pass. Sample set now180/15strata. No semantic truth claimed.
- Outstanding independent labels cannot be replaced with more parser agreement. Step2 engineering is verified; musical-function acceptance remains open. Step3 partial,4 partial,5 partial,6 partial,7 prototype,8 local/remote checks pass with human acceptance pending.

## Step2 follow-through: 2026-10-17

- Read current contracts and safely pulled origin/main; already current.
- Added source-only pattern robustness runner and tests. 29447 overlapping pedal
  windows collapse to7757 anchor/section regions.4790 exact normalized recurring
  shapes have nonoverlapping instances;2393 cross section instances,30 transposed,
  2 time-scaled. Tolerance counts:0=14940,1/8=16128,1/4=20259,1/2=29447.
- Added exact held-note construction intervals; timing-effect uncertainty explicit.
- Prepared six-family source identification gate, copied GP bytes unchanged,
  12 bounded context/focused previews, hashes and finite/nonclipped audio verified.
  Corrected initial near-duplicate sampling before delivery. No human labels entered.
- Browser: all12 media loaded without error, focused playback/pause verified,
  all audio stopped; screenshot in private pedal-identification-v2/review.png.
- Tests:211Python(210pass/1optional skip),18JS/build pass. No unrelated UI edits.
- Persistent detailed results/reproduction: PATTERN_ROBUSTNESS.md. Next acceptance:
  human anchor-function judgments; never substitute brush parameter ratings.

- Release779b84f pushed to origin/main. Composition CI39096189976 success: https://github.com/mtch777/Guitar-Learning/actions/runs/39096189976 . Working tree clean after release; no private source/artifact paths tracked. No public website changes in this continuation. Human gate is the six unchanged-source identification cases at loopback5185; all judgments blank.

## Requested piano-roll annotation update

- Added a white audio-synchronized playhead and green sounding-note outlines for
  both playback modes, including scrubbing and exact step-tempo changes.
- Click/Enter/Space toggles individual source-note anchor selections (pink).
  Export includes exact occurrence ID, pitch and source bar. Same study key keeps
  existing ratings/notes. Clear control affects only note selections.
- Upgrader backs up prior HTML and changes no GP/audio. New builds include feature.
- Browser verified click, reload persistence and exported JSON for occurrence
  0:29:0:1:0. Test selection undone; test export archived privately as QA only.
  Playhead observed x18.61 at0.185s and x413.78 at3.760s; sounding note highlighted.
- 211Python(210pass/1optional skip),18JS/build pass; JS syntax pass. Tempo-change
  fixture verifies x0/480/960 at0/1/3seconds. No public site assets changed.
- User-facing URL remains http://127.0.0.1:5185/ . Screenshot tracking.png private.
