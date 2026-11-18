# Learning Songs

The live lesson is at <https://mtch777.github.io/Guitar-Learning/piano/learning-songs/>.

## Shared song library

The first/default song is **Phoebe Bridgers — I Know the End**, using Edgar
Roock's full piano arrangement converted from his existing MIDI. It contains all
1,396 source note occurrences. The original MIDI, precise event data, MusicXML,
conversion decisions and validation evidence are committed under `scores/`.
See [the score notes](./scores/phoebe-score-README.md) for attribution, small
notation timing adjustments and reproducible conversion commands.

**Upload (.musicxml, .xml, .mxl)** opens the repository's authenticated
upload page. Choose files, commit them to `main`, and return to the lesson after
publishing finishes. **Refresh songs** retrieves the published shared catalog.
No GitHub token is embedded in the site or requested by the lesson.

Original uploads are stored unchanged in `public/piano/learning-songs/uploads`
on `main`. `npm run build` first runs `scripts/piano/build-song-library.mjs`,
which uses the lesson's actual MusicXML parser and pinned ZIP reader. It produces
normalized UTF-8 MusicXML and `song-library.json`; the existing publish workflow
stores them on `gh-pages`. Every device reads that same catalog. There is no
second workflow that races to commit generated files back to `main`.

The build accepts files up to 20 MiB (also enforced on expanded MXL XML), isolates
invalid uploads with visible diagnostics, deduplicates identical normalized
scores and never rewrites source uploads. A refresh failure retains the current
usable lesson and displays the error. Score hashes detect stale publication.

Only preferences and the last selected song remain device-local. Older scores
from the previous browser-only library are preserved and labeled **Device-only
copy**. Select one, use **Download score**, then **Upload** to migrate
it. A legacy local entry cannot override the repository's Phoebe song.

Known development fixtures remain in the catalog and source directories but are
hidden from the song selector. Exact local copies of published songs are also
hidden; remembered selections resolve to the shared copy. Fingerprints identify
these files, so a genuine upload is not hidden because of its title or filename.

## Practice

- **Wait for correct notes:** press Play and hit every highlighted pitch in the current
  chord. Wrong pitches do not advance the score. Tied continuations do not
  require another attack.
- **Continuous playback:** a two-beat count-in starts continuous score/audio playback.
  Correct note starts turn green and missed starts turn red; chord notes receive
  independent feedback. The onset window is ±180 ms. Hold duration is not graded.
- Play/pause, restart, playback speed and sound controls are provided.
- Use a MIDI keyboard or the on-screen piano. The existing global MIDI preference
  is reused. Enable MIDI and Show/Hide are beneath the keyboard.
- The keyboard spans the selected song's lowest through highest playable pitch.
  Continuous playback highlights each sounding pitch for its full duration;
  wait mode highlights the remaining required keys. Pressed keys are green.
  Show/Hide defaults to shown and remembers the user's setting.
- The score shows only the current and next system (row of staves), advancing
  the pair as practice reaches the next row. The keyboard sits immediately below.
  Titles, credits, the legend, Details and computer-key/range controls are omitted
  from the playing view. The original score and its metadata remain unchanged.
- The score reflows to the available screen width and compact window height.
  Dense measures use a smaller engraving scale when needed to preserve complete
  notation in the visible rows.

Arranger attribution and conversion evidence remain in the linked score notes.
Repeat/navigation notation remains visible,
but practice follows written order once. Grace/cue notes are visible but excluded from grading.
Microtonal, unpitched and nonzero-transposing scores are rejected clearly.
Ornaments and techniques remain visible; playback uses written pitches.

## Implementation

| File | Responsibility |
| --- | --- |
| `score-model.js` | MusicXML notes, exact musical time, ties, chords and tempo |
| `score-renderer.js` | Actual OSMD engraving, SVG note mapping, cursor and colors |
| `lesson-engine.js` | Pure pitch/onset grading and lesson state |
| `piano-audio.js` | Web Audio synthesis scheduled on the lesson clock |
| `github-song-storage.js` | Shared public catalog and score loading/hash checks |
| `song-storage.js` | Local preferences and recovery of previous device-only scores |
| `score-upload.js` | XML/MXL reading used by the build's upload indexer |
| `script.js` | Controls, selection, MIDI/manual input and integration |

Dependencies are pinned and served locally; see [vendor/README.md](./vendor/README.md).

## Verification

```sh
npm ci
node --test tests/piano-*.test.mjs
npm run build
```

The optional integration helpers use the actual vendored renderer. Install their
additional dependencies in a separate temporary directory:

```sh
PIANO_CHECK_DEPS="$(mktemp -d)"
npm install --prefix "$PIANO_CHECK_DEPS" --no-audit --no-fund \
  jsdom@31.0.1 @napi-rs/canvas@1.1.1 fake-indexeddb@6.2.4 fflate@0.8.3
node tests/helpers/piano-renderer-check.mjs "$PIANO_CHECK_DEPS/package.json"
node tests/helpers/piano-app-check.mjs "$PIANO_CHECK_DEPS/package.json"
node scripts/piano/validate_phoebe_score.mjs "$PIANO_CHECK_DEPS/package.json"
```

Use a Node version supported by jsdom 31.0.1: `^22.22.2 || ^24.15.0 || >=26.0.0`.
Integration checks use silent simulated MIDI/audio, actual score rendering,
shared-catalog reads, device-local recovery and fresh-device loading. They do not
claim physical-keyboard calibration or audible musical acceptance.
