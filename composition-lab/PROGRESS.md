## Piano roll A/B fix - 2026-10-15

- [x] Fetch/fast-forward main without overwriting local work.
- [x] Roll follows A or B automatically when playback starts, with explicit A/B selector and sketch label. Comparison changes reload B notes; seek/playhead/scroll follow the displayed player. Stale asynchronous loads are discarded; filters reset for the new score.
- [x] Browser QA: B Sketch 02 loaded one part, changing B to Sketch 04 loaded three; empty-space seek advanced B to 6.2s while A stayed 0; Play A restored A roll. Feedback storage/version untouched.
- [x] Node tests: 8 passed; production build passed; diff whitespace clean.
- [x] Pushed implementation `4491f92`; CI and Pages publication passed. Actual Pages deployment `38788256548` succeeded; live B playback selected B / Sketch 02 and displayed its notes. Existing ten human reviews remained intact.

# Composition Lab execution ledger

## Current continuation — recovered inputs and interactive review

Historical missing-input entries below were superseded: the private ZIP was found in Downloads after concurrent remote updates, extracted safely, and all manifest hashes verified. Real pretrained inference and source-conditioned ablations now run; see `benchmarks/RESULTS_2026-10-15.md`. Implementation commit `53531ec` was rebased on concurrent `5518966` and pushed; Composition Lab CI and Pages publication succeeded.

Interactive review acceptance (user explicitly requested the previous UI be found/read/adapted and a deployed link):
- [x] Inspect both older review UIs; preserve the chord/phrase and riff-pair tools and their storage keys.
- [x] Package ten generated sketches (four ablations plus V2 for each source family); exclude commercial originals, source-derived timelines, private reviews and weights.
- [x] Interactive blind A/B playback, seek/loop/speed, piano roll and note audition; no setup upload.
- [x] Case-specific autosave, no stale-case notes, explicit uncertainty, reveal audit, JSON/CSV export and safe feedback restore.
- [x] Unit tests, browser interaction/visual verification, JS/Python regression and production build.
- [x] Commit/push without overwriting concurrent main changes; verify Pages workflow and live URL/assets; deliver link.

### Published review evidence

- Implementation `aeb89b3c89a7d5020c56936b03248697086f4a9f` pushed after fetching and confirming no concurrent divergence. Composition Lab CI `38777752444`, browser preflight `38777752422`, Pages publication `38777752443`, and actual Pages deployment `38777803832` all **success**.
- Live https://mtch777.github.io/Guitar-Learning/composition-ablation-review.html opened in browser with **0 of 10 reviewed**, methods hidden and blank notes. Manifest exactly matches the ten-case package; live Cloud WAV (1,433,294 bytes) and Sweet GP (5,462 bytes) SHA256 match local assets.
- Link is ready for human review. No preference or coherence claim is inferred from QA. Feedback remains browser-local until exported. Older initial checklist and blocker entries below are historical; current measured results supersede them.

### Review implementation verification

- Browser QA used `?qa=1`, a separate storage namespace explicitly excluded from human feedback. A/B playback paused the other player; Save/next advanced and played; case notes and uncertainty survived reload; reveal unlocked the generated GP link; piano-key audition displayed F5; JSON export downloaded successfully; Sweet study opened with blank case-specific notes. Desktop layout and expanded piano roll inspected visually.
- `python -m unittest discover -s . -p 'test_*.py' -q` in composition-lab: **79 passed**. `node --test tests/*.test.mjs`: **8 passed**. `npm run build`: success, includes new review entry. `git diff --check`: clean.
- Reused useful behavior from the old chord/phrase and riff-pair UIs; both remain intact. New standalone page provides ten generated sketches, direct audio, piano roll, blind ratings, local autosave, reveal audit, JSON restore/export and CSV export. Homepage links to it.
- Public package includes only generated GP, synthetic preview audio and their note timelines; source scores, private answer files, model weights and actual user feedback remain excluded. This is UI verification, not a musical judgment.
- Next action: collect real human listening feedback through the deployed review. Human listening remains the next research gate.

## Acceptance checklist — 2026-10-15

- [x] Recover instructions and current main; clean checkout at `0a6886b`; `git pull --ff-only origin main`: already current.
- [ ] P1: reproduce Cloud/Sweet conversion from original GP; occurrence-matched MusicXML timing/pitch/voice audit; explain each of 18 historical discrepancies from source evidence; actual pretrained outputs and comparisons. No accuracy claim without independent labels.
- [x] P2 engineering implementation: exact rational graph with stable occurrence identity, voice succession, simultaneity, overlap, ties, track/beat/bar membership, exact/transposed motifs and interpreted phrase/harmony/section membership. Synthetic cross-bar tie, polyphony, changing-meter and ambiguity regressions pass. Source-corpus semantic validation remains open.
- [ ] P3: four same-seed ablations exported as local GP; reparse and independent renderer verification, metric report, baseline hash preservation and blind playback protocol.
- [ ] P4: source-conditioned multi-role phrase generation, playable voicings, coherent progression/development; deterministic measured target distances, exact zero locks, explicit infeasible requests.
- [ ] P5: independent held-out sources, copying audit, full relevant regressions and playback review; preserve artifacts locally, never invent judgments.
- [ ] Publish verified source and ledger on origin/main, preserving concurrent work; verify Actions. Verify Pages if website changes.

## Evidence and blockers

- Inspected both review UI purposes, Vite entrypoints, composition CI and Pages workflow; no website modifications planned.
- Source-score and MusicXML searches: workspace, G drive, user Downloads/Documents/Desktop and other mounted drive roots returned no `.gp`, `.musicxml` or `.mxl` inputs. Earlier `/mnt/data` paths are historical, not present inputs. Cloud V2 GP baseline also unavailable; checkpoint generator source preserved unchanged.
- Python 3.10 available; global torch present, torch_geometric/partitura/graphmuse/analysisgnn absent. Created isolated `.venv`. Initial PyPI sandbox DNS failed; retry with network approval.
- Upstream README inspected at https://github.com/manoskary/analysisgnn : default model downloads from W&B; pyg-lib required by graphmuse. Model redistribution and corpus licenses remain separate.

## Next action

Implement independently verifiable event relationships and GP/MusicXML occurrence audit while investigating dependency availability. Source-dependent benchmark and listening remain open.

## Implemented and verified in this run

- Fixed sparse voice-slot loss in the rational extractor. Retained source SHA and raw track/master-bar/bar/rhythm/beat/note XML; `exact_score.py` avoids the older top-level extractor.
- Added rational relational graph and occurrence-audited MusicXML view. Overfull voices fail explicitly; do not claim the historical 18 Sweet discrepancies are resolved without source evidence.
- Hardened AnalysisGNN preflight: real subprocess imports, active-interpreter module execution, isolated outputs, expanded harmonic tasks, nonempty CSV/hash evidence, nonzero status on blocked runs. Tests verify that exit zero without predictions is a failure.
- Added explicit-plan controlled generation, joint string/fret fingering, exact zero representation locks, measured target deviations and whole-phrase-block rearrangement. This is a limited prototype, not a trained composition engine. Roles/harmony evidence must be supplied; no source role inference claimed.
- Added GP authoring without a copyrighted compatibility shell, alphaTab independent pitch/timing/tuning checking and MIDI export, descriptive per-track metrics, copying checks, byte-hash holdout leakage guard, anonymous sine-MIDI preview and blank review CSV.
- Fixed an existing review CSV crash: `review_candidates.py` read `novelty_score`, but `validate_structure.py` produces `score`. Existing three failing tests now pass.

### Actual verification commands/results

- In `composition-lab`: `python -m unittest discover -s . -p 'test_*.py' -q` — **76 passed**.
- In checkpoint directory: same discovery command — **138 attempted, 109 passed, 24 errors, 5 skipped**. Errors reference unavailable private `/mnt/data` GP/CSV fixtures. Full checkpoint suite is **not passing** in this clone. Tests were not weakened or relabeled.
- Bundled Node: `node --test tests/*.test.mjs` — **4 passed**.
- Local npm CLI: `npm ci` — succeeded with locked dependencies. `npm run build` — succeeded, Vite 7.3.6, including `dist/composition-review.html`.
- `python controlled_generation.py --demo --out local-artifacts/verified-2026-10-15` — created reference plus four experimental `.gp` files, four MusicXML views, exact timing audits, graph/plan JSON and metric manifest. Authored fixture only; **not** requested source-trained ablations.
- `node verify_gp.mjs <local alphaTab 1.8.4 module> <all five GP files>` — all imported with **3 tracks / 8 bars / 72 notes**, expected pitch/local timing/tuning matched; MIDI files exported.
- Partitura 1.9.0 independently loaded all four generated MusicXML views with **72 notes each**.
- `.venv/Scripts/python.exe playback_review.py local-artifacts/verified-2026-10-15` — five nonzero 16-second synthetic previews, 72 MIDI notes each, blank review CSV. **No listening judgments collected.**
- Baseline source `generate_composition_v2.py` unchanged. Original Cloud V2 GP unavailable and cannot be substituted with the engineering reference.

### Measured controls (percent changed plan units)

| Experiment | Harmony | Rhythm | Melody | Phrase order |
|---|---:|---:|---:|---:|
| harmony | 75 | 0 | 0 | 0 |
| rhythm | 75 | 16.67 | 0 | 0 |
| melody | 75 | 16.67 | 16.67 | 0 |
| phrase-order | 62.5 | 25 | 33.33 | 100 |

Targets for stages 2/3 were rhythm/melody 25; target harmony for stage 4 was 75. Manifest truthfully reports misses and observed candidate ranges. These are discrete engineering distances, not perceptual calibration. All stages have explicit roles; source-trained role ablations remain pending.

### Dependency investigation and outstanding gates

- Isolated `.venv` installed CPU torch 2.5.1, torch-geometric 2.8.1, Partitura 1.9.0, AnalysisGNN source package, prebuilt pyg-lib/scatter/sparse/cluster, Lightning, music21, W&B and GitPython. No global Python changes.
- Upstream AnalysisGNN pinned/inspected at `e115182fb29b74bdcb6bf3547ed427d967580947` under ignored `.local/analysisgnn`.
- GraphMuse unavailable as a matching PyPI distribution; cloned upstream and attempted native build. Actual failure: **Microsoft Visual C++ 14.0 or greater required**. No compiler found in inspected Visual Studio paths, and `wsl --list --quiet` returned no distribution. Did not patch out native samplers or fabricate inference.
- Final `analysisgnn_preflight.py --run --out local-artifacts/analysisgnn-final-preflight` — blocked/nonzero: GraphMuse not importable, AnalysisGNN transitively fails on GraphMuse, no source MusicXML inputs. Local JSON manifest retained. No pretrained predictions, comparison or accuracy result produced.
- Source locations requested from user while independent work continued. Required: original Cloud/Sweet GP, historical MusicXML (if retained), Cloud V2 GP, and held-out source material. No private source/annotation/checkpoint artifacts staged for publication.
- P1 source benchmark, actual P3 source ablations, P4 learned role/phrase engine and P5 held-out listening remain **open**. Next action is source-level discrepancy reproduction and functioning native inference environment, followed by source-conditioned plans and actual listening comparisons.
