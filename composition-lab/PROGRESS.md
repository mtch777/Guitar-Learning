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

## 2026-10-16 — Reference-freedom bend lever

- Implemented reusable fail-closed note-property edit transaction and scripted bend methods; canonical revised semantics in LEVER_IMPLEMENTATION.md and CODEX_CONTEXT.md.
- Actual Time run: seven private full GP outputs and six unique solo previews, bars 95–110. All unrelated XML and non-score archive entries preserved; zero output byte-identical. 100% choices invariant to removing all reference bends.
- Methods are generic frequency/duration/polyphony baselines, not an artist-trained model. Intermediate 25% retained original at seed17; no forced-difference or perceptual calibration claim.
- Validation: all seven alphaTab imports, 120 Python tests, 16 JS tests, Vite build. FFT test verifies rendered bend frequency; browser playback advances without errors. No listening judgments made.
- Private review served on loopback 127.0.0.1:5177; directory local-artifacts/time-bend-levers-v1. No public score/audio or website changes. Pending human judgments; other lever families remain future work.

## 2026-10-16 — Generated-only contextual bends, round 2

- User excluded original/no-bend controls and final-resolution issue. Built three generated-only variants: destination-aware, varied trajectories, and sparser placement. Exact locked base score preserved.
- Added contextual_bends.py, build_bend_v2.py and four regression tests. No AI inference. Targets use observed accompaniment support and following-note proximity; placement excludes overlapping solo sustains. Curves vary with duration and split continuously across ties.
- Three unique private WAV/GP cases, no original/no-bend review case. All independent alphaTab imports, locked XML/archive checks and reference-bend perturbation checks pass; zero encoding fallbacks.
- 124 Python tests, 16 JS tests and build pass. Browser playback verified mechanically; quality awaits listening. Private version0113f9d3324a61c8, directory local-artifacts/time-bend-levers-v2, port5178. No website deployment changes.
- Limits: engineering budgets/spacing and limited one/two-semitone vocabulary, unverified harmonic interpretation, no artist fitting or physical performance certification. Next: assess user feedback on destinations, timing/interaction, trajectory.

## 2026-10-16 — Explicit bend timing, round 3

- Added bend_timing.py and five focused tests. Research/feedback now informs explicit bend start, arrival, hold and release. Meter-aware arrival candidates scored with per-track-normalized pitch support at that instant. Selected notes/peaks held fixed across modes; no final-resolution objective or original/no-bend review cases.
- Enhanced GPIF property encoder to preserve delayed origins/early finishes; quarter-tone-safe tie seams. Independent verify_bend_curves.mjs confirms all 204 solo-note curves per case match alphaTab within 1.4e-15 semitone.
- Actual private Time experiment: three distinct 28.657-second excerpts, nine bent sustains each; 34 full-track selections and displacement targets identical. All non-bend locks/reference-perturbation checks pass. Private feedback from v2 preserved without public annotations.
- 129 Python tests, 16 JS tests, Vite build pass; browser playback advances without errors. Version675391ec9a09b75b; local-artifacts/time-bend-levers-v3; localhost5179. No website modification/deployment. Human quality unjudged.
- Limits: scripted choices, no artist fitting, base pitches remain literal locks, accompaniment observations are not adjudicated harmony. Pre-bends requiring re-fingering and broader vocabulary remain outside this isolated test. Next: listen to timing alternatives, retain supported improvements before broadening methods.

## 2026-10-16 — Current goal expanded to techniques and guitar patterns

- User requested a current tracked goal and execution steps. Created TECHNIQUE_ROADMAP.md with 12 steps, testable acceptance criteria, provisional definitions, locks/edit permissions, rendering/listening gates and source/privacy boundaries; active goal registered.
- Read handoff/context/AGENTS and pulled main ff-only (already current). Audited three private source XMLs: HOPO origin/destination property counts Time87/87, Cloud50/50, Sweet154/154. These are raw definition counts, not validated directed transitions.
- Found beat-level VibratoWTremBar in Time and Sweet (one each). Earlier note-tag-only absence was not complete vibrato coverage. Mapping beat effects is required prework.
- Clarifications requested for fretted pull-off meaning, tremolo type, double-stop category overlap. Independent preflight may continue. No feature-generation quality/completion claim. Documentation-only change; no website build/deployment required.

## 2026-10-16 — First technique and pattern analyzer

- Previous goal turn classified as progress: persistent goal/roadmap committed. This continuation implemented actual scripted analysis, not just planning.
- New technique_analysis.py: exact occurrence inventories, directed HOPO relationships, open/fretted classification, explicit-vs-eligible distinction, source-section counts, raw effect payloads, simultaneous vocabulary intervals and exploratory pedal windows. Source notes and raw XML remain private.
- Actual Time/Cloud/Sweet marked HOPO totals 87/50/154. All directed links independently agree with alphaTab, no unmatched markers. Guitar/bass-only transition breakdown and source-free summaries recorded in TECHNIQUE_ROADMAP.md and benchmarks/technique_analysis_results.json.
- Simultaneity uses half-open rational onset/end boundaries across voices; same-string conflicts excluded; percussion excluded. Dyad/chord labels are notated-base-pitch observations, with unresolved pitch-effect qualifiers. Pedal detector remains partial (especially polyphonic Cloud material); no artist/function inference claim.
- Verification: 142 Python tests, 16 JS tests, Vite build pass. Added independent verify_technique_links.mjs. No website changes/deployment needed. Active goal remains incomplete: technique-effect mapping, broader patterns, exact-lock generation, suitable playback and human validation remain.
- Three user definition questions still pending; no dependent scope silently settled. Next independent work: effect normalization and broader pedal evidence, then controlled fretted/open HOPO experiments with honest audio capability checks.

## 2026-10-16 — HOPO/vibrato controls and real-score batch

- User clarified fretted higher-position pull-offs, bending-based vibrato (not tremolo picking), and requested plain double-stop wording. Updated authoritative context and roadmap; no further category-choice question required.
- Added normalized explicit effect mapping with unknown rate/width preserved; general literal-lock note/beat property/tag transaction; separate fretted/open HOPO controls and finger-vibrato width control. Zero byte identity; full-freedom HOPO redaction covers malformed reference labels. Tied-sustain origin markers placed at terminal segments.
- Actual Time/Cloud/Sweet benchmark completed 30 nonempty modified GP variants. All unrelated XML/archive locks and 30 independent imports/directed-link/note-vibrato checks pass. Twelve source zero checks, 24 HOPO reference perturbations and three source vibrato-width perturbations pass. Private paths technique-edits-v2; public source-free aggregate technique_edit_results.json.
- Authored 7-GP diagnostic set and 7 finite/unclipped GM instrument WAVs. Native internal MIDI rendering fixed the previously unusable diagnostic path; no GP soundbank copied. Verified synth note pitches/on/off unchanged, HOPO destination dynamics changed and vibrato noncenter pitch events emitted. Authentic legato timbre not certified; no musical review falsely presented.
- Pedal queries now accept repeated anchor bursts separated by fills, support polyphonic co-attacks and respect annotated section boundaries. Cloud candidates observed; no inference of confirmed musical purpose. Synthetic counterexamples and tolerance probes added.
- First partial benchmark intentionally stopped for indexed-lookup optimization, preserved in technique-edits-v1. Profile retained privately; optimized v2 completed. No restart based merely on polling timeout.
- Tests: 158 Python, 16 JS, Vite build pass. No public website changes. Goal active; arrangement-pattern controls, broader validation, suitable technique playback and human listening remain open. Next: pattern construction/lock contracts and improved review rendering; retain all bend and technique baselines.


## 2026-10-16 — execute remaining technique engineering and review

- Pulled main ff-only c337e42 to 3d37d1f, preserved concurrent workflow changes. Sources/private annotations remain private.
- Added nested 0–100 release, paired HOPO flags/actual selection reporting, explicit pitch/voicing permissions and occurrence-cloned construction for all five pattern families. Original tables, rational timing, untouched events and archive assets verified.
- Pattern v1 rejected overly strict metadata eligibility; admitted only preserved stem metadata/empty XProperties. v2 completed thirty cases but sometimes selected bass; v3 thirty guitar-only cases independently imported. Time/Cloud/Sweet: 104/706/505 safe events per variant. Verifier explicitly separates written pitch from harmonic sounding pitch and excludes percussion.
- Multiscale reports retain track/section denominators, conditional distributions, staff inventory and unknown phrase/artist identity. Time arm-vibrato independently verified. Alternating pedal windows now also respect sections.
- Final technique-review-v6: eighty GPs/eighty finite/unclipped/nonzero instrument WAVs, higher-neck examples, 35 distinct A/B pairs. Earlier fixture/gate failures and baselines retained. One empty-strength pair and four identical-audio pairs withheld. No original/no-technique control offered, no human ratings invented.
- Browser verified ten selectors/both rolls, actual A/B playback, persisted QA feedback/export. Download check unexpectedly slow. Basic HTTP seeking reset to zero; added loopback byte-range server and verified synchronized timestamps. QA data explicitly isolated/labeled.
- unittest discovery:169 pass; JS tests:16 pass; Vite build:pass. Reproduction in TECHNIQUE_RESULTS.md. Public aggregate technique_construction_results.json contains no notes/annotations. No website change/Pages deployment needed. GitHub CI checked after push separately.
- Remaining human/physical acceptance, authentic legato, pedal/phrase labels and learned artist transfer. Generic rules are not style learning or originality certification. Next: consolidated review feedback and targeted fixes.

- Final notation/pattern checks: Time and Sweet arm-vibrato markers both independently match alphaTab. Exact transposition/time-scaling relationships added for alternating pedal candidates, retaining uncertainty about motif function. Tests:169 pass.

- Delivery commit 96fcbd126d31a848c069b05ca26eb4d58329b926 pushed to origin/main after pulling concurrent remote 301639a. Composition Lab CI run 39004239874 completed successfully: https://github.com/mtch777/Guitar-Learning/actions/runs/39004239874 . Final explanatory review text and this verification record follow in a small delivery commit.


## User-directed diagnostic corrections

- Pulled concurrent main d55ba40. User rejected source-unrelated authored study and opaque A/B; acknowledged mismatch. No new listening study or invented source/style claim.
- Inspected actual close demos: A all32 whole steps, B24 whole/8 half; shared classifier now accepts exactly one semitone, construction verified both corrected cases32/32 half steps.
- Removed fretted HOPO audio comparisons, kept open-string examples; methods visible by name. Removed rating questions.
- Former vibrato A=Slight (360ticks, amplitude0.5semitones), B=Wide (240ticks, amplitude1). Corrected preferred preview profile360ticks/.25semitones; new Slight generation emits explicit profile. GP marker remains qualitative. Independent MIDI comparison:1148 pitch-event ticks identical, offsets halved within2.4e-7 raw units.
- Corrected private bundle technique-corrections-v1 has8families/15clips, preserved old artifacts/feedback. This is a bounded correction before a different source-grounded path, not evidence of musical/style success.

- Correction verification:169 Python tests,16 JS tests,build pass. Actual alphaTab imports verify32/32 half-step dyads in each corrected texture clip. Fifteen WAV exports finite/nonzero/unclipped. Browser confirms removed fretted items/questions and explicit method labels. No public website changes.


## 2026-10-17 — acquire CSV corpus using Songsterr automation

- Read current main automation/usage/workflows, pulled8700931 safely; later resumed after automatic approval infrastructure usage-limit failure stopped execution. User status request resumed task. No completed files discarded.
- Added resumable CSV capture using existing pinned songsterr-dl backend, reversible seven-string GP5 bridge, native GP7 restore/export, source/model/serialized-source checks, independent reimport, named private score catalog and source-only technique inventory.
- Actual98/98 CSV entries/IDs captured,495tracks,98native GP7s. Fixed8string negative shifts, temporary metadata encoding, comparator None sorting errors (reported, not silently passed), exact source rhythm restoration, percussion grace mapping and importer omitted-voice bug. Full-bar silent voice rests allow all98 final GPs to reopen without patches.
-74/98 tested detailed GP7 roundtrip fields pass;24 conversion-difference files remain flagged.98/98 regular source-note/timing/tuning comparisons have zero detected differences in scope; dead notes compared as unpitched. Upstream serialized-source comparator489/495pass,4differences,2errors. Raw JSON/revision data retained as technique authority.
- Source inventory:415guitar/bass tracks,339385regular note segments,316030attacks,10064HOPO markers,858bend markers,2949slide markers,3349half-step coattacks. Not validated musical/function labels. Pedal burst lengths come from actual notation; no preset3/5 generation rule or artist-feel claim.
- Private deliverables: local-artifacts/invent-animate-corpus-v1/gp-files, catalog.csv, source-techniques.json, raw sources and validation reports. Only wrapper code/tests/docs/aggregate results staged. No public website change/Pages deployment needed.
- Tests:172main suite (171pass,1optional skip); all3 corpus-specific tests pass in isolated Python3.13environment. Standalone unmodified alphaTab reader:98pass/0fail. Next acceptance gates and detailed limits in songsterr_automation/CORPUS_RESULTS.md.

- Acquisition delivery c0621ec pushed to origin/main; Composition Lab CI39045738118 completed success. Reusable vanilla-import gate confirms98pass/0fail. JS16pass and buildpass. Follow-up delivery evidence records commands and keeps analysis/recreation acceptance open.
