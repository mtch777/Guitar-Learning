# Exact model bends in the alphaTab pipeline

`songsterr_api/bend_fidelity.mjs` provides a **companion-data solution**,
not a claim that standalone GP7 files are now lossless.

## What is repaired

GP7 export can lose unequal interior bend values or omit curves with more than
four points. alphaTab's imported-model normalization can additionally remove
interior points even when the GPIF file contains them. The adapter records the
pre-export model's exact points, type/style and tied bend-continuation links.
After native import, it validates the GP SHA256, target addresses and note/rhythm
identities before restoring that information. It never patches upstream methods.

```javascript
const {bytes, sidecar} = exportWithExactBends(alphaTab, sourceModel, settings);
// Store both privately. Sidecar contains source-derived musical information.
const {score, restored} = loadWithExactBends(alphaTab, bytes, sidecar, settings);
// Use this restored model for explicit alphaTab analysis/MIDI playback.
```

Apply restoration after import/model finishing and before MIDI generation. Calling
`score.finish()` again can normalize the curve again. Loading the GP without its
sidecar follows the original native import path and can still lose information.

## Existing pipeline integration

`export_csv_gp7.mjs ... PRIVATE_COPIED_CORPUS` now writes `score.gp` plus
`score.exact-model-bends.json` by default. Use a fresh copied private corpus to
preserve originals, or `--recheck` on an explicitly selected working copy.
`--exact-model-bends` remains compatible; `--native-bends-only` is an explicit
opt-out and refuses an output that already has a companion. Native roundtrip
checks still report native losses. Restoration
counts and the companion filename are recorded separately, never as native
roundtrip success.

The catalog copies and renames companions alongside GP files, validating the
GP hash before writing. `render_source_passages.mjs` and
`render_gp_instrument.mjs` discover adjacent `NAME.exact-model-bends.json` files
automatically. The passage renderer also accepts an explicit per-job path, or
`exact_model_bends:false` for a native comparison. A mismatched pair is rejected
before rendering. The routine path restores the
model after native import, and records the adapter and sidecar SHA in its result.
Legacy files without companions use the native path and report that absence.
Both files contain
source-derived material and must remain private.

## Evidence

Optional source-free tests, using the local installation or `ALPHATAB_MODULE`:

```
node --test composition-lab/songsterr_automation/songsterr_api/test_bend_fidelity.mjs
```

Twelve tests pass with installed alphaTab 1.8.4: exact curve and note-bend MIDI
preservation for hold, unequal middle values, release, more than four points,
duplicate middle points, instantaneous release and tied continuation; rejection
of wrong GP hashes, wrong identities, malformed curves and duplicate targets;
upstream prototype unchanged.
The exporter refusal test also verifies existing score, companion and validation
report bytes remain unchanged when overwrite permission was not supplied.
Routine discovery and preservation of the existing native-writer representation
are covered as well. See BEND_WORKFLOW_INTEGRATION.md in the parent directory
for the completed98-pair corpus verification and default workflow.

Private corpus experiment accepted 98/98 intermediate bridge models and restored
866 note-bend curves across 63 entries. Note-specific pitch-bend MIDI streams on
the bend-bearing tracks matched in three selected real cases (1,126; 666; 6,531
events), comparing event track/time/pitch/value and ignoring channel allocation.
This is not a full-song MIDI equivalence result. Aggregate/private evidence is in
`local-artifacts/bend-fidelity-adapter/corpus-probe.json`.

## Limits

- Preserves **pre-export alphaTab model** data. It cannot recover raw API precise
  positions or other information already lost before model creation.
- Does not repair native Guitar Pro interoperability; native Guitar Pro playback
  has not been verified. The GP file alone remains potentially lossy.
- Does not repair whammy curves, percussion, or other non-bend conversion effects.
- Sidecar and its matching GP are a pair. A modified GP requires a newly generated
  sidecar; the loader rejects mismatched bytes rather than guessing correspondence.
- Musical/audible acceptance is not inferred from equal MIDI events.
