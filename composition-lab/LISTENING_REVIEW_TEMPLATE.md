# Reuse this page for every listening checkpoint

User instruction: **repopulate the existing page; do not rebuild it.**

Required, visible in this order:
1. Untouched original audio (never label an earlier edit as original).
2. Changed version(s), each with one plain-English description of what changed.
3. Synchronized piano roll: new/changed, removed/replaced, unchanged. Explicit comparison baseline; all pitches and playing parts included.
4. One to three specific listening questions. Say what judgment is needed.

Reuse four bars before/after by default, matched full-band audio, speed control,
position-preserving version switching, note clicking, phone layout and Wi-Fi link.
Do not rerender verified audio when only wording, display data or questions change.
Do not create a new page, player, design, rendering pipeline, gallery or dashboard.

## Repopulate

```powershell
& .venv/Scripts/python.exe composition-lab/publish_listening_review.py <review.json> --assets <verified-audio-folder> --out <existing-served-folder>
```

Same HTML/JS every time. Only `comparison.json` and verified audio assets change.
The publisher verifies hashes/clocks and writes the manifest last. It does not
change notes or render audio, and validation failure keeps the old review intact.
Old audio assets are retained. Unchanged frontend files are not rewritten.

Input is the existing measured-note comparison payload, plus these required fields:

```json
{
  "schema": "listening-review/1",
  "original_version": "source",
  "default_version": "changed",
  "questions": ["Does the new ending still feel like the same idea?"],
  "versions": [
    {"id":"source", "label":"Untouched song", "description":"No musical edits.", "compare_to":null},
    {"id":"changed", "label":"Changed ending", "description":"Describe the actual audible change.", "compare_to":"source"}
  ]
}
```

This fragment illustrates new metadata, not a complete manifest. Each version
also contains its verified WAV filename, `audio_sha256`, and measured `notes`.
Keep `title`, `artist`, `bars`, `seconds`, `tracks`, `silent_tracks`, `all_parts`,
`bar_times`, `sections` and `playback_note`. Bar times include the end boundary;
optional `beat_times` are actual times, not assumed 4/4. Optional `focus_bars`,
`context_label`, version `subtitle` and `section_labels` describe this review.
Each note retains part/voice, source bar, pitch, start/end seconds, velocity,
string/fret and dead/ghost fields. Times come from the same measured playback.

Currently supports a shared playback clock. Different-duration/tempo comparisons
must explicitly supply a supported alignment in a future extension; never stretch
audio or fabricate timing to squeeze them into this template.

## Fast verification

- Reuse existing source/inverse/audio receipts; no broad gate rerun for a page update.
- Publisher checks full manifests and WAV hashes before replacement.
- One browser check: original loads, changed comparison colors match, questions
  visible, playback/seek/version switch work. Only repeat mobile checks if layout changes.
- Save listening acceptance separately. The UI cannot certify musical quality.

Code: `arrangement-review.html`, `arrangement-review.mjs`, `publish_listening_review.py`.
Current worked input: private `local-artifacts/melodic-movement-invent-animate-v1/t4-expanded-001/review.json`.
