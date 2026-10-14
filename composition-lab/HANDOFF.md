# Guitar-Learning / Composition Lab — cross-chat handoff

**Prepared:** 2026-10-14. **Repository:** https://github.com/mtch777/Guitar-Learning ; **site:** https://mtch777.github.io/Guitar-Learning/ . **Branch of record:** `main`. **Source of truth:** current GitHub `main`, not this prose or older local packages. **Read this file first, then check HEAD, workflows, and code.**

> **Purpose of this handoff:** Preserve the decisions, goals, philosophical foundations, failure analysis, user expectations, and concrete next experiments that are *not obvious just by reading source files*. It is not a substitute for inspecting code. Do not mistake test success, a present file in `main`, or a model prediction for deployed behavior or musical accuracy.

## 1. First 10 minutes of the next chat

1. Fetch current `main` HEAD and inspect `vite.config.js`, `.github/workflows/deploy-pages.yml`, root `composition-review.html`, `public/composition-review/{index.html,app.js,cases.json}`, `composition-lab/README.md`, and the `composition-lab/checkpoints/2026-10-14/` directory. These paths have *different purposes*. Reconcile with any commits after this document. Avoid blanket code replacements.
2. **Confirm the 404 fix actually deployed:** `https://mtch777.github.io/Guitar-Learning/composition-review.html` used to return 404 although a 1 MB `composition-review.html` was committed at repo root. Vite built `dist/` from only the entrypoints listed in `vite.config.js`; root HTML not listed there was not published. Commit `0e5e71ca12c3cb5737113fc710ec8225361c9326` added `compositionReview: resolve(import.meta.dirname, 'composition-review.html')` to the Vite multi-page inputs. The deploy workflow publishes `dist` to `gh-pages`. Check workflow status, `gh-pages` branch contents, and actual HTTP response; a successful commit to `main` alone does not prove the 404 is resolved. Check whether the 1 MB embedded review script builds cleanly and whether navigation works under the `/Guitar-Learning/` base URL. Do NOT redirect this URL to the other, incompatible riff review tool.
3. Confirm that `npm ci`, `node --test tests/*.test.mjs`, and `npm run build` pass. Run Python tests for composition checkpoint with dependencies and appropriate working directory; do not equate past passing counts to current suite coverage.
4. **Review app distinction** (critical):
   - Root `composition-review.html`: **V23-style 60-case chord identity + phrase-boundary review**. Synthetic Web Audio notes, piano roll, reveal prediction only after judgment, CSV for `reference_validation_v22.py`. Linked from root `index.html` as “Listening Review.” Entire data embedded in a large root HTML file.
   - `public/composition-review/`: **different riff-pair listening review** comparing approximately 30 riff pairs from the original three Invent Animate `.gp` songs. Uses alphaTab and local upload of the 3 `.gp` files; judgments are related / unrelated / uncertain. Deployed URL would be `/Guitar-Learning/composition-review/`. Labels are **NOT** interchangeable with chord/phrase labels. It may have separate functionality and dependencies; keep it separate.
   - The older V23 generator and template live under `composition-lab/checkpoints/2026-10-14/v23-review/`; do not assume that the published giant HTML is built automatically on every commit. Compare these versions when regenerating.
5. Read the latest V24 files under the checkpoint to understand source-provided chord annotations. They do not magically produce adjudicated human truth. Use GitHub to determine their actual version and deployment state.

## 2. The user's actual objective (not a narrow Chet Baker app)

Build a **genre-agnostic, musician-useful system** that consumes compatible `.gp` Guitar Pro files, extracts musical structure and performances with high fidelity, learns what makes material stylistically characteristic, and writes **new coherent, playable, genuinely original `.gp` compositions**. It must be able to learn from drastically different kinds of music (extreme/progressive metal, jazz vocal melody, rock lead, etc.) without hard-coded root riffs, chugs, four-bar phrases, specific tuning, scale, meter, or progression. A tool that merely copies, octaves, or scrambles notes is not sufficient.

The user wants **independent 0–100% same→different controls** for aspects of music, e.g. unchanged structure with new chords; unchanged chord progression with new melody; unchanged rhythm with different chords; same melodic harmonic function with different harmony. These are conceptual **difference targets**, *not* probabilities that the software flips a coin before changing a note. Earlier V14–V20 sliders are mostly stochastic variation probabilities and are **not yet calibrated difference distances**. Always explain this without presenting the prototype as fully complete.

The three initial reference scores are Invent Animate's `Cloud Cascade (Tuned Down).gp`, `Nocturne_ Lost Faith (Tuned Down).gp`, `Immolation of Night (Tuned Down).gp`; held-out contrasting material: `Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp`, `Sweet Child O' Mine.gp`. They were uploaded to ChatGPT and may or may not be present in a fresh runtime; their mere filenames in this handoff do **not** imply an accessible absolute path. Search files/Library or ask only if unavailable after searching. Source scores are intentionally not normally committed to public GitHub.

**User interaction style:** highly technical programmer/statistician, strong priority on clear causality, empirical evidence, and efficiency. Prefers concise, accurate, directly actionable replies, without boilerplate optimism or extraneous explanation. When user says “go,” “next,” or “execute,” actually implement and test, not merely propose. When giving changed code requested, give complete changed sections. Never claim GitHub pushed, deployed, full-suite-tested, or musical quality verified without evidence. Never ask for information previously supplied.

## 3. Central philosophy: relationships, not a chain of labels

**The deepest learning from V1–V22:** music must be modeled as a hierarchy of interdependent relationships, not as a pipeline where “identify chord → label melody → identify phrase → learn phrase → generate.” That earlier approach destroyed training coverage when a chord was uncertain. It is not fixed by adding more chord names or more local heuristics.

Concrete commitments:

- **Preserve observations independently of hypotheses.** The exact GPIF tracks, voices, beats, ties, rests, note occurrences, MIDI pitches, frets, strings, timing as rational numbers, articulations and source IDs are observations. Chord identity, harmonic function, root, mode, phrase boundary, melodic vs accompaniment role, and formal section are *interpretations*. Do not overwrite one with the other. Keep provenance and reversible mappings.
- **Unknown does not mean invalid and should not erase training data.** A melodic gesture teaches intervals, contours, register relationships, rhythm, repetition and voice motion even if harmony is unknown. Harmony is an additional view. Never silently drop a whole training phrase because one event lacks a chord label.
- **Represent ambiguity rather than forced certainty.** A rootless voicing can support several harmonies; rank candidate explanations with evidence and context and keep unresolved when necessary. A posterior is not automatically calibrated or ground truth. Avoid terms such as “verified chord” when only a unique template match was obtained.
- **Interactions are bidirectional.** Bass/melody/voicing/context can suggest harmony; suspected harmony can suggest note function; repeated motifs and rests can indicate phrases; phrases and voice leading can clarify harmonic changes. Use joint or iterative scoring with held-out verification rather than independent one-way heuristics. A full neural network is *not required*; a transparent probabilistic graphical model / dynamic programming can establish a baseline.
- **Music is hierarchical and multi-scale.** Individual notes → gestures → phrases → sections → song. Phrases need not be exactly 2, 4, or 8 notes/bars; they cross barlines, can contain rests, ties, pickups, polyphony, and harmonic changes. Song form may come from GP section annotations but often must be inferred.
- **Harmony and melody are relational, but not all notes are chord tones.** For chord changes, a note's *harmonic role and octave* should be the principal transformation representation, rather than locking absolute MIDI pitch. Example minor ii containing R–m3–5 transformed to major IV yields R–M3–5 with octave roles preserved. However, passing tones, suspensions, neighbor tones, chromatic approach and resolution notes require contextual roles (not simply nearest chord tone or constant semitone-from-root). Preserve actual pitches in raw data for fidelity and verification; they need not be a user-facing similarity dimension.
- **Preserving a feature is stronger than preserving its approximate summary.** “Rhythm 0%” means the timing grid/onsets/durations/rests/voice placement remain exact, not merely same density or duration histogram. “Chords 0%” includes timing, quality, function, harmonic rhythm/inversions if selected. “Melody 0%” should explicitly specify chord-relative function, octave, contour, or literal pitch; when users ask for chord changes and melody locks, mapping chord function is the intended default. Conflicting locks must be flagged, not silently broken.
- **Separate target differences from edit probability.** Slider 100 is not a mandate for random noise, and 0% must be a mathematically enforceable identity. Measure difference along the *specific musical feature* and search/optimize for coherent candidate transformations at the requested target. Report feasible ranges, and avoid claiming that transformation probability equals musical distance.
- **Learn from source music rather than baking in genre tropes.** Earlier versions accidentally assumed low-register = bass/root/chug, D Aeolian, fixed 16 bars, A A' B A'' structure, etc. Those were flaws, not the desired sound. Models must be conditioned on actual learned evidence and selected instrument roles.
- **Separate track role and arrangement from harmony.** Mixing vocals, rhythm guitars, acoustic guitars, leads, bass, and doubles into a single sequence biases statistics and produces nonsensical texture. Select or infer each part/role, de-duplicate actual doubles, and model cross-track interactions. Bass is evidence, not necessarily root. A chord attack is not the same as the span of the whole harmony.
- **Musical quality requires listening and human labeling.** Re-importable GP + passing synthetic unit tests prove engineering properties, not correct harmony/phrasing or listenable style. Predictive coverage ≠ identification accuracy. Keep a held-out set and adjudicated labels for measurements; label claims carefully.

## 4. Historical failures worth never repeating

1. **Hard-coded output mistaken for generative learning:** Early V2/V3 user-liked examples sounded coherent partly because patterns/harmony were effectively authored. Treat those as subjective reference points, not empirical success of learning.
2. **Low note = chug/root assumption:** V4 classified low+12 semitones as `low`, destroying distinct pitches and generating repetitive root notes. Never impose metal-centric labels or octave thresholds as semantic truth.
3. **Fixing one feature can regress the whole pipeline:** Browser JS/Python guitar-string classifier work elsewhere in this repo proved that validated FFT/STFT should be frozen and changes localized. Here likewise keep regression baselines, preserve event timings and geometry, avoid ungrounded sweeping rewrites.
4. **Triad-only reharmonization despite richer chord analysis:** A parallel restricted detector wasted existing broader vocabulary. One shared chord vocabulary with uncertainty and clear provenance is preferable; extended 9/11/13/alterations do not by themselves solve missing harmony.
5. **Conservative anchor bridging alone yielded zero coverage improvements:** Requiring identical known chords before/after partial sonorities is safe but mostly inapplicable to songs with frequent changes. Do not keep polishing that rule in isolation.
6. **V16 lost every melodic alternative:** Phrases were rejected if *any* event lacked chord context, and windows were artificially fixed to 2–4 events in a measure. V17 interval-based learning recovered chord-independent examples; V19 variable-length boundaries and V20 joint evidence were initial attempts at deeper redesign.
7. **GP shared note definition edits:** Changing a GPIF note definition can unintentionally mutate multiple occurrences. V18 occurrence-aware writer made per-instance edits possible. Test no collateral edits, total bar timing, voice integrity, physical playability, re-import and zero-lock identity.
8. **Rhythm variation and exact time:** Changing duration IDs without recomputing starts can corrupt meter; earlier regression caught this. Use rational arithmetic, linked GPIF beats/voices, and measure totals; preserve tie/sustain semantics.
9. **“Verified” terminology was wrong:** V20 reported 97 “verified sonorities,” but V21 established they were exact *template matches*, not independently verified identities. In five 20-bar excerpts, 114/767 note attacks matched a unique chord template (14.9% coverage); this was emphatically NOT accuracy.
10. **Track selection changes the conclusion:** Sweet Child has multiple guitar and other pitched tracks; earlier learner pooled incompatible roles and generated chords where lead should be monophonic. Label and log track identity and part role in every evaluation.
11. **Human review is pending:** V22 introduced honest null accuracy rather than 0%. V23 created listening interface. V24 recovered *source-provided* annotations but these are only evidence and must be separately flagged; never automatically label blank human fields.
12. **GitHub file ≠ Pages URL:** Vite publishes only built entrypoints and `public` contents. Always check deployed `gh-pages` branch / actual URL. This caused the `composition-review.html` 404.

## 5. Code lineage and current capabilities — orientation only

The stable(ish) experimental Python line is in `composition-lab/checkpoints/2026-10-14/`. Treat existing `composition-lab/` top-level files as an older, related research line, not necessarily the latest V20–V24 exporter. Current checkpoint includes:

- `music_events.py`, `extract.py`: GPIF extraction; fractional beat durations, multiple voices, provenance.
- `sequence_model.py`, `sequence_generator_v6.py`, `sequence_generator_balanced.py`, `motif_development_v7.py`, `structure_learning_v8.py`: early sequence/motif/section generation; older training and output limitations apply.
- `harmonic_relative.py`: `Chord`, `RelativeNote`, chord-tone degrees/octaves, timing-based mapping; non-chord roles remain simplistic.
- `harmonic_inference.py`, `automatic_harmony_control.py`, `harmonic_continuity.py`, `contextual_harmony.py`, related code: chord hypothesis and strict editing/continuity.
- `similarity_controls.py`: three independent *parameter* controls but nonzero percentage is mostly chance-of-change; 0% lock is tested.
- `gp_similarity_export.py`, `gp_occurrence_writer.py`: playable GP edits, isolation of reused note definitions, learned melody/rhythm hooks.
- `learned_patterns_v16.py`, `relational_learning_v17.py`, `phrase_discovery_v19.py`, `joint_interpretation_v20.py`: successive attempts: from chord-gated fixed windows to chord-independent intervals, variable gestures, and coupled harmonic/motif/boundary *heuristics*.
- `evaluate_v21.py`, `reference_validation_v22.py`: explicit evaluation and review scoring; human-labeled truth remains absent as of the last confirmed baseline.
- `v23-review/{build_review.py,player_template.html,test_review_player.py,README.md}` and standalone deployed/root `composition-review.html`: chord/phrase review UI.
- `v24-reference/`, `V24_*`: source annotations; inspect exact current code / reports rather than assuming complete accurate labels.

Approximate historical local benchmarks (source: previous chat runs, not guaranteed reproducible without scores): V9 balanced model improved rhythm histogram but had poor role mixing; V10 exact tuplets and 41-bar Chet score; V15 valid 0% GP exports; V17 275 chord-independent melodic windows and ~110 distinct interval patterns; V18 102 melody-only note occurrences and 321 combined note occurrences edited; V19 50 candidate gestures, 387 windows, 109 melody changes; V20 344 joint-refined windows, 97 melody-only changes. These numbers are **different measures on different settings**; never rank model quality by the number of edits alone. V21 five-score benchmark and V22 baseline are more appropriate places to start accuracy work.

Many past assistant summaries claimed 40, 47, 52, 58, 67, 68, 79, 84, 90 tests passing at different checkpoints. They do not prove the present entire repo test suite passes or that any GP rendition sounds musical. Re-run relevant tests and report exact commands/scope.

## 6. Two separate review tasks — human purpose matters

**A. 60-case harmonic/phrase review (priority for V20 model)**
- Review objective: Does the model assign correct harmony/chord function and propose a real phrase beginning at a given GP onset?
- User hears surrounding polyphonic context with a synth approximation; can choose focused track, inspect piano roll and hidden predictions; label chord, certainty, phrase yes/no/unknown, comments.
- Each row's `source_file`, `track_index`, `onset_q` keys are essential. Preserve case identity, user-entered fields, source annotations and reviewer identity. CSV should round-trip through `reference_validation_v22.py` unchanged; do not accidentally score source-provided chord symbols as independent human ratings.
- Review should be *blind* to model prediction until after independent judgment, otherwise labels are contaminated. Allow unknown and explicit “not enough context.”
- Source-Chet GP chord symbols: V24 reportedly extracted 69 chord-symbol occurrences, 54 section labels total across five scores, but only 3 of 60 initial cases directly landed on chord-symbol attacks. These annotations have selection bias and uncertain semantics; use as extra evidence, not human truth.
- Current 60 cases sampled across confidence/boundary groups; metrics only describe reviewed sample, not whole corpus. Need expand with negatives, other instrument roles, uncommon harmonic cases, and holdout tracks; use two raters when feasible.

**B. 30-case riff-pair review (separate research task)**
- Objective: Are two GP passages perceptually the same/related motif, even with variation/transposition? Labels: confirmed/rejected/uncertain; source three Invent Animate scores.
- Requires user to upload source files locally for alphaTab playback; alphaTab may depend on CDN, soundfont, browser permissions. It is *not* chord/phrase accuracy data. Distances previously obtained in older motif analysis are candidates, not verification.
- Keep separate storage keys and separate CSV schema; preserve original file names and string/tuning considerations. Do not conflate sound generation from Web Audio V23 and alphaTab riff tool.

## 7. Long-term architecture — concretely what “relationships” must mean

Implement an explicit **event graph / relational score** with layered annotations and a constraint solver:

```
raw GP score (immutable)
  tracks → voices → note/beat occurrences [exact time, MIDI, fret, tie, articulation, provenance]
  + simultaneity/overlap/sequence edges
  + hierarchy: gesture/phrase/section candidates
  + multiple tonal interpretations over spans with evidence/probabilities
  + melodic voice leading/contour + chord-relative function + non-chord function
  + rhythmic motif + meter position + accent/rest hierarchy
  + instrument part/role relationships and repeated/transposed variants
       ↓
user-selected feature locks + requested measured distances
       ↓
coherent candidate generation with feasibility checking
       ↓
playability, exact-time, provenance, originality, musical-distance checks
       ↓
new valid GP file plus audit of achieved vs requested differences
```

Candidate inference can initially use finite-state/dynamic programming, HMM/CRF, scored factor graph, or a transparent beam search, with weak priors learned from source corpus and human labels. Beware tiny five-song training data: fit only defensible parameters, avoid “probabilities” that are merely hand-tuned heuristic scores. Repeated motif edges and voices should inform harmonic scoring, and harmonic changes should influence phrase boundary scores, iterating when warranted. Honor evidence gaps.

**Conceptual decomposition of control space** (future UI should group this, not overload just 3 sliders):
- Form: section identities/order, length, returns, repeats vs variations, phrase placement.
- Harmony: root motion/function, chord quality/extension/inversion, harmonic rhythm, register/voicing, key/mode as a *hypothesis*.
- Melody: harmonic function sequence, register/octave displacement, interval/contour, ornamentation, phrase development, nonchord resolution roles.
- Rhythm: attacks, durations, rests, meter position, swing/tuplets, syncopation, phrase pulse.
- Performance/arrangement: articulation, dynamics, techniques, parts/instruments, independent voices, texture/density, inter-instrument coordination, physical playability.

Preserve feature controls under transformations that can conflict. Example: fixed literal melody pitch AND moved chord AND fixed harmonic role may be mutually impossible; report infeasible; give user precedence choices rather than silently moving notes. “Same melody” was explicitly clarified in conversation to mean **same chord-relative harmonic role and octave**, not necessarily same absolute pitches. Raw actual pitch still needed for correctness and export.

## 8. Prioritized next steps (detailed engineering tasks and acceptance conditions)

### P0 — Verify and stabilize Pages / review UX **before adding musical complexity**
1. Check latest `main` and `gh-pages` heads. Confirm `composition-review.html` exists in the built `gh-pages` branch and actually returns HTTP 200 at the user-reported URL. If not, inspect failed GitHub Actions `deploy-pages.yml` run logs; the pipeline runs Node tests and Vite build before publish. Root cause known: missing Vite multi-page input, fixed in commit `0e5e71ca` but deployment still needs external verification.
2. Load both URLs `/composition-review.html` and `/composition-review/`. They must show different, clearly named tasks; the main trainer link should point to the 60-case chord/phrase review as intended. Test click → playback → label → next → persistence → export CSV → V22 evaluator. Test mobile and blocked Web Audio; don't falsely claim graphical browser verification if only static tests were run.
3. Confirm Pages website's Vite base path, asset URLs, inline scripts, browser security / CSP, offline expectations, `gh-pages` deployment permissions and soundfonts. Check `npm ci && node --test tests/*.test.mjs && npm run build` and confirm `dist/composition-review.html` exists. Check source HTML size/performance (~1 MB). No need to commit original commercial GP songs to public repo.
4. Provide stable cache-busting/versioned link to user if stale and document actual deployed SHA. If Pages is misconfigured to deploy a different branch or directory, fix deployment settings/workflow as needed, then verify again.

### P1 — Collect reliable reference answers
1. Let user review 5–10 meaningful examples, preserving independent blind labels. Prefer representative rather than just obvious examples (known chord, rootless/inversion, uncertain melody-only, repeated motif, phrase boundary and hard negative). Provide audio + tab/context + original track selection and solo/ensemble playback.
2. Export reviewed CSV, validate schema/IDs/answer choices/no duplication, run `reference_validation_v22.py`. Empty/unknown labels must not count as wrong; report denominator. Distinguish event-level vs duration-level accuracy and abstention coverage. Collect more examples when confidence interval too wide.
3. Source chord symbols (V24) may be used as *separate provenance* to bootstrap checks, not secretly fill `human_` columns. Review actual GP annotations for track identity, onsets, spelling/inversion and missing coverage; note that chord labels can refer to accompaniment while reviewed track is melody.
4. Set frozen holdout split by **song**, optionally by performer/genre and track role. Don't tune model on all test examples and declare success. Save labeled/reference revision and evaluator version with result artifacts.

### P2 — Make scoring and baselines diagnostically useful
1. Compute chord exact root+quality accuracy, root-only, extension/inversion when independently annotated; coverage/abstention, top-K recall, calibration plots/Brier/log-loss only if posterior probabilities meaningful. Break down by complete voicing, missing-root, melody-only, percussion, role, harmonic transition and chord ambiguity.
2. Compute phrase boundary precision/recall/F1 at exact beats and tolerance windows **vs labeled boundaries**, with unknowns excluded; distinguish sections from phrases. Compare simple rest-only, interval-jump-only, motif-only, harmony-only, V19, V20, and combined models.
3. Report confusion examples with source note evidence, inferred alternatives, confidence and audio. Prefer a concrete failure mode (“mistakes inversions as new root”) to a broad coverage number. Run ablation experiments and seeded consistency tests. Avoid claiming qualitative improvement without blinded listening.

### P3 — Relational model v2 (replace remaining artificial limits)
1. Define immutable per-occurrence event IDs and graph links for track/voice/measure, temporal overlap, same beat, tie continuation, motif recurrence, phrase membership. Note `GPIF` shared definitions require occurrence identity (V18 experience).
2. Improve joint harmony using all relevant simultaneous/sustained voices, bass, vertical sets, voice leading, and temporal transitions, with multiple competing candidates. Learn modest transition prior only after cross-validation; include no-chord/ambiguous/rootless/pedal cases.
3. Infer phrase hierarchy with variable durations spanning barlines, changes in rhythm, rests, repeated/edited motives, phrase cadences and harmonic changes. Preserve multi-resolution boundaries (gesture vs phrase vs section); don't split simply at any new chord.
4. Extend melodic function beyond chord tones: chromatic neighbor, passing/approach, appoggiatura, suspension and resolution, tension/release; preserve octave and melodic voice leading. Avoid imposing Western functional harmony on all music; model uncertain/non-tonal cases neutrally.
5. Learn joint relationships from all notes without gating them on chord certainty. Attach additional harmonic-role evidence only where defensible; avoid candidate distributions that are practically flat.
6. Add a small sample-level visualization for every inference: observed pitches, selected track/voice, considered harmony candidates, reasons for each phrase boundary, and confidence/abstention.

### P4 — Proper composition with independent, *measured* difference controls
1. Formalize a **metric for each dimension** before coding the UI slider. Rhythm might use normalized event alignment preserving meter; melody relative-function edit distance/contour/phrase transformation; harmony root+quality+timing; structure section sequence similarity. Each metric needs examples reviewed for musical sensibility, and monotonicity checks.
2. Implement exact identity at 0%, and constraint-preserving generation for nonzero targets. Generate a candidate *phrase or section*, not random isolated note edits; score coherent musical relationships jointly. Search/beam optimize achievable actual distances; report requested/achieved + unchanged locks. Don't guarantee mathematically exact 100% if incompatible with constraints.
3. Separate **create new composition** from **transform existing source GP**. Current V15–V20 mostly edit a source score; that's not equivalent to an original composition generator. Generation must support independently synthesized measures/tracks with learned arrangement and structure and inspect novelty relative to training pieces.
4. Include articulation/expressive techniques, tuning/fretboard constraints, multi-voice polyphony, bar duration and ties without corrupting source data; playback/audio review and export re-import are regression gates.
5. Compare against held-out passages and trivial baselines; run multi-seed performance tests, groove/melody/harmony distributions, diversity/copying audits and blind listening. Never equate number of changed note occurrences to sound quality.

### P5 — Engineering / handoff discipline
1. Keep research versions and validated benchmarks; do not overwrite prior `main` logic or guitar trainer behavior for experiments. Move from additive date-stamped checkpoint files to an intentional package/modules only once behavior is independently covered.
2. Add a single `make`/scripted reproducibility command that selects tests by scope, imports, and fixtures. Keep commercial source scores outside Git; fixtures must be redistributable or synthetically generated.
3. Introduce clear data contracts for event graph, hypotheses, review labels, similarity metrics, and GP exporter; version CSV/JSON schemas.
4. For each change record input scores and selected tracks, build SHA, seeds, before/after feature diffs, changed note occurrences, refusal counts, GP re-import, exact-lock checks, human review and remaining limitations.
5. Avoid hundreds of small commits for simple edits when possible. Confirm GitHub HEAD and expected blob SHA before updates, verify content again after commits, and check actual Pages deployment separately.

## 9. Acceptance criteria: what success *really* looks like

- **Observation fidelity:** no lost supported GP timing/voices/ties/positions/articulation on extraction/roundtrip; exact rational timing and track selection, with unsupported cases reported.
- **Inference validity:** chord/phrase labels demonstrably agree with independent reference more often than transparent baselines, with abstention/coverage and uncertainty measured rather than implied.
- **Independent controls:** when feature is 0%, the chosen representation is unchanged to exact tolerance; when 100%, transformed feature is measurably different while other locks remain exact and music remains coherent.
- **Part-aware style learning:** clean lead/jazz melody remains monophonic unless the actual score teaches otherwise; rhythm/accompaniment/chordal roles are not pooled blindly.
- **Output legitimacy:** GP files open/play in both GP-compatible tooling and the renderer, stay in meter, playable at declared tuning, don't mutate unintended source occurrences, and demonstrate novelty.
- **Actual musical evaluation:** user can listen and judge, and review exports feed measurements; benchmark on five source scores plus truly held-out future files, with seeds and revisions recorded.

## 10. Communication and safety rails for the next assistant

- Answer the actual question directly; distinguish plans from results. “Go” means perform implementation, tests and (when part of the established workflow) commit.
- Never assume screenshots, GP files, generated artifacts, or prior `/mnt/data` paths exist in a different runtime. Confirm file paths; library file names are not GitHub file paths.
- Avoid repetitive explanations of genre limitations unless relevant. The user's target music may fuse EDM and modern heavy guitar, but the composition engine itself should **not** hardcode that style.
- When describing an algorithm, specify what the program actually computes, not “it understands music” without concrete representations and test evidence.
- Be explicit that derived chord symbols and phrase cues are hypotheses, not facts. A recognized chord at an attack is not proof of the sustained harmonic span.
- Do not force uncertain segments into invented chords or skip melody learning as a consequence of uncertainty.
- Preserve other Guitar-Learning work (eight-string trainer, guitar-string classifier/audio-model pipelines, song player) when editing web build/review pages.
- The user requested this handoff to concentrate on *the soft philosophy and hard next steps*, because source files already show most implementation. Re-read sections 3, 4, 7, 8 before choosing subsequent changes.

**Immediate recommendation after confirming deployment:** do a complete end-to-end review pass for a handful of cases, obtain genuine reference annotations, evaluate V19 vs V20 vs simple baselines and break down errors by track/harmonic context. Only then spend major effort on a more complex learned joint interpretation model. In parallel retain the independent 0%-lock and GP-export regression suites.