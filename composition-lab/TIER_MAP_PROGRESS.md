# Time × tier example reset — 2026-10-20

## Acceptance checklist
- [x] One map shows exact rational time and all five tiers; spans derive from record times.
- [x] Separate simultaneous melody/harmony lanes; untimed contexts stay off the time axis.
- [x] Representative actual record variations across techniques, chords, modes, progressions, melodies and A/B forms.
- [x] Selected records expose exact JSON and direct previous-tier inputs/next-tier consumers; no tutorial/summary/inspector sections.
- [x] Synthetic scope explicit. Previous detailed example preserved. No private data included.
- [x] Targeted fixture checks pass: deterministic output, adjacent inputs, exact timing, pitch arithmetic/fingering, chord members, technique direction, ties, rest slots.
- [x] Browser: all 39 selector cases render; zero vertically overflowing record cards at actual narrow viewport. Chord JSON/input links opened and visually inspected.
- [x] Commit/push verified source; check exact-head CI.

## Work and evidence
Replaced the rejected inspector layout with a shared-coordinate map, grouped fixture selector and one on-demand JSON drawer. First narrow-screen screenshot exposed off-screen tiers; corrected by transposing time horizontally and tiers vertically below 900px. Wide layout retains vertical time. A subsequent overflow sweep across all 39 cases found zero vertical card overflows. Desktop geometry is implemented but no independent wide viewport screenshot was available in this browser session.

Commands: `build_tier_map.py` generated 39 cases; `python -m unittest discover -s composition-lab -p test_tier_map.py` passed 5 tests. Full regression and JS syntax results recorded below after execution.

Limits: illustrative data only; no new GP analysis, generation, playback or musical-quality claim. These examples are local source assets, not part of the public Pages build. Unrelated local proposal/analysis files preserved.

Final local verification: full Python suite 578 tests, 577 passed and 1 optional skip (includes 5 pre-existing unrelated local tests); JS module `node --check` passed. Browser selected note relation showed input/parent links and separately named chord_ref/previous_ref links, with corresponding highlights. Fixed tier labels staying above cards during horizontal pan. Final screenshot: ignored local-artifacts/tier-map-review.png. ProjectPlanner3000 reviewed source, requested explicit descriptive references and corrected legacy README entrypoint; both addressed. No planner listening or live-browser review claimed.

Delivery: 4b35609 pushed to origin/main; Composition Lab CI 39494394130 completed success for that exact code commit. Available JS regressions: `node --test tests/*.test.mjs composition-lab/test_source_inspector.mjs` passed 28/28. Production build: `node node_modules/vite/bin/vite.js build` passed (npm command absent from PATH; same Vite build invoked directly). Public build excludes this local example; no Pages change/deployment claimed.
