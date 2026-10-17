# CSV corpus acquisition and source-grounded technique work

2026-10-17. **All 98 CSV entries acquired as reconstructed GP7 `.gp` files**, with all available tracks. This is a collection of transcription versions, excerpts, adaptations, collaborations and AI-labeled entries; it is not 98 independent verified artist compositions. No original uploader binaries or new artist-feel results are claimed.

## Measured acquisition results

- 98 distinct Songsterr IDs, 98 captured revision/metadata sets, 495 raw track JSONs and 98 GP7 scores.
- All 98 GP7 files reopen with **unmodified alphaTab 1.8.4**. No special importer patch is needed to read the delivered files.
- All 98 have zero detected differences in the direct regular-note comparison of tuning, written fret/string and declared beat duration. Dead notes are compared as unpitched, not mistakenly interpreted as an open-string fret; grace and percussion mapping are excluded from this particular comparison.
- 74/98 pass the detailed GP model → GP7 → reimport comparison, including the tested rhythm, note, tie, HOPO, vibrato, slide, harmonic and bend/whammy fields. 24 remain flagged for differences, mainly pitch curves; one instrument-program normalization is also flagged. **This is not a lossless corpus.**
- The independent upstream raw-source → serialized GP5 comparator passes 489/495 tracks; four have detected differences and two hit a comparator error on unpitched note data. Every result and converter warning remains in the private catalog/capture reports.
- Source notation and revision metadata remain authoritative for field-level technique analysis. A lost export marker must not become evidence that the artist did not use the technique.

## Private deliverables

All are under `composition-lab/local-artifacts/invent-animate-corpus-v1/`:

- `gp-files/`: 98 scores named with Songsterr ID and title.
- `catalog.csv`: CSV-row provenance, title, artist, revision, score path, conversion checks/warnings and raw-source folder for every entry.
- `songs/<ID>/`: immutable captured revision metadata and raw track notation, intermediate bridge/map, generated score and detailed validation report. Unsupported fields remain in raw JSON.
- `source-techniques.json`: first source-based technique inventory, separate from export fidelity.
- `vanilla-imports.json`: independent unmodified-reader results, 98 passed / 0 failed.
- Earlier probe/derived outputs remain preserved for diagnosis; source scores and private annotations are not committed to Git.

## What changed in the existing automation

The existing `songsterr-dl` backend is reused, pinned locally to commit `a5e6ec76bd30bb626f4381bb78baef7e20ec2c21` (1.2.0), using Python3.13.16. Its seven-string GP5 writer failed immediately on an eighth-string note. The adapter temporarily splits strings into GP5-compatible parts, then restores the original track count, tuning and string identities before writing native GP7. Tests serialize and restore all eight strings.

Exact source durations that GP5 cannot spell are restored before GP7 export. Curve simplification removes only redundant straight/flat points; functional bend/whammy comparisons sample all 61 integer GP bend positions, so different point-list spellings do not masquerade as pitch-curve changes. Unrepresentable/different curves remain failures. An alphaTab GP5 missing-voice bug is guarded during import; explicit full-bar silent rests normalize omitted secondary voices so the final scores reopen normally. Percussion grace-note articulation is repaired from its original drum value. Source metadata Unicode is restored in GP7 after temporary GP5 text folding.

No upstream source is vendored. The installed converter checkout and dependency environment stay ignored locally. Their provenance and licensing remain separate from source-score rights.

## First source inventory — observations, not musical validation

415 guitar/bass tracks contain 339,385 regular written note segments (316,030 non-tied attacks), including 10,064 HOPO-marked, 858 bend-marked and 2,949 slide-marked segments. The query finds 3,349 half-step co-attacks on distinct strings, plus power/extended-power/double-stop candidates. Marked vibrato is sparse; annotation absence is not absence in performance.

Recurring-anchor queries return source-evidenced burst lengths including 1, 2, 3, 4, 5, 8, 16 and others. These overlapping candidates are not independent phrases or adjudicated pedal roles. **No prescribed three/five-note generation pattern is substituted for these observations.** Co-attack vocabulary does not yet certify sounding intervals under bends/harmonics or sustained cross-beat overlap.

## Reproduce

Use the existing pinned backend in an isolated Python >=3.13 environment with PyGuitarPro. Source capture is resumable and restricted to the ignored artifact directory.

```text
python composition-lab/songsterr_automation/songsterr_api/download_csv.py PRIVATE_CSV --out composition-lab/local-artifacts/invent-animate-corpus-v1/songs --upstream LOCAL_PINNED_SONGSTERR_DL
node composition-lab/songsterr_automation/songsterr_api/export_csv_gp7.mjs ALPHATAB_MODULE composition-lab/local-artifacts/invent-animate-corpus-v1/songs
python composition-lab/songsterr_automation/songsterr_api/analyze_corpus_sources.py composition-lab/local-artifacts/invent-animate-corpus-v1/songs --out composition-lab/local-artifacts/invent-animate-corpus-v1/source-techniques.json
python composition-lab/songsterr_automation/songsterr_api/catalog_csv_corpus.py composition-lab/local-artifacts/invent-animate-corpus-v1 --summary composition-lab/songsterr_automation/results/csv_corpus_acquisition.json
```

GP7 export skips already passing reports; `--recheck` explicitly regenerates owned derived exports. The catalog refuses to overwrite a differing existing score copy. Retain old derived versions separately before refreshing that copy. Never enable the older workflow's `save_to_repo` option for this corpus.

## Next acceptance gates

1. **Identify:** build inspectable, source-located examples and counterexamples for each technique; separate observed markings, inferred topology and human musical function. Resolve/filter conversion-affected fields. No precision/recall claim without labels.
2. **Analyze:** query natural distributions and conditional relationships by song, track, section and verified phrase context. Keep differing transcriptions grouped to prevent train/test leakage; curate AI/adapted/collaboration entries before any artist-style fitting.
3. **Recreate exactly:** preserve source pitches, exact timing, voicing and performance observations in a selected real passage; verify export and actual technique-capable playback before changing context.
4. **Transfer to a slightly different context:** change one declared dimension and measure the relationships that should survive. Source evidence determines repetition lengths, responses, density and technique placement.
5. **Create new material:** use held-out source relationships and copying checks to generate controlled novelty, then judge whether it retains source feel. Parsing and annotation counts cannot answer that listening question.

No new generic authored listening exercise, invented emotional labels, or successful feel-transfer claim accompanies this acquisition.

Verification: main Python suite 172 tests (171 passed, one optional PyGuitarPro test skipped); isolated converter environment runs all three corpus-specific tests successfully. Actual corpus import/comparison results are stored separately from those tests. Public result JSON contains aggregates only. No public website changes or Pages deployment required.
