# Source inspector: display coverage and limits

Private viewer only. Source scores, raw captures and derived records stay out of Git.
No detector, generation, approved pedal or musical-content changes.

## Data coverage

The builder prefers `relationships-unblock-v1.json` when present; otherwise
`relationships-v2.json`. The selected filename and exact report hash are shown.
Every song object is copied semantically unchanged. Original GP and track capture
bytes are copied unchanged. Selection is not a claim that every downstream report
uses the same revision or analysis schema.

| Stored fields | Display |
|---|---|
| Song identity/revision/family/partition/hash/flags | Complete field browser; metadata view; provenance |
| shared_layout, timeline, playback | Complete field browser / metadata; GP-driven bar navigation is separate |
| Song summary and layout_warnings | Complete field browser; not projected onto individual notes |
| Track name/part/identity/catalog flags/eligibility/warnings | Track choice, timing warning count and join diagnostics; complete browser |
| rows: pitch/string/fret/voice/onset/duration/section/effects | Live note cards; scrolling roll, marked notes purple; full note on expansion |
| rows: remaining raw_note/raw_beat_effects/flags | Complete note expansion / exact JSON; opaque values not interpreted |
| rest_spans | Track rest count; exact current-bar records and full browser |
| technique_values | Current source bend curve (fraction of written note vs semitones); full record |
| summary.marker_shares | Track technique meters, numerator/denominator and percentage; first-occurrence jump |
| summary.conditional | Marked/unmarked duration, register, bar position, next interval counts; full table expansion |
| summary.marker_pairs/value_histograms and technique_value_histograms | Complete field browser; no invented temporal alignment |
| sections and section summaries | Source section navigation; full nested summaries in browser |
| coattack_groups | Named group counts and first occurrence; current relationship diagram and full record |
| sustain_relationships | Current linked-note diagrams; singleton duration distinguished from tie chain; full records |
| hopo_transition_candidates/unresolved_hp | Linked current record when occurrences match; full browser; candidate status retained |
| pedal_candidates | Nested occurrence groups linked intact; candidate status retained, NOT approved detector output |
| grace_rows, physical_notation_flags, examples, counterexamples | Complete browser; occurrence-linked records when available |
| Original Songsterr track capture | Separate complete browser and existing raw JSON view |

All object keys, array elements, empty arrays, nulls and primitive values remain
available through lazy expansion. Search covers field names and values without
result truncation. This is complete access to loaded artifacts, NOT a claim that
every field has a bespoke chart or every project artifact has been integrated.

## Separate auxiliary artifacts (full files; not merged into live analysis)

- analysis-evidence-v2.json: technique evidence examples / supporting source context.
- api-field-coverage.json: API field coverage by source.
- pattern-robustness.json: stored pattern robustness records.
- source-techniques.json: per-song/track technique and group summaries.
- technique-validation-unblock-v1.json: validation errors, samples and labels.

Links retain original filenames; source files and hashes are unchanged. These are
raw-only report access. Their presence is not a new validation result. Historical
versions can disagree. Missing files are omitted from the manifest, not invented.

## Playback and meaning

GP importer drives audio, roll and playback clock; stored data drives analysis
cards. Exact occurrence/pitch/string/fret/local clock comparison remains visible.
Written segments are not equivalent to physical sounding sustain. Curve is source
analysis, not a promise of native GP bend fidelity. Unknown pitch stays unknown.
No musical quality or emotional intent is inferred. Existing 0-pause/1-normal,
1/8-step speed controls preserved. No public Pages assets changed.

## Observed coverage and verification (2026-10-20)

Scripted union audit of repaired source report: 98 songs, 495 tracks, 15 song
field names, 23 track field names, 22 row field names. This audits the chosen
report, not every private project artifact. Tree preserves arbitrary nested fields.

Browser checks: Cloud Cascade Rhythm I source bend (1 semitone), exact GP join,
nested relationship groups; Heavener simultaneous tapping + hp, advancing playback,
zero pause, raw capture fields, marked/unmarked conditional counts. Search returned
all six track timing-warning arrays in Cloud, including empty arrays. No console
errors observed. These are functional checks, not musical-quality judgments.

Python: 564 tests run, 563 passed, 1 optional skip (includes 5 unrelated local
uncommitted tests). Node inspector: 4 passed; nested-ID preservation/dedup added.
Builder fixture proves repaired-report preference and unchanged auxiliary bytes.
