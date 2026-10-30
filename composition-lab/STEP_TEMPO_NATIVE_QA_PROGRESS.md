# Step-tempo native QA

## Acceptance checklist

- [x] Bind the actual isolated zero/changed workers to complete original capture hashes. Only every alias of the selected global BPM declaration may change.
- [x] Compare complete GP XML, archive inventory/assets, playback profile and exact-bend companion. Only the selected tempo value may change.
- [x] Derive the performed step-tempo ledger independently, including repeat re-entry and explicit resets. Quarter clocks stay fixed; seconds integrate `60 * dq / BPM`.
- [x] Compare all actual MIDI events and their origins against a fresh original native model with only that BPM parameter changed. Independently check pre-influence events and the known dead/palm-mute duration equations.
- [x] Render the same source bars at both tempos. Original/zero PCM must match. Measure the changed PCM without claiming musical fit.
- [x] Run synthetic corruption tests; preserve any first actual failure. No converter repairs or replacement selections.
- [x] Provide and exercise an original/zero-only native path for a fresh no-choice result. It requires no demonstration, changed capture or audio render.
- [x] Run the frozen code on the next preregistered new random input and retain every failure/no-choice result.

## Scope

The counterfactual is a validation oracle, not a generator or source selector. It shares the pinned renderer with the actual output. Complete source and GP field comparisons, independent rational clocks, cap equations and causal checks provide separate checks; agreement does not prove physical guitar performance or artistic fit.

The first operation is explicitly **PARTIAL component-conditioned global tempo**. B.Y.O.B. has source-supported rhythm-component alternatives, but no matching full-ensemble donor. That limitation remains visible even if all artifact checks pass.

## Work log

- Started the independent source/native checker and source-bar preview builder. Production owner/policy and approved detectors are outside this worker's scope.
- `..\.venv\Scripts\python.exe -m unittest test_step_tempo_artifacts -q`: **16 tests passed**. Covered complete aliases, outside note/flag/dynamic changes, unknown ramps, source conflicts, repeat re-entry/reset, persistent seconds offset, wrong BPM/reset/seconds, counterfactual hidden edits, pre-influence events, cap equations, GP field locks, stale capture binding, chord-ID reference consistency, PCM length, attack velocity and a real zero-only interface without a fake changed case.
- Actual builder command: `node build_step_tempo_preview.mjs local-artifacts/step-tempo-control-v1/development-first local-artifacts/parallel-levers-v1/frozen-v1/recovery-same-seed/capture ..\.local\songsterr-venv\Scripts\python.exe ..\.local\songsterr-dl ..\.local\qa\node_modules\@coderline\alphatab\dist\alphaTab.mjs ..\.local\qa\node_modules\@coderline\alphatab\dist\soundfont\sonivox.sf2`.
- The actual isolated edit was the first selected source-supported result: all seven bar-95 aliases, **153 → 162 BPM**, quarters **376–392**. No note or target was replaced for the native check.
- First actual audit refused independently imported chord-diagram UUIDs. The complete GP XML and note/MIDI snapshots already matched. The corrected comparison renames declared chord IDs together with their beat references, retains all values/order/relationships, and rejects orphan references. Original failure/report/log remain beside the unchanged native outputs. No GP or render was regenerated for that correction.
- Final `check_step_tempo_artifacts.check(...)`: **PASS_NATIVE_STEP_TEMPO_PCM_CHANGED**. All **8,767 written notes** and **8,681 played attacks** remain. Complete events: **47,099 → 47,103**; every changed event and origin matches the exact one-parameter native reference.
- **1,180 cap equations checked per case**; no split-execution exceptions in this source. Exactly **21 played durations** changed: seven dead-note caps **76 → 81 ticks**, fourteen palm-muted caps **204 → 216 ticks**. Played pitch, tick onset, velocity and channel remain fixed.
- Performed tempo changes only in **bars 95–98**. Bar **99** restores the original following BPM. The resulting absolute-time difference persists after that reset: **−160/459 seconds**. All seven tracks share the same verified clock.
- Actual preview uses **bars 94–100** for every case. Original/zero PCM matches exactly in focused and ensemble renders. Changed PCM differs in both. Frame counts **445,824 → 430,464** at 44,100 Hz; both match rational source-bar duration rounded to the pinned renderer's 64-frame buffer boundary. No clipping or listening-quality claim.
- Original/zero entry point: `node build_step_tempo_zero.mjs <qa> <backend-python> <backend-root> <alphaTab-module> [native-zero-review-name]`. Its development proof passed **92,617 exact source facts**, complete GP/MIDI equality, **47,099 events**, **152 performed bars** and **16 source tempo marks**, without rendering audio. The first attempt assumed an optional pre-export diagnostic existed even when standalone GP roundtrip passed; that failure is retained in `native-zero-review`. Corrected same-source evidence is in `native-zero-review-retry-v1`.

## Remaining boundaries

- The frozen new random input was Take Me Out (7648). Its 54 components were all refused because explicit ramp-related fields are outside the proved step scope. Both actual source-denied workers recovered all 74,381 source facts. The frozen native step-clock failure remains retained.
- Separate read-only evidence proves original/zero equality for nine tracks, 109 bars, 8,578 written notes and 26,341 MIDI events, including source/native quarter geometry. This is not a source-ramp playback pass.
- After the freeze was closed, the reusable zero-only checker gained the same explicit source/native bar-geometry guard used by the changed-case checker. A mixed-meter/repeated-visit corruption regression was added. **35 targeted tests passed** (17 tempo, 10 palm-mute, 8 group-rhythm). New receipts under `local-artifacts/step-tempo-control-v1/post-freeze-geometry-review/` preserve both original audit files: development zero passes; fresh source still refuses the unproved ramp map; its separate geometry-only check passes.
- Source tempo support remains explicit positive integer quarter BPM, bar-start steps, complete agreeing track aliases and no ramp/unknown tempo fields. No converter repairs were made.
- The native GP roundtrip passes for this development source. This proves the checked codec scope, not that every possible Songsterr field has a GP equivalent.
- Actual performed repeat visits and explicit resets are audited; the authored repeat/reset regression does not prove conversion of every Songsterr repeat/jump notation.
- Native GP `isLinear` behavior differs from the source's absent ramp declaration. The pinned renderer emits measured steps; other GP applications have not been verified.
- Musical support is **PARTIAL**. One source rhythm component supports this tempo alternative; other active components and the full ensemble have no matched donor. Renderer agreement and PCM differences do not establish artist fit.
