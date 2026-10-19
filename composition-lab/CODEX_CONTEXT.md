## Autonomous artist-pipeline work (2026-10-18)

Read AUTONOMOUS_COMPLETION.md for the current persistent checklist and evidence.
Pedals remain approved/closed. Artist profiles, literal-lock controls, role-pitch,
performance and full-song form prototypes have verified private GP batches;
technical validity is not musical acceptance. Commits8319749 and0141e82 passed
GitHub CI. Four full-song previews last122–299seconds; no listening verdict.
Current investigation: source/generated context distributions and an opt-in
same-source-bar cross-role pattern experiment. Preserve independent-role defaults,
old outputs and all private source/model/audio exclusions. Do not infer completion
of steps2–8 from these bounded checkpoints or reopen approved pedal detection.

## Pedals approved — complete (2026-10-18)

User approved the additive continuation review and explicitly said “done with
pedals.” Pedal identification, call/response boundaries and additive phrase
expansion are accepted for the current milestone. Do not reopen generic pedal
identification/listening work. Preserve the accepted detector and expansion pass
as a regression baseline. Next work belongs to broader artist profiles, technique
methods/transfer, levers and composition; approval is not validation of those.

## Additive pedal continuation (2026-10-18)

Latest user direction: keep detection unchanged; expand established phrases only.
Read songsterr_automation/PEDAL_EXPANSION.md and PEDAL_EXPANSION_PROGRESS.md.
Separate pass: pedal_expansion.py; exact anchor, later answers/returns, stronger
earlier-evidence requirement, disjoint merges. All 2,239 support chains retained;
178 expanded/combined outputs in four private review queues on loopback5196.
No seed deletion/shortening or original-role changes. Detector hash unchanged.
Prior port5195 review remains intact. Listening acceptance of expansion is pending.

## Pedal evidence correction (2026-10-18)

Read songsterr_automation/PEDAL_EVIDENCE_CORRECTION.md and
PEDAL_CORRECTION_PROGRESS.md. `pedal_evidence.py` adds strict later-answer timing,
local anchor proof, written-chord/tie handling and final role validation. Baseline
`pedal_register.py` and old artifacts remain unchanged. New runner option:
`rebuild_pedal_review.py --evidence`; do not silently promote the experiment.
Sealed evaluation: 28/28 bounded decisions and 176/176 marked notes; 1,854 scopes
fully audited. Two short excerpts differ from their complete support context;
three complete patterns expose the evidence rather than cropping it. Human
musical acceptance remains pending. Private review is loopback-only; sources,
feedback and commercial-source playback must not be published.

## Pedal acceptance reopened (2026-10-18)

Latest requirements/code mismatch: songsterr_automation/PEDAL_CRITERIA_AUDIT.md.
Current register hypotheses do not establish local anchor identity or independent
response timing. Acceptance remains open; UI improvements are separate.

Read songsterr_automation/PEDAL_BOUNDARY_INVESTIGATION.md before the historical
acceptance below. Pedal-register correction and source-identical review replace
the old labels for review, pending human judgment. Current implementation:
pedal_register.py and songsterr_api/rebuild_pedal_review.py. Preserve old methods
and artifacts as baselines; do not confuse corpus integrity with musical accuracy.

## Current pedal milestone (historical)

User accepted pedal identification after the fresh-song review. Do not reopen that
review. New goal is exact call/response relationships; see songsterr_automation/
PEDAL_DIALOGUE.md. Corpus analysis measured16814operational exchanges across1563
regions with exact occurrence audit, pitch/rhythm/texture/technique/gap/overlap and
same-call answer-family evidence. Source examples remain private. No generation or
musical-intent claim. Current work shifts toward using these observed relationships.

## Latest step2 continuation (2026-10-17)

Read songsterr_automation/PATTERN_ROBUSTNESS.md. Added pedal overlap collapse,
exact normalized nonoverlapping recurrence, rhythmic sensitivity and sustained-note
construction sweep. Private pedal-identification-v2 at port5185 is six unchanged
source passages with highlighted proposed anchors and full/focused audio, not a
technique-edit comparison. Previous brush/transfer review was premature and is not
an analysis acceptance gate. No human judgments entered. 211 Python tests (one
optional skip),18JS/build pass. Semantic anchor function remains for independent
judgment; source-only rule metrics are not musical accuracy.

## 2026-10-17 musical-field validation update

Read songsterr_automation/MUSICAL_FIELDS_RESULTS.md and TECHNIQUE_ANALYSIS_CONTRACT.md. Latest local implementation supersedes the earlier 65-path coverage snapshot: 114 analyzed / 77 retained / 11 unsupported / 16 outside scope, 218 total, zero unmapped. All 98 entries / 495 tracks rerun. Independent raw-readback checks 420119 written/grace occurrences; independent notation oracle checks 190890 eligible attack groups including negatives; zero failed checks. This is rule/preservation agreement, not human musical precision/recall. Raw v1 bend semitone labels were doubled; v2 corrects tone/50; prior GP audio was unaffected. Private source-technique-passages-v5 has 4 contextual comparisons / 8 modified GPs / 16 previews on loopback5183. Pedal/phrase/function and feel remain unvalidated; 24 GP conversion-fidelity flags remain. Persistent checklist and remote delivery evidence: MUSICAL_FIELDS_PROGRESS.md.

**Latest API coverage audit (2026-10-17):** Read songsterr_automation/API_FIELD_COVERAGE.md and API_COVERAGE_PROGRESS.md. Every nested observed path across98metadata/495tracks is explicitly mapped:218paths,65analyzed at varying depths,83retained_only,54unsupported,16not_applicable;0unmapped. This is an audit of current analysis, not implementation of the missing fields. Parent marker presence/raw capture/hash-only use is not complete child-value interpretation. Strict CLI flags future unknown fields. Private per-source coverage remains ignored. Analyzer/source scores/baselines unchanged; precise bend positions, per-point vibrato, brush/whammy/tempo/repeat/rest/role semantics and raw section-marker layout leakage are documented gaps.

**Latest corpus analysis (2026-10-17):** Read songsterr_automation/ANALYSIS_RESULTS.md and ANALYSIS_PROGRESS.md. Source-grounded relational analysis now runs on all98 entries/495tracks, preserving exact source occurrence context and reporting conditional technique distributions, provenance cohorts and candidate work families.88 source-located evidence cases/2904context-control occurrences verified by raw readback.55 overflowing voice/bar observations across25tracks are retained in notation counts and excluded from temporal candidates. No inferred musical-function accuracy, feel preservation or new generation acceptance is claimed. The older first-inventory counts below predate cross-voice coattack/attack-only and timing-quality gates. Private ANALYSIS.md and analysis-evidence.json are in local-artifacts/invent-animate-corpus-v1.
**Current source-grounded corpus direction (2026-10-17):** Read songsterr_automation/CORPUS_RESULTS.md and CORPUS_PROGRESS.md. User rejected authored pattern exercises; song evidence must determine technique relationships/repetition lengths. CSV acquisition complete:98 private reconstructed GPs/495tracks, all reopen in vanilla alphaTab;74 pass tested detailed roundtrip fields,24 flagged. Raw source inventory complete, not musical-function validation. Private folder local-artifacts/invent-animate-corpus-v1; catalog.csv and gp-files/. Next: source-located identification/counterexamples, conditional analysis, exact real-passage recreation, constrained context transfer, then novelty/feel review. Do not revive generic authored A/B studies or interpret conversion/annotation absence as artist style.

**Latest user correction:** Authored blind study retired as unhelpful/source-unrelated. Fretted HOPO listening excluded; retain open-string cases. Vibrato preferred Slight speed, half depth via explicit playback profile (360 ticks / 0.25 semitones). Close texture now EXACTLY one semitone. Corrected labeled diagnostics: technique-corrections-v1, port 5180. No further ratings requested. Older v6/35-pair delivery below is historical.

# Composition Lab — Codex context and autonomous execution plan

**Latest technique execution:** Read TECHNIQUE_RESULTS.md and newest TECHNIQUE_ROADMAP.md entry. Intermediate controls, five construction families, 30 guitar cases, 80 authored GP/audio probes, 35-pair local review implemented. Private technique-review-v6 at port 5180; 5179 is old bends. Human acceptance/authentic HOPO pending. No artist-learning claim.

**Current goal, 2026-10-16:** extend scripted analysis and exact-lock experiments to fretted/open-string HOPO, finger vibrato, pedal patterns, close dyads, power/extended power chords and double stops. Execution checklist and precise definitions: `TECHNIQUE_ROADMAP.md`. Bends remain preserved baseline. User confirmed higher-position fretted pull-offs and clarified that “tremolo” meant bending-based vibrato, not rapid picking. Double stops use the plain definition of two notes together; no further category-choice question needed. Raw beat-level arm-vibrato property exists in Time despite earlier absence of note-level vibrato tags.

**2026-10-16 control contract correction:** latest user instruction supersedes older difference-target language: 0% is a literal selected-feature lock; 100% removes direct reference constraints, without forcing difference. Performance and arrangement are separate. First working bend-only lever, verified endpoints and private audio comparison: `LEVER_IMPLEMENTATION.md`. Other levers are not claimed implemented under this revised contract.

Updated 2026-10-15. Read `composition-lab/HANDOFF.md` for full historical detail (it is long). Verify against current main.

**External comparison 2026-10-16:** read `EXTERNAL_COMPARISON.md` and the source-free external comparison/copying JSON reports. Actual upstream Yin-Yang generator/refiner/selector and AMT accompaniment ran on source-conditioned inputs. Nineteen GPs independently verified; six phrase and four arrangement cases loaded privately in separate review tabs. Earlier identical four-second openings confirmed. One upstream negative duration rejected with paired retry; two no-future AMT controls hit explicit resource caps. Sweet motif returns include 16-event source matches. No artist fitting, learned global-form success, originality certification or new human listening verdict is claimed. Previous baselines/ratings preserved.

**Latest autonomous continuation:** read `EXECUTION_16.md` and `AUTONOMOUS_RESULTS.md` before the historical missing-input notes below. Inputs and pretrained inference were recovered in earlier commits. The current run generated 100 full-length experimental GP compositions and 15 control outputs, with a private 22-case consolidated review. Structural/form and guitar-transfer acceptance gates remain failed/partial; no new human musical judgments exist. Private artifacts and weights remain outside Git. Current code and recorded measured evidence supersede earlier blockers.

## Objective
Analyze symbolic music in Guitar Pro (.gp) files, learn relationships among harmony, melody, rhythm, phrasing, structure, instrument roles and guitar techniques, and generate genuinely original, coherent, playable multi-track Guitar Pro compositions. Genre agnostic, not hard-coded to one song, key, tuning or instrument count.

## User's key feedback and lessons
- Original Cloud Cascade V2 baseline sounded musically better than source-conditioned Sweet Child experiment, even though the baseline was hard-coded and inflexible.
- Cloud and Sweet baseline outputs were effectively the same D Aeolian eight-string riff generator, independent of input source. This is not acceptable source-conditioned generation.
- Sweet Child source-conditioned output was discordant and mostly chords with no melodic phrases. It sampled Izzy Stradlin's rhythm guitar independently for pitches/rhythm, ignoring lead melody, chord progression, bass, drums, voice leading, phrases, form and roles. Both Sweet outputs were wrongly 8-string because the writer used Cloud Cascade as a shell.
- A score round-trip or GP parser passing is not evidence of musical quality. Require real generated GP artifacts, playback, metrics and listening comparisons.
- Avoid endless isolated diagnostic scripts; connect relational analysis (P3) to actual composition generation (P4).

## Research-backed architecture
Immutable occurrence-level GP events with rational onset/duration and all original track/voice/note/string/fret/tie/technique metadata
  -> temporal, harmonic, voice, phrase and section relational graph
  -> multi-task predictions (root, quality, inversion, bass, non-chord tones, phrases, cadences, roles)
  -> independently conditioned role/phrase/harmony/rhythm generation and edit operations
  -> exact occurrence-aware GP export and verifiable listening tests.

Relevant research and code:
- AnalysisGNN: https://github.com/manoskary/analysisgnn (multitask graph analysis, pretrained inference; upstream under construction; classical-to-rock domain shift must be measured)
- BeatEdit: https://github.com/Haoyu-Gu/BeatEdit-code (KEEP/DELETE/REPLACE/INSERT sparse editing)
- DadaGP: https://github.com/dada-bots/dadaGP (guitar-specific tokens and techniques)
- REMI-z: https://github.com/Sonata165/REMI-z (track/bar/note hierarchy)
- Partitura https://github.com/CPJKU/partitura; GraphMuse; FIGARO https://github.com/dvruette/figaro; mir_eval; JAMS.
- Check checkpoint licensing, training data and redistribution separately.

## Five development steps, in order, but advance independent work if blocked
1. **Source fidelity + AnalysisGNN benchmark.** Verify existing exact GP extraction and occurrence-aware writer. Round-trip through canonical representation, DadaGP-inspired tokens and REMI-z-style hierarchy; report attacks, pitch, durations, sustains, voices, string/fret, ties/effects, track and bar positions lost. Convert original GP to MusicXML without losing note identity where possible. Run actual pretrained AnalysisGNN on Cloud Cascade and Sweet Child; collect task outputs and compare to existing inference and human evidence. Do not claim completion if dependencies/checkpoints unavailable. Existing benchmark preflight: composition-lab/benchmarks/analysisgnn_preflight.py. Earlier local XML conversion reported Cloud 6 tracks/111 bars/5314 notes, Sweet 9 tracks/185 bars/10138 notes and 18 Sweet voice-duration discrepancies; those claims need independently reproducible validation.
2. **Relational P3 graph.** Build on exact events with NEXT_IN_VOICE, SIMULTANEOUS, OVERLAPS, SUSTAINS_INTO, SAME_TRACK, SAME_BEAT, SAME_MEASURE, REPEATS/MOTIF_OF, phrase/section membership. Instrument identity != musical role. Preserve separate chord root/quality/inversion/bass/non-chord-tone hypotheses with confidence. Tests must include held notes, cross-bar ties, polyphony and changing meter.
3. **Controlled ablation.** Generate same-seed examples with harmony only; harmony+rhythm; +melody; +roles/phrases. Export real GP, validate reparsing, compare melodic notes, sustain ratio, lead continuity, phrase lengths, chord-tone fit, bass movement, onset patterns, copying and track roles. Blind listening comparison with Cloud V2 baseline; don't fabricate human judgments.
4. **Phrase-aware multi-role generation.** Generate multi-track role-specific melody, harmony, bass, percussion as supported by source. Honor source tuning/instrumentation or explicitly chosen target. Add exact 0% locked dimensions and measurable independent 0-100% harmony/melody/rhythm/structure controls; implement coherent progression, voice leading, motif variation, playable guitar constraints, and form.
5. **Held-out validation.** Freeze baselines, cross-song splits, no train/test leakage, originality/copying audit, regression suite, reproducible generation seeds, GP artifacts, and listening review protocol. Report limits and actual measured results.

## Existing code pointers
- composition-lab/checkpoints/2026-10-14/extract.py
- composition-lab/checkpoints/2026-10-14/music_events.py
- composition-lab/checkpoints/2026-10-14/gp_occurrence_writer.py
- composition-lab/checkpoints/2026-10-14/gp_similarity_export.py
- composition-lab/checkpoints/2026-10-14/sequence_generator_balanced.py
- composition-lab/checkpoints/2026-10-14/joint_interpretation_v20.py
- composition-lab/checkpoints/2026-10-14/phrase_discovery_v19.py
- composition-lab/review_structure_probe.py
- composition-lab/HANDOFF.md (full project history)
- Two separate review UIs exist; do not confuse chord/phrase judgment UI with riff-pair listening UI.

## Execution protocol
Maintain a checked-in progress ledger with acceptance evidence, actual commands, artifacts and next action. Continue automatically after each successful test, within agent/runtime limits. Retry sensible failures, but never fake completion. If a prerequisite is blocked, record the blocker and work on other independent steps. Commit verified code, not private source scores. Avoid changing unrelated guitar-trainer UI. Summarize only when work is done or human input is truly required.

## CRITICAL 2026-10-15 handoff correction: missing local inputs FOUND

Previous assistant claimed the files were unavailable. They have now been recovered from this ChatGPT conversation's mounted artifacts, and a **private local input ZIP** was created for the user to download and extract into the local clone. Do not assume Codex has access to ChatGPT uploads. Do not commit the private ZIP or any original commercial score to the public repository.

ZIP: `Composition_Lab_Codex_Private_Inputs.zip` (supplied to user as a ChatGPT attachment, NOT hosted on public GitHub). Extract into `G:\\Guitar-Learning\\composition-lab\\`. Archive paths start with `private-sources/`. The directory is now in the repository's `.gitignore`.

Recovered contents:
- `private-sources/Cloud Cascade (Tuned Down).gp` — original 6-track, 111-bar source, SHA256 `63cfae7762a5ac56b2f0521d8c01cbf6025fac74ea525c7a6b7d260703492f66`.
- `private-sources/Sweet Child O' Mine.gp` — original 9-track, 185-bar source, SHA256 `17c5ecc0606a6334bf2818ba3f2d1f4a8574f0777cf6750565f644a0ee0b9e7f`.
- `private-sources/experiments/cloud_experiment/` — `Cloud_Cascade_V2_Baseline.gp`, `Cloud_Cascade_Source_Conditioned.gp`, `source_conditioned.py`, `EXPERIMENT_REPORT.md`.
- `private-sources/experiments/sweet_child_experiment/` — `Sweet_Child_V2_Baseline.gp`, `Sweet_Child_Source_Conditioned.gp`, `source_conditioned.py`, `EXPERIMENT_REPORT.md`.
- `private-sources/analysisgnn/` — `gp7_to_musicxml.py`, `conversion_report.json`, `preflight/manifest.json`, and two converted MusicXML scores in `musicxml/`. These are experimental outputs and must be independently verified.
- `private-sources/LOCAL_INPUTS_MANIFEST.json` — hashes of original and experiment GP files.

The converted MusicXML export reported 5314/5314 notes and 0 invalid bars for Cloud, and 10138/10138 notes and 18 invalid bars for Sweet. These are **duration discrepancies**, not necessarily 18 missing notes. Investigate against source rational-time events and GP tuplets/voices. The previous preflight did not run pretrained AnalysisGNN inference because torch_geometric, partitura, graphmuse, and analysisgnn were unavailable. The ZIP contains the converter and exports; `composition-lab/benchmarks/analysisgnn_preflight.py` is already committed.

**Critical remaining limitations/gaps**:
1. Codex needs the user to extract the ZIP locally. A GitHub commit cannot transfer private copyrighted sources into a Windows local clone safely.
2. Neither a runnable pretrained checkpoint nor trained inference predictions have been provided. Codex must install dependencies, obtain checkpoint under license, and run inference.
3. The baseline experiment reports contain structural checks, not verified human blind listening; do not invent evaluations.
4. Source-conditioned scripts may embed old machine-specific paths. Fix paths locally and preserve their prototype nature.
5. GP/MusicXML fidelity (ties, techniques, fret/string, track role, tuplets) requires systematic validation; note counts alone are insufficient.
6. The detailed handoff predates these experiments; this document is the latest correction.
7. A persistent agent loop is subject to runtime limits; use checked-in progress and acceptance evidence, not false claims of indefinite execution.

**Next action for Codex**: after `git pull` and local ZIP extraction, verify SHA256, inspect reports and converter, rerun the 18 discrepancy analysis, then run AnalysisGNN benchmark while progressing independent graph and generator work. Never publish the private sources.
