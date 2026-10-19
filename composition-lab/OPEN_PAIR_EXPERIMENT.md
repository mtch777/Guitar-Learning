# Experimental open-string pair consumer

This opt-in tool connects observed interval/duration relationships to open-string
hammer-on and pull-off decisions. Existing generation defaults stay unchanged.
It models written technique annotations; it does not establish physical execution,
audible legato, artist feel or musical quality.

## Requirements and results

| Requirement | Verified result |
|---|---|
| Learn from eligible positives and negatives | 10,191 existing opportunities rejoined exactly; no missing/duplicate endpoints or invented negatives |
| Preserve original baseline | Origin-only probabilities reproduce the existing model exactly |
| Test relationships, not just annotation rates | One fixed pair candidate beats origin-only and shuffled-destination controls in development family validation |
| Keep adverse results | 61/103 development direction-family comparisons and 9/12 examined-holdout comparisons improve; others remain recorded |
| Affect actual generation | Four preserved generated cores x two methods x three seeds: 24 comparison GPs; 147/210 probabilities change, three selections change in two of 12 comparisons |
| Preserve unrelated music | All 24 plus six engineering controls pass XML/archive locks, native directed graphs and MIDI export; native pitch/fret/string/rhythm/tuning/program/meter/tempo unchanged |
| Literal zero / unlocked 100 | Zero is byte-identical; 100 proposes from a target-redacted input; original markers do not affect proposals |
| Measurable intermediate behavior | At 50%, 16/33 units released; all 34 unreleased endpoint fields exact; deterministic repeat byte-identical |

A probability change need not change the outcome of the same random draw.
None of these counts is an artist-accuracy or listening score.

| Prediction error (lower is better) | Origin-only | Pair candidate | Shuffled destination control |
|---|---:|---:|---:|
| Development family validation: log loss | 0.551045 | 0.535932 | 0.558756 |
| Development family validation: Brier | 0.180697 | 0.172952 | 0.180748 |
| Previously examined holdout: log loss | 0.502979 | 0.458524 | 0.508513 |
| Previously examined holdout: Brier | 0.171532 | 0.152816 | 0.173999 |

Weights are equal per feature, family and song within family. The holdout has
already been examined; these are descriptive notation results, not pristine
confirmatory generalization. The development evaluation leaves one family out.
One candidate/settings set was frozen before fitting; no held-out tuning.

## Fixed experimental choices

- Origin context is the existing attack context.
- Fret distance buckets: 1-2, 3-5, 6-12, 13+ semitones.
- Destination duration relative to origin: shorter, equal, longer.
- Pair estimates shrink toward the origin-only probability with one
  family-equivalent of prior support. Missing pair cells fall back exactly.
- Separate eligible direction denominators and family/song weights are retained.
  These bins/prior are experimental choices, not user requirements or artist laws.
- The same stable per-pair random draw and release key are used by both methods.
  Shared endpoints keep separate origin/destination properties.

## Reproduce with private inputs

All three CLIs require fresh outputs under ignored `local-artifacts`.
`REPORT.json` is the accepted relationship analysis matching the existing
`BASELINE.json` performance model. The join verifies its training-event hash.
The source revision and supplied family assignments remain external provenance;
this does not authenticate commercial score correctness or rights.

```powershell
.venv/Scripts/python.exe composition-lab/open_pair_opportunities.py REPORT.json BASELINE.json composition-lab/local-artifacts/pair-run/joined.json --artist "Invent Animate"
.venv/Scripts/python.exe composition-lab/open_pair_model.py composition-lab/local-artifacts/pair-run/joined.json BASELINE.json composition-lab/local-artifacts/pair-run/model.json
.venv/Scripts/python.exe composition-lab/pair_conditioned_performance.py CORE.gp BASELINE.json SHAPES.json composition-lab/local-artifacts/pair-run/model.json composition-lab/local-artifacts/pair-run/output.gp --hammer 100 --pull 100 --seed 17
```

`open_pair_model.py --permuted` fits the fixed shuffled-destination control.
Its reusable fitting/scoring helpers support family-separated evaluation.
The public join and model tables exactly reproduce the frozen private experiment.
Packaged consumer outputs are rechecked against the original native-verified
GP bytes, with pre/post implementation hashes; changed code seals are not
retroactively attributed to the first prototype run.

The consumer writes private hidden-input and eligibility GP intermediates plus
the requested output/audit. Original target annotations are available only for
unreleased locks. Models, source scores, source-located reports, GP/MIDI/audio
and all frozen private experiments stay outside Git.

Inherited source-exclusion reasons are not newly counted: the old empty exclusion
Counter is not evidence of zero exclusions. Existing generated cores were reused;
this is not new melody, harmony or form generation. No listening judgment,
new review UI, default promotion or complete roadmap-step acceptance is claimed.
