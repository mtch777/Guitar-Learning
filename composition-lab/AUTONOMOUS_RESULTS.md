# Consolidated autonomous experiment — 2026-10-15

All 16 workstreams were exercised. This is an exploratory research release, not completion of the genre-agnostic composition objective. Failed acceptance gates remain failed. No human listening judgment has been manufactured.

## Deliverables

- 100 generated, three-role, 64-bar GP files: 128 seconds each at the explicitly supplied 120 BPM / 4/4 target. Independent alphaTab import checks pitch, rational local timing, strings, tunings, instruments and bar counts. All 100 pass; all have zero implemented mechanical-constraint violations.
- 15 additional exported GP control examples (0/25/50/75/100 for harmony, melody and rhythm), independently imported and checked.
- Private consolidated review: 20 full-length pieces and two historical 16-bar generated references. The references are shorter; this is **not a matched full-song preference experiment**. Seven questions retain the user's terminology: idea development, meaningful pauses/holds and meaningful ending.
- Private ZIP `local-artifacts/autonomous-v1/Composition_Lab_Generated_Review.zip` contains the 115 generated/control GPs, review bundle, aggregate results and README. It excludes source scores, feedback, corpus and weights.
- Source-free aggregate evidence: [benchmarks/autonomous_results.json](benchmarks/autonomous_results.json). Raw note-level predictions, corpus, weights and commercial source inputs remain ignored locally.

## What actually generated the new batch

Official Yin-Yang generator weights sample a cached pool of 126 accepted two-bar phrases from 128 attempts, conditioned on grouped training MTC folk contexts. A locally learned contour/length state model proposes successive phrase states. Nearest learned clusters choose cached phrases; content repeats/truncates to the proposed 1–4 bar length. A locally fitted joint pitch-class-set/bass model conditions on the current lead pitch and beat position. Source instrument tunings/programs, fingering constraints and a quarter-note accompaniment grid complete the arrangement.

This is a hybrid learned/engineered experiment. **AnalysisGNN, GraphMuse and Partitura do not generate these notes.** AnalysisGNN remains a separate analysis benchmark. Fixed 4/4, 120 BPM, three roles, cached two-bar material and quarter-grid accompaniment limit this release. There are no learned drums, vocals or guitar techniques. The form model's failed gate means its output must not be presented as validated narrative development.

## Measured acceptance results

| Step | Result and remaining gate |
|---|---|
| 1 Freeze | 757 earlier files rehashed unchanged, including prior baselines and feedback. Baseline main b236c98. |
| 2 Representation | Cloud 5,314 occurrences → 5,001 sounding events, 313 explicit tie joins; Sweet 10,138 → 9,006, 1,132 joins. 100% occurrence coverage; no unresolved tie markings or overlapping inferred lanes. Independent source import agrees on attacks/ties. Three known Sweet natural-harmonic written/sounding pitch differences are explicit. Inferred lanes are hypotheses; raw global GP metadata is retained, not all performance techniques interpreted. |
| 3 Corpus | 2,000 MTC pieces, 1,686 family/content groups; 964 instrumental / 1,036 vocal. **Five-style target failed**: these are one folk tradition. MTC CC BY-NC-SA 3.0 research scope; no blanket commercial or checkpoint redistribution rights. |
| 4 Splits | 1,395 train / 312 development / 293 test, grouped by tune family and relative-content hash. Zero shared groups/families/exact-relative-content hashes across splits. Scratch models respect split; external pretraining overlap remains possible. |
| 5 Relationships | Original-occurrence-linked boundary, motif and simultaneous-harmony observations on both GP sources; confidence/unknown harmonic interpretations preserved. Twenty independently annotated contrasting GP pieces unavailable; semantic relationship accuracy remains unestablished. |
| 6 Structural validation | 21,180 held-out events / 1,573 boundaries. Learned exact-boundary F1 **0.571**, best simple baseline **0.354**. Below 0.70 target, not validated in guitar domain. Motif/section semantic truth remains unavailable. |
| 7 Architecture | Existing AnalysisGNN / Yin-Yang / guitar token and hierarchical research compared in context; runnable pretrained phrase inference, local adaptation, scratch boundary/form and joint-role paths. No claim that all researched architectures are integrated or licensed for redistribution. |
| 8 Phrase learning | Actual pretrained inference plus previous two-source adaptation/permutation experiments. Earlier official test: 53/53 matched contexts improve NLL; selector 48/53. Guitar adaptation did not reliably improve frozen inference. New 126-phrase pool is inference, **not evidence of guitar-domain learning success**. |
| 9 Form | 100 full outputs exceed count target, but held-out form-state NLL **4.4117** vs independent **4.2920**, shuffled training **4.4497** (lower is better). **Failed independent baseline gate.** Supplied progress bins and length buckets are explicit scaffolding. |
| 10 Roles | Source-disjoint joint-token NLL improvement 4.36% Cloud→Sweet and 11.27% reverse; one direction misses 10% target. Only two source songs; no 20-song claim or functional-harmony accuracy. |
| 11 Playability | 100/100 pass implemented frets 0–24, tuning, string uniqueness, simultaneous hand-span, duration/voice checks. Fifteen controls also pass. These checks do not certify musician playability, transitions, expression or audio quality. |
| 12 Controls | 2,000 cases; 400 positive structure requests explicitly infeasible. Remaining 1,600 feasible cases have zero exact-zero violations. Three-axis monotonic sweeps: 300, minimum Spearman ≈1. Harmony/rhythm mean achieved 0/25/50/75/100; melody 0/24.47/49.85/75.53/100. Independent structure/role control and perceptual calibration remain **unsupported**. Harmony control currently transposes voicings, not harmonic-function preservation. |
| 13 Compositions | 100 independently checked full GP outputs, 50 using each source's role/tuning observations. Distinct seeds/provenance saved locally; no musical-quality acceptance inferred. |
| 14 Originality | All 100 screened against two GP sources + 2,000 corpus pieces. No exact transposition-relative 16- or 32-event matches. Eight-event and coarse contour/rhythm matches are recorded. This limited screen is neither proof nor legal certification of originality; multi-style generalization remains untested. |
| 15 Musical validation | Private 22-case review prepared with A/B playback, piano rolls, GP downloads, seven ratings, local storage and JSON/CSV exports. Human quality, three-listener and controlled preference gates remain pending for consolidated collaboration. |
| 16 Workflow | Fresh-workspace CLI reproduced end-to-end with two 64-bar pieces and eight neural samples, independent imports, audits and a new review bundle. Main 100-piece run retained. Regression/build and remote release evidence recorded in EXECUTION_16.md. Five consecutive runs of this new pipeline have not been claimed. |

## Reproduction and review

Use `.venv/Scripts/python.exe run_composition_pipeline.py --help` from `composition-lab` (or prefix script with `composition-lab/` at repository root). Supply existing authorized local `--cloud`, `--sweet`, `--archive`, `--models`, `--alphatab`, `--node` and a **new** `--out` below `composition-lab/local-artifacts`. Defaults: 100 pieces, 128 sampled phrases. There are no hidden downloads or overwrite/resume shortcuts; commands, return codes and logs are retained in the private output folder. Torch/Transformers, NumPy, SciPy, scikit-learn and the local alphaTab module are required. Historical generated references must remain at the existing sibling native-ablation paths.

Executed individual commands at repository root:

```text
.venv/Scripts/python.exe composition-lab/benchmarks/freeze_evidence.py --out composition-lab/local-artifacts/autonomous-v1/frozen-evidence.json
.venv/Scripts/python.exe composition-lab/research_corpus.py --archive .local/yinyang-data.zip --out composition-lab/local-artifacts/autonomous-v1/corpus --limit 2000
.venv/Scripts/python.exe composition-lab/structural_learning.py --corpus composition-lab/local-artifacts/autonomous-v1/corpus/corpus.json --out composition-lab/local-artifacts/autonomous-v1/structure-v3
.venv/Scripts/python.exe composition-lab/build_neural_pool.py --models .local/yinyang-models-verified --corpus composition-lab/local-artifacts/autonomous-v1/corpus/corpus.json --out composition-lab/local-artifacts/autonomous-v1/neural-pool.json --count 128
.venv/Scripts/python.exe composition-lab/composition_engine.py --workspace composition-lab/local-artifacts/autonomous-v1 --count 100 --bars 64
node composition-lab/verify_gp.mjs ALPHATAB_MODULE GENERATED_GP_FILES
.venv/Scripts/python.exe composition-lab/batch_validation.py --workspace composition-lab/local-artifacts/autonomous-v1 --report-name validation-report-v2.json
.venv/Scripts/python.exe composition-lab/build_final_review.py --workspace composition-lab/local-artifacts/autonomous-v1
.venv/Scripts/python.exe composition-lab/package_experiment.py --workspace composition-lab/local-artifacts/autonomous-v1 --aggregate composition-lab/benchmarks/autonomous_results.json
```

These commands are evidence of execution, not an instruction to overwrite existing outputs. Source extraction/graph steps are included in the one-command runner. Structure-v3 corrects unknown-state smoothing in likelihood scoring; the persisted model hash equals v2, so generated sampling is unchanged. The earlier v1 review/validation files remain preserved. The v2 bundle adds the preferred questions; schema validation keeps prior review storage separate.

Open `composition-ablation-review.html?study=final`, then load the private `consolidated-review-v2.json`. If the desktop file picker fails, expand “File picker unavailable? Paste review JSON” and paste the file contents. No network upload occurs. Browser previews use fixed-gain simple synthesis, not Guitar Pro's instrument soundbank. Prefer the real GP files for arrangement/instrument assessment. QA uses `&qa=1` and is explicitly excluded from human feedback.

## Next research decisions after review

Use the consolidated outputs to select failures worth addressing; do not run another round of tiny pitch tweaks. The substantive open work is a rights-appropriate multi-style polyphonic corpus, guitar-domain boundary/motif truth, a form model that beats independent sampling, learned accompaniment timing/voice leading, and genuinely independent structure/role controls. These are research gaps, not UI polish or gates that a passing parser can close.
