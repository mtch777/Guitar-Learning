# Step 2 continuation: recurrence, sensitivity and sustained notes

2026-10-17. Analysis only. No new listening experiment or generated music.

## Acceptance checklist

- [x] Account for candidate overlap before interpreting counts as separate patterns.
- [x] Measure exact pitch/rhythm/duration recurrence on nonoverlapping windows.
- [x] Distinguish recurrence within/across source-labeled sections and transposition/time scaling.
- [x] Quantify rhythmic-tolerance sensitivity without tuning to human judgments.
- [x] Analyze constructions over held-note intervals, not just simultaneous attacks.
- [x] Edge tests: held-note onset, half-open note boundaries, same-string exclusion,
  overlap collapse, separate sections, transposition and time scaling.
- [ ] Independent musical-function labels. This is not needed to calculate the
  observations above; it is needed before claiming functional accuracy.

## Actual corpus findings

393 temporally eligible guitar/bass tracks; 102 others excluded by scope/timing.
All raw source occurrences and previous reports remain preserved.

| Observation | Result |
|---|---:|
| Pedal candidate windows | 29447 |
| Overlap-collapsed anchor/section regions | 7757 |
| Recurring normalized shapes with nonoverlapping instances | 4790 |
| Shapes recurring across distinct source-labeled section instances | 2393 |
| Recurring shapes with a transposed instance | 30 |
| Recurring shapes with a time-scaled instance | 2 |

Recurrence requires matching anchor-relative simultaneous pitch sets, attack
offsets and note durations after exact rational time normalization. A match does
not assert motif identity. Overlap-collapsed regions group by anchor and section;
different anchors may still overlap, so this is not a count of independent riffs.
Source-labeled sections may be unannotated instances; they are not inferred phrases.

| Maximum relative anchor-period difference | Candidate windows |
|---|---:|
| 0 (exact period) | 14940 |
| 1/8 | 16128 |
| 1/4 | 20259 |
| 1/2 (existing default) | 29447 |

The default is permissive: 14507 windows disappear under exact repetition. This
is threshold sensitivity, not evidence that either group is musically correct or
incorrect. Other eligibility rules remain fixed. No threshold was fit to feedback.

## Sustained constructions

Exact half-open [onset,end) sweep across all voices on each eligible track, split
at every occurrence boundary, including ties. Same-string overlap is excluded
from construction labels. Base written pitches remain separate from pitch effects.

| Construction | Labeled intervals | Total quarter-note duration |
|---|---:|---:|
| Double stop | 30672 | 36952/3 |
| Exact semitone texture | 3245 | 5029/4 |
| Power chord | 18311 | 40261/6 |
| Extended power chord | 12521 | 18140/3 |

These are boundary-split intervals, not separate attacks or riffs; labels overlap.
The machine report additionally distinguishes intervals containing held notes.
Effects can change sounding intervals; no acoustic dissonance claim follows.

## Reproduction

```text
python composition-lab/songsterr_automation/songsterr_api/analyze_pattern_robustness.py composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json --public composition-lab/songsterr_automation/results/pattern_robustness.json --private composition-lab/local-artifacts/invent-animate-corpus-v1/pattern-robustness.json
```

Private output includes exact members, regions, recurrence provenance and held-note
intervals. Public output has aggregate counts only and hashes the analyzed input.
No raw music, annotations or checkpoint is published.

## Remaining boundary

Technical observation is now broader than the previous candidate-only inventory.
Still unsupported: whether an anchor is serving a musical pedal role, whether
contrasts are call/response, intended emotional function and inferred phrase truth.
Do not request user review of brush parameters or use the old transfer UI to
establish detection accuracy. Human semantic adjudication is a separate gate.

## Source identification gate

Private pedal-identification-v2 contains six unchanged source GPs from conservatively
separated title families, selected only from non-AI/non-junk metadata with detailed
GP roundtrip pass and timing eligibility. Three exact-period and three variable-period
cases. An initial sampler selected near-duplicate Absence versions; conservative
family-similarity exclusion corrected that before delivery. v1 is preserved privately.

Twelve 6.26–17.60 second context/focused previews (one 8.70-second case and other
short windows), fixed gain, nonzero/unclipped, source and audio SHA checks pass.
All twelve media elements readyState4 / no errors; playback and pause exercised.
Browser responses remain unreviewed. Gold source notes identify the proposed anchor;
question: does it act as a repeating anchor while other notes provide contrast?
No technical brush/stroke choices, generated alternatives or A/B labels.

Private loopback link: http://127.0.0.1:5185/ . This checks selected positives only;
it cannot estimate recall or population precision. Source transcription correctness,
physical technique and guitar tone are not adjudicated by this GM preview.
The previous transfer review is not the requested analysis gate.

Verification: 211 Python tests, 210 pass / 1 optional skip; 18 JS tests and Vite build
pass. No public website assets changed; private scores/audio/feedback are ignored.
