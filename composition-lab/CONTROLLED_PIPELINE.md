# Controlled generated-core pipeline

`compose_controlled.py` connects the verified methods without changing their
sampling rules. This is a bounded prototype, not a completed composition engine.
Input must be a plain three-role GP produced by the empirical composer, with its
matching `.expected.json`. Existing performed scores, extra archive members,
nondefault notation, or mismatched canonical data are rejected before export.

Supported controls, each an integer0–100:

| Controls | What can change |
|---|---|
| `harmony`, `melody`, `bass` | Pitches and physical fingering of the selected role |
| `rhythm` | Event timing within existing voice/bar/event/rest topology |
| `tempo` | Initial global tempo |
| `programs` | Existing tracks' MIDI programs |
| `bend`, `finger_vibrato` | Eligible performance annotations |
| `hammer_on_from_open`, `pull_off_to_open` | Eligible same-string open transitions |
| `palm_mute` | Whole eligible coattack muting decisions |

Omitted controls are0. Zero means a literal lock;100 releases decisions without
requiring a different outcome. For a fixed stage input, intermediate settings
release nested subsets of opportunities. Changing an upstream control can change
downstream proposals and eligibility, so combined pipeline runs are not globally
nested variation sets. These percentages are not percentages of audible difference.
Bar count, section labels, meter, tuning, track count and event topology stay fixed.
Labels alone do not preserve returning musical material.
Unsupported controls fail explicitly. Changing rhythm or pitches can change
cross-track harmony and performance opportunities: perceptual effects are coupled.

Stages run rhythm → harmony pitch → melody/bass pitch → metadata → performance → palm muting. Harmony proposals use observed written voicings/root steps, not inferred functional chord progressions. The
manifest records controls, seed, artist, input/model/code hashes and each stage's
decisions. Final expected-score, technique, bend-curve, palm-flag and approved
vibrato playback sidecars support independent native validation. All-zero output
preserves the complete input GP bytes. Changed-core exports regenerate score
summary metadata and may have different ZIP timestamps; compare member contents
for deterministic musical replay, not archive hashes alone.

Run locally, writing a fresh directory under ignored `local-artifacts`:

```powershell
.venv/Scripts/python.exe composition-lab/compose_controlled.py `
  PATH/TO/generated.gp PATH/TO/private-config.json `
  composition-lab/local-artifacts/my-controlled-run
```

Private configuration example (replace model paths with local fitted files):

```json
{
  "artist": "Invent Animate",
  "seed": 17,
  "controls": {"melody": 50, "bend": 100, "palm_mute": 100},
  "models": {
    "composer": "PATH/TO/composer-model.json",
    "role_pitch": "PATH/TO/role-pitch-model.json",
    "performance": "PATH/TO/performance-model.json",
    "shapes": "PATH/TO/private-bend-shapes.json",
    "palm": "PATH/TO/palm-model.json"
  }
}
```

Only required model files are read. Palm-only use needs only `palm`; supply an
explicit artist when that model contains multiple artist labels. All-zero use
needs no model. No original commercial scores, fitted note-level models, private
feedback or rendered audio belong in Git. Native import/render success is an
engineering check, not musical acceptance or physical-performance validation.

For a repeatable sweep over a folder of plain cores, use
`run_controlled_batch.py BASELINES PRIVATE_CONFIG OUT --strengths 0 50 100`.
Its configuration takes `models`, `artist`, `seed` and optionally `dimensions`
(a list of supported controls; defaults to all eleven). It does not take the
single-run `controls` field. Each source/strength gets a fresh subfolder.
Failed cases are preserved and recorded while independent cases continue; the
CLI exits unsuccessfully if any case fails. Batch completion means exports only;
native import, curve/link/flag and playback checks are separate requirements.

To retain an explicit generated theme-return plan, set single-run `form_plan` to
the generated `.plan.json` path. Batch configuration instead accepts `form_plans`,
a map from input GP filenames to their plan paths. The plan must cover the bars
exactly and agree with labels, meter and event/rest/voicing topology. Returns copy
the **new proposal's** first occurrence with exact rational timing; no original
pitch bank is used. All0 settings still preserve complete input GP bytes.

When a plan contains returns, `harmony`, `melody`, `bass` and `rhythm` must each be
0 or100. Intermediate settings fail explicitly because their occurrence masks
can conflict with exact return constraints. Metadata and later performance
settings may remain intermediate. Use batch `--strengths 0 100` for an all-control
sweep with returning themes. Core notes/rhythm repeat; later bend/vibrato/legato/
muting decisions can differ between occurrences. This preserves a supplied
relationship, without claiming theme discovery, development or musical quality.
