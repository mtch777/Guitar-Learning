# Guitar String Classifier — Experiment Record

Permanent compact record of completed experiments. GitHub Actions artifacts expire; these results should not be recomputed merely to regenerate outputs.

Primary evaluation is candidate-masked physical-string classification with leave-one-entire-MIDI-out validation unless noted otherwise. Dataset: `training/data/ringing_384`, 384 ringing recordings, 8 strings, frets 0–24.

## Results

| Experiment | Run | Best result | Errors | Artifact |
|---|---:|---:|---:|---:|
| Baseline 107 features | 36354714761 | 371/384 = 96.6146% | 13 | 10943980624 |
| Full harmonic 214 | 36354714761 | 372/384 = 96.8750% | 12 | 10943980624 |
| Time-phase screening | 36358305377 | 0–160 ms all, 95.0521% @ 40 trees | — | 10945985689 |
| Time-phase confirmation | 36361317622 | MFCC 0–120 ms, 370/384 = 96.3542% | 14 | 10945587990 |
| Three-model calibrated fusion | 36363139786 | **379/384 = 98.6979%** | **5** | 10946491780 |
| Step 5 Abeßer reproduction | 36370931642 | AR32, 188/384 = 48.9583% | 196 | 10950522386 |
| Step 6 Abeßer classifier comparison | 36374793618 | HGB, 222/384 = 57.8125% | 162 | 10953065549 |
| Step 7 Abeßer + strong-model fusion | 36383682332 | Existing 3-model isotonic remains 379/384 | 5 | 10953427540 |
| Step 8 temporal aggregation | 36384052764 | 3×40 ms MFCC mean, 376/384 = 97.9167% | 8 | 10953663191 |\n| Step 9 Stage-A pitch tournament | 36437584822 | librosa YIN 240 ms, 375/384 = 97.6563% MIDI | 9 MIDI | 10977090483 |
| Step 10 multi-hypothesis inference | 36450596841 | hard top-1 joint, 366/384 = 95.3125% | 18 joint | 10983346754 |
| Step 11 compact spectral CNN | 36459606684 | candidate-masked, 307/384 = 79.9479% | 77 | 10986904978 |
| Step 12 engineered + learned complementarity | 36463295082 | oracle unchanged at 382/384 = 99.4792%; 0 CNN rescues | 2 oracle | 10987679899 |
| Step 13 SIF feasibility | 36464844099 | feasibility gate failed; median expected-vs-control +1.14 dB | — | 10989825794 |
| Step 14 calibration/personalization | 36470556416 | medium prototype, 362/384 = 94.2708% | 22 | 10991343882 |
| Step 15 candidate-mask + context ablation | 36477918087 | temporal masked 120 ms, 376/384 = 97.9167%; correct singleton context upper bound 384/384 | 8 acoustic | 10994099328 |
| Step 16 final time × method tournament | 36479004613 | temporal MFCC 120 ms, 376/384 = 97.9167%; YIN 240 ms, 375/384 = 97.6563% MIDI | 8 Stage-B / 9 MIDI | 10995776554 |
| Step 17 final architecture tournament | 36480723812 | YIN240→fusion3 370/384 = 96.3542% end-to-end; oracle-pitch fusion3 379/384 = 98.6979% | 14 end-to-end / 5 Stage-B oracle-pitch | 10996203285 |

## Key conclusions

### Static engineered features
The 107-feature baseline reaches 96.6146%. Expanding to 214 harmonic features reaches 96.8750%, only one additional correct recording. Static feature expansion alone is near a ceiling on this dataset.

### Early MFCC
A 26-feature MFCC model using 0–120 ms reaches 370/384 = 96.3542%. It is only one error behind the 107-feature baseline and two behind the 214-feature model, while being much smaller.

Its errors are complementary: among baseline, harmonic and early-MFCC models, only two recordings are wrong for all three. Their oracle is 382/384 = 99.4792%.

### Calibrated fusion — current overall best
Leave-one-MIDI-out isotonic calibration across baseline + harmonic + early MFCC reaches **379/384 = 98.6979%, 5 errors**. This remains the best demonstrated offline system through Step 8.

### Abeßer experiments — closed
Step 5's Abeßer-style AR/LDA/RBF-SVM transfer was weak; AR32 reached 48.9583%. Step 6 showed classifier choice matters: HGB improved the same representation to 57.8125%, but remained far behind existing models.

Step 7 answered the complementarity question:

- Abeßer unique rescues versus all three strong individual models: **0**
- three-model oracle: 382/384
- four-model oracle with Abeßer: 382/384
- three-model isotonic: **379/384**
- four-model isotonic + Abeßer: 378/384

Therefore Abeßer adds no demonstrated useful coverage and should receive no further investment unless data/extraction methodology materially changes.

Step-7 artifact SHA256: `8240cf27819459e8dcc934c44495c80da05def0538d94febc09c9b05b75f9db6`.

### Step 8 temporal aggregation — temporal structure is useful
Six independent 40 ms MFCC classifiers were evaluated from 0–240 ms. Equal probability averaging of the first three frames, covering 0–120 ms, was best:

- single broad 0–120 ms MFCC: 370/384 = 96.3542%, 14 errors
- **three 40 ms classifiers averaged over 0–120 ms: 376/384 = 97.9167%, 8 errors**
- improvement: +6 correct, +1.5625 percentage points
- first five frames tied at 376/384 but require 200 ms rather than 120 ms
- recency weighting was worse than equal weighting
- later frames did not exceed the 0–120 ms result

Step-8 artifact SHA256: `59d74af732b10557ec6760a8317b3b7bef3f89da032afd70c4aaeebd3553542b`.

The three-frame 0–120 ms temporal model is now a strong lightweight production/fusion candidate.

### Step 9 Stage-A pitch detection — YIN wins

Four pitch detectors were tested at 40/80/120/160/200/240 ms on all 384 recordings.

Best per detector:

- **librosa YIN, 240 ms: 375/384 = 97.6563%, 0 octave errors, 8.30¢ median absolute error, 1.01 ms mean detector runtime**
- librosa pYIN, 240 ms: 375/384 = 97.6563%, 0 octave errors, 7.51¢, 69.60 ms
- custom YIN, 160 ms: 374/384 = 97.3958%, 0 octave errors, 9.39¢, 2.25 ms
- current browser correlation, 200 ms: 366/384 = 95.3125%, 6 octave errors, 11.71¢, 2.71 ms

Thus the best YIN result cuts the current detector's MIDI errors from 18 to 9 and eliminates its six octave errors. pYIN adds major runtime cost without improving exact MIDI accuracy. Custom YIN is nearly tied and preserves multiple pitch hypotheses for Step 10.

Step-9 artifact SHA256: `e38e632233c7f786ebcd03595dbf767f6e390c7abc24c5d1e788ba62db326efb`.

Do not rerun Step 9. Step 10 should consume its preserved per-recording outputs/candidate hypotheses.

### Step 10 multi-hypothesis inference — closed

Using preserved custom-YIN 160 ms outputs plus recomputed raw three-frame MFCC Stage-B probabilities:

- hard top-1 joint tuple: **366/384 = 95.3125%**
- top-2: 303/384 = 78.9063%, 0 rescues, 63 regressions
- top-3: 259/384 = 67.4479%, 0 rescues, 107 regressions
- top-5: 207/384 = 53.9063%, 0 rescues, 159 regressions
- pitch top-2/top-3/top-5 oracle all remained **374/384**, identical to top-1

The preserved alternative YIN candidates contain no additional correct MIDI values. Keep hard top-1 for this detector design; do not continue this multi-hypothesis branch unless a materially different detector produces genuinely complementary hypotheses.

Step-10 artifact SHA256: `93b1d4e60387c8da79465c4551a4ce3ba89b12bdcaf2bf3ec3006ea9e255cc78`.

### Step 11 compact spectral CNN — closed

The fixed 25,864-parameter log-mel CNN over the first 160 ms reached **288/384 = 75.00% raw** and **307/384 = 79.9479% candidate-masked**. It is far below the surviving engineered/MFCC systems. Artifact SHA256: `3661550b335cea6d3c3b4b7a77703e7da823f9e82f10327bebe98244edbf45dd`.

### Step 12 engineered + learned complementarity — closed

Using preserved OOF predictions only, the strong-three oracle was **382/384 = 99.4792%** and remained **382/384** after adding the CNN. CNN unique rescues: **0**; CNN wrong while at least one strong model was correct: **75**. The same two recordings were wrong across all four: `s5_f24_hard_ringing.wav` and `s5_f24_normal_ringing.wav`.

No learned+engineered fusion is justified. Artifact SHA256: `5eaf5b5e2e9646f12ddd956763f233a02ef776009f8c96ff6ff7cdbce51d8602`.

### Step 14 calibration / personalization — small positive effect

Smoke passed, then the gated real run evaluated all **384 recordings** with leave-one-entire-MIDI-out validation. Calibration anchors were drawn only from training MIDIs, so the held-out MIDI did not contribute to its own personalization.

The tested calibration budgets were:

- minimal: frets **0 and 12** per string
- medium: frets **0, 5, 7, 12, 17, 19 and 24** per string

Results:

- unpersonalized base: **361/384 = 94.0104%**, 23 errors
- minimal prototype: **361/384 = 94.0104%**, 1 rescue / 1 regression
- minimal reliability prior: **359/384 = 93.4896%**, 0 rescues / 2 regressions
- **medium prototype: 362/384 = 94.2708%, 22 errors, 1 rescue / 0 regressions**
- medium reliability prior: **360/384 = 93.7500%**, 0 rescues / 1 regression

The medium prototype therefore improved this Step-14 base by exactly **one recording = +0.2604 percentage points**, with no regressions. This is evidence that fixed-rig personalization can help, but the demonstrated gain is small relative to the calibration effort. Reliability-prior personalization was harmful and should not be carried forward.

This Step-14 base is not the existing 379/384 calibrated three-model fusion; the experiment used the lightweight three-frame MFCC representation as its personalization test bed. Therefore **379/384 remains the best demonstrated overall offline system**.

Run: `36470556416`. Artifact: `10991343882`. Artifact SHA256: `b1c78236386f8ef36e15e613594d2de079f51b9902541ac5c9e25902f0094f76`.

### Step 15 candidate-mask + trainer-context ablation

Smoke passed, then the gated real run evaluated all **384 recordings** under leave-one-entire-MIDI-out validation. Acoustic and trainer-context layers were reported separately.

Acoustic layers:

- A — raw first 40 ms acoustic probabilities: **311/384 = 80.9896%**, 73 errors
- B — + physical MIDI/string/fret feasibility mask: **336/384 = 87.5000%**, 48 errors
- C — + equal temporal mean of three independently trained 40 ms frames over 0–120 ms: **376/384 = 97.9167%**, 8 errors

Thus the physical candidate mask added **25 correct recordings**, and temporal aggregation added another **40**. Layer C exactly reproduced the Step-8 376/384 result.

Stored WAVs contain no quiz state, so trainer context was tested as explicit controlled scenarios rather than misreported as acoustic accuracy. The implementation reproduced the current `getGuitarTrainerAudioHints(midi)` answer-string semantics: context restricts Layer-C string probabilities only when a matching answer exists.

Context results:

- no matching answer: **376/384**, 0 rescues / 0 harmful overrides
- true string + strongest physically valid competitor: **376/384**, 0 rescues / 0 harmful overrides
- true-string-only singleton: **384/384**, all 8 acoustic errors rescued / 0 harmful overrides — an optimistic gameplay upper bound, not acoustic accuracy
- deliberately wrong/stale singleton: **28/384 = 7.2917%**, with **348 harmful overrides**

Conclusion: candidate masking and temporal evidence are both major contributors to acoustic performance. Trainer context can eliminate remaining errors when it uniquely and correctly identifies the physical answer position, but authoritative stale/wrong context can catastrophically override correct acoustic decisions. Keep context as a separately reported gameplay prior and design production logic so uncertain/stale context cannot blindly replace strong acoustic evidence.

Run: `36477918087`. Artifact: `10994099328`. Artifact SHA256: `fee5678b720cebf982eef64dadbafe25dfffb658145965b6773ab3f7c07e56ef`.

### Step 16 final time × method tournament

Smoke passed, then the gated real run evaluated the small survivor-only timing grid on all **384 recordings** with no trainer context.

Stage B — temporal MFCC string classification:

- 80 ms: **373/384 = 97.1354%**, availability ≈ **81.75 ms**
- **120 ms: 376/384 = 97.9167%**, availability ≈ **122.62 ms**
- 160 ms: **375/384 = 97.6563%**, availability ≈ **163.50 ms**

The Stage-B Pareto frontier contains 80 ms and 120 ms. The 160 ms point is dominated because it is slower and one recording worse than 120 ms. Therefore **120 ms is the best demonstrated Stage-B accuracy/latency operating point**, while 80 ms remains a plausible provisional-decision option if ~41 ms lower latency is worth three additional errors.

Stage A — pitch detection:

- librosa YIN 80 ms: **335/384 = 87.2396%**
- librosa YIN 120 ms: **367/384 = 95.5729%**
- librosa YIN 160 ms: **370/384 = 96.3542%**
- librosa YIN 200 ms: **374/384 = 97.3958%**
- **librosa YIN 240 ms: 375/384 = 97.6563%**
- custom YIN 80 ms: **352/384 = 91.6667%**
- custom YIN 120 ms: **369/384 = 96.0938%**
- custom YIN 160 ms: **372/384 = 96.8750%**
- custom YIN 200/240 ms: **373/384 = 97.1354%**

Librosa YIN remains the highest-accuracy Stage-A method, with accuracy continuing to improve through 240 ms. Custom YIN does not surpass it at any final operating point.

Conclusion: do not extend Stage-B beyond 120 ms; 160 ms adds latency and loses accuracy. For Stage A, retain librosa YIN 240 ms as the highest-accuracy reference and shorter YIN timings as lower-latency tradeoffs for the final architecture tournament.

Run: `36479004613`. Artifact: `10995776554`. Artifact SHA256: `27099c240ebd3f40561c8de10a3b6d6090b9a9dd538548f77e10cd7880cc7344`.

### Step 17 final architecture tournament

Smoke passed, then the gated real run compared only evidence-supported complete pipelines on all **384 recordings**. Stage-A predicted MIDI drove the physical candidate mask; trainer context was excluded.

Key complete-pipeline results:

- **YIN 240 ms → calibrated fusion3: 370/384 = 96.3542% end-to-end**, 375/384 pitch correct, 379/384 string correct when scored independently, and **98.6667% string accuracy conditional on correct pitch**. Estimated availability ≈ **276.99 ms**.
- YIN 240 ms → temporal MFCC 120 ms: **367/384 = 95.5729% end-to-end**, 375/384 pitch correct, 376/384 string correct independently, **97.8667% conditional string accuracy**. Estimated availability ≈ **243.78 ms**.
- Oracle pitch → fusion3: **379/384 = 98.6979%**, reproducing the existing best physical-string result.
- Oracle pitch → temporal MFCC 120 ms: **376/384 = 97.9167%**, reproducing the proven temporal Stage-B result.

Thus fusion retains its **+3 correct-recording** advantage over temporal MFCC in the complete pipeline, but costs roughly **33 ms additional processing** in this Python measurement and uses a much heavier representation: **347 features vs 78**. The fusion string-confidence Brier score was **0.01363**, versus **0.05844** for temporal MFCC.

The deployable Pareto frontier contained:

- YIN 200 ms → temporal MFCC 120 ms
- YIN 200 ms → fusion3
- YIN 240 ms → fusion3

YIN 240 ms → temporal MFCC was dominated.

Most importantly, the remaining end-to-end ceiling is increasingly **Stage A** rather than Stage B. With YIN 240 ms, 9/384 recordings already have the wrong MIDI before final string selection. When pitch is correct, fusion identifies the string correctly on **370/375? No: conditional Stage-B accuracy is 98.6667%, i.e. 370 correct end-to-end out of 375 correct-pitch cases, leaving only 5 conditional string failures.** Therefore Step 18 should prioritize browser YIN parity, onset/decision timing and live pitch stability at least as strongly as further Stage-B work.

Production choice is not yet based on offline accuracy alone: fusion is more accurate and better calibrated, while temporal MFCC is substantially simpler/faster. Step 18 must determine whether fusion's +3/384 offline gain survives browser/runtime complexity and live behavior.

Run: `36480723812`. Artifact: `10996203285`. Artifact SHA256: `77743ed19d9564ccc4253e37d940615bbd11eb23b250be77fd0745e13f5ae527`.

### Step 13 SIF feasibility — closed

Smoke passed after correcting the feasibility sampling/overlap logic, then the gated real run evaluated **360/360 usable fretted recordings**.

- median expected SIF peak vs matched controls: **+1.1378 dB**; gate required ≥3 dB
- expected peak control-win fraction: **59.3889%**; gate required ≥70%
- recordings with positive expected-vs-control advantage: **57.2222%**; gate required ≥65%

The SIF signal failed all three predeclared survival criteria. **Kill the SIF branch; do not build a SIF classifier.**

Run: `36464844099`. Artifact: `10989825794`. Artifact SHA256: `1aa375e45771e1775d9c9bd4ab8e9060fce7e619eb82b779d51e4b5b39eda062`.

## Permanent overlap result

`training/results/reference/error_overlap_fusion_screen.json`

Preserves the original three strong models' individual results, pairwise error overlap, unique saves, oracle, majority vote and highest-raw-confidence screen without requiring model reruns.

## Experiment policy

Every remaining experiment uses exactly:

1. **Smoke test**
2. **Real run**, gated on smoke success

Do not rerun completed experiments merely to regenerate outputs. Save metrics, predictions, configuration/feature metadata, error analysis, run/artifact IDs and hashes needed for future comparisons.

## Remaining program

14. Calibration/personalization — **complete**; medium prototype gave +1 correct / +0.2604 pp, no regressions
15. Candidate-mask + context ablations — **complete**; mask +25 correct, temporal +40, context retained as separate gameplay prior
16. Final time × method tournament — **complete**; Stage-B 120 ms best accuracy/latency point, Stage-A librosa YIN 240 ms highest accuracy
17. Final architecture tournament — **complete**; YIN240→fusion3 370/384 end-to-end, fusion retains +3 over temporal MFCC
18. Browser/runtime + live-site validation — smoke → real

See `training/research/Guitar-String-Analytics-Handoff-2026-09-27.md` for the full Steps 1–17 synthesis, revised direction, detailed methodology, implementation context and continuation instructions.

### Step 18 parity correction — 2026-09-29

The earlier comparison of browser Stage-B **374/384** to Python **376/384** mixed two masks: the browser result used detected MIDI, while the Python Step-15 result used ground-truth MIDI. Run `36523203527` (Smoke → Real passed, commit `159e702`) scores both masks on the same browser features:

- Browser Stage B with **ground-truth MIDI**: **375/384**; like-for-like Python reference: **376/384**.
- Browser Stage B with **detected MIDI**: **374/384**; browser pitch: **373/384**; end-to-end tuple: **364/384**.
- Python versus browser ground-truth-MIDI predictions differ on four recordings: `s3_f00_soft` and `s7_f00_soft` are browser-only errors; `s5_f06_normal` is a Python-only error; `s8_f00_soft` is wrong in both paths but predicts different strings. Net browser Stage-B deficit: one recording.

Run `36522192223` (Smoke → Real passed, commit `615f608`) tested librosa-resampled float WAVs through the unchanged JS frontend and classifier. Detected-MIDI Stage B remained **374/384**. Compared with JS linear resampling, `s8_f00_soft` was rescued and `s5_f04_normal` regressed. This rules out changing resampling alone as a demonstrated accuracy fix. The JS STFT/power math remains validated; do not alter it. Investigate the four decision disagreements with ground-truth MIDI before attributing the residual to a DSP stage.

Run `36590513302` (Smoke → gated Real passed, workflow commit `2e6add6`) performed a controlled 2×2 feature crossover on all 384 recordings, with ground-truth MIDI masks and the same leave-one-MIDI-out folds, classifier settings, and three 40 ms frames:

| Training features | Test features | Correct / 384 |
|---|---|---:|
| Python | Python | **376** (reproduced reference) |
| Python | JS | **376** (two rescues, two regressions versus Python/Python) |
| JS | Python | **373** (one rescue, four regressions versus Python/Python) |
| JS | JS | **375** (reproduced browser true-MIDI baseline) |

The four Python/Python versus JS/JS prediction disagreements are `s3_f00_soft` (3→2), `s5_f06_normal` (3→5, a JS rescue), `s7_f00_soft` (7→6), and `s8_f00_soft` (7→6, both wrong). Python-trained models continue to score 376 when tested on JS features, while JS-trained models score 373 on Python test features. **Training-feature differences have the stronger demonstrated effect**, but test-feature differences also swap individual decisions and recover two of the JS-trained/Python-tested errors. The experiment identifies which side of model fitting contributes; it does not yet identify a specific DSP stage or justify changing STFT. The artifact preserves per-frame raw and masked class probabilities and MFCC feature vectors for all four disagreements and two controls.

Run `36605089514` (Smoke → Real passed) isolated the dB stage using exact JS power/mel inputs. JS mel versus librosa mel from the same JS power had mean RMSE **2.43e-9**; JS MFCC versus librosa MFCC from the same JS dB had mean RMSE **5.65e-14**. The remaining exact-input dB difference came from JS applying the 80 dB floor **per spectral frame** instead of across the entire segment. An opt-in segment-global floor matches librosa dB/MFCC to numerical precision, but Stage-B true-MIDI accuracy was **374/384** with global training and test features versus **375/384** with the unchanged default. Do not promote that change alone.

The next exact-waveform check found the other missing setting: `librosa.feature.mfcc(y=...)` centers frames with **constant zero padding**, while JS used **reflect padding**. The earlier exact-centered-sample STFT check correctly validated STFT math but bypassed this padding choice. Run `36605997762` (Smoke → Real passed) tested zero padding plus segment-global dB flooring. On six recordings with identical librosa-resampled WAV samples, MFCC RMSE was below **8.59e-6**. With ordinary JS linear resampling, the four train/test combinations were original/original **375**, original/corrected **373**, corrected/original **377**, and corrected/corrected **375** out of 384. The mixed 377 result is not a consistent deployment path; corrected/corrected made two prediction swaps and no net gain. Both changes remain opt-in. Standard validation run `36605997790` passed and reproduced unchanged default Stage-B **375/384** with true MIDI, **374/384** with detected MIDI, and **364/384** complete tuples.

Run `36606741095` (Smoke → Real passed) fed all 384 recordings through librosa resampling into float WAVs, then the opt-in JS zero-padding + segment-global-dB extractor. Across **1,152 frames**, JS versus Python MFCC mean RMSE was **3.99e-6**, max **1.54e-5**, with **zero frames above 1e-4**. Browser-compatible JS features scored **376/384** under ground-truth MIDI and produced **the exact same string prediction on all 384 recordings** as the Python Step-15 reference. The detected-MIDI-mask score was **375/384**. Thus numerical feature and prediction parity is resolved under matched preprocessing; the ordinary deployed JS-linear pipeline remains at **375/384** true-MIDI Stage B. Do not claim that changing resampling alone improved accuracy: the earlier isolated ablation did not. Next prioritize Stage-A error analysis, runtime optimization, fusion comparison and guided live validation; do not rewrite validated FFT/STFT math.

Run `36608387084` (Smoke → Real passed, 384 recordings) completed Stage-A error overlap and complete tuple impact with the **same JS Stage-B features and leave-one-MIDI-out models**. Browser custom YIN: **373/384** MIDI, **364/384** complete tuples. Python custom YIN on the independently loaded waveform: **373/384** MIDI, with **exactly the same MIDI decision as browser JS on all 384**. Python librosa YIN240: **375/384** MIDI and **366/384** complete tuples; it rescued both browser-only pitch errors, `s1_f05_hard` (true MIDI 32; JS 33 from 53.486 Hz; Python 32 from 53.352 Hz, straddling the semitone boundary) and `s3_f12_hard` (true MIDI 51; JS 32 from 51.708 Hz; Python 51 from 155.613 Hz). For the latter, custom YIN's two top minima had nearly equal confidence (~0.744208 for MIDI 32 and ~0.744090 for MIDI 51). The other nine errors are shared. Both rescued cases also had correct string classification when the MIDI was corrected. This isolates an **algorithm/decision-rule difference**, not a bug in the JS custom-YIN port or upstream waveform. The Real artifact preserves predictions and `pitch_details.json`; the CSV's `js_confidence` column in this run was accidentally overwritten by string confidence, but the detailed JSON has the correct JS pitch confidences (0.710602 and 0.744210). The script's column names were corrected after the run without rerunning the completed experiment. A browser port of the reference YIN/median behavior requires separate runtime and live validation; the offline +2/384 tuple gain is not yet a production result.

Run `36613549255` (Smoke → Real passed) implemented an **opt-in browser-compatible reference-style YIN240**: centered 4096-sample zero-padded frames, 1024-sample hop, 0.1 trough threshold and median frame frequency. Both JS detectors ran on the same preprocessed waveform in alternating order, with identical Stage-B features and leave-one-MIDI-out models. The new JS path matched Python librosa YIN's **MIDI decision on all 384 recordings**; it changed only the two known browser errors. Pitch improved **373→375/384** and complete tuple accuracy **364→366/384**, with no regressions. On the GitHub runner after the first 25 recordings, paired median pitch compute time was **3.47 ms** current custom YIN versus **13.61 ms** reference-style YIN; p95 was **3.70 versus 14.01 ms**. This is ~**10.15 ms** extra median compute for +2 correct tuples. The opt-in path's confidence is a CMND-derived diagnostic and is not calibrated for live gating. Standard validation run `36613549215` passed and reproduced the unchanged default 373 pitch / 364 tuples. **This is an offline browser-compatible front-end result, not a live-site deployment**: `src/audio/pitch.js` still runs its separate correlation detector on microphone frames. Live integration must account for 240 ms observation, sample-rate/preprocessing and confidence/hold behavior before judging production accuracy.


### Step 18 browser/runtime validation — in progress

The browser frontend now runs end-to-end on the 384-recording dataset with an exact **Smoke test → gated Real run** workflow. The original Meyda MFCC path was replaced by a browser-native librosa-like MFCC implementation; the summary label still says Meyda and is stale.

Current browser real result after matching librosa-style frame-RMS trimming:

- pitch: **373/384 = 97.1354%**
- temporal Stage-B string accuracy: **374/384 = 97.3958%**
- string accuracy conditional on correct pitch: **97.5871%**
- end-to-end tuple: **364/384 = 94.7917%**
- mean JS pitch runtime: **~3.54 ms**
- mean JS MFCC feature runtime: **~123.16 ms** (brute-force DFT; optimization intentionally deferred until parity is solved)

The Python temporal Stage-B reference remains **376/384 = 97.9167%**, so browser Stage-B is now only **2 recordings / 0.5208 pp** below the reference. Before the trim fix, browser Stage-B was 371/384; matching librosa-style trimming recovered three correct recordings.

Deep numerical parity localized the remaining discrepancy. Trim/segment/centering are now very close to the Python waveform path (trimmed-head mean correlation **0.999638**). Most importantly, the isolated STFT test feeds Python the **exact JS-centered samples** and produces power spectra with mean RMSE **4.58e-15**, max RMSE **8.93e-14**, correlation **1.0**. Therefore the JS STFT/power-spectrum math itself is verified equivalent to librosa. The apparent ordinary power mismatch is caused by the small upstream waveform difference, which is amplified through power → mel → dB → MFCC.

Current downstream parity from the ordinary independent Python/JS waveform paths:

- power: mean RMSE **0.396885**, corr **0.974313**
- mel: mean RMSE **0.008376**, corr **0.986021**
- dB: mean RMSE **3.66835**, corr **0.983492**
- MFCC: mean RMSE **6.11716**, corr **0.997854**

Conclusion: **do not change STFT/FFT math.** It has now been isolated and verified exactly. The next parity work should identify/eliminate the remaining upstream sample-level difference (WAV loading/resampling/trim boundary semantics) and then rerun Smoke → gated Real. Only after temporal parity is accepted should the brute-force DFT be optimized and fusion3 be ported/compared in-browser.

Latest successful run: `36516288014` (Smoke and Real both passed). Head: `84e8e50586f57a12c4244cde81f80b7a7a7979fa`.

### Live paired YIN pitch trial (2026-09-29)

- Opt-in page: `live-yin-test.html`; normal trainer decisions are unchanged.
- Same live microphone stream feeds the existing 4096-sample correlation detector and the reference-style YIN port on a rolling 240 ms window resampled to 22,050 Hz. Captures 1.2 seconds per labeled pluck and exports paired frame decisions, confidence, RMS, sample rate, and compute time.
- Suggested grid: 8 physical strings (1 lowest) × frets 0/5/12/19/24 × soft/normal/hard × two repeats (240 independent plucks). Use `python training/summarize_live_yin.py exported.json` for paired pluck-level pitch accuracy and discordance; frames are never counted as independent trials.
- Smoke: synthetic MIDI 27/32/51/63/75 at 22,050/44,100/48,000 Hz yielded the target reference YIN MIDI; report fixture counted a paired win; Vite production build passed.
- Pending: actual guitarist/microphone trial. Reference confidence is uncalibrated; live string-classifier and lesson-gate accuracy cannot be concluded from this pitch-only trial. The new detector remains isolated from the normal trainer.
