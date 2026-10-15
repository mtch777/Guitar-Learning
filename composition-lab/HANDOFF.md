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

---
## Supplemental successor-chat answers (8–12), 2026-10-14

**Scope:** The successor provided questions 8–12 only. The exact text of questions 1–7 was not included; do not invent it.

### 8. Why 20 measures, 60 cases, and those tracks?
The five scores deliberately spanned three original Invent Animate sources and two contrasting songs (Chet Baker jazz and Sweet Child O' Mine rock). This was a small exploratory variety check, not statistically representative or a secure held-out split after repeated model iterations. First 20 measures was a speed/reproducibility cap, not a musical or long-term design decision; it biases intros. Twelve cases per score (60 total) was a manageable blind-review pilot, not a sample-size/power calculation. The V21 sampler seeded shuffling by track, round-robins four strata: model boundary/nonboundary × unique chord-template match/unresolved. This is a deliberately stratified sample, NOT an unbiased random sample for population accuracy. Track selection automatically prefers the most pitched events with tuning; this is a convenient proxy, NOT inferred melodic/guitar/harmonic role. It can choose vocal/sax. Preserve 60-case identities; build future explicit role-stratified and song-section-spanning test sets separately.

### 9. Was browser review actually exercised?
NO confirmed graphical browser end-to-end test of the V23 review interface. Seven targeted automated tests covered case mapping, embedded source data, JavaScript syntax and V22-compatible review schema, NOT audible Web Audio, responsive drawing, navigation, localStorage persistence or CSV downloads. User later reported the root composition-review.html URL returned 404. GitHub had the source HTML but Vite omitted it from the multi-page dist build; the entry was added to vite.config.js in commit 0e5e71ca12c3cb5737113fc710ec8225361c9326. A live web fetch on 2026-10-14 now loads the intended review page, meaning the observed 404 is resolved. That is STILL NOT evidence that its JS interactions/playback work. Test Play/Stop, track focus, changing tempo/context, next/previous, judgments, reload persistence, export/import roundtrip into reference_validation_v22.py, and mobile/console failures. Keep the 60-case chord/phrase page distinct from /composition-review/ riff-pair tool.

### 10. Important bugs and uncertainty
Resolved: V16 rejected melody windows without complete chord assignments; V17 learned intervals without chords but GP reused note definitions; V18 cloned note occurrences so edits did not leak. V20 initially inferred changes almost everywhere due overly broad uncertain chord scores, then restricted evidence. Unresolved: no human ground truth so no real chord or phrase accuracy; chord-template matches are not independently verified; probability scores uncalibrated; phrases heuristic and unlabeled; rootless/incomplete and passing-tone interpretations weak; instrument role and interactions across bass/melody/accompaniment weak; 0–100 nonzero values are edit probabilities rather than measured musical distance; limited rhythm substitutions, tie/articulation/tempo/complex-score fidelity; GP transformations not proof of originality or pleasing composition; review browser interactions unverified. V24 GP chord symbols are source annotations rather than adjudicated truth. Site presence does not imply functional UI. Browser storage can be lost unless user exports CSV. Never claim historic aggregate test counts equal freshly run HEAD tests.

### 11. Preserve the user's constraints
Genre agnostic, not hard-coded metal riffs, root/chug logic, D Aeolian, 4/4, fixed 16-bar forms or fixed phrase lengths. Learn ALL available intervals/rhythms even with unknown harmony. Keep raw MIDI/timing as observations; use harmonic role plus octave for melody transformation (minor ii R-m3-5 can map to major IV R-M3-5), but capture passing/suspension/resolution relationships too. Controls must independently preserve/change song form, chords, melody, rhythm, etc.: 0% exact lock; 100% meaningful coherent difference, not random noise or probabilistic application alone; report incompatible locks. Handle ambiguity honestly, measure actual accuracy with blind listening labels, maintain playability and exact GP occurrence isolation, test and push on 'Go', verify deployment, and do not break the other Guitar-Learning site/classifier/trainer components. Prefer concise, concrete, non-patronizing status and complete changed sections when code requested.

### 12. Exact continuation and success criteria
P0: Verify main HEAD, vite.config.js, .github/workflows/deploy-pages.yml, index.html, composition-review.html and V23 review template/build_review.py. Run npm ci, Node tests, npm run build and check dist/composition-review.html, live Pages HTTP and a real browser. Add a browser smoke test for case navigation, labeling, persistence, export/import and Web Audio activation; test audio manually. Do NOT fabricate review answers. Then independently review 5–10 varied cases and score using reference_validation_v22.py; preserve source/track/onset IDs, unknown labels and blinded judgments, expand/adjudicate 60 cases. First modeling comparison: instrument-role-stratify evaluate_v21.py; extend reference_validation_v22.py with breakdowns; add ablations/evidence tracing in joint_interpretation_v20.py and phrase_discovery_v19.py. Compare V19 rests/jumps/sections, V20 joint heuristics, and simple section/barline/chord-template baselines on identical human-labeled onsets. Report chord precision/coverage/abstentions and phrase precision/recall/F1 by role, song and musical context, stating uncertainty. Success initially means functional reviewed-data roundtrip, reproducible diagnosis and exact 0%-lock/regression stability. Claim improved music inference only if independent held-out labels show it beats baselines. Do not modify GP generator simply to increase count of changed notes.

**Underlying philosophy:** Build a multi-layer relationship model in which raw observations never disappear when a higher-order interpretation is uncertain. Harmony, melody, rhythm, arrangement, motif and form are interacting hypotheses over exact musical events, not successive gates. A test passing or note changed is not a measure of musical understanding.


---

## Supplemental successor-chat answers (1–7), 2026-10-14

**Evidence levels:** CONFIRMED = observable source, repository, files, test outputs, or explicit chat statement. RECOLLECTION = previous-chat account with no independent audio verification. HYPOTHESIS = proposed explanation not established by reviewed labels or an ablation. This is a continuation of the existing 8–12 supplement, not a replacement for the code or prior handoff.

### 1. Uncommitted / local-only artifacts, with precise scope

**CONFIRMED:** GitHub main contains the active V14–V22 modules, V23 player source, V24 source-annotation extractor and reports, and a root \`composition-review.html\`. V24's code and exported report **were subsequently pushed** under \`composition-lab/checkpoints/2026-10-14/\` (also check \`v24-reference/\`). Do not repeat the earlier tentative assertion that V24 was unpushed. Fetch HEAD before deciding which local script is newer.

**Local outputs that must NOT be presumed to have GitHub copies:** These are conversation artifacts on the prior working filesystem, typically \`/mnt/data/\`, not a comprehensive tracked-file diff. In particular:
- Generated studies: \`Original_16_Bar_Guitar_Study.gp\`, \`Original_16_Bar_Guitar_Study_V2.gp\`, \`Original_16_Bar_Guitar_Study_V3.gp\`, \`Original_16_Bar_Guitar_Study_V4_Data_Driven.gp\`, \`Original_16_Bar_Guitar_Study_V4_Step4.gp\`, \`Original_16_Bar_Guitar_Study_V5_Sequence.gp\`, \`Original_16_Bar_Guitar_Study_V6_Generalized.gp\`, \`Original_16_Bar_Guitar_Study_V7_Motifs.gp\`, \`Original_32_Bar_Guitar_Study_V8_Learned_Structure.gp\`.
- Unseen-song studies: \`Chet_Baker_Unseen_Test_V8.gp\`, \`Chet_Baker_Exact_Rhythm_V9.gp\`, \`Sweet_Child_Unseen_Test_V9.gp\` and \`Chet_Baker_Unseen_Test_metrics.json\`.
- Reharmonizations: \`Chet_Baker_Chord_Relative_Reharmonized.gp\`, \`Chet_Baker_Reharmonized_Full_Chord_Vocabulary.gp\`, \`Chet_Baker_Extended_Chord_Reharmonized.gp\`, \`Chet_Baker_Harmonic_Continuity_V11.gp\`, \`Chet_Baker_Contextual_Harmony_V13.gp\`.
- Control experiments: \`Chet_Baker_V15_chords.gp\`, \`Chet_Baker_V15_melody.gp\`, \`Chet_Baker_V15_rhythm.gp\`, \`Chet_Baker_V15_combined.gp\`, \`Chet_Baker_V16_rhythm.gp\`, \`Chet_Baker_V16_combined.gp\`, \`Chet_Baker_V17_Seed_17.gp\`, \`Chet_Baker_V18_melody.gp\`, \`Chet_Baker_V18_combined.gp\`, \`Chet_Baker_V20_melody.gp\`.
- Portable bundles \`Guitar_Learning_Checkpoint_2026-10-14.zip\`, \`V15_GP_Similarity_Export.zip\`, \`V16_Learned_Phrase_Export.zip\`, \`V17_Relational_Learning.zip\`, \`V18_Occurrence_Writer.zip\`, \`V19_Phrase_Discovery.zip\`, \`V20_Joint_Interpretation.zip\`, \`V21_Music_Validation.zip\`, \`V22_Reference_Validation.zip\`, \`V23_Review_Player.zip\`, \`V24_Source_Annotations.zip\`. Some source contents of these bundles are committed; the archives themselves need not be.
- Broader pre-checkpoint analysis exports: \`Harmonic_Anchors_By_Beat.csv\`, \`Harmonic_Anchors_Report.json\`, \`Riff_Tonality_By_Measure.csv\`, \`Original_Songs_Instrument_Detail.csv\`, \`Original_Songs_Measure_By_Measure.csv\`, \`Original_Songs_Musical_Breakdowns.xlsx\`, \`Original_Songs_Google_Sheets_Import.xlsx\`. Earlier handoff/research files and JSON feature summaries also existed in local artifacts/Library; search before assuming they were committed.
- Source scores existed in conversation/Library: \`Cloud Cascade (Tuned Down).gp\`, \`Nocturne_ Lost Faith (Tuned Down).gp\`, \`Immolation of Night (Tuned Down).gp\`, \`Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp\`, \`Sweet Child O' Mine.gp\`. Source ownership and licensing matter; do not upload third-party song files to a public repo without authority.

**Important distinction:** These are confirmed prior local *filenames*, not proof that every file is still recoverable by the next chat, nor proof that none happens to be duplicated in a repository asset. \`/mnt/data\` is runtime-local; retrieve from conversation/Library attachments or regenerate. Verify actual bytes and GitHub HEAD before claiming a complete backup. Older repo history may include some generated examples.

**Human labels:** As of V24, **zero confirmed human chord or phrase labels** were collected; the 60-case review remains unlabeled. V24 source-authored chord diagrams are weak reference annotations, **not independent human adjudication**. Thus no legitimate chord/phrase accuracy percentage exists yet. Prior passing-test counts are historical; rerun current HEAD.

### 2. What was actually listened to and musical feedback

**RECOLLECTION supported by previous conversation:** The user listened to early generated **V2 and V3** material and said they sounded good / promising. The critical later discovery was that this attractiveness came partly from *hard-coded* D Aeolian / heavy-riff structure / predetermined forms, so it **did not validate data-driven style learning**. Preserve both observations: pleasant output is important, but hand-authored scaffolding is not learning. Avoid attributing praise to V4–V24 without an explicit recorded audition.

**CONFIRMED explicit failure feedback:** V4 data-driven example sounded like an overly repetitive low C / failed to reproduce the source riff's two-note alternation. Root cause traced to categorizing any note within an octave of the lowest tuning as \`low\`, and then implicitly using \`low\` as a root/chug role. That erased melodic pitch distinctions and created a falsely root-centered style. Dropped this assumption in Step4.

**CONFIRMED technical evaluations, NOT listening judgments:** V9 style-distribution metrics improved with blended order sampling, but that does not establish musical quality. Chet Baker V10 preserved tuplets/dots after a timing fix; Sweet Child V9 revealed cross-track pooling/role contamination. Chet Baker V15–V20 exports were re-imported and statistically checked; changed-note counts are **not evidence anybody listened to or liked them**. V23 synthesized review player had no confirmed full browser listening run. If asked which specific V2/V3 passages sounded best, there is insufficient preserved bar/time-level feedback; do not invent one.

### 3. Failed/rejected approaches and WHY

- **Hard-coded 'good-sounding' riff generator:** D Aeolian, root/chugs, metal phrasing, 4/4, predetermined 16-bar or A–A′–B–A″ structure can sound coherent but is not general style learning; rejected as architectural default, not as an optional user style.
- **Low/high register = instrument or harmonic function:** V4 cutoff \`pitch <= lowest_tuning+12\` conflated pitch register with role; lost a crucial alternating-note distinction. Never equate 'low' with root/chug.
- **Unconditional pooling of all pitched guitar tracks:** Sweet Child training mixed lead, clean, rhythm and acoustic styles; generated attacks were fairly close numerically (6.66 vs 6.34/bar) yet notes/bar, chord frequency, and range were very different (generated 12 vs 7.85 notes/bar, ~35.7% vs 12% chord attacks, MIDI 39–72 vs 39–85). Explicit role/track conditioning remains unimplemented.
- **Fixed 4/4 / fixed-size motif assumptions:** Some earlier pattern code only used 4/4 segments, and V16's 2–4 contiguous events within one bar excluded genuine long/cross-bar phrases, ties, and varied polyphony. V19 partially addressed phrase-length/boundary issues; not human-validated.
- **Chord-required melody training:** V16 \`if all(assignments)\` discarded the whole group if a single chord wasn't recognized. Chet Baker: no melodic alternatives exported. V17 independent pitch-interval learning yielded 275 source windows / 110 distinct sequences without requiring chords, proving the structural gating flaw. Keep chord-relative interpretations as optional additional evidence.
- **One-note independent transposition/rhythm shuffling:** V15 random pitch offsets and adjacent duration swaps preserved some invariants, but did not learn musical phrases, development, contour/resolution, or coherent differences. Keep as diagnostic baselines only, not the target generation algorithm.
- **Probability of changing vs measured distance:** 80% trigger probability does not imply 80% musical difference; reject as the final interpretation of user controls. Likewise 100% must not imply random maximum entropy or every note must differ.
- **Edit GP definition IDs in place:** Shared note/beat IDs can be referenced in many occurrences. Naive writer silently leaks edits or refuses most transformations. V18 occurrence cloning solved much of this; source IDs can legitimately change, so validate musical events rather than demanding unchanged internal IDs.
- **Overconfident unlabelled chord detection:** V20 initial scoring interpreted almost every attack as a change; restricted to evidence-supported matches and explicit uncertainty. Chord-template fit is not a verified chord; count 'supported templates' instead of 'accurate chords'.
- **Too-conservative contextual chord continuation:** V12/V13 only filled same-chord, concordant, two-sided short gaps; 28 Chet Baker candidates, 0 added. This was a *safe failed coverage experiment*, not a proof that rootless chords have no recoverable harmony. Do not relax gates blindly.
- **Source chord symbols treated as ground truth:** V24 showed GP diagram \`KeyNote\` can be a placeholder; actual transcriber chord name comes from \`DiagramCollection Item.name\`. Even that name is an annotation, not independent verified truth.
- **Tests/exports confused with musical validation:** 79/79 passing, re-importable GP, 97 changed notes, a visible deployed HTML page, or 114/767 unique chord-template matches do not measure harmonic correctness, audible quality, or JS behavior. This is a recurring reporting failure to avoid.

### 4. Exact next agreed experiment after V24

No single V25 algorithm or quantitative target was explicitly agreed on. At the end of V24 the plan was to use author-provided chord symbols as **weak independent evidence**, then collect blind reviewed chord/phrase labels and compare inference with real references before more heuristic sophistication. Immediately afterward, the user changed priority to **deploying V23 listening review to the existing GitHub Pages framework**, then requested a complete handoff, then supplied successor-chat questions. Those deployment/handoff tasks superseded spontaneous model redesign.

Recommended executable next iteration:
1. Verify live \`/Guitar-Learning/composition-review.html\` *renders* (previous 404 is now observed fixed), then **test actual browser interactions** with a real browser: prev/next, play/stop and focused-track playback, tempo/context changes, model reveal sequencing, save/next, reload persistence, CSV export and V22 scorer import, mobile layout. Do not call the UI tested from HTML fetch alone.
2. Run a pilot of 5–10 blinded examples across at least two different scores/roles; check the notes in context, and collect **independent annotations rather than copying model/source chord labels**. Keep unresolved as a valid human answer.
3. Establish role-aware baseline metrics, annotate source-symbol provenance separately, compare V19/V20 against simple rest/jump/barline/motif baseline on identical labeled examples. Report precision, recall, F1 and abstention coverage, with example-level error explanations. Avoid optimizing on the same review set used for final claims.
4. Only after diagnosing common mistakes, change \`joint_interpretation_v20.py\`, \`phrase_discovery_v19.py\`, and/or the role/track selection in \`evaluate_v21.py\`; rerun held-out checks, exact 0% locks, GP re-import, and deploy smoke.

**Success means** the pipeline gathers valid labels with functional playback and reproducibly demonstrates a real accuracy gain (not merely more guesses/edits); no claim of learned musical understanding before the review.

### 5. Philosophy / conceptual breakthroughs

- **Observation ≠ interpretation ≠ artistic quality**: pitch/onset/tie/string are file facts; 'minor9', 'phrase beginning', 'passing tone', 'melody voice' are hypotheses; whether the output sounds good is another question. Store all three separately.
- **A musical explanation is a *network of relationships*, not a pipeline of required labels:** bass motion, simultaneous voicing, voice leading, melodic contour, arrival/resolution, repetition, rests, and form must inform one another. Unknown chords do not invalidate rhythmic or interval learning.
- **Preserve raw pitch as evidence, not as the control's conceptual definition:** for reharmonization melody is best encoded as chord-relative function plus octave; nonchord tones additionally need their approach/suspension/passing/resolution relations to surrounding events. Literal same pitches vs same harmonic function are distinct operations.
- **Represent doubt rather than manufacture certainty:** store competing chord/function/phrase hypotheses with evidence and missing-information tags. Probabilities need calibration; do not assign numeric confidence merely because a template matches.
- **Phrases are hierarchical and role-dependent:** note→gesture→phrase→section→song; boundaries may cross bars, meter changes, chords or voices. Section labels are not guaranteed and section markers are not validated phrase ground truth.
- **The source data may be misleading or incomplete:** a single voice does not imply melody; a low guitar note does not imply bass root; a GP chord name is a transcriber's assertion; source transcriptions can disagree.
- **Generalization needs hard negatives and unseen repertoire:** 3 familiar metal songs + two contrasting tunes are not a diverse benchmark. Generated note counts do not show new music is original. Separate train, tune, blind test corpora and protect genuinely unseen works.
- **Musically constrained transformation over random substitution:** locks must be exact, conflicts explicit; variation should preserve voice-leading, register/playability, rhythmic feasibility, phrase coherence and user-selected dimensions, never secretly break a lock.
- **Independent feature sliders aren't independent musical variables:** changing harmony necessarily changes absolute pitches if melodic *roles* remain fixed. Make representation-level invariants explicit instead of hiding cross-feature consequences.

### 6. Similarity controls — precise agreement and unresolved mathematics

**Firm semantic decisions:** 0% = exact identity for the specified feature. Chords=0 locks progression/harmony; melody=0 locks chord-relative degree/function **and relative octave**, not necessarily the literal MIDI pitches if chords change; rhythm=0 locks note/rest onsets and durations; structure=0 would lock ordered sections, lengths and recurrence. Changing chords minor ii R–m3–5 to major IV R–M3–5 should preserve degree functions 1/3/5 and octaves and derive the new actual pitches. User explicitly said absolute pitch need not be a separate similarity control; retain raw pitches for lossless extraction and validation. Nonchord events require a richer relation than 'semitone offset from root'.

**Not actually agreed/finalized:** No accepted distance equation, normalized weights, theoretical 100% bound, perceptual calibration, method of reconciling incompatible locks, role definitions for polyphonic material, or treatment of ambiguous chords as a single exact harmonic function. No globally valid 'maximum musical distance' is known: it depends on representation and feasibility.

**Reject:** Edit-trigger probability passed off as 0–100 similarity; independent uncorrelated pitch randomization; universal fixed-chord/scale/phrase templates; false confidence that a transformed role is always uniquely identifiable. V14–V20 strengths are implementation approximations, **not** demonstrated perceptual controls.

**Recommended mathematical design (PROPOSAL, not user-agreed):** each dimension d has a feature map \`f_d(song)\`, a normalized and empirically validated distance \`D_d(f_d(original),f_d(output))\`, and feasibility constraints \`C(output,locks)\`. Solve/choose \`argmin [musical coherence cost + sum_d w_d |D_d - target_d|]\` subject to *hard equalities* for all 0%-locked dimensions and instrument constraints. When target distances conflict with locks, return shortfall/alternatives; do not silently violate locks. Report *achieved* distances, not requested edit triggers. Calibrate with blind human judgments and style-relative examples; avoid claiming arbitrary distance is perceptually 80%.

### 7. Architecture: firm decisions vs unimplemented

**Firm:** multi-track/voice data retained in extraction; original GP note IDs and exact Fraction timing supported; safe per-occurrence write isolation; independent raw and inferred layers; no required chord inference to learn sequences; role plus octave encoding for chord-tone mapping; multiple hypotheses/unresolved labels preferable to hallucinating harmony; source section annotations are evidence, not universal truth. No baked-in instrument roles; infer/condition on observed tracks rather than assume the lowest notes are bass or all guitar parts are interchangeable.

**Still unimplemented or partial:** genuine cross-track synchronized arrangement generation, explicit instrument-role segmentation (melody/bass/chordal/riff/percussion) with confidence, tracking voice identity across measures, hierarchical musically validated phrases and section discovery without GP labels, joint probabilistic inference across tracks/time, nonchord approach/suspension-resolution modeling, confidence calibration, phrase-to-section generative hierarchy, true distance-calibrated sliders, independent blind listener quality evaluation, full complex-score GP roundtrip fidelity including ties/articulations/expression/tempo and unusual voices/meters. V20 is *heuristic fusion*, not a trained graphical model or a complete relational music model.

**First specific files for next engineering increment (after review-player smoke):** \`composition-lab/checkpoints/2026-10-14/evaluate_v21.py\` for explicit track/role selection and sampling; \`reference_validation_v22.py\` for ground-truth provenance, abstention-sensitive metrics and per-role breakdowns; \`joint_interpretation_v20.py\` and \`phrase_discovery_v19.py\` for evidence tracing/ablation; \`composition-lab/checkpoints/2026-10-14/v23-review/player_template.html\`, \`build_review.py\`, root \`composition-review.html\`, \`vite.config.js\` for deployment/function tests. Run on the identical 60 seeded cases with a separate held-out follow-up set; fix failures indicated by reviewed evidence, not guessed abstractions.

### Other facts easily lost between chats

The V21 60 cases were chosen via a stratified four-group sampler, not random population sampling; 20-measure cutoff was convenience and biases intros. V24 has 69 Chet Baker chord-symbol occurrences (transcriber, not truth), 54 source section markers across five scores, and only 3 of 60 selected cases at annotated chord onset. V18 increased exported melody edits from 4–8 to 102 by cloning shared note definitions. V19 found 50 candidate gestures / 387 windows; V20 found 97 template-supported sonorities and 151 unresolved attacks on Chet Baker and reduced windows to 344; these counts do not establish phrase/chord accuracy. V21 found 114 unique-template matches over 767 attacks in five first-20-measure excerpts (14.9% coverage, not accuracy). Verify all historical numbers against their specific scripts and data before using them as a current benchmark.


## V23 review-player verification and commit policy — 2026-10-14

**User instruction:** Push ongoing Composition Lab changes to GitHub as work proceeds, including **both** the actual scripts/files and this handoff. Report commit links; never claim a change was pushed before the write succeeds.

### Verification status (do not overclaim)

- Earlier Chromium smoke testing was reported to pass 60-case data loading, navigation, in-page annotation/save, review counts, model reveal, piano-roll redraw, and 60-row/17-column CSV generation. The corresponding results were produced in the prior assistant runtime; **do not treat these as independently reproduced from a clean checkout**.
- A later attempt to verify browser reload persistence, audio scheduling/audible playback, actual downloaded CSV, and live GitHub Pages interactions was **inconclusive** due to browser navigation restrictions/timeouts. These remain **unverified**.
- Source review confirms the V23 template uses browser localStorage, Web Audio oscillator synthesis, and CSV Blob export. Presence of implementation is not proof of functional behavior in a real browser.
- The live review URL is https://mtch777.github.io/Guitar-Learning/composition-review.html ; verify with real browser interaction before reporting success.
- **No independent human chord or phrase labels have been collected.** Musical accuracy remains unknown; 114/767 template-supported attacks is coverage, not accuracy.

### Committed regression baseline

- `composition-lab/checkpoints/2026-10-14/v23-review/test_review_player_contract.py`: dependency-free static template contract tests for controls, handlers, payload marker, export fields, local persistence hooks, and blind prediction reveal. This is **not** an end-to-end browser test. Run the file with Python and report the actual outcome before claiming it passed.
- Next: implement a repeatable real-browser test with reload persistence, real CSV download parsing, Web Audio scheduling, and mobile checks; collect a small set of blind human judgments from different source songs/roles, then run V22 scorer with provenance and abstention coverage.
- For every subsequent increment, commit the implementation/test changes and append confirmed results, known failures, and next steps to this handoff.


### V23 listener-controlled reference chord audition (2026-10-14)

- User requested alternatives to the free-text chord identity field and buttons to hear reference chords **while the example plays**.
- Implemented independent chord audition controls in both `composition-lab/checkpoints/2026-10-14/v23-review/player_template.html` and the published-source `composition-review.html`. Users select any chromatic root and major, minor, diminished, augmented, dominant7, major7, minor7, sus2 or sus4; audition a sustained synthesized reference chord concurrently with the score context; stop it separately; or transfer its name to the chord-answer text field (without automatically saving).
- Reference audition is user-controlled and never populated by the model's prediction. It is intentionally a **listening aid**, not a validated automatic chord classifier. The available chord vocabulary is limited; users can still type arbitrary labels or `unknown`.
- Added static regression checks for the reference controls in `v23-review/test_review_player_contract.py`. **Browser/audio interaction and actual deployed GitHub Pages remain unverified** until a live browser test. These commits were not accompanied by an executed automated test run.
- The root HTML page is committed on `main`; GitHub Pages publication timing and cache behavior must be verified independently.
