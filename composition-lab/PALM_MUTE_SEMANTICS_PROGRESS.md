# Palm muting: source and playback evidence

This is a bounded investigation, not a new creative lever. Production analysis, selection, ownership and admission rules were not changed.

## Acceptance checklist

- [x] Identify the source field and its scope from the retained converter.
- [x] Check source markings against actual reimported GP notes on a fixed capture.
- [x] Export one explicitly synthetic muted/unmuted pair with identical written notes and timing.
- [x] Compare the entire GP content and MIDI event stream; identify every allowed difference.
- [x] Render both synthetic files and verify a measurable, unclipped audio difference.
- [x] Record what playback proves, what it does not prove, and missing ownership.
- [ ] Combine this evidence with the independent source-opportunity census before implementation.

## Source contract

| Question | Evidence |
|---|---|
| Where is the marking? | `track.measures[].voices[].beats[].palmMute`. It belongs to the whole beat. |
| Which notes does it affect? | The converter applies a true marking to every note in that beat, including simultaneous notes. |
| Does it carry forward? | No. Each beat is evaluated independently. An absent or false marking does not inherit the previous beat's mute. |
| What must remain distinct? | Raw absence, explicit false and explicit true. Absence/false have the same current playback effect but different exact source representations. |
| What is not stored here? | Palm pressure, damping intensity, hand position or an acoustic spectrum. Unknown typed values must not be interpreted using the converter's general truthiness coercion. |
| What does GP store? | Per-note palm-mute flags. GP5 imports them into `note.isPalmMute`; GP7 writes and reads `PalmMuted` properties. |
| Where is it owned now? | Present declarations already have reversible Tier2 technique owners. Absent fields have no optional beat-mute owner for controlled insertion/removal. |

## Measured results

The fixed B.Y.O.B. capture and its already verified native export were used; no new song was selected.

| Check | Result |
|---|---|
| Regular beats examined | 7,318: 784 explicitly true, 6,534 absent |
| Regular native notes examined | 8,763; 1,137 palm-muted |
| Source/native flag mismatches | **0** |
| Excluded from this mapping | Four grace beats; they remain explicit exclusions |
| Synthetic source difference | One existing beat's boolean changes from false to true |
| Synthetic GP differences | Exactly two note `PalmMuted` properties; all other GPIF/archive content identical |
| Synthetic MIDI differences | Only those two notes' performed lengths: 960 → 160 ticks at 120 BPM |
| Locked MIDI fields | Pitches, attack times, velocities, channels, instrument settings, and every other event |
| Rendered proof | Two 88,256-sample WAVs at 44,100 Hz; RMS difference 0.00996076; neither clips |

The synthetic material is an authored execution diagnostic, not music selected from a source song. It is not listening approval.

## Playback limits that affect the design

AlphaTab's palm-mute branch caps the performed note length at `min(written playback ticks, floor(tempo × 80 / 60))`. At 120 BPM this is 160 ticks, or approximately **83.3 ms**. Written note duration stays unchanged.

The player keeps the same instrument and soundfont. The audible result demonstrates shorter sustain, not a measured physical palm-contact timbre. Notes already shorter than the cap need not change audibly.

The mute branch runs before staccato, ties, legato-slide continuation and let-ring duration handling. Their combinations need separate proof. Existing plain-rhythm ownership refuses active muting; this investigation did not loosen that condition.

## Reproducible evidence

Private folder: `local-artifacts/palm-mute-semantics-v1/`.

- `prepare_synthetic.py`: creates only the labeled diagnostic captures.
- `audit_semantics.mjs`: checks fixed-source/native flags and captures actual MIDI from the synthetic exports.
- `summarize.py`: checks source, GP, MIDI and WAV differences independently and writes `summary.json`.
- `native-export.log`, `native-semantics.json`, `audio-jobs.results.json`: retained export and render evidence.

Executed through the existing `export_owned_capture.py`, `export_csv_gp7.mjs --restore-pitched-graces`, and `render_source_passages.mjs`; no converter or renderer repair was introduced.

Pinned code evidence: backend `build.py:170` and `guitarpro_writer.py:167`; AlphaTab core GP5 importer at line 18620, GP7 importer at 21186, performed-duration branch at 43560, GP7 exporter at 66657. Exact runtime and artifact hashes are retained in the private reports.
