# Recording-time review export

`export_recording_review(segments, recording_duration=...)` is a pure, opt-in packaging helper. No file I/O, model loading, classification rules or default-pipeline changes.

Each input segment requires a unique nonempty `id`, `start_seconds`, `end_seconds` and full `candidate_weights` distribution. Other metadata (such as decoded label/provenance) is preserved. Empty weights require explicit `status: unknown`. Inputs must be finite, sorted, nonoverlapping, within the recording and distributions must sum to one. Invalid mass is rejected, never silently normalized.

The output retains every detected boundary and candidate alternative. Adjacent sections sharing a winning label are NOT merged: identical winners do not imply identical function evidence. Leading/internal/trailing uncovered intervals are explicit unknown gaps. Outputs are deep copies, not caller aliases. Candidate scores remain uncalibrated, and neither labels nor timings become verified through export.

## Why preserve boundaries?
A frozen two-song diagnostic showed merging same-label sections hid pre-chorus alternatives and reduced reference-role top-three coverage in one song. Preserving sections recovered information without changing any winning labels. This is NOT an accuracy improvement or a reason to fit thresholds to the evaluation songs.

## Validation
Eight focused tests cover retained same-winner boundaries, different distributions, gaps, unknowns, invalid timing/mass/IDs, and no mutation. Combined with recording-evidence and source-tempo regressions:40 tests passed. A12-recording smoke test preserved159 detected segments and all distributions, with12 explicit short uncovered tails against original file durations. No audio, lyrics or model weights included in source.

Example input:

```python
segments = [
    dict(id='1', start_seconds=0, end_seconds=4,
         candidate_weights={'verse': .9, 'pre-chorus': .1}),
    dict(id='2', start_seconds=4, end_seconds=8,
         candidate_weights={'verse': .55, 'pre-chorus': .45}),
]
review = export_recording_review(segments, recording_duration=8)
# Two distinct evidence records remain, despite the same largest weight.
```
