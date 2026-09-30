# Guitar Physical-String Analytics — Current Handoff (updated 2026-09-30)

## NEXT CHAT START HERE

**Source of truth:** `mtch777/Guitar-Learning`, branch `main`. Step 18 remains open. Steps 1–17 are complete; keep their historical research below and the experiment ledger in `training/EXPERIMENTS.md`. Never infer production accuracy from a stored-WAV result. String **1 is lowest**, string **8 highest**; open MIDI `[27,34,39,44,49,54,58,63]`, frets 0–24.

**Latest verified final offline stability run:** `36668469829` on `67284bb6f75d44de55240a4e5d8cc1ab8b7ab93d`; documentation advanced afterward. Refetch `main` and its current tree before editing. GitHub Pages: `https://mtch777.github.io/Guitar-Learning/`.

### Current measured results and boundaries

| Variable / stage | Status | Evidence | Action |
|---|---|---|---|
| STFT/power and matched preprocessing | Validated offline | Exact centered samples gave power RMSE 4.58e-15; matched librosa-resampled waveform + opt-in zero padding/segment-global dB gave MFCC mean RMSE 3.99e-6 and identical string predictions on all 384 | Keep the parity settings experimental; do not rewrite validated spectral math |
| Ordinary browser-compatible temporal Stage B | Baseline preserved | True-MIDI mask 375/384; detected-MIDI mask 374/384; Python reference 376/384. Corrected settings alone with JS linear resampling did not improve the consistent train/test path | Do not claim resampling or dB/padding alone fixes accuracy |
| Browser-compatible reference YIN240 | Offline port validated, opt-in | Run `36613549255`: MIDI 375/384, tuple 366/384; all 384 MIDI decisions match Python librosa YIN. Custom-YIN baseline: 373/384 MIDI, 364/384 tuple. Extra median pitch compute ~10.15 ms | Live confidence, timing, and gating remain unvalidated |
| Step-18 temporal MFCC runtime | Optimized in training frontend | Smoke 36 → Real 384 stored WAVs. All 29,952 Float32 model inputs exactly unchanged; median 3-segment runtime 99.460→0.777 ms, 128×, same runner | FFT is default in `training/step18_browser_frontend.mjs`; `--dft` retains baseline, `--compare-fft` runs paired comparison |
| Fusion3 browser path | Raw-input and detected-MIDI harmonic test validated offline; live pending | Archived OOF 379/384; fresh matched-audio 378/384; raw-JS-feature-trained 377/384 strings and 368/384 complete tuples with reference YIN. Detected-MIDI harmonic retraining changed zero final decisions; Python/JS decisions agree 384/384 | Keep experimental; measure complete response timing/confidence and live capture before trainer switch |
| Frame → pluck → fusion3 replay | Streamed pitch and early-event policy compared offline; live pending | Correlation 303/384 tuples; hybrid 373/384 tuples. First position: immediate 362/384, selective held-out gate 369/384, always-wait 373/384; selective adds four wrong first events against wait | Keep early events withheld in the experimental quality baseline; validate real lesson flow before integration |
| Callback phase / leading silence | Whole-frame silence control passed; shifted capture coverage limited by WAV ends | One/two silent callbacks: 383 captures and 373 tuples, no pre-onset events. Partial phases +23/+46/+70 ms: 40/97/160 newly incomplete captures; small paired prediction changes | Keep misses separate from acoustic errors; obtain longer original tails or label synthetic-tail stress explicitly |
| Live behavior | Pending guitarist input | [Paired live pitch page](https://mtch777.github.io/Guitar-Learning/live-yin-test.html?v=af21453) deployed, Pages run `36616795763` passed and page loaded. No actual guitar recordings yet | Full trial prepared at `live-pipeline-test.html`; collect 24 pilot trials and export ZIP. No actual live accuracy result yet |

**Production separation:** `training/step18_browser_frontend.mjs` is the 512-point temporal MFCC/YIN experiment harness. The normal trainer still uses `src/audio/pitch.js` correlation and `src/audio/ringing-pluck-buffer.js` confidence/hold gates; its full-model `src/classifier/ringing-features.js` already uses a separate 2048-point FFT. The live trial is an isolated page and does not change normal lesson decisions. The 128× offline MFCC gain is **not** a measured live-trainer speedup. Reference-YIN confidence is a CMND-derived diagnostic and not calibrated to the live `pitchConfidence >= 0.55` gate.

### Current offline conclusion and next action

- The original full-WAV estimated-MIDI fusion experiment was **368/384 complete tuples** with preserved reference-YIN pitch. The callback replay is a distinct, stronger timing/gating protocol: current 4096-sample correlation yielded **304/384 pitch** and **303/384 held-out fusion tuples**; a correlation-start/rolling-240-ms-YIN-vote hybrid yielded **380/384 pitch** and **373/384 tuples**, 72 rescues and two regressions. Both captured 383/384 stored WAVs. YIN-only capture after the 240 ms window completed just 166/384: all 384 triggered, but 218 ended before 0.82 more seconds were available. Do not interpret its 132/384 tuples as intrinsic YIN accuracy.
- The hybrid still allowed 33 singleton-string events before capture, 14 wrong. Its first position event matched the label **362/384**, versus 373/384 at the completed fusion decision. A paired policy score on the **same saved 384 outputs** withheld the early event: **11 rescues, zero regressions, one missing under either policy**. It delayed 19 already-correct early events by median **796.57 ms** among the 33 affected; overall first-event median 887.66→887.77 ms. These are position proxies; the quiz, visible cells, context prior, transitions and actual lesson acceptance were not replayed. Reproducible scorer `training/score_step18_event_policy.mjs`, workflow `step18-event-policy.yml`, run `36659607658`, artifact `11073313570`, permanent result `training/results/reference/step18_event_policy_real_384.json`.
- **Selective gate test:** First-frame confidence, dBFS, MIDI and timing were extracted from the same original WAV replay. A one-dimensional early rule was chosen for each entire held-out MIDI note using other notes only, requiring zero wrong early events in training folds. It kept **six correct fast events**, but produced **four wrong early events** that replaced correct final decisions: **369/384** correct first positions versus **373/384** always-wait. Full-sample MIDI `>=83` looks safe for seven early events but is selected on the evaluation set and is not validated. The learned policy fails the zero-regression gate. Do not deploy it. See `training/score_step18_selective_early.mjs`, `.github/workflows/step18-selective-early.yml`, and `training/results/reference/step18_selective_early_real_384.json`. Actions run `36665632798` passed Smoke → gated Real on `6d3ba4823089e48aa2906fab9aad3e3491f4b583`; artifact `11075223801` SHA256 `d500c29ef29e768c2484c8f5199f3e621f0ba0e003e97d8a7bb6531c7cdb94d3` reproduces all paired counts. This is a stored-WAV position proxy, not actual trainer acceptance.
- **Callback robustness completed:** 1,024/2,048/3,072 leading zero samples changed the phase within a 4,096-sample callback; 4,096/8,192 samples supplied one/two full silent callbacks. An initial experiment exposed a harness bug: it switched to YIN after 240 ms of stream time even without a pluck. The corrected experimental hybrid keeps correlation as the onset trigger until the buffer starts, then YIN votes. With whole silent callbacks, captures and tuples held **383/384 and 373/384** with no pre-onset position event. Partial phase shifts produced **40/97/160 newly incomplete captures**, mainly because many saved WAVs stop at ~0.82 seconds. Among all **222 recordings capturable under every condition**, aligned baseline was **214/222** tuples versus **217/222** for each partial phase; this selected subset does not establish an improvement. Do not score incomplete clips as acoustic errors or infer real-stream robustness without longer tails. Run `36661979277` passed Smoke → Real; artifact `11074254391`, SHA256 `bbe55fbec0f376bb198c70c47b1aee20940d9ff3c700f51aa397b6e9f3540266`; compact per-recording report `training/results/reference/step18_phase_robustness_real_384.json`.
- **Final offline stability test completed:** fixed two-frame agreement scored **369/384** first positions, with seven wrong early events and four regressions versus wait. Requiring two rolling-YIN frames scored **372/384**, with four wrong early events and one regression. Correct early events saved median 724/543 ms respectively. Neither rule rescued a failed final tuple; both failed the zero-regression gate. No threshold fitting/retraining was used. Source replay retains entire-MIDI-held-out fusion models. Actions run `36668469829` passed Smoke → gated Real; artifact `11077151815`, SHA256 `315cce1ae1cb3e594997125d6c962e922c51733f3458500f050846469b18814e`, reproduces all counts. Workflow success does not mean the candidate quality gates passed. See `training/results/reference/step18_stable_early_real_384.json` and `.github/workflows/step18-stable-early.yml`.
- **Next is live collection:** full-pipeline isolated trial is `live-pipeline-test.html`; instructions `training/research/LIVE-PIPELINE-TRIAL.md`. Start the default **24-pluck pilot**, export the ZIP and inspect input/capture/labels before the full 240 grid. The page uses final estimated-MIDI-trained models with a hash/provenance manifest, hybrid completed decisions and paired correlation+same-fusion control. It records Float32 WAVs, target labels, frame/event timing, probabilities, CPU/queue, misses and input channel settings. Labels never enter inference. Analyze with `training/summarize_live_pipeline.py`. Acoustic target matching is measured; actual lesson acceptance is not. Paired inference adds CPU load. Actual guitar results are still pending.
- Normal trainer decisions remain unchanged: it uses its existing 107-feature full model and correlation frame path. The fusion3 model is still experimental. Reproducible workflows: `.github/workflows/step18-full-replay.yml` (run `36654208125`, artifact `11071960789`) and `.github/workflows/step18-yin-gate-replay.yml` (run `36655131322`, artifact `11072790013`, SHA256 `c0259b29538b5f08d6c06522df67c92e588e6481e86a1d841b29204bfd3f4432`). The latter passed Smoke → Real and measured hybrid Node-runner median YIN frame compute 12.23 ms, fusion 51.85 ms and capture plus inference 887.77 ms from first stored sample. Per-recording reports: `training/results/reference/step18_full_replay_real_384.json` and `step18_yin_gate_*`. Every new experiment uses Smoke → gated Real; do not rerun historical experiments merely to regenerate artifacts.

### Live test status and design limits

`live-yin-test.html` records the same microphone stream through current correlation and a rolling 240 ms reference-style YIN. The suggested pitch-only grid is 8 strings × frets 0/5/12/19/24 × soft/normal/hard × 2 repeats = **240 plucks**. It exports paired frame decisions, RMS, confidence and compute times; `training/summarize_live_yin.py` scores one decision per pluck and paired discordance. This is **not a full physical-string or gameplay validation**: no Stage-B model decisions, onset-to-decision timing or lesson gate outcome are captured. A subsequent guided full-pipeline test must label known target string/fret, acceptance/rejection, overlap cases, repeated/transitional notes, noise and stable latency. The user now requests live testing next after the final offline stability test.

### Execution and reporting rules

- Every new experiment uses **Smoke → gated Real** with the smallest meaningful Smoke, progress output and preserved results. Do not rerun completed runs merely to regenerate outputs.
- When reporting status, use the current **Variable / stage | Status | Evidence | Action** table. Do not append the old “Remaining experiment steps” list.
- Candidate masks and trainer context are separate from raw acoustic output. Step 15 found 348 harmful overrides under deliberately wrong/stale singleton context.
- The connected GitHub file API can publish changes when local `git push` lacks credentials. Fetch each current file blob SHA immediately before replacing it; do not overwrite concurrent work. Training-only changes need no browser cache-key edit.
- After code deployment provide a cache-busted Pages link, action run, and clearly separate stored-WAV, browser-compatible, and actual live measurements.

## Historical research and experiment record

The material below preserves the methods, literature, Steps 1–17, and earlier Step-18 snapshots. Statements phrased as “current,” “next,” or “outstanding” inside those older snapshots describe their time of writing. **Use the table and next-offline-work section above for current decisions.**

## Project / production context

- Repository: `mtch777/Guitar-Learning`
- Branch: `main`
- Live site: `https://mtch777.github.io/Guitar-Learning/`
- String numbering is intentionally nonstandard:
  - String 1 = lowest-pitched physical string
  - String 8 = highest-pitched physical string
- Default open-string MIDI: `[27,34,39,44,49,54,58,63]`
- Allowed fret range: 0–24.
- Pitch can map to multiple physically possible `(string,fret)` positions. The central research problem is distinguishing those positions acoustically.
- Conceptual stages:
  - Stage A: onset + pitch/F0 hypotheses
  - Stage B: physical string/fret acoustics
  - Stage C: temporal and trainer context
- Preserve these stages separately in evaluation so task context cannot masquerade as acoustic accuracy.
- A future architecture may score joint `(MIDI,string,fret)` hypotheses rather than committing to one MIDI before string classification.
- Evaluate Stage B under both ground-truth MIDI and detected MIDI.

## Dataset

- Dataset: `training/data/ringing_384`
- 384 WAV recordings, about 94.7 MB.
- All 8 strings, frets 0–24.
- Naming: `s{string}_f{fret}_{soft|normal|hard}_ringing.wav`.
- Strings 1–2 have soft/normal/hard at every fret.
- Strings 3–8 have many non-anchor frets at normal strength; anchors such as 0, 5, 7, 12, 17, 19, 24 include multiple strengths.
- Dataset granularity matters: one recording is ~0.2604 percentage points of total accuracy.
- Fixed MIDI entangles string and fret. That is acceptable for physical-position prediction but must be remembered when interpreting learned acoustic features.
- Pick strength, technique, pickup configuration, setup/session and input gain are possible latent/confounding variables.

---

# Final deep-research summaries

These are the conclusions from the deep-research work that led to the experiment program. They should remain available even when individual source files or old chats are no longer in context.

## 1. Abeßer — Automatic String Detection for Bass Guitar and Electric Guitar

Abeßer remains the most directly relevant published architecture found for our physical-string prediction problem. It takes a known fundamental frequency, models the post-attack guitar signal as slightly inharmonic decaying sinusoids, estimates the first 15 partials with an autoregressive spectral model, converts them into 48 physically motivated features, reduces them with supervised LDA, and classifies the string with an RBF SVM. It then applies a fretboard-validity mask and sums class probabilities across five adjacent frames.

The 48 features are:

- inharmonicity β: 1
- relative amplitudes of first 15 partials: 15
- eight statistics of partial amplitudes: 8
- normalized frequency deviations of first 15 partials: 15
- eight statistics of frequency deviations: 8
- partial-amplitude/spectral slope: 1

The eight statistics are max, min, mean, median, mode, variance, skewness and kurtosis.

The physical stiff-string model is approximately:

`f_k = k f_0 sqrt(1 + β k²)`

Important implementation details from the publication:

- guitar audio downsampled to roughly 10.1 kHz
- 256-sample frames
- 64-sample hops
- first 15 partials
- modified-covariance AR spectral estimation rather than ordinary FFT peak picking
- percussive/attack transition detected from AR process variance
- harmonic-decay frames used rather than the attack
- first five frames after the transition aggregated
- normalization → LDA → RBF SVM
- LDA dimension = `Nstrings - 1`; direct 8-string generalization is 7
- C and gamma chosen with a three-fold grid search
- impossible strings zeroed before the final decision

On the paper's six-string electric-guitar data, the reported progression was roughly F1 .70 raw → .81 with plausibility filtering → .90 with filtering plus five-frame aggregation. A frame-level MFCC baseline was much weaker in that publication.

The paper's electric-guitar feature selection strongly emphasizes high-order partial geometry. The normalized 15th-partial frequency deviation was especially important. Other highly ranked information included inharmonicity, variance/skewness of frequency deviations and relative partial amplitudes.

The major reproducibility gaps are important:

- exact AR order is not published
- partial-amplitude extraction from the AR representation is underspecified
- the mode statistic over 15 continuous values is underspecified
- therefore our implementation is a method reproduction, not a bit-exact reconstruction

The core research lesson is more important than the old SVM:

> The highest-value thing to copy from Abeßer is explicit measurement of where each partial sits relative to a stiff-string harmonic model, combined with partial amplitudes and enough post-onset temporal evidence to make a stable decision.

The original POC logic was therefore:

- parity branch: modified-covariance AR → 48 features → scaler → LDA7 → RBF SVM
- modern branch: robust partial extraction → same physical feature family → modern classifiers
- compare raw → candidate mask → temporal aggregation
- compare Abeßer-only → current-only → combined features/probabilities
- report ambiguous-note performance separately so candidate masking cannot inflate apparent acoustic performance

A failure of modified covariance + RBF SVM does not automatically falsify the physical idea. It can instead indicate that the estimator/classifier does not transfer.

## 2. Harmonic / partial / inharmonicity investigation

The deeper physical investigation reinforced that same-pitch notes can differ because different physical strings have different stiffness, tension, core geometry and vibrating length. A perfectly flexible string has partials at exact integer multiples of F0; a stiff string's upper partials progressively shift.

For small β, the deviation grows strongly with harmonic number. This is why H15 can contain more string-identifying information than H2/H3 even when the fundamental is identical.

Hjerrild & Christensen provide an especially important physical extension. Their inharmonicity parameter relates to elastic modulus, core diameter, tension and vibrating length approximately as:

`B_s ∝ E_s d_s^4 / (T_s L_s²)`

Because fret position changes vibrating length, they derive a predictable fret trajectory:

`B_s(f2) = B_s(f1) 2^((f2-f1)/6)`

That suggests a powerful personalized model: instead of learning every fret independently, estimate a physical-string stiffness trajectory and use the candidate fret to predict expected inharmonicity.

Hjerrild's short-segment work is especially relevant because it used approximately 40 ms segments and reported low string/fret error in its own experimental setting. This made a short-latency physical estimator a high-priority future challenger.

Partial amplitudes provide a second fingerprint, but they are more confounded by plucking position and pickup transfer function. The strongest representation should preserve both:

- frequency geometry: actual partial frequencies, β, deviations from expected positions
- amplitude geometry: relative partial amplitudes, missing harmonics, spectral slope, temporal change

Do not collapse the spectrum too early into only H2/H1, H3/H1 or generic centroid.

Useful packages:

- Essentia: SpectralPeaks/HarmonicPeaks are useful references, but Essentia's scalar `Inharmonicity` is not equivalent to Abeßer β or Hjerrild B.
- librosa: useful for rapid harmonic-energy features, but harmonic interpolation alone does not recover the actual shifted peak frequencies needed for the strongest physical features.
- NumPy/SciPy: appropriate for a custom physical peak/β estimator.

The recommended first physical POC was to compare a custom peak-based extractor with an Essentia reference extractor on identical audio, compute our own β/deviations, and then add the Hjerrild-style short parametric estimator.

The most important evaluation subset is **ambiguous pitches** — notes physically playable on two or more strings. Otherwise the candidate mask can solve examples without any acoustic string information.

## 3. SIF / inverse-string-frequency investigation

SIF attacks the physical-position problem from a different direction.

When a string is fretted, it is divided into:

- the sounding fret→bridge segment
- the inverse/opposite nut→fret segment

The opposite segment can have resonances whose frequency depends on the physical string and fret even when the sounding pitch is shared by multiple positions. Research suggests this can contain string/fret information.

The major concern for our system is acquisition. A microphone near the fretboard can hear mechanical/opposite-segment vibration; our ordinary magnetic pickup is primarily sensitive to the sounding segment near the pickup. Therefore SIF is scientifically interesting but should not receive major implementation effort until a cheap feasibility test proves that the inverse resonance is measurable in our actual pickup recordings.

The correct experiment is binary:

- choose same-pitch/different-position recordings and low/mid frets
- calculate expected inverse-segment resonance regions
- inspect spectral SNR/support at those frequencies
- if a stable position-dependent signal exists, continue
- if it does not, kill the branch

SIF should remain a low-cost feasibility experiment, not an assumed production feature.

## 4. SpectroFusionNet / learned representation fusion

SpectroFusionNet does not solve physical-string identification directly. It classifies electric-guitar playing techniques, so its value is architectural rather than task-equivalent.

It uses complementary time-frequency representations such as:

- MFCC representation
- continuous wavelet transform
- Gammatone representation

and CNN backbones including MobileNetV2, InceptionV3 and ResNet50. Late fusion of representations improved results, with MFCC + Gammatone particularly useful in the reported task.

The transferable lesson is:

> Different representations can contain complementary guitar information, and decision/late fusion can outperform forcing all evidence into one representation.

Do **not** copy a heavyweight ResNet50 architecture merely because it worked for technique classification. Our first learned string model should be small and should only survive if its mistakes complement the engineered models enough to justify latency/complexity.

This research directly motivated:

- a later small-CNN tournament
- multiple representations only after a simple learned baseline
- probability/late fusion before complex embedding fusion
- judging learned models by unique error rescues, not just standalone accuracy

## 5. TheStringTheory audio engine

After code/package-level inspection, TheStringTheory was promoted from an interesting repo to a major **architectural reference**, but not to the main physical-string solution.

Its strongest transferable ideas are:

1. dedicated fast monophonic F0 path rather than making a deep/polyphonic model do everything
2. preserve detector confidence and gate weak frames
3. explicit onset detection
4. temporal aggregation and hold/debounce behavior
5. run expensive/deep analysis asynchronously as secondary evidence
6. use exercise/chart context only in a final verifier
7. use register-specific fallback behavior because low/high guitar notes fail differently

Its live engine uses a real-time scheduler around multiple detectors. Important observed concepts include:

- HFC onset detection
- YINFast pitch
- confidence/RMS gating
- median/hold behavior
- harmonic verification
- deeper Basic-Pitch-like secondary analysis
- expected-note/context bonuses
- per-string calibration concepts
- separate fast and deep processing threads

The strongest limitation for our task is equally important:

> Nothing found in TheStringTheory provides an acoustic solution to same-pitch physical-string identification comparable to explicit partial-frequency deviation / inharmonicity features.

Its spectral verifier determines whether expected notes are acoustically plausible; it does not independently establish which physical string generated a shared pitch.

The strongest synthesis was therefore:

`TheStringTheory-style front end + physical string features + fretboard mask + multi-frame aggregation + separate context verifier`

The architectural boundary is critical: log the raw acoustic prediction before context enters, then separately log any context reranking. This lets us measure how much performance comes from listening versus knowing the trainer's expected answer.

## 6. ChartPlayer / PitchDetect

ChartPlayer/PitchDetect is useful for Stage A, but its most valuable component is its **multi-candidate autocorrelation representation**, not its final pitch-selection rule.

The investigated stack:

- mono ring buffer
- detector update around every 50 ms
- 4096-sample pitch window
- zero-padding for FFT autocorrelation
- up to 16 interpolated autocorrelation peaks with strengths
- separate 8192-sample spectral/chord analysis
- simple continuity heuristics for final pitch
- a separate dual-envelope onset detector exists, although ChartPlayer's active note path did not directly use it

The key discovery was that the correct F0 could remain present among raw autocorrelation candidates even when ChartPlayer's selected `CurrentPitch` was wrong. The repo's own development history moved in the same direction: gameplay logic was changed to inspect multiple detected peaks to improve fast transitions.

Synthetic stress tests were diagnostic rather than product-accuracy estimates. They exposed two structural weaknesses in the stock selector:

- raw autocorrelation thresholding is amplitude-dependent
- strong harmonics/missing fundamentals can seed octave/period errors that continuity then preserves

Therefore:

> For our system, ChartPlayer's candidate generator is more valuable than ChartPlayer's candidate selector.

The correct POC is not simply “ChartPlayer vs Pitchy top-1.” It is to preserve a top-K pitch candidate set with normalized confidence and feed those candidates into downstream physical-position inference.

This research directly motivates the Stage-A tournament and the later hard-MIDI vs multi-hypothesis experiment.

## 7. Jam Origin MIDI Guitar

Jam Origin provides strong evidence that ordinary mono guitar audio can support sophisticated low-latency note tracking without a hex pickup, but it should not be treated as proof of physical-string identification.

Public information supports a mature temporal tracking system — onset sensitivity, pitch prediction, note identity, bends/slides, dynamics, note lifetime and state — but modern MG2/MG3 internals are proprietary. Current public material does not justify inventing FFT sizes, hidden neural architecture, confidence probabilities or exact detector latency.

Jam Origin is therefore most useful in two roles:

### Stage-A external oracle/reference

Run Jam Origin on the same labeled dry-DI recordings as our open detectors and compare:

- onset accuracy/latency
- first-correct pitch latency
- stable-correct latency
- octave errors
- false notes
- missed soft notes
- pitch trajectory stability

Then hold Stage B fixed and measure how much downstream physical-string accuracy changes. This tells us whether Stage A is actually the bottleneck.

### Instrument-specific template inspiration

Historical Jam Origin material/patent work suggests another idea highly relevant to our fixed rig: teach the recognizer what individual playable positions on the particular instrument sound like, including onset/sustain exemplars and candidate-relative spectral comparisons.

That complements Abeßer rather than replacing it:

- Abeßer: physically interpretable harmonic fingerprint
- instrument calibration/template matching: empirical fingerprint of this guitar/interface
- fretboard: hard physical candidate constraints
- temporal aggregation: confidence/stability

The strongest architecture emerging from the Jam investigation was:

`onset → robust F0 → candidate mask → [physical harmonic/inharmonicity evidence + calibrated string/fret templates + attack/early-sustain evidence] → classifier → multi-frame confidence`

A concrete future POC is a calibrated per-string/per-fret spectral-template matcher evaluated specifically on same-pitch/different-string examples, then fused with the surviving engineered representations.

Jam Origin itself should remain a benchmark/reference unless a documented API output is experimentally proven to provide reliable physical-string identity.

---

# Cross-research synthesis

The researched systems solve different layers:

- Abeßer / Hjerrild / SIF: physical string or position
- ChartPlayer / TheStringTheory: onset, pitch and temporal front end
- Jam Origin: mature black-box transcription/tracking reference plus calibration inspiration
- SpectroFusionNet: representation/fusion inspiration

The strongest overall research architecture became:

`onset → several F0 hypotheses → confidence → physically possible (MIDI,string,fret) candidates → acoustic string evidence → temporal aggregation → optional trainer-context reranking`

The biggest unresolved acoustic question at the start of experimentation was:

> At what time after onset, with what analysis-window length, are same-MIDI notes played on different physical strings maximally separable on our actual 8-string pickup signal?

That question motivated the time-phase experiments.

Other major synthesis conclusions:

- instrument specificity may be an advantage because deployment uses a fixed guitar/interface chain
- pickup configuration and session/day can be confounders
- open strings may deserve separate treatment
- technique/pick strength is a latent variable
- probability calibration is essential for meaningful fusion
- candidate count must be reported; one-candidate notes are trivial after masking
- acoustic-only, mask-adjusted, temporal and trainer-context outputs must be separately logged
- Stage A and Stage B must be evaluated separately before complete-pipeline conclusions are drawn

---

# Existing production baseline and prototypes

## Production baseline

The existing training pipeline uses 107 engineered features:

- attack: 13 MFCC mean/std plus spectral centroid, bandwidth, rolloff, flatness and ZCR statistics
- sustain: corresponding feature family
- five amplitude/energy features

The expanded harmonic model uses 214 features and adds harmonic ratios, temporal regions/deltas, peak-shape/inharmonicity-related information.

Current Python stack includes:

- librosa
- NumPy/SciPy
- scikit-learn
- XGBoost

Important files include:

- `training/train_full_ringing.py`
- `training/run_harmonic_ablation.py`
- `training/analyze_classifier_errors.py`
- `training/FEATURE_PARITY.md`
- `training/browser_feature_parity.js`

The production research split is leave-one-entire-MIDI-out, with candidate masking based on tuning and fret range.

## Prototype families originally planned

- A0 current baseline
- A1 Abeßer 48 → LDA → RBF-SVM
- A2 Abeßer 48 → tree/boosted classifier
- A3 current + Abeßer → boosted classifier
- A4 expanded harmonic features → boosted classifier
- B1 temporal probability aggregation
- B2 learned temporal model if simple aggregation proves insufficient
- C1 small raw STFT/log-mel CNN
- C2 F0/harmonic-aligned CNN
- C3 complementary representation late fusion
- D1 engineered + learned embedding
- D2 probability fusion
- E1 SIF feasibility
- P1 Stage-A pitch detector tournament

The program intentionally evolved based on measured results rather than blindly executing every prototype.

---

# Experiment rules

Every remaining experiment must have exactly:

1. **Smoke test**
2. **Real run**

The smoke test must traverse the whole real pipeline with the smallest practical amount of real data/processing. The real run must be gated on smoke success.

Long jobs must emit:

- extraction progress `x/N`
- current model
- fold `x/N`
- held-out MIDI where relevant
- elapsed time
- ETA

Do not rerun completed experiments merely to regenerate outputs. Rerun only when data, implementation, features or evaluation methodology changed enough to invalidate the old result.

Save:

- metrics
- predictions
- configuration
- feature metadata
- confusion matrices
- error analysis
- artifact/run identifiers
- enough information to compare future models without recomputing old ones

GitHub Actions artifacts expire; important results must also be recorded permanently in the repo.

---

# Evaluation protocol

Primary metrics:

- physical-string accuracy
- macro F1
- per-string precision/recall/F1
- confusion matrix
- performance by MIDI/fret/pick strength/candidate count
- top-2 accuracy / correct-string rank / top-2 margin
- confidence calibration
- feature extraction latency
- inference latency
- onset→decision latency
- browser computational cost

Important separate outputs:

- raw acoustic prediction
- candidate-masked prediction
- temporally aggregated prediction
- trainer-context-adjusted final prediction

Primary difficult subset:

- notes with two or more physically possible strings

Also evaluate:

- ground-truth MIDI → Stage B
- detected MIDI → Stage B

This separates pitch-tracking failures from physical-string-classifier failures.

---

# Completed experiments — preserve, do not rerun

## Baseline / full-harmonic benchmark

Run: `36354714761`

Baseline 107:

- 371/384 correct
- **96.6146%**
- 13 errors

Full harmonic 214:

- 372/384 correct
- **96.875%**
- 12 errors

Interpretation:

- doubling the engineered feature count fixed only one additional recording
- static feature expansion alone is near a ceiling
- remaining errors are structured, especially neighboring strings S4/S5/S6
- harmonic information is real but current use is inefficient

Artifact: `10943980624`

## Time-phase screening

Run: `36358305377`

- 45 windows
- 7 feature families
- 40-tree screening

Best overall:

- all features
- cumulative 0–160 ms
- **95.0521%**

Best MFCC:

- cumulative 0–120 ms
- 26 features
- **94.7917%**

Other key observations:

- attack 0–40 ms: 83.3333%
- 40–80 ms: 92.9688%
- 80–120 ms: 93.75%
- early useful information is strong
- dedicated harmonic families are weak standalone
- very late-window collapse is partially confounded by zero-padding when recordings are shorter than the requested region

Artifact: `10945985689`

## 100-tree time-phase confirmation

Run: `36361317622`

Best configuration:

- **MFCC 0–120 ms**
- 26 features
- 370/384
- **96.3542%**
- 14 errors

Comparisons:

- all 0–900 ms: 96.0938%
- all 0–120 ms: 95.8333%
- all 0–160 ms: 95.8333%
- MFCC 0–160 ms: 95.5729%
- MFCC 0–80 ms: 94.7917%

Key conclusion:

> A 26-feature early MFCC model is only one error behind the 107-feature baseline and two behind the 214-feature harmonic model.

Adding 74 more features in the same early window reduced performance. This model is extremely attractive for low-latency browser inference.

Artifact: `10945587990`

## Preserved error-overlap / simple-fusion screen

Permanent result:

`training/results/reference/error_overlap_fusion_screen.json`

Individual:

- baseline 107: 371/384
- harmonic 214: 372/384
- MFCC 0–120/26: 370/384

Error overlap:

- baseline + harmonic: 8
- baseline + MFCC: 3
- harmonic + MFCC: 2
- all three wrong: only 2

The two universally missed recordings:

- `s5_f24_hard_ringing.wav`
- `s5_f24_normal_ringing.wav`

MFCC uniquely rescues 6 recordings missed by both larger models.

Oracle any-model-correct:

- 382/384
- **99.4792%**

Simple majority:

- 375/384
- **97.65625%**

Highest raw confidence:

- 378/384
- **98.4375%**

Conclusion:

> Error complementarity/fusion is substantially more promising than blindly increasing feature count.

## Confidence-calibrated fusion

Run: `36363139786`

Results:

- **isotonic calibrated fusion: 379/384 = 98.6979%, 5 errors**
- logistic calibrated fusion: 378/384 = 98.4375%
- highest raw confidence: 378/384 = 98.4375%
- meta-logistic: 375/384 = 97.65625%
- majority: 375/384 = 97.65625%

Current best demonstrated offline system:

> **98.6979% — 379/384 — 5 errors**

Compared with the best individual 214-feature model's 12 errors, calibrated fusion cuts errors by more than half.

Artifact: `10946491780`

## Step 5 — Abeßer reproduction

Script:

`training/run_abesser_reproduction.py`

Final run:

`36370931642`

Smoke: passed.

Real results:

- AR32: 188/384 = **48.9583%**, macro-F1 0.475058
- AR48: 169/384 = **44.0104%**, macro-F1 0.407428
- AR64: 184/384 = **47.9167%**, macro-F1 0.462974

AR32 is best of the tested fixed orders.

Conclusion:

- faithful-ish Abeßer representation/classifier transfer is dramatically worse than our current models
- do not discard the representation until complementarity is tested
- result can reflect extractor/classifier/domain mismatch rather than absence of physical signal

Real artifact:

- ID `10950522386`
- SHA256 `f93abe4ea8fe0fb09f6208d8d60de2ad49816e5c15227402a27b992b9360ab08`

Known implementation caveats:

- docstring may still mention LDA(5), but actual 8-string implementation uses 7
- mode statistic currently rounds to six decimals
- transition detection and partial assignment include adaptations where the paper is underspecified
- skew/kurtosis precision warnings can occur on near-constant vectors
- SVC internal probability calibration is not necessarily group-aware, although the outer held-out MIDI remains untouched

## Step 6 — Abeßer classifier comparison

Script:

`training/run_abesser_classifier_comparison.py`

Workflow:

`.github/workflows/string-classifier-abesser-classifiers.yml`

Run:

`36374793618`

Smoke: passed.

Real results:

| Classifier | Correct | Accuracy | Macro-F1 | Errors |
|---|---:|---:|---:|---:|
| Histogram Gradient Boosting | 222/384 | **57.8125%** | **0.5700** | 162 |
| Extra Trees | 220/384 | 57.2917% | 0.5669 | 164 |
| Random Forest | 219/384 | 57.03125% | 0.5612 | 165 |
| Logistic | 195/384 | 50.78125% | 0.4934 | 189 |

Conclusion:

- classifier choice matters substantially for the Abeßer representation
- HGB recovers 34 recordings versus the Step-5 AR32 SVM
- nevertheless, 57.8% remains far below the ~97% existing models
- Abeßer should not receive more standalone tuning before testing whether its errors are complementary to the strong models

Artifact:

- ID `10953065549`
- SHA256 `f780d877ea674874ae9c2e43b89f5ff156f88d49764d4d82ba5b348ab52fd36d`

---

# Current evidence-based conclusions

1. The 107/214-feature models are already near a static engineered-feature ceiling on this dataset.
2. Early **26-feature MFCC at 0–120 ms** is remarkably efficient and almost matches the large models.
3. Its errors are highly complementary to the large models.
4. **Calibrated three-model fusion remains the current overall winner: 379/384 = 98.6979%, 5 errors.**
5. Abeßer-style features are weak standalone on this guitar/dataset even after replacing the original classifier.
6. Step 7 confirmed that Abeßer contributes **zero unique rescues** beyond the three strong individual models and does not raise their oracle ceiling.
7. Adding Abeßer to calibrated isotonic fusion actually reduced performance from 379/384 to 378/384. Further Abeßer investment is stopped.
8. Step 8 showed that temporal aggregation is useful: equal averaging of three independent 40 ms MFCC classifiers over 0–120 ms reached **376/384 = 97.9167%, 8 errors**, versus 370/384 for the single 0–120 ms MFCC model.
9. Equal early-frame weighting beat the tested recency weighting. Extending aggregation past 120 ms did not improve the best result, reinforcing that useful string-ID evidence is concentrated very early.
10. The next major question is Stage-A pitch detection: pitch/onset quality and multi-hypothesis handling may now matter more than additional static string features.
11. Offline accuracy alone cannot determine the production winner; latency, robustness, calibration and browser cost remain required.

---

# Step 7 — COMPLETE: Abeßer feature/model fusion

Script:

`training/run_abesser_fusion.py`

Workflow:

`.github/workflows/string-classifier-abesser-fusion.yml`

Final run:

`36383682332`

Smoke: **passed**.

Protocol:

- no completed base model was retrained
- preserved out-of-fold predictions were reused
- fusion fitting remained leave-one-entire-MIDI-out
- compared the existing three strong models with and without Step-6 Abeßer HGB predictions

Individual preserved results:

- baseline 107: 371/384 = 96.6146%
- harmonic 214: 372/384 = 96.8750%
- MFCC 0–120 ms: 370/384 = 96.3542%
- Abeßer HGB: 222/384 = 57.8125%

Complementarity:

- Abeßer errors overlapping baseline errors: 7
- overlapping harmonic errors: 7
- overlapping MFCC errors: 7
- **Abeßer unique saves versus all three strong models: 0**
- oracle three strong models: **382/384 = 99.4792%**
- oracle after adding Abeßer: **382/384 = 99.4792%**

Fusion:

| Fusion | Correct | Accuracy | Errors |
|---|---:|---:|---:|
| Three-model calibrated isotonic | **379/384** | **98.6979%** | **5** |
| Four-model + Abeßer calibrated isotonic | 378/384 | 98.4375% | 6 |
| Three-model calibrated logistic | 378/384 | 98.4375% | 6 |
| Four-model + Abeßer calibrated logistic | 378/384 | 98.4375% | 6 |
| Three-model meta-logistic | 375/384 | 97.6563% | 9 |
| Four-model + Abeßer meta-logistic | 375/384 | 97.6563% | 9 |

The four-model isotonic selector chose Abeßer only twice and finished one error worse. Four-model logistic never selected Abeßer. The meta-logistic selected Abeßer heavily but did not improve accuracy.

Conclusion:

> Abeßer-derived evidence adds no demonstrated complementary coverage to the strong existing models on this dataset. Stop further Abeßer investment unless the dataset or extraction methodology materially changes.

Real artifact:

- ID `10953427540`
- SHA256 `8240cf27819459e8dcc934c44495c80da05def0538d94febc09c9b05b75f9db6`
- size 22,433 bytes

Do not rerun Step 7 merely to regenerate output.

---

# Step 8 — COMPLETE: multi-frame temporal aggregation

Script:

`training/run_temporal_aggregation.py`

Workflow:

`.github/workflows/string-classifier-temporal-aggregation.yml`

Final run:

`36384052764`

Smoke: **passed** after the smoke-only sparse-class encoding issue was fixed in commit `fe8a7bdf486df913a3d9729524b488df4f8f90db`.

Real protocol:

- 384 recordings
- leave-one-entire-MIDI-out validation
- candidate masking before temporal aggregation
- six independent 40 ms MFCC classifiers:
  - 0–40 ms
  - 40–80 ms
  - 80–120 ms
  - 120–160 ms
  - 160–200 ms
  - 200–240 ms
- 100 XGBoost trees per real classifier
- tested individual frames, equal cumulative averaging and recency-weighted cumulative averaging

Individual 40 ms frames:

| Frame | Correct | Accuracy |
|---|---:|---:|
| 0–40 ms | 336/384 | 87.5000% |
| 40–80 ms | **366/384** | **95.3125%** |
| 80–120 ms | 356/384 | 92.7083% |
| 120–160 ms | 354/384 | 92.1875% |
| 160–200 ms | 354/384 | 92.1875% |
| 200–240 ms | 358/384 | 93.2292% |

Equal probability averaging:

| Frames included | Correct | Accuracy |
|---|---:|---:|
| first 2, 0–80 ms | 373/384 | 97.1354% |
| **first 3, 0–120 ms** | **376/384** | **97.9167%** |
| first 4, 0–160 ms | 375/384 | 97.6563% |
| first 5, 0–200 ms | 376/384 | 97.9167% |
| first 6, 0–240 ms | 375/384 | 97.6563% |

Recency-weighted averaging:

- first 2: 373/384 = 97.1354%
- first 3: 374/384 = 97.3958%
- first 4: 371/384 = 96.6146%
- first 5: 372/384 = 96.8750%
- first 6: 371/384 = 96.6146%

Key comparisons:

- prior single-window MFCC 0–120 ms: **370/384 = 96.3542%, 14 errors**
- best multi-frame temporal MFCC: **376/384 = 97.9167%, 8 errors**
- gain from temporal aggregation: **+6 correct, +1.5625 percentage points, 14 → 8 errors**
- current overall three-model calibrated fusion: **379/384 = 98.6979%, 5 errors**

Conclusion:

> Treating the first 120 ms as three independent observations and averaging their candidate-masked probabilities is materially better than collapsing the same broad period into one MFCC summary. The useful temporal structure is real. Equal weighting was better than the tested recency weighting, and adding later frames did not exceed the 0–120 ms result.

This makes the three-frame 0–120 ms model a serious lightweight production candidate and a candidate for later fusion testing.

Real artifact:

- ID `10953663191`
- SHA256 `59d74af732b10557ec6760a8317b3b7bef3f89da032afd70c4aaeebd3553542b`
- size 90,348 bytes

Do not rerun Step 8 unless the data, temporal representation or evaluation methodology materially changes.

---

# Results synthesis after Steps 1–12

The first twelve experiments materially changed the direction of the project. The evidence no longer points primarily toward inventing increasingly large physical/string feature sets. String identity is already highly recoverable from this fixed guitar/interface/player setup. The remaining practical problem is increasingly an **end-to-end inference, complementarity, calibration, latency, and deployment problem**.

## What the first twelve experiments established

| Experiment | Main result | Main lesson |
|---|---|---|
| Baseline engineered model | 107 features → **371/384 = 96.6146%** | Existing engineered features were already strong. |
| Harmonic expansion | 214 features → **372/384 = 96.8750%** | Doubling engineered features fixed only one additional recording. |
| Time-phase screen | early signal strongest | String-identifying information is concentrated early after the pluck. |
| Early MFCC confirmation | 26 MFCC features, 0–120 ms → **370/384 = 96.3542%** | A tiny early representation nearly matches the large models. |
| Calibrated fusion | **379/384 = 98.6979%, 5 errors** | Existing strong models make complementary errors; fusion is extremely valuable. |
| Abeßer reproduction | best reproduced SVM **188/384 = 48.9583%** | Published physical-string features transferred poorly to this rig/data. |
| Abeßer classifier comparison | best HGB **222/384 = 57.8125%** | Better classifier helps, but cannot rescue a weak representation. |
| Abeßer fusion | no improvement; zero unique rescues | Abeßer contributes no useful complementary evidence to the strong models. |
| Temporal MFCC | three 40 ms frames, 0–120 ms → **376/384 = 97.9167%** | Independent early observations are much stronger than one broad early summary. |
| Stage-A pitch + joint inference | YIN up to **375/384 = 97.6563%**; multi-hypothesis path failed | Pitch detection is now a major bottleneck; naive alternative-pitch branching does not solve it. |
| Compact spectral CNN | raw **288/384 = 75.0000%**; masked **307/384 = 79.9479%** | A small learned log-mel CNN was far below engineered/MFCC models; do not expand learned-model search unless preserved predictions show unusual complementarity. |

## Strongest findings

### 1. The first approximately 120 ms contains most of the useful string evidence

The single-window 0–120 ms MFCC model reached **370/384 = 96.3542%** using only 26 features.

Splitting the same early period into independent 40 ms observations and averaging probabilities improved this to:

**376/384 = 97.9167%, 8 errors.**

Later temporal evidence did not beat the 0–120 ms result:

- 0–80 ms: 373/384 = 97.1354%
- 0–120 ms: **376/384 = 97.9167%**
- 0–160 ms: 375/384 = 97.6563%
- 0–200 ms: 376/384 = 97.9167%
- 0–240 ms: 375/384 = 97.6563%

Therefore the important phenomenon is not simply the average spectrum of the attack. **How the spectrum evolves through several early observations contains useful string information.** Waiting substantially longer has not produced better Stage-B classification.

### 2. Complementarity matters much more than feature-count growth

The 214-feature harmonic model improved the 107-feature baseline by only one recording:

**371 → 372 correct.**

But calibrated isotonic fusion of baseline + harmonic + early MFCC reached:

**379/384 = 98.6979%, 5 errors.**

The three-model oracle reached:

**382/384 = 99.4792%.**

Therefore most of the information required to solve the remaining recordings already exists somewhere among the strong representations. The high-value question is increasingly:

> How can complementary evidence be extracted and combined efficiently?

rather than:

> How many more engineered descriptors can be added?

### 3. Stage-A pitch detection is now comparable in importance to Stage-B string classification

Step 9 showed:

- current browser correlation, best tested point: **366/384 = 95.3125%**, 18 MIDI errors, including 6 octave errors
- custom YIN at 160 ms: **374/384 = 97.3958%**, 10 MIDI errors, 0 octave errors
- librosa YIN at 240 ms: **375/384 = 97.6563%**, 9 MIDI errors, 0 octave errors
- librosa pYIN at 240 ms: same 375/384 exact-MIDI accuracy but about 69× the measured Python detector runtime of librosa YIN

Stage-B alone is already around 98%, and the best preserved string fusion is 98.70%. Stage-A pitch errors can therefore dominate otherwise-correct downstream inference.

## Step 10 — COMPLETE: hard MIDI versus multi-hypothesis inference

Script:

`training/run_multi_hypothesis_inference.py`

Workflow:

`.github/workflows/string-classifier-multi-hypothesis.yml`

Final successful run:

`36450596841`

Smoke: **passed** after fixing the smoke-only training-coverage problem so the smoke evaluates a small subset while retaining the full training pool.

Real: **passed**.

Protocol:

- all 384 recordings
- preserved Step-9 custom-YIN 160 ms outputs; Step 9 was not rerun
- Stage-B = Step-8-style equal mean of three independent 40 ms MFCC probability models over 0–120 ms
- Stage-B raw 8-string probabilities had to be recomputed because the preserved Step-8 CSV retained only final masked predictions/confidence, not the full raw probability vector needed to remask under alternative candidate MIDIs
- leave-one-entire-true-MIDI-out Stage-B training
- no trainer context
- compared hard top-1 MIDI with top-2/top-3/top-5 joint `(MIDI,string,fret)` scoring

Results:

| Method | Joint correct | Joint accuracy | Regressions vs hard | Unique rescues vs hard |
|---|---:|---:|---:|---:|
| **hard top-1** | **366/384** | **95.3125%** | — | — |
| top-2 | 303/384 | 78.9063% | 63 | **0** |
| top-3 | 259/384 | 67.4479% | 107 | **0** |
| top-5 | 207/384 | 53.9063% | 159 | **0** |

Hard top-1 details:

- MIDI correct: **374/384 = 97.3958%**
- physical string correct: **376/384 = 97.9167%**
- joint tuple correct: **366/384 = 95.3125%**

Most important result:

- pitch top-2 oracle: **374/384**
- pitch top-3 oracle: **374/384**
- pitch top-5 oracle: **374/384**

The preserved custom-YIN alternative candidates contained **zero additional correct-MIDI rescues beyond top-1**. The multi-hypothesis scorer therefore had no pitch oracle headroom and merely introduced incorrect competitors.

Conclusion:

> Keep hard top-1 MIDI for this detector design. Drop the current multi-hypothesis branch unless a future pitch detector produces genuinely complementary alternative hypotheses.

Real artifact:

- name: `string-classifier-multi-hypothesis`
- ID: `10983346754`
- size: 339,482 bytes
- SHA256: `93b1d4e60387c8da79465c4551a4ce3ba89b12bdcaf2bf3ec3006ea9e255cc78`

Do not rerun Step 10 unless the pitch-hypothesis representation or Stage-B methodology materially changes.

## Step 11 — COMPLETE: compact learned spectral model

Script:

`training/run_spectral_cnn.py`

Workflow:

`.github/workflows/string-classifier-spectral-cnn.yml`

Final successful run:

`36459606684`

Smoke: **passed**.

Real: **passed**.

Protocol:

- all 384 recordings
- mono 22.05 kHz
- onset-aligned first 160 ms
- 48-bin log-mel spectrogram
- FFT 256, hop 64
- input shape 48 × 52
- compact CNN: Conv16 → Conv32 → Conv64 → global average pooling → Dense32 → 8 logits
- 25,864 parameters
- 18 epochs
- leave-one-entire-MIDI-out evaluation across 61 MIDI folds
- held-out MIDI excluded from both training and normalization
- fixed recipe; no held-out-fold hyperparameter tuning
- raw acoustic and physical candidate-masked metrics reported separately
- full OOF logits/probabilities preserved for Step 12

Results:

| Output | Correct | Accuracy | Errors | Macro-F1 |
|---|---:|---:|---:|---:|
| CNN raw acoustic | 288/384 | **75.0000%** | 96 | 0.7361 |
| CNN + physical candidate mask | 307/384 | **79.9479%** | 77 | 0.7837 |
| Reference: 3×40 ms MFCC | 376/384 | **97.9167%** | 8 | — |
| Reference: calibrated three-model fusion | 379/384 | **98.6979%** | 5 | — |

The candidate mask rescued 19 recordings relative to the CNN's raw output, but the learned representation remained dramatically below the engineered/MFCC systems.

Conclusion:

> The first compact learned spectral approach is not competitive. Do **not** respond by launching a CNN architecture/representation search. Step 12 should first use the already-preserved OOF CNN probabilities to measure error overlap, unique rescues and oracle improvement. The CNN survives only if it provides unusually complementary evidence despite its weak standalone accuracy.

This strengthens the broader result that, on the current small fixed-rig dataset, simple early MFCC/engineered representations generalize much better across held-out MIDI than this end-to-end learned spectral representation.

Real artifact:

- name: `string-classifier-spectral-cnn`
- ID: `10986904978`
- size: 95,051 bytes
- SHA256: `3661550b335cea6d3c3b4b7a77703e7da823f9e82f10327bebe98244edbf45dd`

The artifact preserves five output files, including OOF predictions/logits/probabilities, training curves, fold normalization metadata, config and summary.

Do not rerun Step 11 merely to regenerate these outputs.

## Step 12 — COMPLETE: engineered + learned complementarity gate

Script:

`training/run_engineered_learned_fusion.py`

Workflow:

`.github/workflows/string-classifier-engineered-learned-fusion.yml`

Final successful run:

`36463295082`

Smoke: **passed**.  
Real: **passed**.

Step 12 intentionally reused preserved out-of-fold predictions and **did not retrain** Steps 1–11. It compared the baseline, harmonic, confirmed 0–120 ms MFCC, and Step-11 candidate-masked CNN predictions.

Results:

| Measure | Result |
|---|---:|
| baseline | 371/384 correct |
| harmonic | 372/384 correct |
| MFCC | 370/384 correct |
| CNN candidate-masked | 307/384 correct |
| strong-three oracle | **382/384 = 99.4792%** |
| strong-three + CNN oracle | **382/384 = 99.4792%** |
| CNN unique rescues | **0** |
| CNN wrong while at least one strong model was correct | **75** |

The CNN added **zero oracle headroom**. All four models still jointly failed the same two recordings:

- `s5_f24_hard_ringing.wav`
- `s5_f24_normal_ringing.wav`

Conclusion:

> **Close the learned/CNN branch.** The CNN supplies no unique rescue and no increase in oracle accuracy, so calibrated engineered+learned fusion is not justified. Do not spend compute on CNN fusion, architecture search, or alternate learned representations unless future evidence materially changes the premise.

This reinforces the current direction: prioritize the proven early MFCC/engineered systems, targeted physical feasibility tests, personalization/calibration, context ablations, latency, and live/browser validation.

Real artifact:

- name: `string-classifier-engineered-learned`
- ID: `10987679899`
- size: 17,714 bytes
- SHA256: `5eaf5b5e2e9646f12ddd956763f233a02ef776009f8c96ff6ff7cdbce51d8602`

Do not rerun Step 12 merely to regenerate these results.

## What went as expected

- **Early attack information mattered.** Physical/string-specific attack and spectral behavior were expected to be useful, and the time-phase experiments confirmed this strongly.
- **Temporal evidence helped.** Multiple observations through the attack improved materially over a single broad-window summary.
- **Candidate masking is powerful and remains architecturally appropriate.** MIDI sharply constrains physically possible string/fret positions.
- **Different representations make complementary mistakes.** The fusion experiments strongly confirmed this.
- **The existing pitch detector had octave/subharmonic problems.** The known live failure mode was reproduced objectively: six octave errors at its best tested operating point, versus zero for the YIN methods.

## What was unexpected

### Abeßer transferred extremely poorly

The magnitude of the failure was much larger than expected:

- reproduced SVM: about 49%
- best alternative classifier on the representation: about 58%
- zero unique rescues when added to the strong models

This indicates that generalized physical descriptors from that method transfer poorly to this specific 8-string/pickup/interface/data regime.

### MFCC was much stronger than expected

Only 26 MFCC statistics from 0–120 ms nearly matched the 107- and 214-feature engineered systems. Three independent MFCC snapshots reached **376/384**, outperforming either large engineered model individually.

MFCC should therefore be treated as a primary signal, not merely a cheap approximation.

### More features sometimes hurt

Within the early 0–120 ms region, MFCC-only produced **370/384**, while the larger approximately 100-feature early representation produced **368/384** in confirmation.

Feature proliferation can add noise rather than useful information.

### Simple calibrated fusion beat more elaborate fusion

Calibrated isotonic fusion reached **379/384**, while the tested meta-logistic fusion reached **375/384**.

Complexity has not correlated reliably with quality.

### The tested multi-pitch hypothesis path was decisively harmful

The expectation that some correct MIDI values might survive as second/third candidates was not supported. Top-2 through top-5 contained no additional true-MIDI oracle recoveries, and actually selecting among them sharply reduced accuracy.

## Focus from this point forward

Prioritize:

1. **The proven early MFCC/engineered representations and their complementary evidence.** The learned spectral branch has now been tested and closed.
2. **Early temporal modeling**, because the first approximately 120 ms is the strongest Stage-B region found so far.
3. **Stage-A pitch quality**, especially YIN-family behavior and eventual browser-compatible implementation.
4. **Calibration and personalization** for this fixed guitar/interface/player setup.
5. **Explicit separation of raw acoustic, physical-mask, temporal, and trainer-context performance.**
6. **Latency and browser/live behavior**, because offline accuracy is already near the point where implementation quality can matter more than tiny benchmark gains.
7. **Unique rescues and error overlap**, rather than standalone aggregate accuracy alone.

Avoid:

- further Abeßer investment unless its methodology materially changes
- blindly adding harmonic/physical descriptors
- assuming longer analysis windows are better
- using pYIN merely because it is more sophisticated; it showed no exact-MIDI gain over librosa YIN at much greater measured Python runtime
- the current multi-hypothesis pitch scheme
- large combinatorial searches
- treating tiny aggregate accuracy differences as sufficient evidence; with 384 recordings, one recording is approximately 0.2604 percentage points
- hiding acoustic errors behind trainer context during evaluation

## Revised direction for Steps 11–18

The remaining program is intentionally narrower than the original plan.

### 11. Learned spectral model — COMPLETE
**Smoke test passed → Real run passed.**

Keep the first learned model deliberately small and early-window focused. The purpose is **not** to build a large neural replacement for a system that is already strong.

Result: the first compact log-mel CNN was **not competitive as a standalone model**. Raw accuracy was 75.00%; physical candidate masking raised it to 79.95%, still far below the 97–99% surviving systems.

Start with one compact log-mel CNN, approximately 0–160 ms as originally specified. Preserve raw logits/probabilities. Candidate masking remains a separate post-model stage.

Primary survival criteria now emphasize:

- unique rescues versus baseline/harmonic/Step-8 temporal
- oracle improvement when added to survivors
- error overlap
- calibration
- latency/model size

Standalone accuracy is secondary. If the CNN merely reproduces the same errors, stop learned-model expansion. Only investigate F0-aligned/CQT/Gammatone alternatives if the first CNN demonstrates useful learned complementarity.

### 12. Engineered + learned fusion — COMPLETE
**Smoke test passed → Real run passed; learned branch closed.**

Reuse preserved out-of-fold predictions; do not retrain completed experiments merely for fusion.

The benchmark remains:

**379/384 = 98.6979%, 5 errors.**

The preserved-prediction complementarity gate found **0 CNN unique rescues** and no oracle gain: 382/384 both before and after adding the CNN. Therefore no calibrated engineered+learned fusion was justified. The learned branch is closed.

Step 10's multi-hypothesis branch is excluded from the main candidate pool because it produced zero rescues and substantial regressions.

### 13. SIF feasibility — COMPLETE
**Smoke test passed → Real run passed; SIF branch closed.**

The real run evaluated **360/360 usable fretted recordings**. The expected inverse-segment-frequency peak did not separate strongly enough from matched nearby controls:

- median expected-vs-control advantage: **+1.1378 dB**; required ≥3 dB
- expected peak control-win fraction: **59.3889%**; required ≥70%
- positive recording fraction: **57.2222%**; required ≥65%

The signal failed all three predeclared survival criteria. **Do not build a SIF classifier; the SIF branch is closed.**

Run: `36464844099`  
Artifact: `10989825794`  
Artifact SHA256: `1aa375e45771e1775d9c9bd4ab8e9060fce7e619eb82b779d51e4b5b39eda062`

### 14. Calibration / personalization — COMPLETE
**Smoke test passed → Real run passed.**

The experiment used the lightweight three-frame MFCC representation as its personalization test bed and kept leave-one-entire-MIDI-out validation. Calibration anchors were selected only from training MIDIs, preventing the held-out MIDI from contributing to its own personalization.

Calibration budgets:

- minimal: frets 0 and 12 per string
- medium: frets 0, 5, 7, 12, 17, 19 and 24 per string

Results:

- base: **361/384 = 94.0104%**
- minimal prototype: **361/384 = 94.0104%**, 1 rescue / 1 regression
- minimal reliability prior: **359/384 = 93.4896%**, 0 rescues / 2 regressions
- **medium prototype: 362/384 = 94.2708%, 1 rescue / 0 regressions**
- medium reliability prior: **360/384 = 93.7500%**, 0 rescues / 1 regression

Personalization therefore produced a real but marginal demonstrated benefit: the medium prototype gained **one correct recording (+0.2604 percentage points)** with no regressions. The reliability-prior approach was harmful.

Interpretation: personalization remains eligible as a lightweight optional component, but the observed benefit does **not** justify a large calibration burden or a broad personalization search. The existing calibrated three-model fusion at **379/384 = 98.6979%** remains the best overall offline result; Step 14 did not test or supersede that fusion.

Run: `36470556416`  
Artifact: `10991343882`  
Artifact SHA256: `b1c78236386f8ef36e15e613594d2de079f51b9902541ac5c9e25902f0094f76`

### 15. Candidate-mask + context ablations — COMPLETE
**Smoke test passed → Real run passed.**

The experiment maintained the required separation between acoustic performance and trainer-context gameplay behavior.

Acoustic layers:

- A — raw first 40 ms acoustic probabilities: **311/384 = 80.9896%**
- B — + physical MIDI/string/fret feasibility mask: **336/384 = 87.5000%**
- C — + equal temporal mean of three independently trained 40 ms frames over 0–120 ms: **376/384 = 97.9167%**

The physical mask contributed **+25 correct recordings** and temporal aggregation contributed another **+40**. Layer C exactly reproduced Step 8's 376/384 result.

Because stored WAVs do not contain quiz state, D/E were controlled context scenarios rather than claims about live-lesson frequency. The test reproduced `getGuitarTrainerAudioHints(midi)` answer-string semantics:

- no matching answer: **376/384**, no change
- true string + strongest valid competitor: **376/384**, 0 rescues / 0 harmful overrides
- true-string-only singleton: **384/384**, all 8 remaining acoustic errors rescued / 0 harmful overrides; optimistic upper bound only
- deliberately wrong/stale singleton: **28/384**, **348 harmful overrides**

Production implication: context is powerful only when trustworthy and sufficiently specific. It must remain a separately reported gameplay prior and should not blindly override strong acoustic evidence when context may be stale or wrong.

Run: `36477918087`  
Artifact: `10994099328`  
Artifact SHA256: `fee5678b720cebf982eef64dadbafe25dfffb658145965b6773ab3f7c07e56ef`

### 16. Final time × method tournament — COMPLETE
**Smoke test passed → Real run passed.**

Only surviving methods and the predeclared small timing grid were evaluated; no trainer context was used.

Stage B — temporal MFCC:

- 80 ms: **373/384 = 97.1354%**, availability ≈ **81.75 ms**
- **120 ms: 376/384 = 97.9167%**, availability ≈ **122.62 ms**
- 160 ms: **375/384 = 97.6563%**, availability ≈ **163.50 ms**

The Stage-B Pareto frontier is 80 ms and 120 ms. The 160 ms point is dominated by 120 ms: slower and one recording less accurate. The 120 ms model is therefore the best demonstrated final Stage-B operating point; the 80 ms model remains useful only if a provisional lower-latency decision is valuable.

Stage A — surviving YIN methods:

- librosa YIN 80/120/160/200/240 ms: **335 / 367 / 370 / 374 / 375 correct**
- custom YIN 80/120/160/200/240 ms: **352 / 369 / 372 / 373 / 373 correct**

Librosa YIN at 240 ms remains the highest-accuracy Stage-A point at **375/384 = 97.6563%**. Custom YIN does not exceed it, and its 200→240 ms extension adds no accuracy.

Interpretation for Step 17: use **120 ms temporal MFCC** as the main Stage-B candidate. Treat **librosa YIN 240 ms** as the highest-accuracy Stage-A reference, with shorter YIN timings retained only as latency tradeoffs. Do not reopen broad timing search.

Run: `36479004613`  
Artifact: `10995776554`  
Artifact SHA256: `27099c240ebd3f40561c8de10a3b6d6090b9a9dd538548f77e10cd7880cc7344`

### 17. Final architecture tournament
**Smoke test → Real run. Central decision experiment.**

This becomes the main system-selection experiment.

Likely candidate structure, subject to Steps 11–16:

**onset → YIN-family hard top-1 MIDI → early temporal spectral/string evidence → physical candidate mask → calibrated decision**

Potential additions survive only if prior evidence supports them:

- lightweight personalization
- calibrated fusion
- trainer context, always reported separately

Do not include the current Abeßer or multi-hypothesis branches.

Compare complete pipelines on accuracy, remaining error taxonomy, calibration, robustness, onset→decision latency, CPU/preprocessing cost, model size, implementation complexity, and browser compatibility.

### 18. Browser/runtime + live-site validation
**Smoke test → Real run. Highest practical importance.**

Offline performance is now strong enough that deployment behavior can dominate small benchmark differences.

Require:

1. Python↔browser parity on stored WAVs, including intermediate features/probabilities rather than prediction agreement alone.
2. Controlled live guitar testing across strings/frets/strengths/repeats/transitions/sustains/noise.
3. Explicit Stage-A versus Stage-B versus context error logging.
4. Onset→first-decision and onset→stable-decision latency.
5. Debug UI that explains why a note did or did not map.

Do not declare production success from offline stored-WAV accuracy alone.

## Revised strategic path

The evidence after seventeen experiments changes the program from:

> research many representations → add features → find the highest-accuracy classifier

to:

> **focus on the proven early MFCC/engineered path → cheaply test only genuinely different physical evidence → personalize if useful → quantify context separately → determine the minimum reliable decision time → select the simplest non-dominated complete architecture → prove Python/browser parity → prove it with controlled live guitar.**

This is the evidence-supported direction for the remaining experiments.

---

# Browser / live-site integration

Current trainer integration:

- `trainer.js` imports `setupLiveGuitarInput` from `./input/live-guitar.js`.
- Trainer exposes `window.getGuitarTrainerAudioHints(midi)`.
- Hints include:
  - whether MIDI matches an answer
  - answer strings
  - answer positions with string/fret/interval/octave
- Audio emits `guitar-note-detected`.
- `activateDetectedFret({midi,string})` converts MIDI/string to fret using current tuning and dispatches a synthetic note-cell click.
- Sustained-note repeat lock is about 350 ms.

Trainer hints are useful in production but dangerous during acoustic evaluation. They must not contaminate the raw classifier benchmark.

Recommended diagnostic logging/UI:

- ground-truth string/fret when known
- detected/predicted fret
- pitch error cents
- pitch confidence/stability
- onset age / analysis-window timing
- string-model confidence
- top-2 margin
- raw logits/scores and probabilities
- candidate mask
- candidate fret per string
- correct-string rank in labeled testing
- raw vs masked vs final correctness
- override/context source
- previous MIDI/string/fret
- deltas and time since previous note
- OOD score if implemented
- individual important spectral/physical features
- volume and per-string diagnostics

---

# Final live validation requirements

Use controlled labeled playing where the user deliberately plays known positions.

Cover:

- same MIDI on every physically possible string
- all eight strings
- open strings
- low/mid/high frets
- soft/normal/hard picks
- repeated notes
- fast transitions
- sustained notes
- neighboring strings, especially S4/S5/S6
- very high frets
- S5 fret 24, especially because hard/normal examples were missed by all three original strong models
- silence/noise and false-trigger behavior

Separate:

- Stage-A pitch mistakes
- Stage-B string mistakes
- temporal mistakes
- trainer-context corrections

Measure:

- pluck → first usable decision latency
- stable-decision latency
- feature extraction time
- model inference time
- CPU/browser responsiveness
- confidence calibration
- raw acoustic accuracy
- masked accuracy
- final gameplay accuracy

Before production acceptance, run the same stored WAVs through Python and browser implementations and compare:

- intermediate features
- probabilities
- masks
- final predictions

Python↔browser parity is mandatory.

---

# Production decision criteria

A new method survives only if it provides at least one of:

- unique error rescues
- better calibrated confidence
- lower latency
- greater robustness
- meaningful implementation simplification
- enough overall accuracy gain to justify its cost

A lightweight 26-feature 0–120 ms model may be preferable to a slightly more accurate heavyweight model if it improves live responsiveness and implementation reliability.

Fusion has already demonstrated enough error reduction to justify continued investigation.

Do not keep a method simply because it was interesting in the literature.

---

# Repository / workflow rules

- Latest `main` is always source of truth.
- Before updating an existing GitHub file, refetch its latest blob SHA immediately before the write.
- Never parallel-write the same file.
- Inspect recent commits because user changes may have landed independently.
- Never overwrite unrelated recent work.
- After repo changes, provide deployed URL with cache-busting short commit:
  - `https://mtch777.github.io/Guitar-Learning/?v=<shortcommit>`
- Training-only changes do not require browser asset cache edits.
- Old `.github/workflows/string-classifier-benchmark.yml` has a dangerous push trigger involving `training/run_time_phase_experiment.py`.
- Do not casually edit `run_time_phase_experiment.py`; doing so previously triggered an expensive redundant 315-config screen.
- Prefer freezing obsolete expensive workflows to manual dispatch before touching their watched files.

---

# Permanent result preservation still needed

Create/maintain a permanent experiment manifest such as `training/EXPERIMENTS.md` or structured equivalent containing for every experiment:

- hypothesis/purpose
- code commit
- workflow run ID
- artifact ID/hash
- dataset
- split/evaluation protocol
- features
- model
- metrics
- confusion/error summary
- conclusion
- superseded status
- whether rerunning is unnecessary/prohibited

Artifacts are not enough because they expire.

---

# Required behavior for continuation

- Do not rerun completed experiments.
- Use preserved results.
- Every remaining experiment: **Smoke test → Real run**.
- Real run must be gated on smoke success.
- Every long job must print useful progress and ETA.
- When checking a run, report actual model/fold/progress where logs allow it, not merely “running.”
- Distinguish unavailable streaming stdout from unavailable job state.
- Preserve outputs continuously.
- Keep project responses concise.
- Execute requested GitHub changes rather than only describing them.
- Do not silently expand experiment scope.
- Do not change methodology mid-experiment without explicitly explaining why.
- Do not call an experiment successful until the workflow completes successfully and results are inspected.
- Until the program is complete, project responses should end with the remaining experiment steps.

---

# Synthesis after 17 experiments

## What we have learned

The problem has narrowed substantially. The strongest evidence now supports a compact staged system rather than continued representation search:

**onset → reliable hard top-1 pitch → early temporal MFCC string evidence → physical candidate mask → calibrated decision → guarded trainer context**

Physical-string identity is concentrated early after the pluck. The best lightweight Stage-B representation is three independent 40 ms MFCC classifiers averaged over 0–120 ms: **376/384 = 97.9167%**. This result has now been reproduced across Steps 8, 15 and 16.

Simple guitar physics is a major part of the solution. Step 15 quantified the progression:

- raw first 40 ms: **311/384**
- + physical candidate mask: **336/384** (**+25 correct**)
- + three-frame temporal evidence: **376/384** (**+40 more correct**)

Complementarity matters more than feature count. The original baseline/harmonic/early-MFCC models were individually similar at 370–372 correct, but calibrated isotonic fusion reached **379/384 = 98.6979%**, while their oracle reaches **382/384 = 99.4792%**. The remaining problem is increasingly about selecting/trusting complementary evidence rather than discovering a radically stronger representation.

Stage A is a first-class bottleneck. Librosa YIN at 240 ms reaches **375/384 = 97.6563% MIDI accuracy with zero octave errors**, versus **366/384 with six octave errors** for the tested browser-correlation reference. End-to-end architecture selection must therefore consider pitch and string classification jointly rather than treating pitch as solved preprocessing.

## What went as expected

- Early attack/onset information is highly discriminative.
- Temporal evidence helps: three independent 40 ms observations over 0–120 ms outperform a single broad 0–120 ms MFCC window.
- Physical candidate masking is powerful.
- Different strong representations make complementary errors, making calibrated fusion useful.
- Longer Stage-B windows are not automatically better: Step 16 confirmed **120 ms > 160 ms** in both accuracy and latency.
- Trainer-known valid positions can be extremely powerful when the context is genuinely correct and specific.

## What went unexpectedly

Several theoretically attractive branches transferred poorly or provided no complementary value:

- **Abeßer-style physical features:** roughly 49% with the reproduction and 58% with the best alternate classifier; **zero unique rescues** versus the strong models.
- **Compact spectral CNN:** 75.0% raw / 79.95% masked and **zero unique rescues**; the strong-model oracle remained 382/384 after adding it.
- **Current multi-hypothesis YIN scheme:** alternative candidates contained **zero additional correct MIDI rescues**; top-2/3/5 inference introduced large regressions.
- **SIF:** failed all three predeclared feasibility gates; the physical signal was too weak/non-specific.
- **Personalization:** medium prototype gained only **one correct recording (+0.2604 pp)**. Positive, but too small to justify broad calibration/model search.
- **Trainer context:** correct singleton context gave the controlled upper bound of 384/384, but deliberately wrong/stale singleton context produced **348 harmful overrides**. Context can be more dangerous than the acoustic classifier if treated as authoritative.

## Focus from here

1. **120 ms temporal MFCC + physical mask** as the primary lightweight Stage-B candidate.
2. **Librosa YIN family** for Stage A, with 240 ms as the highest-accuracy reference and shorter windows retained only as latency tradeoffs.
3. **Existing calibrated three-model fusion** because it remains the best offline physical-string result at 379/384; Step 17 must determine whether its +3 correct over temporal MFCC justifies extra implementation/preprocessing cost.
4. **Guarded trainer context**, kept separate from acoustic metrics and used as a soft/safeguarded prior rather than an unconditional override.
5. **End-to-end latency, calibration, browser parity and live behavior**, because these can now matter more than one or two stored-WAV errors.

## Avoid

Do not spend further experiments on:

- Abeßer-style feature search without materially new data/methodology
- broad CNN/neural architecture search
- the current multi-hypothesis pitch candidate scheme
- SIF
- broad personalization search
- broad timing grids
- feature-count expansion for its own sake
- arbitrary aggregate accuracy chasing
- authoritative trainer context
- reporting context-assisted gameplay results as acoustic accuracy

On this 384-recording dataset, one recording is about **0.2604 percentage points**. Small gains must justify their latency, calibration burden, browser complexity and maintenance cost.

## Revised direction for Steps 17–18

The original program was broadly:

> search representations → add physical features → try learned models → optimize classifier accuracy

The evidence now supports:

> **compare only the surviving complete architectures → quantify end-to-end accuracy/latency/calibration/complexity → port the selected system exactly to browser → prove Python/browser parity → validate with controlled live guitar**

### Step 17 implication

Step 17 is a **system-selection experiment, not another representation search**. Compare only evidence-supported complete pipelines. At minimum, preserve separate Stage-A, Stage-B and end-to-end metrics and compare:

- 120 ms temporal MFCC + physical mask
- the calibrated strong-model fusion where practical
- YIN + surviving Stage-B configurations
- optional personalization only if its demonstrated +1 rescue is worth the burden
- trainer context separately from acoustic performance

Evaluate tuple accuracy, Stage-A errors, Stage-B errors conditional on correct MIDI, error overlap/unique rescues, calibration, onset→decision latency, CPU/preprocessing cost, model size, implementation complexity and browser suitability.

### Step 18 implication

Step 18 is the **production acceptance gate**, not a cosmetic final check. Offline stored-WAV accuracy alone is no longer sufficient. Require Python↔browser parity for intermediate features/probabilities/masks/predictions and controlled live testing of repeated notes, transitions, sustains, all strings/fret ranges/pick strengths, difficult neighboring strings/high frets, noise/false triggers, first-decision latency and stable-decision latency.

The project is no longer trying to establish whether physical-string identification is feasible. It is choosing between a very strong simple Stage-B system (**376/384**) and a somewhat more complex fused system (**379/384**), while integrating a Stage-A pitch system around **375/384** and proving that the complete architecture behaves correctly in the browser and on live guitar.

---

# Step 17 result — final architecture tournament

Smoke and gated real run both passed on all **384 recordings**. Only evidence-supported complete pipelines were compared. Stage-A predicted MIDI drove the physical feasibility mask; trainer context remained excluded from acoustic/end-to-end metrics.

Results:

- **YIN 240 ms → calibrated fusion3: 370/384 = 96.3542% end-to-end**
  - pitch correct: **375/384**
  - conditional string accuracy when pitch is correct: **98.6667%**
  - estimated Python availability: **~276.99 ms**
  - 347 features
- YIN 240 ms → temporal MFCC 120 ms: **367/384 = 95.5729%**
  - pitch correct: **375/384**
  - conditional string accuracy: **97.8667%**
  - estimated availability: **~243.78 ms**
  - 78 features
- Oracle pitch → fusion3: **379/384 = 98.6979%**
- Oracle pitch → temporal MFCC 120 ms: **376/384 = 97.9167%**

The existing Stage-B results were reproduced exactly under oracle pitch. Fusion therefore retains its **+3 correct** advantage over temporal MFCC, but costs roughly **33 ms** more processing in this Python implementation and requires a much heavier feature path. Fusion was also substantially better calibrated in this experiment: string-confidence Brier **0.01363** versus **0.05844** for temporal MFCC.

The deployable Pareto set was YIN200→temporal120, YIN200→fusion3, and YIN240→fusion3. YIN240→temporal120 was dominated.

The major architectural conclusion is that **Stage A is now the larger remaining end-to-end bottleneck**. YIN240 has 9 MIDI errors. Among its 375 correct-pitch recordings, fusion leaves only **5 string errors**. Step 18 must therefore treat browser pitch parity, onset handling, pitch stability and live decision timing as primary acceptance criteria, not merely validate the string classifier.

The final production choice remains intentionally open until browser/live validation: fusion has the best demonstrated accuracy and calibration, while temporal MFCC is simpler and faster. Step 18 decides whether the +3/384 fusion gain survives browser implementation cost and live behavior.

Run: `36480723812`  
Artifact: `10996203285`  
Artifact SHA256: `77743ed19d9564ccc4253e37d940615bbd11eb23b250be77fd0745e13f5ae527`

---

# Exact continuation point

**Completed through Step 17:** baseline benchmark, harmonic expansion, time-phase screen, 100-tree confirmation, error-overlap/fusion screening, calibrated fusion, Abeßer reproduction, Abeßer classifier comparison, Abeßer fusion, temporal aggregation, Stage-A pitch detector tournament, hard-MIDI versus multi-hypothesis inference, compact learned spectral CNN, engineered+learned complementarity gating, and SIF feasibility.

**Current best overall physical-string classifier/fusion:** calibrated isotonic three-model fusion — **379/384 = 98.6979%, 5 errors**.

**Current best temporal Stage-B model:** equal average of three independent 40 ms MFCC classifiers over 0–120 ms — **376/384 = 97.9167%, 8 errors**.

**Current best Stage-A pitch detector tested:** librosa YIN at 240 ms — **375/384 = 97.6563%, 9 MIDI errors, 0 octave errors, mean detector runtime 1.01 ms**. Custom YIN at 160 ms reached **374/384 = 97.3958%, 0 octave errors**.

**Closed branches:** Abeßer representation, current multi-hypothesis YIN candidate scheme, learned/CNN representation, and SIF. Do not rerun or expand them without materially new evidence/methodology.

**Step 13 conclusion:** across 360 usable fretted recordings, SIF achieved only **+1.1378 dB median expected-vs-control**, **59.3889% control-win fraction**, and **57.2222% positive recordings**, below all three survival thresholds. The SIF branch is closed.

**Step 14 conclusion:** medium prototype personalization improved its lightweight MFCC base from **361/384 to 362/384**, one rescue with no regressions. The effect is positive but small; keep personalization optional and do not expand into a broad search. Reliability priors were harmful.

**Step 15 conclusion:** the physical candidate mask improved the first-frame acoustic model by **25 correct recordings**, and three-frame temporal aggregation added another **40**, reaching **376/384**. Correct singleton trainer context can rescue all 8 remaining errors in the controlled upper-bound scenario, but deliberately wrong/stale singleton context caused **348 harmful overrides**. Context must remain separate and guarded.

**Step 16 conclusion:** the final timing comparison confirms **120 ms temporal MFCC** as the best demonstrated Stage-B accuracy/latency point at **376/384**, while **librosa YIN 240 ms** remains the highest-accuracy Stage-A point at **375/384**. Stage-B 160 ms is dominated by 120 ms.

**Step 17 conclusion:** the best tested complete pipeline was **YIN 240 ms → calibrated fusion3 at 370/384 = 96.3542% end-to-end**. With oracle pitch, fusion remains **379/384**, versus **376/384** for temporal MFCC. Fusion therefore buys +3 correct Stage-B decisions but adds roughly 33 ms Python processing and substantially more feature complexity. With YIN240, only 5 of 375 correct-pitch cases remain string errors, making Stage A the larger remaining end-to-end bottleneck.

**Next:** Step 18 — browser/runtime + controlled live validation. Run **Smoke test → Real run**. Treat this as the production acceptance gate: prove Python↔browser parity, validate Stage-A YIN/onset behavior and Stage-B probabilities/masking, measure real browser decision latency/CPU, and test controlled live notes/transitions/repeats/noise before selecting fusion versus temporal MFCC for production. Preserve outputs and do not rerun completed experiments merely to regenerate data.


---

# Historical Step 18 snapshot — early browser parity work

> This section records the state before matched-preprocessing parity, reference-YIN port, live-trial page and FFT optimization. The current state is in NEXT CHAT START HERE above.


Step 18 is active. The browser validation infrastructure now executes the required **Smoke test → gated Real run** over the stored 384-recording dataset and includes a deep Python↔JS numerical parity harness.

## Browser pipeline status

After replacing the mismatched Meyda MFCC representation with a browser-native librosa-like implementation and then matching librosa-style frame-RMS trimming, the latest successful real run produced:

- pitch: **373/384 = 97.1354%**
- temporal Stage-B string: **374/384 = 97.3958%**
- conditional string accuracy with correct pitch: **97.5871%**
- end-to-end tuple: **364/384 = 94.7917%**
- mean JS pitch runtime: **~3.54 ms**
- mean JS feature runtime: **~123.16 ms**

The temporal Python reference is **376/384 = 97.9167%**, leaving a two-recording browser gap. The brute-force JS DFT is intentionally unoptimized until numerical parity is resolved.

## What has now been verified

The trim correction reduced the waveform discrepancy dramatically. The current trimmed-head comparison has mean RMSE **0.0003124** and correlation **0.999638**; segment and centered-waveform correlations are likewise ~0.999.

A new isolation test then removed all upstream disagreement by feeding librosa STFT the **exact JS-centered waveform samples**. Result:

- power-spectrum mean RMSE: **4.5826e-15**
- maximum RMSE: **8.9297e-14**
- correlation: **1.0**

This verifies that the JS Hann-window + DFT/power implementation is mathematically equivalent to the librosa STFT reference for identical input. **Do not modify the STFT/FFT implementation in response to the ordinary power mismatch.**

The remaining ordinary-path differences are downstream consequences of a small upstream sample-level discrepancy:

- ordinary power: RMSE **0.396885**, corr **0.974313**
- mel: RMSE **0.008376**, corr **0.986021**
- dB: RMSE **3.66835**, corr **0.983492**
- MFCC: RMSE **6.11716**, corr **0.997854**

Therefore the current investigation target is **before STFT**: determine the residual difference in decoded/resampled/trimmed waveform samples and/or exact trim boundary behavior. Fix only that layer first, rerun Smoke → gated Real, and see whether browser temporal Stage-B reaches the Python 376/384 reference.

## Continuation order

1. Resolve residual upstream waveform parity; do not touch verified STFT math.
2. Smoke test the complete browser pipeline.
3. Gated Real run over all 384 recordings and compare against 376/384 temporal reference.
4. Once parity is accepted, replace/optimize the brute-force DFT and verify no accuracy regression.
5. Port and compare browser fusion3 against browser temporal120.
6. Build the guided live-test UI with explicit string/fret/pick-strength instructions and automatic accepted/rejected feedback.
7. Controlled live validation across all strings, fret ranges, strengths, repeats, transitions, overlap cases, high frets, known S5f24 hard cases, silence/noise, and first/stable decision timing.

Latest successful Step-18 run: `36516288014`; head `84e8e50586f57a12c4244cde81f80b7a7a7979fa`. Smoke and Real both passed.
