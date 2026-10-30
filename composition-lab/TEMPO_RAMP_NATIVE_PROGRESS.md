# Tempo ramps: measured conversion and playback gaps

## Scope

Read-only investigation of the retained **Take Me Out** capture (7648), the existing converter and the pinned AlphaTab runtime. No new song, notes, interpolation rule, generated score, audio or converter repair.

## What the source actually declares

- Nine agreeing tracks; **54 declarations represent six global tempo marks**.
- All six marks are integer quarter-BPM values at bar starts.
- Marks at bars 31–34 have explicit `linear: true`: **36 literal fields** across the nine aliases.
- Every track also has `automations.gradualTempo: true`: **nine literal fields**.
- The first two marks lack `linear`; absence remains distinct from explicit false.
- Global marks: bar 1 = 142; bar 30 = 142; bar 31 = 127; bar 32 = 122; bar 33 = 114; bar 34 = 105 BPM.

Those declarations do **not**, by themselves, establish the interpolation equation or the direction in which a flag applies.

## Where the information goes

| Stage | Observed behavior |
|---|---|
| Captured JSON and our source facts | Literal `linear` and `gradualTempo` fields are retained. The tempo selector correctly refuses this unproved execution. |
| Converter `build.py`, `_tempo_changes` | Reads measure, position, integer BPM and visibility. Does not read either ramp-related field. |
| Converter `model.TempoChange` | Contains measure, position, BPM and visibility; has no ramp state or transition parameter. |
| Converter `guitarpro_writer.py`, `_apply_tempo_changes` | Writes every GP5 tempo change with `MixTableItem(duration=0, allTracks=True)`. |
| AlphaTab GP5 importer | Reads the GP5 duration byte but constructs every subsequent tempo automation with `isLinear=true`, regardless of that duration. A true flag here is not proof of a preserved source flag. |
| AlphaTab GP7 writer/reader | Writes and reads `<Linear>`/`isLinear` as notation data. |
| AlphaTab MIDI generator | Emits a discrete BPM event at each automation position. `_generateMasterBar` does not branch on `isLinear`. |

## Targeted experiments

Private evidence: `local-artifacts/tempo-ramp-native-v1/`.

1. `probe_converter.py` builds the complete neutral model from three in-memory versions of the **same** capture: captured flags, flags absent, and existing flags set false. **All three complete models and their hashes match exactly.** Original capture hashes remain unchanged. This proves the converter discards these fields before GP serialization.
2. `probe_native.mjs` reloads the existing original GP for three in-memory cases: imported flags, all false, all true. **All 26,341 MIDI events hash identically**, and the full performed-bar schedules match. An independent model comparison verifies that only declared `isLinear` values differ, after consistent chord-ID normalization.
3. The observed native tempo schedule is six discrete steps (the initial BPM event is duplicated). No intermediate ramp events are emitted. This proves the pinned renderer ignores the flag; it does not prove that the discrete schedule matches Songsterr playback.

Commands:

```text
..\.local\songsterr-venv\Scripts\python.exe local-artifacts/tempo-ramp-native-v1/probe_converter.py
node local-artifacts/tempo-ramp-native-v1/probe_native.mjs
```

## Minimum evidence needed before a fix

Use this same retained capture and an authoritative source timing implementation or measured Songsterr event clock. For one flagged transition, record both endpoints and at least two interior beat positions. Establish:

- Whether `linear` governs the incoming interval, outgoing interval, or another scope.
- Whether `gradualTempo` enables/disables those individual flags, and what absent versus false means.
- Whether interpolation is in BPM or beat duration, and whether its independent variable is musical time or elapsed seconds.
- Exact behavior at endpoints, explicit repeated marks, repeats/re-entry and gaps.

Then a minimal constant-note fixture can verify the proven timing law, GP representation and bounded MIDI timing error. **Do not select a plausible equation and call it source semantics.** Merely preserving `<Linear>true</Linear>` would still leave the current renderer playing steps.

## What remains true about the frozen result

The frozen step-only run is still a refusal. Original/zero source facts, complete native GP/MIDI and quarter geometry match, but **source ramp execution is unproved**. No frozen failure or score was replaced.
