# Hosted riff composer MVP — 2026-11-05

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
- [x] Connect Generate to Python worker and results to existing alphaTab playback (browser check pending).
- [ ] Verify tempo, original/developed, playback readiness, errors and downloads.
- [x] Run relevant Python tests, existing JS tests and site build.
- [ ] Publish only owned files to main; verify deployment and served page.

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
