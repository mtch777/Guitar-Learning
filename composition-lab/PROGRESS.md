### Actual external pipeline comparison — 2026-10-16

Implementation checkpoint **8531cc9** pushed; [CI 38934755234](https://github.com/mtch777/Guitar-Learning/actions/runs/38934755234) succeeded. Final source/results **fc4d033** pushed; [CI 38937715731](https://github.com/mtch777/Guitar-Learning/actions/runs/38937715731) succeeded. Completed actual source-conditioned official Yin-Yang generation/refinement/selection and official AMT sampling, not a renamed cached sampler. Results, commands, revisions, hashes, constraints and failures: [EXTERNAL_COMPARISON.md](EXTERNAL_COMPARISON.md). Nineteen GP outputs independently checked; six phrase / four fixed-lead arrangement review cases loaded using the current deployed UI. Human judgments blank; previous review and 757 frozen files unchanged. Negative-duration output rejected, paired seed retry retained; no-future controls resource-limited; source-motif copying flags explicit. Latest local checks: 106 Python / 16 JS tests / build pass. Private scores, model weights, source excerpts and existing human annotations remain outside Git. Existing review HTTP 200, deployed asset unchanged; no website source changed or private media published. Technical comparison ready, musical acceptance pending.

### Autonomous 16-workstream continuation — 2026-10-15

Latest source release **05ebae7**, rebased onto concurrent main b1e23c6 and pushed. Full measured status and acceptance criteria: [EXECUTION_16.md](EXECUTION_16.md), [AUTONOMOUS_RESULTS.md](AUTONOMOUS_RESULTS.md), and [aggregate results](benchmarks/autonomous_results.json). Generated 100 independently verified 64-bar, three-role GPs plus 15 control GPs. All 757 frozen earlier files unchanged. Grouped 2,000-piece MTC corpus; actual scratch training and pretrained inference; form/boundary/guitar transfer failures remain explicit. Independent structure/role controls remain unsupported. No human judgments fabricated.

Post-integration **102 Python / 16 JS tests / Vite build pass**. Composition CI **38839360124**, publisher **38839360119**, actual Pages deployment **38839387529** all succeeded. Live review HTTP 200 and expected built asset verified; 22-case private bundle loaded in delivered browser tab, 0 human cases reviewed. File-picker crash worked around with verified paste-JSON input. Generated-only review ZIP and raw results remain ignored locally. Next action: consolidated musical review, then substantive data/model decisions based on the failed gates rather than further tiny pitch-only experiments.

### Remote verification for learned milestone

`731b8ee` and `bc71c08` are on origin/main. Final source CI `38799052169`, Pages publication `38799052190` and deployment `38799112326` all succeeded. Working tree clean before this log update. No website/review content changed. Code and source-free aggregate reports published; checkpoints, upstream code/data, raw source tokens, private judgments and all newly learned GP/audio artifacts remain ignored/local. Learned phrase-conditioning demonstrated on original-domain author-listed held-out data; GP transfer and musical-quality gate still open.

### Official-domain model calibration follow-up

- Author-provided official data archive obtained locally (111.7 MB); included annotation license inspected, corpus kept ignored. No data or upstream code redistributed.
- Fixed an independent confirmation on remaining 80 test-list songs after the 20-song pilot: 76 eligible, 53 matched meter/key/mode negative controls. Generator real-context NLL 0.54374 vs wrong 0.99361 vs none 1.42736, 53/53 real-context wins; selector 48/53 correct rankings. Train/test filenames disjoint (23,733 train / 100 test), related melody-family overlap unknown.
- This is evidence of learned phrase conditioning in folk-domain annotated phrases, not guitar transfer or learned global form. Retain the external pretrained architecture as a reference. Tiny GP adaptations and new listening promotion remain unapproved by evidence.
- Implementation/source adaptation committed as `731b8ee`; calibration extension and final evidence follow in next commit. 93 source-free Python tests, 10 JS tests and production build verified.

### Learned experiment execution evidence

- Official 32,050,686-parameter phrase generator loaded strictly; actual pretrained and 10-step paired/permuted adaptations run in both source-disjoint local folds. Pretraining overlap unknown.
- Corrected source-token alias bug (Position_0 vs Position_0.0); superseded misleading initial gain. Corrected v3 overall NLL Sweet frozen/paired/permuted 1.04664/1.05648/1.06847; Cloud 1.63825/1.48743/1.48936. No reliable organization improvement.
- Ran official pretrained refiner and selector too: exploratory G,G,R,R chains, not learned form. Selector pair rankings Sweet 6/8, Cloud 1/2; insufficient musical validation.
- All 20 corrected GP files independently verified by alphaTab; MIDI/synthetic previews prepared locally. No listening review solicited or quality judgments invented. Artifacts: local-artifacts/learned-organization-v3 and learned-chain-v2.
- 93 Python / 10 JS tests and build passed; archive preparation/hash verification executed. Read LEARNED_ORGANIZATION.md and aggregate JSON for methods, commands, actual results, corrections and limits.
- Research/engineering test completed; musical organization acceptance gate NOT passed. Freeze small adaptations. Next substantial requirement is a less lossy sustained/voice-aware representation and larger rights-cleared song-disjoint corpus, not more ending heuristics.

## Learned organization milestone - 2026-10-15

Decision: freeze all heuristic outputs/review datasets; no new listening battery until an end-to-end learned method has reproducible evidence.

Acceptance criteria:
- [x] Sync main and recover current instructions/code; inspect actual external method code and checkpoint availability, separate weights/data licensing.
- [x] Compare at least three primary-source approaches; choose a runnable path, record restrictions and reject unsupported claims.
- [x] Implement source-preserving adapter and learned generation, with source/weights/tokenization provenance; real local GP artifacts independently checked.
- [x] Predeclare held-out split and metric before evaluation; compare context-aware prediction with matched shuffled/ablated context; no training or tuning on human reviews. Explicitly distinguish unknown pretrained corpus overlap from verified holdout.
- [x] Train/test or run pretrained inference; test input-conditioning sensitivity, validity, copying and failures. Report negative results rather than relabeling them progress.
- [x] Regression and CI; commit/push code and aggregate evidence only. Keep learned weights/private source-derived artifacts outside Git. No website changes intended.

Research started: official Yin-Yang repository cloned only into ignored .local at 59a2a001884a1f235ef9a0313565487874f6e3b9. It exposes phrase generator/refiner/selector and a public artifact download; code/weight redistribution license not established. Official MeloForm README describes expert-system scaffold plus neural refinement; full expert implementation not released there. AccoMontage targets piano accompaniment selection/style transfer, not source-native guitar phrase generation. Investigate dependencies/downloads before selecting.

## Passage feedback labels - 2026-10-15

- [x] Sync main; rename thread to Idea development; split combined rating into Meaningful pauses/holds and Meaningful ending, all B relative to A.
- [x] Retain existing thread judgments and legacy combined ending data; new fields start blank. Editing spreads existing records so legacy ratings are not discarded. Export v2 names each field explicitly; storage/dataset versions unchanged.
- [x] Browser QA verified independent ratings survive reload; 10 JS tests/build passed. Implementation `4f1ee57` pushed; Pages deployment `38793897213` succeeded and all three labels confirmed live.

## Audible passage experiment - 2026-10-15

User found the pitch-only set too subtle to judge. No forced preference inferred.

- [x] Freeze previous generated roles/motif baseline; preserve old studies and feedback.
- [x] Generate explicit 4/4 demonstrations: rhythm/breathing; rhythm plus shared contour and held answers. Accompaniment exact; lead timing/counts deliberately change. This is authored scaffolding, not learned phrase intelligence.
- [x] Export full and melody-only GP for both families and all three conditions; all 12 independently verified by alphaTab for pitch, timing, tuning/programs and MIDI. New developed leads have 60 notes each versus baseline Cloud 96/Sweet 176; this is a multi-variable demonstration, not a clean causal estimate for melody alone.
- [x] Package 4 opening/closing 8-second passages, full/solo modes and two experimental comparisons. One common gain per family/mode across all variants, no per-clip peak normalization. Old full GP baselines retained locally and in previous studies.
- [x] 84 Python / 10 JS tests and build passed. Browser QA measured synchronized switch A=6.04424s, B=6.04423s; verified mode/download changes, separate blank feedback for second experiment, QA persistence. Browser policy may require Play after mode changes; UI gives that instruction.
- [x] Implementation `fa40771` pushed; CI `38792353008`, Pages publication `38792352826` and deployment `38792416542` succeeded. Live page loaded with blank feedback, 8-second audio/no media errors and B playback. Manifest and sampled WAV/GP hashes verified. Musical difference/quality remains for human review.

## Targeted phrase experiment checklist - 2026-10-15

- [x] Freeze prior roles/motif GP and V2 hashes; use private human feedback without publishing annotations.
- [x] Implement a 2x2 pitch-only test: inherited baseline, linked contour, phrase-end chord-tone targeting, combined. Keep accompaniment, note counts, attacks/durations, tuning/programs unchanged. Predeclare unequal 3/5/3/5-bar phrase spans as experimental scaffolding, not learned boundaries.
- [x] Verify invariants, playable writing, independent alphaTab GP/MIDI, copying and boundary metrics; report regressions without quality claims.
- [x] Package a separate blind dataset with original baselines, isolated feedback version, preserved old review, and phrase-specific prompts.
- [x] Python 82 tests and JS 9 tests passed; production build passed. Browser QA verified separate 0/10 state, phrase prompts and B piano roll/playback.
- [x] Implementation `b43b6ff` pushed. CI `38789328167`, Pages publication `38789328210` and actual deployment `38789382287` succeeded. Live new study opened with blank feedback and B playback/roll working. Live manifest and sampled WAV/GP hashes match. Human preference remains unmeasured until reviewed.

See `PHRASE_EXPERIMENTS.md` for design, actual manipulation measurements and limits. Ten-case public set `5fd2e0965c77454d` preserves prior baseline GP/WAV byte hashes. AlphaTab independently verified all eight 16-bar controlled GP files, including unchanged 3-role counts, exact notation timing, tuning and programs. Original-source eight-event copying checks: Cloud all 0%; Sweet all 1.3746% against Sweet, 0% against Cloud. No musical quality inferred.

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

## 2026-10-16 — Time scripted bend test

- Pulled main ff-only from 18a4217 to fe762d9, preserving concurrent Songsterr work.
- Implemented standard-library-only bend_analysis.py and six tests; no AI/model calls for measurements or labels. Checklist, definitions and measured results: BEND_ANALYSIS.md.
- Ran supplied Downloads/time.gp; private occurrence report and generated Markdown under local-artifacts/time-bends/. Source SHA256 bd656f927c89b00fbc366b8659879d606937e4ff33fef60367023802c53aa89b.
- Independent alphaTab agrees on all 15 track note/attack/bend-segment counts. Exact explicit ties fully linked. Solo 37/153 bend-containing sustains; median duration 2 vs 2/3 quarter beats. Vocal bends, absent vibrato tags and absent solo rests limit interpretations.
- Actual verification: 112 Python tests, 16 JS tests and npm build pass. No website modifications; no Pages deployment required.
- Unresolved: artist-level corpus rates, validated phrase/harmonic relationships and performance interpretation. Reports explicitly retain unknowns. Next: extend tested relational queries and corpus coverage, without substituting AI labels.
