# Musical-field implementation and source comparisons

- [x] Timing/identity: normalize marker text; validate song/revision/part identity and metadata vocal/empty flags; shared meter/pickup layout; explicit rest spans and bounded repeat/ending playback order. Acceptance: exact rational written occurrences retained; malformed/conflicting observations reported, no silent repair.
- [x] Technique values: exact source bend/whammy curves including precise positions and point vibrato; tremolo fractions and brush native values. Acceptance: correct quarter-tone/semitone units independently checked; unknown native units remain explicit.
- [x] Relationships: tie-aware sustained gestures, overlaps and technique-to-neighbor/context measurements; tempo/sound timelines. Acceptance: observations distinguish written/sounding hypotheses; no invented phrase/function labels.
- [x] Run corpus and refresh field-coverage matrix. Acceptance: all98 entries/495tracks processed, note counts reconciled, prior outputs preserved privately, unmapped fields fail strict audit.
- [x] Source comparisons: actual existing source GP passages, selected technique changes only, literal zero byte locks and all unrelated XML/archive members locked. Acceptance: actual GP outputs independently reopen; render nonzero variants with source/track/bar context and measurable audio differences; no authored riff or fretted-HOPO listening substitute.
- [ ] Tests/build, persistent results, commit/push main and verify CI. Listening/feel acceptance remains for the user; do not mark it passed from serialization or synthetic audio.

2026-10-17: main0713557 clean/up to date; read handoff/context/current analyzer, audit and exporter/transaction tools. Found previous raw-source bend summaries mislabeled tone/25 quarter-tone units as semitones. Correct raw semitone scale is tone/50, consistent with alphaTab quarter-tone model and GPIF analysis. Existing GP conversion preserves raw tone units; no claim that existing audio was doubled. Correction will be versioned and old private outputs retained. Captured precisePosition uses0..100 versus coarse position0..60;25/216 points differ from the coarse fractional position. Corpus tempo.linear is absent/false throughout; unsupported ramp conventions must not be invented. Brush duration/shift remain native until units can be independently established.

## Verification 2026-10-17

- Fresh ff-only origin/main pull: already current; local work preserved.
- Corpus rerun completed: 98 entries / 495 tracks; independent validator: 420119 raw occurrences, 190890 attack groups, 9707 HP-pair invariants, zero failed checks. 168 private inspection seeds / 14 strata. See results/technique_validation.json.
- Rebuilt evidence: 88 cases / 2904 raw-readback occurrences. Strict API audit: 218 paths, zero unmapped.
- Main environment: 207 Python tests, 206 pass / 1 optional dependency skip. Isolated converter environment: 21 songsterr + 16 source + 2 validator tests pass. JS: 18 pass. Vite build pass.
- New validator fault-injection tests detect missing groups and corrupted durations. No model inference or fabricated labels used.
- New results and family contract: MUSICAL_FIELDS_RESULTS.md and TECHNIQUE_ANALYSIS_CONTRACT.md. Outstanding: independent semantic truth, pedal function, phrase interpretation and musical listening acceptance. Earlier 24 source GP roundtrip flags remain.
- Delivery: source/aggregate commit and CI/Pages verification pending below. No private source, raw evidence, audio or feedback will be staged.
