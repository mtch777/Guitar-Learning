# Full pipeline live trial

Open `https://mtch777.github.io/Guitar-Learning/live-pipeline-test.html` on the guitar-connected computer.

## First session: 24-pluck pilot

1. Use clean interface input with the fixed drop-D# tuning shown on the page. Set the guitar volume and interface gain once; do not change them during a block.
2. Enable microphone and select the interface. Channel **2** defaults to the user's guitar input; choose channel 1 if the browser exposes only mono. Verify the guitar moves the selected channel's level, and avoid clipping.
3. Keep **Pilot · 24 normal plucks** selected. It covers all eight strings at frets 0, 12 and 24.
4. Press Record, remain quiet until **PLAY NOW**, then play the displayed position once and let it ring. Each trial records six seconds, including the quiet lead-in.
5. After 24 trials, **Export ZIP**. Send that ZIP for analysis before doing the full 240-pluck grid. Export stays local until shared.

Predictions are hidden during collection to avoid prompting technique changes. Wrong labels, accidental extra plucks, or wrong-string playing should be noted when sending the ZIP; they are not model errors. Target labels are never provided to acoustic inference.

## Follow-up tests

After the pilot confirms input and capture, collect soft/normal/hard × two repeats at frets 0/5/12/19/24 on all eight strings. Export in blocks of 24–40; verify the downloaded ZIP before clearing. At 40 retained trials the page pauses until export and clear. Each block retains globally unique trial IDs for deduplication.

Use Manual / edge cases for silence (no note), two repeated plucks with muting, and two-position transitions. Two cues appear at approximately one and three seconds. Overlap trials deliberately leave the first note ringing and are a stress test of a monophonic pipeline; do not pool them with single-note accuracy.

## What is measured

- Hybrid: correlation starts each 0.82-second capture; rolling reference-style YIN votes once available; final fusion supplies string. No early singleton actions.
- Paired control: correlation triggers/votes, with the same final fusion model. This isolates the detector/capture change. It is not the production trainer's older 107-feature classifier.
- AudioWorklet collects 4096-sample blocks; a dedicated Worker runs both routes. ZIP contains original mono Float32 WAV audio, labeled targets, all frame measurements, model hashes, sample rate/channel/device settings, first/final capture events, confidence/probability diagnostics, CPU, queue and delivery timing, callback gaps, and incomplete captures.
- Final models use estimated-MIDI harmonic features from the validated 384-recording protocol; calibrators use estimated-MIDI-masked OOF probabilities. Models fit all 384 training recordings. Live trials are independent evaluation; fitted training predictions are not accuracy evidence.

Paired inference increases CPU load. Report compute and queue time separately. Timing starts at an audio threshold/capture trigger frame, not an externally timestamped physical pluck. The page measures whether a predicted physical position matches the label. Actual lesson acceptance and question changes require a later isolated lesson-flow check.

## Analyze exports

```sh
python training/summarize_live_pipeline.py first-block.zip second-block.zip --out live-summary.json
```

The analyzer validates ZIP/audio integrity, deduplicates repeated exports, separates aborted/gapped trials, scores first position and misses/extras for single plucks, silence false events, ordered repeat/transition results, paired rescues/regressions, confidence intervals and latency. Inspect each wrong/missing event against exported audio before attributing it to a model or gate.

## Preflight evidence and reproduction

Local engine replay matched **58 held-out recording outcomes** and capture times from the saved hybrid replay. The newly fitted model export matched Python on **1,152/1,152 argmax decisions** across 384 vectors; maximum probability difference **1.67e-7**. Synthetic silence and MIDI-51 tones were checked at 44.1 and 48 kHz. AudioWorklet channel-2 block assembly and Float32 WAV/ZIP CRC round-trip passed. Production Vite build passed.

The browser preflight workflow is `.github/workflows/live-pipeline-preflight.yml`. It uses synthetic stereo audio through actual browser AudioWorklet/Worker capture, checks a deliberately mismatched target label does not influence the detected MIDI, records a silence control, and validates the exported raw audio. This is engineering verification, not guitar accuracy.

Fit/export the final bundle using the preserved estimated-MIDI feature artifact from run `36641228328`:

```sh
python training/train_step18_fusion_final.py fusion_estimated_features.json --out public/model/fusion3-live
node training/export_step18_raw_calibration.mjs fusion_real/python_oof_probabilities.json public/model/fusion3-live/calibrators.json training/results/reference/step18_reference_yin_midi_384.json
```

Dependency versions and file hashes are recorded in `public/model/fusion3-live/manifest.json`.

## Gain calibration and input guidance (2026-09-30)

The live trial page now has a diagnostics-only calibration: three seconds of muted input, followed by one open-string pluck for each of eight strings at hard, normal, and soft strength (24 picks). Click Measure for each step; wait for PLAY NOW. Guitar volume and tone stay maximum, bridge pickup selected. Keep the physical Focusrite gain fixed during each pass; restart after changing gain. Changing input channel/device or stopping input invalidates the active calibration.

Silence floor is the 90th percentile of 4096-sample block RMS. Each pick records absolute peak, strongest block RMS, near-full-scale sample count, and strongest-block-to-silence margin. Advisory criteria: less than 3 dB digital peak headroom, samples >=0.999 absolute amplitude, strongest block RMS below the existing -48 dBFS onset gate, or noise margin below 20 dB. These are engineering heuristics, not validated boundaries for classifier accuracy. Pitch confidence is still needed by the actual onset gate. Possible clipping is a digital warning; the interface clip indicator must also be checked because upstream distortion can occur below digital full scale.

The page compares each calibration peak with the same open-string/strength raw WAV where available. `public/model/gain-reference.json` contains raw absolute peaks for all 384 WAVs, a dataset filename/content digest, and explicit level-only semantics. This is not spectral similarity, waveform correlation, or a confidence calibration. One recording per target cannot establish an ideal level or distinguish picking strength from gain.

Calibration history can be downloaded separately as JSON. Trial ZIPs include history/reference provenance and a snapshot of the calibration at each trial start. Models, PCM, resampling, feature extraction, gates, capture timing, and early-action policy are unchanged. No digital gain, normalization, compression, limiter, EQ, or automatic threshold adjustment is introduced. Live peak/noise advice is visible; classification predictions remain hidden during scored collection. A completed calibration assesses the measured picks, not general accuracy, other frets, or analog clipping absence.

Validation: `node training/check_gain_calibration.mjs` exercises clipping, low-level gating, poor noise margin, verdicts, and unchanged PCM. The browser preflight measures synthetic silence and one synthetic hard step, verifies reference feedback and calibration export, then runs the existing paired trial and silence checks. Human gain suitability and picking feedback remain to be validated with real input.

Prior full-pipeline synthetic browser preflight passed in run 36670809357; Pages publication passed in run 36670809420 (commit a78cf04). These validate plumbing, not real-playing accuracy.


## Human-paced calibration (2026-09-30)

Supersedes the calibration timing instructions above. The target stays visible before and during recording. “I’m ready — start countdown” gives five seconds to put the mouse down and pick up the pick. Silence is then measured for three seconds. For notes, PLAY NOW waits indefinitely for a block at least 12 dB above the measured silence floor (minimum trigger -90 dBFS); recording lasts three seconds from that detected input. This diagnostic trigger does not change the model’s existing onset threshold. Weak input below the diagnostic trigger requires checking input/gain; it never silently advances. A live audio heartbeat timeout reports disconnected/stalled input. Cancel discards the in-progress recording. Completed results remain on screen until Next recording; Record again discards the current calibration result and prepares the same target. The final result remains displayed. This change affects calibration only, not the scored six-second trial protocol.

Browser regression check explicitly waits five seconds after PLAY NOW without playing and verifies the prompt remains, then verifies the saved result stays until the user clicks Next recording.
