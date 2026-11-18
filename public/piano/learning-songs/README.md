# Piano Learning Songs

This static lesson displays an imported MusicXML score and uses the same parsed notes for score highlighting, local audio and keyboard grading. The page is `piano/learning-songs/` beneath the site's base URL. This document describes the implementation in this directory; it does not establish that a particular revision has been deployed.

## Using the lesson

Choose a saved song, or use **Upload score** to open one or more `.musicxml`, `.xml` or `.mxl` files. Choose a mode and press **Play**. Input can come from a connected MIDI keyboard, the on-screen piano, or the computer keyboard.

| Mode | Behavior | Grading |
| --- | --- | --- |
| **Wait for the right notes** | Highlights the next attack group and waits until every required pitch has been struck. Chord pitches may be entered separately. A wrong pitch does not advance the score. | Pitch only; no time limit. Rests do not require input. |
| **Play in time** | Starts with a two-beat count-in, then advances continuously at the score's tempo and selected speed. With Sound enabled, the written attacks also play through the local instrument. | Correct pitch within **±180 ms** of its onset is a hit. Pending notes become misses after that window. Hits turn green; misses turn red. |

Both modes grade fresh key strikes. Held-key repeat events do not supply additional strikes. A tie continuation does not require another strike; simultaneous unison notes share one physical key strike while retaining their separate written noteheads. **Note lengths, releases, velocity and sustain-pedal technique are not graded.** The score's note durations are still used for audio and timeline length. All included pitched parts are practiced together; there is no part or hand selector in this version.

Controls:

- **Pause / Play:** freezes and resumes the lesson position and grades. Pausing also stops current audio. Leaving or hiding the page pauses the lesson automatically.
- **Restart:** clears grades and returns to the beginning. If the lesson was playing, it starts again; otherwise it remains ready.
- **Speed:** 25–150% in 5% steps, available while paused. Changing speed or practice mode starts a fresh attempt. The timed grading window stays ±180 ms.
- **Sound:** enables the local synthesized instrument. Audio begins only after user interaction. If browser audio is unavailable, the lesson can continue silently.
- **Keyboard:** `A W S E D F T G Y H U J K` plays a chromatic octave, initially C4–C5. `Z` / `X` or the octave buttons move the visible range. Pointer and accessible button activation also work.
- **Connect MIDI:** requests Web MIDI input permission and attaches connected inputs. The lesson reuses the site's shared `PracticeMIDI` enabled preference. MIDI strikes grade notes; they are not sent back to an output device or echoed through the local instrument. Browsers without Web MIDI can use the on-screen or computer keys.

## Imports, saved songs and privacy

The browser accepts **score-partwise MusicXML** in `.musicxml` or `.xml`, and compressed MusicXML archives in `.mxl`. An `.xml` extension alone does not establish that a file is MusicXML. MXL's declared score path is used when present. Other notation formats must first be converted to MusicXML outside this page; MIDI, PDF, images, audio and native notation projects are not direct uploads here.

The maximum input size is **20 MiB** (`20 × 1024 × 1024` bytes). MXL extraction also limits the combined size of extracted XML entries to 20 MiB. Empty files, invalid archives, malformed XML, unsupported score structures and unusable notation receive an error in the page.

A candidate is parsed and rendered before it becomes a saved library entry. An unsuccessful replacement keeps the previous usable score and selection available. If a valid score opens but storage is unavailable or full, it remains usable for the current visit and the page reports that it was not saved persistently.

Uploaded score data stays in this browser's **IndexedDB** database, `piano-song-library-v1`. The last selected song and lesson preferences use **localStorage**. No score-upload request is sent to a server. This is local storage for the current browser profile and site origin, not account sync or encrypted storage. Clearing site data removes saved scores and preferences; another browser or device has a separate library.

## Current first song and bundled test score

**Phoebe Bridgers — I Know the End** is the first library metadata entry. A verified notation score is still needed, so this entry asks the user to upload MusicXML before practice is enabled. The available performance MIDI has not been silently converted into a purported original written score. The **Upload this score** action attaches a single chosen score to that entry; the ordinary upload action also recognizes the song title in a filename or MusicXML title. That association is a convenience, not verification of the uploaded arrangement's identity.

**Conversion test · 20 notes** is a separate, usable fixture. It is Michael Cuthbert's *Cuthbert NWC Test*, a genuine NoteWorthy Composer developer example with four parts, two measures per part and 20 written pitched notes. The lesson has 19 distinct playable attacks because a simultaneous unison is merged for keyboard input. This fixture is not a Phoebe Bridgers arrangement.

### Fixture provenance

The source repository is [cuthbertLab/music21](https://github.com/cuthbertLab/music21), pinned to commit `86a7dc8a5fb3b1996ac0202d6bb9b4d4b9d19197`. The downloaded originals were retained unchanged in the conversion experiment.

| Item | Source and method | SHA-256 |
| --- | --- | --- |
| Original binary `cuthbert_test1.nwc` | [Pinned upstream file](https://raw.githubusercontent.com/cuthbertLab/music21/86a7dc8a5fb3b1996ac0202d6bb9b4d4b9d19197/music21/noteworthy/cuthbert_test1.nwc); input used for the bundled conversion | `23cd8cdb11eda159ccf8d165e1c38fb6c44d6cd5b9a545310ec51ddaf04eb59e` |
| Text counterpart [conversion-test-source.nwctxt](./scores/conversion-test-source.nwctxt) | Unchanged [upstream `cuthbert_test1.nwctxt`](https://raw.githubusercontent.com/cuthbertLab/music21/86a7dc8a5fb3b1996ac0202d6bb9b4d4b9d19197/music21/noteworthy/cuthbert_test1.nwctxt) | `6092906c16414d6ea1872f99c607d36f04fc53cad7b9be113f4411458cf1ba76` |
| Bundled [conversion-test.musicxml](./scores/conversion-test.musicxml) | music21 **10.5.2**: parse the binary with `format="noteworthy"`, then write MusicXML with `makeNotation=False` | `e8744c600ec44b90cea8cca50684df2752ff3d19cc9a31a6a8cb1e678bb17cdb` |

The original binary's metadata and the retained text counterpart explicitly identify Michael Cuthbert and **Public Domain**. This is the fixture's own rights statement, separate from music21's source-code license. No notes were generated or manually transcribed for this conversion.

The conversion experiment compared the music21-parsed source events with a parse of the exported MusicXML, including parts, pitches, onsets, durations, rests and voices. That check was exact for this fixture. It is a parser-derived round trip, not an independent proof of every source-parser or engraving behavior. The app's renderer check separately verifies the mapping of all 20 written notes to the actual rendered score.

## Version 1 notation limits

The parser retains exact fractional score times alongside numeric values. It supports chords, rests, several parts and staves, voices using MusicXML backup/forward timing, tuplets expressed by divisions and durations, key and meter changes, tied notes, and numeric tempo changes. Stable note IDs link the written score to the shared attack model.

The following limits are deliberate and surfaced as warnings or import errors:

- **Repeats, alternate endings and navigation:** display as written; playback and both modes visit each written measure once. Repeat jumps, D.C./D.S. and coda navigation are not performed.
- **Grace and cue notes:** remain visible but are excluded from audio and grading. Hidden starting notes are excluded from practice; a hidden continuation of a visible tie can still extend that tie's duration.
- **Ornaments and performance techniques:** remain in the notation where the renderer supports them; audio and grading use the written pitches rather than realizing trills, bends, slides or glissandi. Dynamics and instrument-specific expression are not modeled by the simple local sound.
- **Tempo:** exact numeric MusicXML sound/metronome instructions are used. If no initial tempo is supplied, the lesson uses 120 quarter notes per minute and warns. Non-numeric tempo instructions retain the previous tempo.
- **Transposition:** nonzero instrument transposition is rejected; export a concert-pitch score first. Ordinary key changes and octave markings are not themselves rejected; encoded pitch data supplies the target MIDI pitch.
- **Unsupported pitches:** unpitched percussion, microtonal pitches and pitches outside MIDI 0–127 are rejected. A score must contain at least one playable pitched attack.
- **Incomplete or ambiguous notation:** missing/invalid durations or divisions, invalid backup timing, duplicate part IDs, and unmatched, noncontiguous, unfinished or ambiguous ties are rejected rather than guessed.
- **File structures:** MusicXML `score-timewise` and unrelated XML dialects are not accepted. This is a supported subset of MusicXML, not a general conformance validator or universal score player.

## Implementation and verification

| Module | Responsibility |
| --- | --- |
| [score-upload.js](./score-upload.js) | File checks, text decoding and bounded MXL extraction |
| [score-model.js](./score-model.js) | Written notes, exact timing, tie chains, attack groups and tempo conversion |
| [score-renderer.js](./score-renderer.js) | OpenSheetMusicDisplay engraving, note mapping, cursor and colors |
| [lesson-engine.js](./lesson-engine.js) | Pure pitch/onset grading and practice state |
| [piano-audio.js](./piano-audio.js) | Local Web Audio synthesis and scheduling |
| [song-storage.js](./song-storage.js) | IndexedDB scores and local preferences |
| [script.js](./script.js) | UI, transport, input adapters and integration |

Browser dependencies are pinned and served locally; see [vendor/README.md](./vendor/README.md).

From the repository root, install the normal development dependencies and run the focused tests:

```sh
npm ci
node --test tests/piano-score-model.test.mjs tests/piano-lesson-engine.test.mjs tests/piano-upload.test.mjs
```

The optional integration helpers load the actual vendored renderer. Install their additional dependencies in a separate temporary prefix, leaving the repository dependency files unchanged:

```sh
PIANO_CHECK_DEPS="$(mktemp -d)"
npm install --prefix "$PIANO_CHECK_DEPS" --no-audit --no-fund \
  jsdom@31.0.1 @napi-rs/canvas@1.1.1 fake-indexeddb@6.2.4 fflate@0.8.3
node tests/helpers/piano-renderer-check.mjs "$PIANO_CHECK_DEPS/package.json"
node tests/helpers/piano-app-check.mjs "$PIANO_CHECK_DEPS/package.json"
```

Use a Node version supported by jsdom 31.0.1: `^22.22.2 || ^24.15.0 || >=26.0.0`. The helpers check actual score rendering and app integration with simulated MIDI, clocks, IndexedDB and silent audio nodes. These are technical checks; they do not claim physical-keyboard latency calibration, listening acceptance or remote deployment verification.
