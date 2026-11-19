# Learning Songs

The live lesson is at <https://mtch777.github.io/Guitar-Learning/piano/learning-songs/>.

## Shared song library

The first/default song is **Phoebe Bridgers — I Know the End**, using Edgar
Roock's full piano arrangement converted from his existing MIDI. It contains all
1,396 source note occurrences. The original MIDI, precise event data, MusicXML,
conversion decisions and validation evidence are committed under `scores/`.
See [the score notes](./scores/phoebe-score-README.md) for attribution, small
notation timing adjustments and reproducible conversion commands.

**Upload song** is the only entry point for adding a score. With no saved GitHub
token, its first screen is **Save Token**, independent of selecting a file or
starting an import. Saving a token shows the two choices: **Upload file** or
**MuseScore URL**. Later visits skip the token screen; Change/Forget are available
in a collapsed section. The token is stored only in this browser's localStorage,
not in the repository. Because GitHub Pages is static, the fine-grained token
needs Contents: read and write, limited to this one repository.

**Upload file** accepts `.musicxml`, `.xml` and `.mxl`. The browser validates
the score, then saves the unchanged original directly to this repository's
`main` branch through GitHub's Contents API. The lesson adds the uploaded song
immediately, then polls for the Pages publication.
If publication is delayed, **Refresh** retrieves the latest shared catalog.

**MuseScore URL** accepts score-page links when the user's browser has the
optional [MuseScore import userscript](./musescore-auto-import.user.js) installed.
Version 1.1.0 of the helper triggers MuseScore's piano tutorial MIDI loading
automatically in a hidden same-origin frame, then returns the signed MIDI link
to the lesson for GitHub Actions MIDI-to-MusicXML conversion and publication.
After the one-time browser setup, no manual MuseScore navigation or Play click
is part of the import flow. The form detects older installed helpers and links
to the update. This browser setup is required for MuseScore score-page links.
The same URL form also accepts direct `.mid`, `.midi`, `.musicxml`, `.xml` or `.mxl`
links from supported hosts; direct XML downloads additionally require CORS access.

The earlier conversion experiment produced 28 nonempty MusicXML outputs from
other note-data formats, but those conversions ran in separate desktop/server
tools. The lesson does not yet execute them in the browser. The Upload dialog
lists the tested source extensions separately so an offline conversion is not
mistaken for direct import support.

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

The GitHub token, preferences, last selected song and any older browser-only
scores remain device-local. Those older scores are labeled **Device-only copy**.
Select one, use **Download score**, then **Upload song → Upload file** to migrate
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
- The inline ↓/↑ controls transpose the score one semitone at a time. Notation,
  playback, required MIDI notes and keyboard range change together. A pitch
  change pauses and resets the attempt; selecting another song restores its
  original pitch. Source uploads remain unchanged.
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
Microtonal and unpitched scores are rejected clearly. Scores encoded for
transposing instruments must first be exported at concert pitch.
Ornaments and techniques remain visible; playback uses written pitches.

## Implementation

| File | Responsibility |
| --- | --- |
| `score-model.js` | MusicXML notes, exact musical time, ties, chords and tempo |
| `score-transpose.js` | Semitone transposition of a copy of the original notation |
| `score-renderer.js` | Actual OSMD engraving, SVG note mapping, cursor and colors |
| `lesson-engine.js` | Pure pitch/onset grading and lesson state |
| `piano-audio.js` | Web Audio synthesis scheduled on the lesson clock |
| `github-song-storage.js` | Shared public catalog and score loading/hash checks |
| `song-storage.js` | Local preferences and recovery of previous device-only scores |
| `score-upload.js` | XML/MXL reading used by upload validation and the build indexer |
| `github-song-upload.js` | Authenticated direct upload of unchanged originals |
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
