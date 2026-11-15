# Bar harmony: separate analysis output

`bar_harmony.analyze_bar_harmony(source_bars, cells, tonal=None)` is a pure callable beside the existing musical analysis modules. It does not replace or mutate existing consumers, transpose notes, read files, or write outputs. It reuses `musical_tier2.THEORY_FORMS`, including power chords. No experiment modules or third-party packages are required.

## Input contract
All time coordinates are rational strings in quarter-note units. Use actual source bars, including pickups and meter changes, not inferred fixed4/4 windows.

- `source_bars`: sorted contiguous dictionaries `{bar: identifier, start_q: '0', span_q: '3'}`. Positive durations required.
- `cells`: sorted nonoverlapping time slices at actual note onset/release boundaries. Each has `start_q`, `end_q`, `pcs` (unique observed pitch classes0..11), `low_pc` (actual lowest active pitched note modulo12, or null), `unknown_pitch` (bool), `source_ids` (stable string identifiers), optional `role_evidence` (list of dictionaries with observed `pcs` from piano/rhythm channels).
- Build cells across all pitched channels, excluding percussion and unpitched dead notes. Preserve ties/sustains. Do not mistake lowest pitch class numerically for lowest MIDI pitch. Duplicate channels must not duplicate pitch classes. Unrepresented gaps mean no pitched evidence, not proven silence. Do not transpose to a chart's key.
- Optional `tonal.selected_collections`: dictionaries with `pcs`. Optional `tonal.original_report.ranked`: dictionaries with sharp-spelled `tonic` (C,C#,D,D#,E,F,F#,G,G#,A,A#,B) and numerical `score`. These are soft additional evidence, not mandatory gates. Use existing original-pitch tonal estimates.

```python
from bar_harmony import analyze_bar_harmony
rows = analyze_bar_harmony(
    [{'bar': 1, 'start_q': '0', 'span_q': '3'}],
    [{'start_q': '0', 'end_q': '3', 'pcs': [0,4,7], 'low_pc': 0,
      'unknown_pitch': False, 'source_ids': ['synthetic-example']}])
assert rows[0]['candidates'][0]['label'] == 'C:major'
```

## Output and interpretation
One row per source bar, exact start/end/length, observed pitch-class durations, sounding and unresolved fractions, source identifiers, ranked candidates and unknown weight. Status is `candidates`, `unknown`, or `no_pitched_evidence`. The last can contain drums; it is not silence.

Candidates expose observed cores, labels, individual score terms, simultaneity, extra notes and normalized relative weights. `confidence` is null intentionally: weights are evidence shares, NOT calibrated accuracy. No missing third is invented for a power chord. Sequential evidence can support a chord but can also be melody; `temporal_only` preserves that distinction. Roots currently must occur in evidence. The vocabulary is not exhaustive.

Weights combine duration, bass, chordal role, simultaneity, tonal evidence, conflicting thirds and a soft unsupported-extension penalty. Candidates are retained even when not first. Multiple chords in a bar can be alternatives; the main output deliberately does not split at each small change. Duration fraction matters when interpreting a strong normalized score in a mostly empty bar.

## Verification and scope
- [x] Portable callable; no experiment imports, file reads/writes or source mutation.
- [x]14 original behavior checks plus validation/nonmutation checks, discovered by unittest.
- [x] Source-bar count/coverage and original pitch evidence verified on six development songs in the local experiment.
- [ ] Application/UI consumer wiring: intentionally unchanged, separate output is ready to call.
- [ ] Musical accuracy acceptance: not established by technical tests.

Run `python -B -m unittest test_bar_harmony -v` from composition-lab. Existing CI discovers this test module. All Windows generated artifacts/temp/cache destinations must be F:. Local development evidence remains private; copyrighted source captures and chart extracts are not published.

Development outcome:3902 note-level factual sections became619 actual bars (555 with candidates,47 unknown,17 without pitched evidence). This is granularity, not accuracy. Midnight Hymn and Never There opening bar hypotheses improve; Feel the Same preserves unsupported thirds as power chords. Short Gb changes inside Ab/Gb bars can rank second. Naturehold root/inversion ranking remains unresolved. No full-corpus run or new holdout tuning was performed.

## Source delivery log
2026-11-15: ported018 without experiment imports; independent review checked scoring parity and identified malformed-context checks, now covered. Four unittest methods cover14 baseline checks plus invalid inputs and nonmutation. New module plus existing musical_tier2 suite:36 tests passed. Six development song outputs matched018 exactly before final validation-only changes; final recheck is recorded in the private run log. No UI/legacy consumer edits, no full-corpus run and no claims of calibrated accuracy.
