# Modular riff builder — current delivery, 2026-11-05

## Playback shape highlighting — current request

- [x] Trace the exact shape material used by generation, including combined
  palettes and the selected fretting-hand window; keep generated music unchanged.
- [x] Show that shape on the existing fretboard as its timed block plays, using
  blue/orange for changes, dotted extensions and filled currently sounding notes.
  Keep open strings separate (gray string labels), intervals and all 24 frets.
- [x] Follow seek, pause, section transitions, repeated shapes, rests and the end
  of the riff. Do not pretend one section necessarily uses one source shape.
- [x] Verify metadata against the actual choice and unchanged output, timeline
  boundaries/random assembly, native playback and release build.
- [x] Verify publication and hosted behavior.

Root owns UI/integration/publication. Data agent owns engine trace plus public
engine/manifest and Python checks. UI agent owns a pure timeline helper/tests;
Planner reviews interpretation and evidence. No corpus expansion or pitch-rule
change. Strong counterexample: a union of two palettes or a trimmed contact window
must not be presented as one unchanged source shape. Missing geometry stays unknown.

`block.shape_usage` records the winning mode-compatible ordinary window, separate
tapping candidates, actual used contacts/opens and source role/shape IDs. Display
shows full ordinary windows only for multi-contact shapes, plus actual tapping;
single/open contexts get honest labels. Mixed core/extension evidence is retained,
with core taking visual precedence. Colors follow displayed geometry and roles,
not source IDs. Filled notes follow the written clock; native acoustic articulation
remains the player's responsibility.

Verification: all 80 JS tests pass, including 11 shape timeline/frame tests and
real public Python output; all 9 public pattern-engine Python tests pass; build
passes. Seven pre-edit complete-result hashes remain identical after removing
ONLY added shape metadata. Private/public engine copies match SHA-256
cab423c3eacb471c3b6adc0dae62399d863ba4932b533a6097f82d0fcc75ee33 and the manifest.
Planner independently reran 20 focused Python/JS checks and found no material blocker.

Published implementation df90006469b43ebcf969aa987a94d38c439a5fc8 (nine files).
Pages build 42129246304 and deployment 42129346867 passed. Hosted IA / Aeolian
arpeggio-interval then pedal-single example verified: quarter 0 shows Shape 1 blue,
five outlined positions, one dotted extension and two current notes; seeking to
quarter 8 shows Section 2 / Shape 2 / combined in orange, five outlined positions
and one current note. Quarter 16 clears all outlines/current notes/open labels and
reports End of riff; seeking back restores the correct shape. All 24 frets and
interval labels remain. Playback stayed stopped; verification exercised the same
written-clock display path via seek plus native/MIDI tests, not acoustic listening.
URL: https://mtch777.github.io/Guitar-Learning/riff-builder.html?v=df90006

## Exclude from random — current request

- [x] Add a compact checkbox dropdown named Exclude from random: Reference artists,
  Mode, Tempo, Style, Focus and Length. It applies to both random buttons.
- [x] Preserve excluded global values and each current section's excluded values;
  added sections repeat the current row sequence, while a single section uses row 1.
  Random seeds still produce new music. Preserve exclusions through every retry.
- [x] Choose remaining fields only from compatible available references. Refuse
  unavailable locked combinations without changing the locks or previous output.
- [x] Verify mixed/all/no exclusions, differing section rows, retries/refusal and
  actual engine generation; run relevant release checks.
- [x] Verify publication and the hosted UI.

Root owns page/worker/styles/progress/release; UI agent owns random helper/tests;
Planner reviews constraints and evidence. Core music engine and corpus stay unchanged.
Counterexample: locked Invent Animate + unsupported chord labels must not silently
become another artist/style. User-edited current settings, not the previous result,
are the preservation baseline. This UI feature does not change tier acceptance.

Local checks: `node --test tests/*.test.mjs` passes 69 tests, including 22 focused
random/exclusion checks; the public `test_riff_pattern_browser.py` passes 5 tests;
`npm run build` passes. Tests retain all six excluded fields through repeated A/B
rows and forced retries, reject impossible/invalid locks without sampling around
them, preserve the current snapshot through asynchronous calls, and verify distinct
actual Invent Animate / Aeolian outputs with all visible fields held fixed.
Native playback checks pass for both outputs. No listening-quality claim is made.

Published: 164196d3344b5d4ee536b404f8a1392e0782bbe7, exact seven-file commit.
Pages build 42127958220 and deployment 42128028148 passed. Planner independently
reran all 22 focused tests and reviewed the page/worker/helper integration.
Hosted checks: all six selected fields retained IA / Aeolian / 142 BPM /
arpeggio / single / two bars. Editing tempo to 153 and adding a one-bar pedal row
then requesting four sections preserved 153 BPM and the A/B/A/B style/length values.
An unavailable locked IA chord choice refused without changing that selection or
replacing the prior playable six-bar result. Checkbox selection/count, Escape
dismissal and player readiness verified; audio remained stopped.
URL: https://mtch777.github.io/Guitar-Learning/riff-builder.html?v=164196d

## Random generation — current request

User requested Generate random section and Generate random riff with a 1–10
section-count dropdown, sampling all available filter options.

- [x] Add both buttons and exact 1–10 count; random section creates a fresh one-section riff.
- [x] Sample one nonempty artist subset, E mode and tempo per riff, then independent
  available style/focus/length choices and seeds for each section. Keep chosen
  settings visible and editable after success.
- [x] Use the unchanged engine; bounded section retries retain successful earlier
  sections and record attempts. Reference availability is not proof of generation.
  Never substitute global settings after partial success. Failure retains the
  previous complete playable riff.
- [x] Verify 1/10 sections, unsupported-combination avoidance, exact event clocks,
  retry/exhaustion behavior, no input mutations, normal generation/regeneration,
  native playback conversion and site build.
- [x] Verify deployment and hosted UI.

Root owns HTML/CSS/page/worker/docs/release. UI agent owns riff-random.js and its
focused tests. Planner reviews scope and concrete outcomes. No corpus, production
composition controls, private input assets or existing music algorithms change.
Strong counterexamples: changing mode under prior sections; treating available
references as guaranteed success; wrong offsets/duplicate note IDs when assembling
multiple generated sections; partial failure replacing a complete prior riff.

Verification: `node --test tests/*.test.mjs` passes all 61 tests (14 random-generation
checks including the real public Python engine). `test_riff_pattern_browser.py`
passes all 5 tests. `npm run build` passes. The frozen ten-section seed 20261105
generates exactly ten sections in 13 section attempts and matches whole-engine
events/section evidence exactly. Native score/MIDI preserves 349 written notes:
344 fresh attacks plus five explicit legato-slide destinations, verified against
destination pitch bends and sustained origins. The initial attack-count mismatch
was an incorrect test assumption, not an adapter defect; no technique was removed.
Seed 73051 also produces a complete one-section result. Failed attempts stay in the
exported random-generation receipts; availability and bounded retries bias the
distribution toward feasible material, so equal output probabilities are not claimed.

Published implementation: b739f2ec854e068358e87246c948db019ffa24ce (exact seven-file
commit; no core engine or corpus changes). Pages build 42126684820 and deployment
42126742719 both passed. Planner independently ran the 14 focused tests and found
no material blocker. Hosted checks passed on the first live calls: random section
produced ERRA / Ionian / 85 BPM, one four-bar melodic single-note section; random
riff with count 10 produced Invent Animate + Currents / Lydian / 122 BPM, ten
sections totaling 30 bars. Selected settings populated the editable controls;
ten corresponding playback buttons, native tab, fretboard and Play-ready state
were present. Audio remained stopped; musical usefulness still needs listening.
URL: https://mtch777.github.io/Guitar-Learning/riff-builder.html?v=b739f2e



The existing site now connects artist/mode/independent section inputs to a shared
reference-pattern engine. This replaces the three fixed recipe buttons; the old
Python recipe assets remain only as regression evidence. No Composition Lab Cloud
controls, source captures or tier acceptance statuses change.

## Contract

- Artist multiselect strictly filters available source material: Invent Animate,
  Currents and ERRA. It does not weight artist taste.
- E mode: Aeolian, Dorian, Ionian, Mixolydian, Lydian or Phrygian.
- Add independent sections: style, mostly single notes/intervals/triads/chords or
  mixed, and 1/2/4 bars. Tempo 80–200. Generate a new complete riff or regenerate
  one section while retaining the other sections exactly.
- Reuse observed complete rhythmic units, including rests/subdivisions and each
  coattack member's own hold. Assign new ordered pitch roles into compatible
  Drop E shapes. Repeated anchors can remain; novelty is checked across a section.
- Existing fretboard/player, tab, speed controls and JSON export remain. Clicking
  a section starts playback there. Output is original-only, per user instruction.
- No arbitrary source cropping, quarter-note filler, artist/style substitution,
  automatic key selection or original/developed comparison.

## Evidence and current limits

Existing-logic transfer is complete: the 127-capture private library retains
original observations and adds verified pitch/voicing, technique and accepted
pedal-response relationships. Shared selector 14 tests pass; 1,260 frozen queries
separate retrieved material from feasible generation and preserve rhythm pools
when only mode changes.

The browser pack contains 701 short derived templates and 529 shape palettes,
supported by 1,592 observations from 88 captures / 57 songs. It is 211,152 bytes gzip;
full scores and private review prose are excluded. Thirty-nine captures supply no
supported template, including 26 without positive style tags. Boundary-held context,
crossing techniques and unimplemented effects remain visible exclusions. They are
implementation/data gaps, not evidence that those riffs cannot be changed.

Positive style tags belong to containing riffs, not every short local gesture.
The builder shows missing labelled material. In particular, Invent Animate lacks
positive melodic/chordal/rhythmic labels in this frozen library; it does have
arpeggio/pedal/other material with varied attack cardinality. Do not infer those
musical constructions are absent from the artist. Current labels need enrichment.

The first actual run exposed distant palette unions, held-contact reach omissions
and a per-block novelty restriction. Fixed before release: core/extension/tapping
roles retained; ordinary contacts stay within one six-fret region per short unit;
active held frets count; tapped-only contacts require tapping. Complete-unit
assembly backtracks, and unchanged anchors may support a changed response.
The first attempt remains in private EXAMPLES.first-attempt.json. The same seed 1
now generates all seven supported contrast cases; two admission failures remain.
This six-fret bound is an MVP search constraint, not a universal guitar rule.
Cross-section development, learned preference and human execution/listening
acceptance are not claimed.

## Verification and release

- 25 focused engine/pack/physical regressions pass (12 engine, 6 pack contracts, 7
  independent regressions). All six offered modes plus Currents/ERRA contrasts
  pass the fixed representative checks.
- 5 public Python tests pass: contrasted structures, exact Drop E/mode placement,
  request validation, deterministic generation, independent section regeneration,
  immutable pack and truthful no-match behavior.
- Native event adapter verifies actual generated pitches/onsets and written holds,
  plus unequal chord-member holds, cross-bar ties, rests, triplets and composite
  notation. Source expression marks remain explicit; articulation may alter sound
  duration. Native/MIDI correctness does not establish musical quality.
- `node --test tests/*.test.mjs`: 47 pass; existing Python recipe tests: 7 pass;
  `test_riff_pattern_browser.py`: 5 pass. `npm run build`: pass.
- Published main commit 229321f06d8153060effc2fd7bcd4d12f0c15029 using an exact
  14-file list and expected-head lease. Committed file list and asset manifest
  verified separately. Pages build 42120764917 and deployment 42120812491 succeeded.
- Hosted page verified: generation through the Python worker, two sections,
  independent second-section regeneration (first evidence identical), previous
  playable output retained after a genuine no-match, all-three-artist chord/interval
  request, Dorian request, seek, half speed, native tab/fretboard and Play ready.
  Audio stayed stopped; no listening quality or live-guitar approval is claimed.
- Planner independently reran 19 tests and audited all seven generated outputs:
  corrected physical scope, exact clock/member evidence and preserved failures pass.
- URL: https://mtch777.github.io/Guitar-Learning/riff-builder.html?v=229321f
- Next: user listening feedback on musical usefulness; targeted improvements to
  local style labels and shape transitions. Broad artist modeling and related
  section development remain outside this first independent-section version.

Private detailed receipts live in local-artifacts/fretboard-study-2026-11-04/
riff-engine-001. Public packaging is reproducible using package_pattern_browser.py;
pattern-manifest.json records both source and delivered asset digests.

---

# Hosted riff composer MVP — 2026-11-05

## Current UI correction — original only

User removed the original/developed comparison for this starting point.
- [x] Remove version controls, difference counts, changed-note coloring and comparison prompt.
- [x] Show/play only the original score; JSON download also contains only that score.
- [x] Preserve existing musical functions and earlier comparison evidence.
- [x] Verify build and hosted generation after publication.

The worker projects the existing generator's original score into the page result.
Historical paired-output Python API remains available for regression evidence;
its alternate score is not sent to the page or exported by this UI.

Published5965c0fec5e41b0d33fbac53e596060eae498e0f; Pages build42089870804
and deployment42089928331 succeeded. All36JS tests and Vite build pass.
Hosted browser verified original-only generation reaching Ready/Play, with no
version buttons, difference counts or changed-note legend. Original musical
functions are unchanged. The old page was briefly served during deployment;
the completed deployment was then verified using?v=5965c0f.

The implementation record below describes the initial paired-output delivery.

User request: the simplest existing riff composer, triggered from the existing
GitHub Pages site. This is a separate site delivery, not a change to the Cloud
Cascade controls assignment or tier acceptance.

The page runs the existing generation-002 Python recipe functions in a browser
worker. No server, credentials, workflow-dispatch UI, new generator, or corpus
upload. The MVP has the three existing recipes, tempo, original/developed output,
playback and downloadable results. Repeating identical inputs is deterministic.

## Acceptance checklist

- [x] Inspect current main, site deployment and existing composer; Planner start review.
- [x] Package unchanged musical functions and seven minimal source-derived cells;
  omit full commercial scores, source identities and private annotations.
- [x] Confirm all six default outputs equal the saved generated scores exactly.
- [x] Connect Generate to Python worker and results to existing alphaTab playback.
- [x] Verify tempo, original/developed, playback readiness, input errors and JSON download.
- [x] Run relevant Python tests, existing JS tests and site build.
- [x] Publish only owned files to main; verify deployment and served page.

## Progress

- Baseline main: dcd0fca2f65966c87cf69b881b170894116ff001.
- Existing deploy-pages.yml builds Vite and publishes gh-pages with historical files retained.
- Existing site uses alphaTab 1.8.4 and its sampled-guitar playback.
- Planner start review supports browser Python; critical counterexample is a
  Generate button loading canned results rather than executing the composer.
- Root owns integration/deployment; engine agent owns packaging/regression;
  UI agent owns the isolated builder page/worker. Other worktree changes are excluded.
- `python -B -m unittest discover -s composition-lab -p test_riff_browser.py -v`: 7 pass.
- `node --test tests/*.test.mjs`: 36 pass, including six native-score/MIDI comparisons
  and a tempo override. Optional native alphaTab tests explicitly skip in CI without
  the private local installation; source-score fingerprints still run without corpus.
- `npm run build`: pass. Minimal musical payload is 14,153-byte Python plus
  5,852-byte input JSON. No cache files included in the owned publication list.
- Native tests caught a read-only Score.tempo assignment; the adapter now uses
  tempo automation and all native note/clock comparisons pass. Musical taste is unchanged.
- Planner independently reran the Python tests and approved the bounded packaging.
- Initial localhost browser preview timed out. Hosted browser verification remains
  required after deployment; no browser execution claim is made from unit tests.
- Published main commit: ed9f42ff5a6a40a583a425ffa1ffd323bc5b875d. Pages publishing
  workflow 42085126171 succeeded. Public URL:
  https://mtch777.github.io/Guitar-Learning/riff-builder.html
- Hosted browser Generate executed the Python worker for all three recipes:
  Fracture Dialogue142, Open Orbit132 and Glass Counterweight175. All reached
  Ready/Play enabled with native tab and interval fretboard. Original/developed
  switches and half-speed selection passed; 7/2/2 and12/2/2 change summaries shown.
- Browser JSON download equals local generate('conversation',142) completely.
  Download tooling returned very slowly; no repeated download was initiated.
- Screenshot visually confirmed the hosted controls, 24-fret board and green
  changed contacts. Browser playback was kept stopped; no audible taste or
  real-guitar performance approval is claimed. Prior native/MIDI checks supply
  written-event fidelity evidence. The page is marked as the user deliverable.
- Local shared checkout retains unrelated work. Publication used an exact owned
  file list through GitHub's commit API, not a blanket staging/commit operation.
- Broader Composition Lab CI42085126130 also passed. The separate existing live
  pipeline preflight42085126493 failed before its browser test: its Playwright
  installation does not support the runner's ubuntu26.04-x64. Its site build and
  calibration checks passed. This is not reported as a passing browser preflight;
  hosted builder browser verification above was independently completed.
