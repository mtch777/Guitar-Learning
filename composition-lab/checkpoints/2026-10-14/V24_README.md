# V24: Source-authored chord and section annotations

## Purpose
Recover author-supplied symbolic references from GP7 scores and attach them to the existing V21 review cases. These are **not verified human ground truth** and must not overwrite human-review fields.

## Result
- Chet Baker GP: 69 chord-symbol *occurrences* mapped from beat `<Chord>` IDs to staff `DiagramCollection` `Item.name` entries. These are source-author labels, not inference.
- Other four GP scores: no corresponding beat-attached chord diagrams were found using this extraction method.
- Across five scores: 54 section markers.
- Three of the 60 sampled cases coincide with an annotated chord beat; **57 remain without same-attack source labels**. This does NOT imply the other passages have no harmony.
- Human-verified chord labels: 0. No legitimate model accuracy metric exists yet.

## Safety/quality distinctions
GP `<Chord><KeyNote>` inside diagram definitions can be a placeholder; it is **not** the source chord identity. Use diagram `Item.name` (`Em9` etc.). Annotations describe the transcriber's intended symbol and may be incorrect; annotations on one beat do not automatically cover neighboring beats. No hardcoded genre assumptions or fabricated harmony continuation.

## Files
- `source_annotations_v24.py`: extraction and mapping to review CSV.
- `test_source_annotations_v24.py`: 7 tests.
- `V24_source_annotations.json`: every extracted occurrence and section.
- `V24_review_with_source_annotations.csv`: original 60 cases, unmodified human columns, and source-symbol context.
- `V24_annotation_report.json`: per-score counts and coverage.

## Reproduce
With `extract.py` and `music_events.py` from the checkpoint alongside the script, run `python source_annotations_v24.py`; then `python -m unittest test_source_annotations_v24.py`.

## Next proper accuracy step
Human-reviewed chord and phrase labels (ideally with several independent reviewers or consensus adjudication). Source-provided chord labels can be assessed as a distinct, *weakly supervised* reference set, but should not be treated as correctness by default.