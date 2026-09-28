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
| Step 8 temporal aggregation | 36384052764 | 3×40 ms MFCC mean, 376/384 = 97.9167% | 8 | 10953663191 |

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

## Permanent overlap result

`training/results/reference/error_overlap_fusion_screen.json`

Preserves the original three strong models' individual results, pairwise error overlap, unique saves, oracle, majority vote and highest-raw-confidence screen without requiring model reruns.

## Experiment policy

Every remaining experiment uses exactly:

1. **Smoke test**
2. **Real run**, gated on smoke success

Do not rerun completed experiments merely to regenerate outputs. Save metrics, predictions, configuration/feature metadata, error analysis, run/artifact IDs and hashes needed for future comparisons.

## Remaining program

9. Stage-A pitch detector tournament — smoke → real
10. Hard-MIDI vs multi-hypothesis inference — smoke → real
11. Learned spectral model — smoke → real
12. Engineered + learned fusion — smoke → real
13. SIF feasibility — smoke → real
14. Calibration/personalization — smoke → real
15. Candidate-mask + context ablations — smoke → real
16. Final time × method tournament — smoke → real
17. Final architecture tournament — smoke → real
18. Browser/runtime + live-site validation — smoke → real

See `training/research/Guitar-String-Analytics-Handoff-2026-09-27.md` for detailed methodology, literature research, implementation context and continuation instructions.
