# Learned organization experiment: preregistered protocol

2026-10-15. Freeze all prior heuristic outputs and private feedback. No further listening UI changes in this milestone.

## Research decision

- Yin-Yang (Bhandari et al., 2025): official https://github.com/keshavbhandari/yinyang at `59a2a001884a1f235ef9a0313565487874f6e3b9`; paper https://arxiv.org/abs/2501.17759. Phrase generator/refiner/selector pretrained on monophonic folk phrases. Chosen for a narrowly scoped generator/conditioning experiment; this is not a reproduction of the complete three-model framework. Full form remains externally supplied in that framework, not automatically learned.
- MeloForm: https://github.com/microsoft/muzic/tree/main/meloform . Expert scaffold plus neural refinement; official README explicitly says only neural-network code is released. Not a drop-in learned form engine.
- AccoMontage: https://github.com/zhaojw1998/AccoMontage . Phrase selection and style transfer for piano accompaniment; useful multiscale precedent, but not a guitar/lead composition replacement.

Yin-Yang official artifacts downloaded from README's Google Drive id `1cMGRjUonP3qoKtHA_gqc39GZA4O_zdbh`, 890 MB archive, SHA256 `1a4d3c7c482d27a6a53ee8ea8615f87749fede29d9033ba94bba956194152627`. Extract only configuration/tokenizer/model dictionaries with checked paths; load torch dictionaries with weights_only=True, strict keys. No training_args pickle is loaded. No repository code or checkpoint license was established; do not redistribute upstream code, weights or corpus. Paper license does not establish code/data/weight license. Adapter/experiment are original in-house code; dependencies remain ignored.

## Fixed protocol before metrics

Two cross-song folds: fit on Cloud, evaluate Sweet; reverse. Pretrained corpus membership of these exact songs is UNKNOWN, so only local adaptation is source-disjoint. Do not call this a verified pretraining holdout.

Monophonic attack view: voice 0, highest pitch per written event; grace and tie destinations excluded; tied attack durations are written durations, not merged sustains. Original canonical sources unchanged. Every exclusion and timing rounding recorded. Only complete 4/4 windows, two bars context + next two bars target, stride four; this is a fixed continuation task, not phrase-boundary inference. Unsupported timing tokens/windows rejected; no silent token deletion. Nearest vocabulary timing allowed only within 0.005 quarter notes. Instrument, velocity and technique are absent from this pretrained vocabulary.

Training: all non-percussion tracks in fitting song, deduplicate identical context+target pairs, fixed first 32 eligible unique pairs, 10 AdamW updates, learning rate 0.00005, seed 17, batch 1. This is a small adaptation probe, not adequate stylistic training. Train paired and deterministic context-permuted controls from identical pretrained weights, same targets/update count. No test-based model selection or parameter adjustment. Evaluation: selected Cloud lead track 0 / Sweet lead track 3, deduplicate identical pairs, first up to 8 eligible windows in source order. Tiny/repetitive coverage is a limitation, not evidence of robust evaluation.

Primary checks: teacher-forced target-token mean NLL with real context versus another held-out context and no context; frozen pretrained versus adapted; paired versus permuted training. Tokens include structure/pitch/time, so this is not a perceptual score. Record paired count and every row; no population confidence claim from two songs. Source sensitivity: same random seeds and grammar, change source/context and compare output token hashes. A change proves dependence, not meaningful organization.

Generate local GP continuations from pretrained and paired/permuted-adapted checkpoints with seeds 17 and 29; no inference-time motif/ending rewrite. Grammar restricts model samples to valid two-bar monophonic 4/4 timing and target instrument pitch bounds; explicit representation/playability constraints, not learned coherence. Decode strictly, retain raw sampled IDs, reject truncation/invalid candidates rather than quietly repairing them. Exact fractions and native tuning/program in GP; independent alphaTab validation and MIDI playback artifacts. Copying audit against both private sources and structural validity; no musical-quality/originality claim.

Decision gate: call out positive or negative context effects and adaptation generalization. Do not solicit another listening battery solely because model inference or GP writing succeeds. If evidence is weak, preserve result and identify next substantial model/data requirement.

## Follow-up preregistration: full learned phrase components

After the generator-only run, Cloud had no distinct evaluation contexts and adaptation's gain was largely timing/position rather than pitch. Do not interpret it as learned long-range form. A separate follow-up will check the official pretrained selector's ranking of real next windows versus wrong-target windows (same fixed eligible source rows; no fitting). Identical targets excluded from contrasts. Selector score is the official last-logit sigmoid, not calibrated musical confidence.

Generate an 8-bar local prototype with four 2-bar generated blocks, compare generator-only against generator plus pretrained refiner and selector, seeds 17/29 for each source. All starting content in exported GP is newly sampled, not the source context. The explicit block schedule is G,G,R,R: masked-pitch and masked-duration variants of the first generated motif enter the refiner for blocks 3/4; request CA_True only on the final block. Select among three candidates using the pretrained selector. No hand-written contour or target-note corrections. This is a source-conditioned, learned phrase-content pipeline with an authored schedule, NOT learned global form or a complete Yin-Yang reproduction. If selector ranking or context evidence is weak, do not promote output to another listening battery. Record raw candidates, scores, rejection reasons, copying checks and final GP. This follow-up is exploratory, not an untouched confirmatory test of the earlier protocol.

## Implementation corrections, before reporting conclusions

Exploratory v1 mismatch rotation sometimes supplied identical context; v2 marks unavailable contrasts null and chooses genuinely different contexts where possible. V2 tokenization then revealed a more important confound: lexical tie-breaking chose Position_0 rather than the upstream float spelling Position_0.0. That produced an artificial large adaptation gain in position prediction. Regression added; v3 uses canonical float aliases. Earlier v1/v2 aggregate gains are superseded, not evidence of musical learning. Chain v2 reruns the same schedule with corrected input aliases. No model hyperparameters or test membership changed in response to the metrics.

## Corrected actual results

Primary artifacts: ignored `local-artifacts/learned-organization-v3` and `local-artifacts/learned-chain-v2`. V1/v2 continuation metrics and chain-v1 inputs are superseded by tokenizer/control corrections. Source-free aggregate evidence is committed as `benchmarks/learned_organization_results.json`; full tokens, per-window data, adapted weights and scores stay local.

| Adaptation train / evaluation song | Frozen NLL | Paired adaptation | Permuted-context adaptation | Evaluation pairs |
|---|---:|---:|---:|---:|
| Cloud / Sweet | 1.04664 | 1.05648 | 1.06847 | 8 |
| Sweet / Cloud | 1.63825 | 1.48743 | 1.48936 | 2 |

Lower is better for token prediction only. Each fold prepared 32 unique training pairs but the fixed 10-update probe actually used only its first 10 targets. Sweet adaptation on Cloud is nearly matched by permuted training; Cloud adaptation on Sweet slightly worsens overall frozen-model NLL. There is no reliable demonstrated organization gain. Pitch-only NLL on Sweet changes 2.37891 -> 2.27450 (permuted 2.30909), while Cloud changes 3.22506 -> 2.92441 (permuted 2.91512). Aggregate improvements in one token family do not establish musical improvement.

Real context beats distinct mismatched context in 5/8 Sweet windows for the frozen model and 4/8 for either adapted condition. Cloud's two unique context/target pairs have identical contexts, so it supplies **zero usable context contrasts**; those mismatch values are null. No-context losses are higher, but that is an unequal-length/conditioning ablation, not proof of phrase semantics. The particular first distinct Sweet context pair tested with seed 17 produced identical sampled output for all three model conditions, despite differing token likelihoods. This single probe does not establish general insensitivity, but it fails our desired strong perceptible-conditioning check.

Selector: real target ranks above wrong target in 6/8 Sweet and 1/2 Cloud cases. These are tiny overlapping-content, nonrandom samples, not accuracy estimates; sigmoid scores are not calibrated confidence. The eight exploratory 8-bar chains (two families x two methods x two seeds) all serialize and independently match alphaTab pitch, timing, native tuning/program and MIDI. No candidates were rejected in those actual runs. Generator-only note counts: Cloud 35/59, Sweet 35/43. Refiner/selector: Cloud 51/43, Sweet 64/64. Different counts do not imply better structure. Exported GP includes only sampled notes, not original input motif/context.

All 12 corrected two-bar outputs independently passed the same checks. Twenty corrected GP files and corresponding MIDI/sine previews are local. Exact relative eight-event copying matches are zero where sufficient windows exist; at least one short output has no eligible windows (null, not zero evidence). This limited audit does not establish originality. Preview preparation is mechanical; no listening judgment is invented. No website or review dataset changed.

Verification: 93 source-free Python tests; 10 JS tests; production build passed. Optional ML runtime: Python 3.10, torch 2.5.1+cpu, transformers 4.34.1; gdown 6.4.2 only for official download. `pip check` reports pre-existing optional AnalysisGNN dev requirements black/flake8/pytest absent; runtime inference ran successfully. Full historical checkpoint tests remain separately limited by missing private fixtures, as documented earlier.

## Reproduce

1. Download official artifacts as documented in the upstream README to ignored `.local/yinyang-artifacts.zip` (do not download/publish its corpus).
2. `python composition-lab/benchmarks/prepare_yinyang.py .local/yinyang-artifacts.zip .local/<fresh-model-directory>` verifies the pinned archive and extracts safe model dictionaries. The helper was executed and hashes verified against the actual inference files. Model dictionaries use strict `weights_only=True` loading; no remote execution or pickle training arguments.
3. `python composition-lab/benchmarks/learned_organization.py --models .local/<model-directory> --sources composition-lab/private-sources --out composition-lab/local-artifacts/<fresh-experiment>` performs fixed adaptation/evaluation and produces GP/weights/raw evidence. Output must be in ignored local-artifacts and fresh.
4. `python composition-lab/benchmarks/learned_phrase_chain.py --models .local/<model-directory> --sources composition-lab/private-sources --out composition-lab/local-artifacts/<fresh-chain>` runs exploratory generator/refiner/selector chains.
5. Run existing `verify_gp.mjs <alphaTab module> <GP paths>` to independently check all expected canonical events and export MIDI. Use `playback_review.render_midi` for local previews. No automatic listening-quality assertion.

## Decision and next substantial work

**Gate not passed:** do not promote this to a new listening battery or claim learned global form. This turn completed an end-to-end external learned-model/adaptation test, not the composition-engine objective. The tested model is monophonic folk-domain, not multi-role GP-aware, and its form schedule is supplied. Research supplies a useful architecture pattern, not a finished solution.

Preserve the frozen external model as a reference; do not promote the small adapted checkpoints. Next data/model work should (1) preserve sustained melodic identity through polyphony/ties rather than picking highest written attacks, (2) establish a larger rights-cleared, song-disjoint and stylistically varied corpus with reliable structural evidence, and (3) learn cross-role/phrase relationships before re-testing long-range organization with robust context controls. Additional per-note ending rules are not the main path. Training on these two songs or tuning to the user's review cannot resolve the corpus/generalization bottleneck. Code/weight redistribution rights also remain unverified, so weights and upstream code are not published.

## Follow-up preregistration: official split calibration

Before assessing the model's guitar-domain suitability, evaluate the frozen generator and selector on the first 20 eligible official test-list songs, in author-provided order, first annotated phrase -> second. No adaptation/tuning. Verify test/train filename disjointness; distinct melody-family overlap is unknown. Wrong-target/context controls use another eligible song, preferring the same meter, with exact duplicate token content rejected. Inputs follow original numeric token spellings from released JSON and key/mode metadata; target length/cadence annotations are not supplied. This differs from the GP projection and is a calibration, not a direct performance comparison.

Official README data download `1DhtQV0-jVH1lOreqXY5V8L1qHOSO5PwZ`, archive SHA256 `3f1b11c8416eea63fd9bad9229877160dc5e518d0f22b026aaee7ae18964c4da`, 111,713,460 bytes. Read JSON directly from ZIP; do not extract/publish corpora. Included annotations/LICENCE_Data assigns MTC feature values CC BY-NC-SA 3.0 and distinguishes ESSEN provenance; that does not establish unrestricted rights over all derived scores or checkpoint weights. Keep everything local, commit aggregate measurements only. This official-test calibration is exploratory and does not retroactively make either guitar source a verified pretrained holdout.

Official pilot calibration: 18 same-meter contrasts all favored real context, but key differences could explain that. A stricter same-meter/key/mode recheck left 7 contrasts: 7/7 favored real context, selector 5/7. Do not present that post-hoc stricter pilot as a confirmatory population estimate. To test the finding independently within the supplied split, now lock the remaining 80 test-list songs (indices 20 onward), identical token budgets and same-meter/key/mode matching, no adaptation. All compatible pairs are reported, with exclusions; no further metric-driven changes. This remaining-song check precedes its actual measurements.

## Official-domain confirmation result

Completed frozen-model evaluation on remaining 80 author-listed test songs, with no fitting. 76 met token/phrase budgets; 53 had a distinct wrong context/target with matching meter, key signature and mode. Generator real-context NLL **0.54374**, wrong-context **0.99361**, no-context **1.42736**; real context lower in **53/53** pairs. Selector ranked the real continuation higher in **48/53** pairs. The preceding same-key pilot was 7/7 and 5/7 respectively, not merged into these confirmation counts. Of the 80 songs, four failed eligibility and 23 eligible songs had no matched negative within the selected pool. No training/test filename overlap with the listed 23,733 training songs, but related tune-family overlap cannot be ruled out. Metrics use first two human-annotated phrases, so this does not test automatic phrase discovery or complete-song generation.

This establishes useful **learned phrase-conditioning evidence in the original monophonic folk domain**, not perceptual quality, global form, genre-agnostic behavior or successful guitar transfer. It rules out concluding that this architecture has no useful learned context behavior just from the weak GP-domain test. Retain it as a reference. Do not promote the tiny adapted guitar checkpoints or declare the composition engine solved. The GP-transfer/listening gate remains unpassed; no new human listening battery is requested.

Reproduce the official check with `python composition-lab/benchmarks/yinyang_official_test.py --archive .local/yinyang-data.zip --models .local/<model-directory> --lists .local/yinyang/artifacts --out composition-lab/local-artifacts/<fresh-official-check> --start 20 --limit 80`. Data JSON is read directly from the ZIP; no corpus material is committed. Corrected local learned GP artifacts remain available in the two ignored directories cited above.
