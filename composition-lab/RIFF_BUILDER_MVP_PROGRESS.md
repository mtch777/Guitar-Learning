# Modular riff builder — current delivery, 2026-11-05

The existing site now connects artist/mode/independent section inputs to a shared
reference-pattern engine. This replaces the three fixed recipe buttons; the old
Python recipe assets remain only as regression evidence. No Composition Lab Cloud
controls, source captures or tier acceptance statuses change.

## Contract

- Artist multiselect strictly filters available source material: Invent Animate,
  Currents and ERRA. It does not weight artist taste.
- E mode: Aeolian, Dorian, Ionian, Mixolydian, Lydian or Phrygian.
- Add independent sections: style, mostly single notes/intervals/triads/chords or
  mixed, and 1/2/4 bars. Tempo80–200. Generate a new complete riff or regenerate
  one section while retaining the other sections exactly.
- Reuse observed complete rhythmic units, including rests/subdivisions and each
  coattack member's own hold. Assign new ordered pitch roles into compatible
  Drop E shapes. Repeated anchors can remain; novelty is checked across a section.
- Existing fretboard/player, tab, speed controls and JSON export remain. Clicking
  a section starts playback there. Output is original-only, per user instruction.
- No arbitrary source cropping, quarter-note filler, artist/style substitution,
  automatic key selection or original/developed comparison.

## Evidence and current limits

Existing-logic transfer is complete: the127-capture private library retains
original observations and adds verified pitch/voicing, technique and accepted
pedal-response relationships. Shared selector14 tests pass;1,260 frozen queries
separate retrieved material from feasible generation and preserve rhythm pools
when only mode changes.

The browser pack contains701 short derived templates and529 shape palettes,
supported by1,592 observations from88 captures/57 songs. It is211,152 bytes gzip;
full scores and private review prose are excluded. Thirty-nine captures supply no
supported template, including26 without positive style tags. Boundary-held context,
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
The first attempt remains in private EXAMPLES.first-attempt.json. The same seed1
now generates all seven supported contrast cases; two admission failures remain.
This six-fret bound is an MVP search constraint, not a universal guitar rule.
Cross-section development, learned preference and human execution/listening
acceptance are not claimed.

## Verification and release

-25 focused engine/pack/physical regressions pass (12engine,6pack contracts,7
  independent regressions). All six offered modes plus Currents/ERRA contrasts
  pass the fixed representative checks.
-5 public Python tests pass: contrasted structures, exact Drop E/mode placement,
  request validation, deterministic generation, independent section regeneration,
  immutable pack and truthful no-match behavior.
-Native event adapter verifies actual generated pitches/onsets and written holds,
  plus unequal chord-member holds, cross-bar ties, rests, triplets and composite
  notation. Source expression marks remain explicit; articulation may alter sound
  duration. Native/MIDI correctness does not establish musical quality.
-Publication/browser verification: pending in this current work record.

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
