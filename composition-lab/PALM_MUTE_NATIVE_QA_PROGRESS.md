# Palm-mute native output verification

Bounded scope: verify a source-supported change to the complete same-part coattack's palm-mute declarations. Selection and inverse ownership belong to the policy worker. This checker must never choose notes or change their pitches, written timing, dynamics, or other execution markings.

## Acceptance checklist

- [x] Independently compare actual inverse output against raw source with only declared mute fields changed; preserve absent versus explicit false.
- [x] Bind every member and every beat of a simultaneous coattack, including multiple voices.
- [x] Check full GP XML, archive contents, playback profile and exact-bend companion; allow only selected `PalmMuted` properties.
- [x] Check full MIDI and note origins. Only release times of bound selected attacks may change, according to the pinned renderer's duration equation and the tempo at each occurrence.
- [x] Check identical source/zero output, six render receipts, sample count, gain, clipping and actual PCM differences. Identical PCM remains an honest result; do not select another target to force a difference.
- [x] Synthetic corruption tests cover missing voices, unrelated source/GP/archive changes, MIDI pitch/onset/velocity/order changes, wrong releases, changing tempos, incomplete receipts and misleading audio.
- [x] Run the actual selected Sweet Child coattack through native export, independent checks and six renders.
- [x] Retain first results. The first actual run passed; its report is preserved separately from the later stricter recheck.
- [ ] Obtain ProjectPlanner3000 review of evidence and limits.

## Files and commands

- `check_palm_mute_artifacts.py`: independent source, GP, MIDI and PCM checks; also exposes the inexpensive `check_source` entry point used by the actual inverse runner.
- `audit_palm_mute_gp.mjs`: reads actual native mute flags and written durations; binds them to the existing full native snapshot and pinned renderer constants.
- `build_palm_mute_preview.mjs`: exports and renders actual isolated-worker captures; performs no musical selection.
- `test_palm_mute_artifacts.py`: synthetic checker tests, never presented as source-derived music or an actual native integration run.

Commands completed:

```text
python -m unittest test_palm_mute_artifacts -q
9 tests passed (3.931 seconds)

node --check audit_palm_mute_gp.mjs
node --check build_palm_mute_preview.mjs
python -m py_compile check_palm_mute_artifacts.py
passed
```

Actual runner: private `local-artifacts/palm-mute-control-v1/development-first`. Its unchanged source-selected coattack passed the native build, with no substitute selected.

Actual command (paths abbreviated here; the builder logs retain each invoked command's output):

```text
node build_palm_mute_preview.mjs <development-first> <original-capture> <backend-python> <backend-root> <alphaTab-module> <soundfont>
NATIVE_PALM_MUTE_OUTPUT_CHECKED
PASS_NATIVE_PALM_MUTE_PCM_CHANGED
```

Observed results:

- Each case contains 10,138 native notes, 6,684 beats, 8,981 performed MIDI attacks and 38,124 MIDI events.
- Exactly three selected `PalmMuted` flags changed. Only their three release durations changed, from 166 to 480 ticks. Pitch, attack time, velocity, channel, all other MIDI markers and the rest of each GP archive stayed fixed.
- Both focused and ensemble source/zero PCM match exactly. All six files contain 254,720 samples at 44,100 Hz; no clipping. Changed PCM begins at 2.258141 seconds, after the selected attack at 2.175484 seconds.
- The existing standalone GP bend roundtrip remains false in all three cases. All three pass the declared **GP plus hash-bound exact-model bend companion** comparison. This work did not repair or hide that limitation.
- A later self-review added explicit rejection of changed archive member names and inactive playback-profile changes. Both have corruption tests. The unchanged actual artifacts passed again; the report is byte-identical to the initial pass.

Private evidence: `native-preview/palm-mute-artifact-audit.json`, `native-preview/palm-mute-artifact-audit.initial.json`, `native-preview/independent-review-receipt.json`. The receipt binds code, artifacts, counts and both report hashes. No source score or audio is included in public code.

## Fresh frozen source

The new random capture was Queen / Innuendo, Songsterr 24056. The unchanged runner found no supported independent on/off alternative: 1,303 eligible coattacks, zero supported choices. It retained the source instead of manufacturing a change.

- Actual zero and 100% no-choice workers reconstruct all **91,443 captured source facts** exactly.
- Original and zero exports each contain **16 tracks, 156 bars, 7,001 notes**.
- The independent source-to-model and serialized GP5 comparisons report **zero differences on all 16 tracks**, for both outputs.
- Both standalone checked-model GP7 roundtrips pass. Thirteen hash-bound bend curves remain preserved in their companions; passing this song does not remove the earlier Sweet Child standalone bend limitation.
- Normalized complete GP XML, archive names and other assets, playback profiles, companion curve payloads, and all **23,093 MIDI events** match source to zero.
- No redundant unchanged audio was rendered. This is successful refusal/exact-recreation evidence, not evidence of an audible intervention on the new song.
- The private final receipt independently rechecked all source hashes and every code/runtime hash in the frozen plan. No production or test file changed during the frozen run.

Commands completed without repairs:

```text
export_owned_capture.py <fresh-source> <backend> <native-zero-review/source>
export_owned_capture.py <actual-zero-capture> <backend> <native-zero-review/zero>
export_csv_gp7.mjs <module> <native-zero-review> --restore-pitched-graces
review_source_bridge.py
review_native.mjs
summarize_review.py
PASS_EXISTING_SOURCE_CODEC_AND_ZERO_NATIVE_EQUALITY
```

Private final receipt: `local-artifacts/palm-mute-control-v1/native-zero-review/review-summary.json`. It records the complete source inventory, artifact and verification-script hashes, both codec reports, original/zero/native equality and explicit scope limits. ProjectPlanner3000 received both the development intervention and fresh refusal evidence for final review.

## Limits

AlphaTab currently implements this marking by capping note duration. It does not establish a physically authentic muted timbre. Nonzero PCM difference is a measurement, not proof of musical suitability or a human listening judgment. Exact native output does not independently establish donor eligibility or broader style fidelity; those require the separate policy and source-context review.
