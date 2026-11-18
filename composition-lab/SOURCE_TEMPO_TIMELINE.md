# Opt-in source-tempo timeline

`source_tempo_timeline` constructs a declared score clock, NOT recording alignment. It is independent of generator/classifier defaults and performs no I/O.

Input is validated normalized metadata, not arbitrary raw Guitar Pro/capture dictionaries. Caller must recognize all source navigation/repeat/ending encodings and set `navigation_present`, normalize source field aliases, and explicitly supply zero/one-based measure indexing. Omitted tempo position/linear/type mean normalized bar-start/non-ramped/quarter-note only; do not silently treat unknown raw semantics as these defaults.

Supports discrete bar-start quarter-note tempo changes and rational bar durations. Rejects missing initial BPM, invalid values, intra-bar changes, ramps, unsupported tempo units and conflicting events. Repeats/navigation require an explicit playback order. Each visit stays distinct. Ambiguous tempo restoration at jumps is rejected when destination has no explicit tempo marker and inherited/current playback tempos differ; no universal restoration or carry-forward rule is assumed.

All returned times have `validation_status=unverified_score_clock`. Audio identity, recording offsets, performance drift, omissions/version differences and independent synchronization validation remain separate requirements. Do not feed these straight into the recording-evidence adapter as verified times.

Seven real-capture regression checks preserve constant-tempo duration on six songs. Agora's encoded116→96BPM change adds5.819s against the old single116BPM clock, and its separate audio experiment supported6/6 held-out attack blocks. That is acoustic support, not human ground truth or a general accuracy guarantee. Tests also cover explicit repeats, endings/navigation gates and ambiguous jump tempos.

Darkbloom also exposed an encoded repeat:89writtenbars become97visits, adding18.462s. Applying it does NOT prove recording alignment: held-out attack score fell0.2216→0.1912 and the source remains about19.76s shorter than the recording. Keep this failure unresolved, not corrected by another guessed tempo or omitted section. The constant-tempo regression comparison uses the same expanded visit order on both sides.
