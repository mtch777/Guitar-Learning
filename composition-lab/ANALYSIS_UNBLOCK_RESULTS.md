# Targeted analysis probes and verified repairs — 2026-10-18

Requirements: preserve source facts; test causes with small experiments; repair
only demonstrated defects; preserve approved pedals and private baselines.
See ANALYSIS_UNBLOCK_SCOPE.md for the initial hypotheses, not current conclusions.

## Acceptance checklist

- [x] Run all seven probes in parallel across three explicitly authorized agents.
- [x] Independently check whole-rest interpretation against native GP readback.
- [x] Repair explicit measure-rest semantics; retain literal source duration.
- [x] Recheck all98 captured entries for note/timing preservation.
- [x] Isolate dead/tied flag loss and prove GP7 supports both flags.
- [x] Repair only identity-checked regular dead/tied destinations; preserve baselines.
- [x] Resolve ghost dynamic inheritance with provenance and unknown-value handling.
- [x] Probe all five observed slide types; measure candidate exceptions.
- [x] Isolate bend shape loss with real and source-free synthetic counterexamples.
- [x] Independent agent review: no blocking defect found in the narrow repairs.
- [ ] Repair remaining pitched source overflows (no safe automatic correction known).
- [ ] Resolve unpitched tie meaning separately from pitched sounding sustain.
- [ ] Implement and independently validate a full slide endpoint resolver.
- [ ] Repair both demonstrated bend-loss stages and validate playback behavior.

## Observations and action

| Issue | Observation | Delivered / remaining |
|---|---|---|
| Whole-rest overflow | All27 affected guitar rests independently reopen as full-bar rests with duration matching meter. Explicit measure/voice/beat flags distinguish them from a literal whole-duration rest. | Fixed narrow semantic duration and pickup evidence handling.55→14 overflow warnings overall;39→12 guitar.16guitar tracks cease failing timing. |
| Note-containing overflow | All12 guitar cases remain overlong in native GP, matching raw durations. Two repeated duration patterns, no demonstrated parser correction. | Preserve quarantine; do not trim notes or change meter by guesswork. |
| Ties | All21 guitar warnings have contiguous same-string/fret predecessors;18dead→dead,3dead→pitched. Matcher requires known pitch. | Cause of warning established, not proof all should sustain. No matcher change; mixed transitions remain unresolved. |
| Dead/tied export | Intermediate GP5 writer chooses tie instead of dead;18destinations lose dead flag. GP7 supports both. | Restore regular source dead/tie flags with exact beat/string/fret/tie guards. Eight copied scores independently reopen:18repaired,3pitched ties unchanged. |
| Ghost dynamics |928active ghost events:31local explicit markings,897inherited earlier voice markings. | Previous claim that897 lacked usable dynamics was wrong. Analyzer now reports inherited written dynamics and origin, without inventing ghost attenuation or calibrated loudness. |
| Slides | Shift/legato examples independently link same-string notes; below/above are entries, downwards exits. All1651shift+1164legato occurrences(including grace) have contiguous next-note candidates.24candidates dead,44same-fret; may overlap.110legato are grace. | Typed endpoint opportunity confirmed; candidates are not all validated links. No invented pitch for unspecified entry/exit endpoint. |
| Bend export | A real curve fails with simplification both enabled and disabled. GPIF exporter shares one value between its middle offsets; unequal middle values can be lost. | Simplifier removal alone rejected as a fix. Existing curve failures remain. |
| Bend importer/playback | Synthetic equal-middle hold survives GPIF parsing, then alphaTab Note.finish collapses it to a ramp. MIDI bend stream24→16events with changed ticks/values. | Confirmed separate model/playback loss. Added optional source-free reproducible probe; no upstream patch or listening claim. |

## Preservation and verification

- All98entries/495tracks compared before/after narrow timing repair:
  419,968regular occurrence records unchanged; grace records unchanged;
  zero changed/removed source notes. All470previously timing-eligible tracks retain
  their note fields.41rest spans corrected(27guitar), raw notation retained.
- Old-vs-rebuilt independent native comparison of eight copied scores finds
  exactly18scalar changes, all dead:false→true. Tested timing, tuning, programs,
  note identity and other technique fields unchanged. All8 direct source checks
  have zero differences.3/8 still have pre-existing bend-inclusive failures.
- Python:394tests run,393passed,1optional skip. JS:27tests passed, including3
  source dead/tie guard tests; mismatch mutations fail before export writes.
- Strict API audit:218paths,114analyzed/77retained/11unsupported/16outside scope,
  zero unreviewed. Refreshed implementation hashes, including dynamics helper.
- Existing occurrence reports and source scores remain unchanged; new analysis
  outputs use `relationships-unblock-v1` names. Approved pedal detector unchanged;
  recovering formerly excluded tracks can expose additional candidates.
- Exact detector regression on470previously eligible tracks: all29,447pedal
  candidates,42,337coattack groups and9,707HOPO candidates unchanged; no track
  becomes ineligible.355additional pedal candidates occur only on newly eligible
  tracks, not through changes to accepted pedal rules.
- Full fresh analysis completed on98entries/495tracks: timing-excluded guitar
  tracks20→4; all timing-excluded tracks25→6. Recovered material adds541double
  stops,42power chords,27extended power chords,10semitone dyads and140HOPO
  transitions. These are rule-defined detections, not new musical acceptance.
- Independent fresh audit:420,119source occurrences checked for raw preservation,
  identity, pitch and timing;193,766eligible coattack groups,9,847HOPO pairs,
  29,802pedal-candidate invariants and captured curve readback checked. Zero
  failed checks. This is not musical precision/recall or a request to reopen
  approved pedal review.
- Vite production build passed via `node node_modules/vite/bin/vite.js build`;
  npm is absent from this shell, so the installed Vite entry point was used.

## Reproduction

```powershell
.venv/Scripts/python.exe -m unittest discover -s composition-lab -p 'test_*.py'
node --test tests/*.test.mjs composition-lab/songsterr_automation/songsterr_api/test_restore_dead_ties.mjs
node composition-lab/benchmarks/bend_roundtrip_probe.mjs .local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs
```

The bend command exits0 when the diagnostic executes; `fidelity_equal:false`
explicitly reports known fidelity failure, not a passing preservation test.
Private probe scripts/results are under local-artifacts: timing-overflow-*,
ties-dead-ghost-probe.json, dead-tie-restoration-probe/, dead-tie-restored-native.json,
dead-tie-regression-probe.mjs, ghost-dynamics-effective-summary.json and
slides-bends-probe/. Source scores/annotations/audio remain ignored.

No website changes. Musical quality, full artist fidelity and native Guitar Pro
audio behavior are not established by these engineering checks.
