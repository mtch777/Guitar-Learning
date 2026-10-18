# Exhaustive before/after pedal comparison

## Acceptance checklist

- [x] Freeze inputs: old pedal-feedback-v2/corpus-regions.json versus corrected
  pedal-register-review-v4/corpus-analysis.json, using relationships-v2.json.
  Full input SHA256 fingerprints are retained in the private catalogue.
- [x] Align identical song / part / source-section identities. Compare exact
  rational interval unions, not unmatched region counts or guessed phrase names.
- [x] Enumerate both directions without sample selection or silent quality
  filtering. Keep complete section yes/no flips separate from within-section
  extensions, retractions and other partial changes.
- [x] Build every changed span into the searchable UI, with consecutive bounded
  inspection parts, identical source notes under both highlight modes, complete
  pitch range, clickable source identities and a playback cursor.
- [x] Include actual context labels from neighboring source sections; do not turn
  a neighboring pedal gray merely because the selected change is elsewhere.
- [x] Provide cached local source playback on demand and unchanged full GP links.
  Display unavailable repeat/duration preview ranges explicitly instead of hiding
  them or pretending the timing matches. Scores and private data stay ignored.
- [x] Test interval subtraction/merging, exact tuplet boundaries, unchanged
  fragmented coverage and interrupted new chains. Run Python/JS/build and browser
  checks. Commit/push verified implementation; check remote CI before delivery.

## Results

Compared 1854 source scopes on the common eligible-track universe. Entire section
labels flip in 140 removed / 67 added sections. Including partial and boundary
differences produces 322 lost / 967 gained tagged spans, not 1289 inferred musical
phrases. A different selected anchor inside unchanged coverage is not a gained or
lost tagged passage and is outside these two lists.

All 1289 changed spans appear in the catalogue, split into 1844 consecutive review
parts. The audit checks 92168 written-note displays, zero duplicate occurrence IDs
within a part, and no skipped intervening part. 192 preview parts have unresolved
repeat mapping or excessive duration; their notes and full GP remain available.
No unsupported playback-timing claim is made for those parts. Source conversion
fidelity flags remain visible and are not silently excluded.

Old/new interval difference invariants are checked during construction. Merging
overlapping duplicate old tags avoids invented changes due only to fragmentation.
Boundary changes remain included, explicitly marked as partial changes rather
than novel musical discoveries. Corpus variants remain separate entries.

## Execution

Builder: songsterr_api/build_pedal_diff.py, with report, old regions, new corpus
analysis, private source songs directory and a NEW private output folder.
Server: composition-lab/serve_pedal_diff.py, with private output directory,
--port 5191, and existing local alphaTab module/Sonivox soundfont paths.

Private final output: local-artifacts/pedal-diff-v3. Prior partial builds remain
preserved. The renderer validates finite nonclipped nonzero source audio and
records source/media hashes. Preview requests are validated against a fixed job
index and serialized/cached; arbitrary filesystem paths or commands cannot be
supplied by the page.

Browser checks cover both complete lists, the whole-section filter, before/after
note changes, consecutive-part navigation and local audio preparation. This is
an inspection tool, not a new listening judgment or an accuracy certification.
Python unittest discovery: 243 tests, one optional skip; JS: 21 pass; Vite build
passes. GitHub run status is checked separately before reporting delivery.

## Piano-roll scaling correction

- [x] Reproduce the single-pitch roll: its 42-unit SVG viewBox was stretched to
  a 340px container, enlarging note height, label glyphs and outlines vertically.
- [x] Use actual container width and fixed 340px screen coordinates; cap note
  height at 12px, center narrow pitch ranges, retain full-range fitting, and
  recompute horizontal geometry on resize. Playback cursor uses the same plot
  coordinates as the notes. Source notes, durations and analysis are unchanged.
- [x] Browser verification: reported case retains all 24 notes, 12px rendered
  note height, 16px label bounds. Widest available range (55 semitones) retains
  all 92 notes inside bounds, with readable unstretched label text.
- [x] JS syntax and all 21 existing JS tests pass. Remote CI checked before
  reporting delivery; private served script updated from the tracked source.

## Full-passage roll correction (supersedes the cosmetic fix above)

The earlier fix capped drawing sizes but still showed only one audio chunk beneath
a heading describing the full passage. In the reported passage, part1 has24notes
at one pitch; all three parts contain109notes over a much larger range. That scope
mismatch made a technically complete chunk display misleading for passage review.

- [x] Default to the entire displayed passage, deduplicating occurrences across
  consecutive audio parts. Retain a checkbox for inspecting just the active part.
- [x] Show the active audio range explicitly in text and a blue outline; keep
  playback and note seeking mapped to the full passage's rational-time axis.
- [x] Add real keyboard/pitch rows, compact single-pitch layout, distinct note
  blocks, quarter-note grid and bar markers from original shared-layout metadata.
  Drawing gaps between blocks do not change source durations or playback timing.
- [x] Update the builder and all1289private comparison records with source bar
  positions. Notes, source scores, tags and rendered audio remain unchanged.
- [x] Independently compare full-passage occurrence sets against original source
  rows across all1289cases:92168note displays, zero missing or extra occurrences.
- [x] Browser:109whole-passage notes,24part1notes,47part2notes, full range visible;
  changing audio parts keeps the entire passage displayed. Clicked note x90.5
  matches cursor x90.49999 after seeking. Audio scope text matches each selected
  part. Repeated blocks are visibly separated, with readable pitch and bar labels.
- [x] Python243tests/one optional skip, JS21pass, production build pass. Commit
  and remote checks verified before final delivery. Human visual acceptance is
  not inferred from these mechanical checks.
