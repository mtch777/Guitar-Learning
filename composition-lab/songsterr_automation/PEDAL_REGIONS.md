# Pedal identification correction

The earlier burst-window detector remains preserved as a historical baseline.
The new pedal_regions.py identifies recurring standalone single-note or dyad
anchors with at least three attacks and at least two temporally separated higher
contrasts between returns. It retains the continuing anchor attacks across the
source-labeled section instead of displaying only one six-burst window. Pitches
inside changing multi-note chords are not mined as independent anchors.

A lower, at-least-equally recurring overlapping pattern can dominate a weaker
higher candidate. Several distinct candidates can remain; this is not a trained
artist model or a guaranteed unique musical role. Rules use no song names or keys.

## Acceptance and actual results

- [x] Preserve private feedback with original hash; validate study and every selected note ID/pitch/bar.
- [x] Keep blank and Unclear answers distinct; unselected notes remain unknown.
- [x] Add repeated-chug, interval-anchor, changing-chord and sustained-overlap tests.
- [x] Compare against the original unchanged highlights without replacing prior feedback.
- [x] Rerun393eligible corpus tracks:3733region hypotheses,3274single-note /459interval.
- [ ] Independently validate on untouched songs and missed-case annotations.
- [ ] Resolve partial dyad voicings and reliable phrase-level extent.

Private development comparison:130notes marked; original highlights cover18;
revised hypotheses cover129. This is selected-note coverage, NOT precision/recall:
marks can be incomplete and these examples informed the rules. The chords-only
review passage now has no hypotheses. One marked partial interval note is missed;
additional hypotheses are unreviewed. Do not silently convert them to correct or
incorrect labels. No feedback text or note-level annotations are published.

Section-wide extension can bridge unrelated material, and strict exact pitch sets
can miss partial dyads, octave variants and changing anchors. These remain explicit
limitations. Both original and revised source observations remain locally available.
The existing review and its original gold highlights are not silently replaced.

## Reproduction

```text
python composition-lab/songsterr_automation/songsterr_api/evaluate_pedal_regions.py composition-lab/local-artifacts/invent-animate-corpus-v1/relationships-v2.json --public composition-lab/songsterr_automation/results/pedal_regions.json --private composition-lab/local-artifacts/pedal-feedback-v1/corpus-regions.json --feedback composition-lab/local-artifacts/pedal-feedback-v1/feedback.json --cases composition-lab/local-artifacts/pedal-identification-v2/cases.json
```

Feedback comparison is written privately beside the corpus report. Published
results contain only corpus aggregates and input hashes. Existing source GPs,
audio and earlier baseline reports remain unchanged.
