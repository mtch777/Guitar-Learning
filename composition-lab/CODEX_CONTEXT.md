# Composition Lab — Codex context and autonomous execution plan

Updated 2026-10-15. Read `composition-lab/HANDOFF.md` for full historical detail (it is long). Verify against current main.

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
