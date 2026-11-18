# Piano song lesson

## Active request

Build the actual lesson at `public/piano/learning-songs/`: saved-song dropdown
with the last selection restored; upload control showing supported extensions;
full sheet music with play/pause and restart; wait-for-correct-notes practice;
continuous timed practice with green hits and red misses. First/default song:
Phoebe Bridgers — I Know the End, using a genuine structured source.

This is the piano trainer, not a Composition Lab transformation. The latest
explicit song request governs this feature's artist selection. Keep unrelated
guitar/Composition Lab behavior intact. MIDI and audio QA must be silent.

## Acceptance checklist

- [x] Inspect current main (`9bdd1922ec2a`), piano source, shared MIDI/tracker and deployment workflow.
- [x] Implement full score rendering, shared score events and timing.
- [x] Persist successful uploads and last song selection; reload them without re-upload.
- [x] Advertise only browser-supported input formats and reject invalid files clearly.
- [x] Wait mode: wrong pitch cannot advance; all chord pitches required; ties/rests handled.
- [x] Timed mode: audio/score share a clock; per-note hits/misses persist; restart clears results.
- [x] Support existing MIDI auto-connect and usable manual test input.
- [x] Research actual I Know the End sources; retain provenance and disclose source limits.
- [ ] Attach a verified structured notation file for I Know the End. The named first entry currently requests an upload.
- [x] Verify score parsing, mode transitions, upload/reload and error recovery.
- [x] Run relevant unit tests and production build.
- [ ] Inspect the deployed page and mobile layout before claiming live verification.

## Design and disproof cases

MusicXML is the common input. Render the original notation; derive practice
attacks from those same notes. Preserve part/staff/voice, exact musical time and
ties. A tied continuation does not demand a new key strike. Simultaneous notes
must remain one practice position; two identical pitches at different onsets
must require separate strikes. Tempo changes affect playback and grading equally.
Unsupported notation/navigation must be visible, not silently turned into a
different lesson. A malformed upload must leave the previously usable song intact.

Original downloaded conversion-lab samples and converter experiments remain
outside the application source; passing an offline conversion is not proof of
browser-native upload support. No guessed or substitute tune may be labeled as
the requested Phoebe Bridgers song.

## Progress

- Created an isolated sparse checkout of the current main branch.
- Existing page has no song engine; existing piano pages supply shared MIDI
  preference and practice tracking. Existing Pages workflow publishes `public/piano`
  through Vite and stamps HTML asset URLs with the source commit.
- Prior deployment authorization was confirmed from the earlier piano work.
- Parallel work: source-score discovery and a focused MusicXML event parser.

## Verification and repairs

- `node --test tests/piano-*.test.mjs`: 42 passed. Covers parser, independent
  voices, chords, ties, tempo changes, practice modes and actual compressed MXL.
- `npm run build`: passed. The existing Vite app still builds; piano remains a
  static page under the existing Pages workflow.
- Actual vendored OSMD rendering check: 20/20 bundled notes and 8/8 adversarial
  notes mapped. Separate chord members retain separate red/green colors. Tied
  and unison heads share their attack grade. Written-order cursor, restart,
  resize and atomic failed replacements pass.
- Integrated app check uses real application code, renderer, ZIP reader and MIDI
  adapter with silent simulated audio/MIDI and IndexedDB. Upload, persistence,
  fresh-page restoration, count-in, pause/restart and both grading modes pass.
  Pending audio resume is cancelled by mode changes; failed resume cannot freeze
  the monotonic lesson clock. Audio scheduling translates the lesson clock into
  the audio device's clock. No hardware MIDI or listening acceptance is claimed.
- Fixed per-chord-head coloring, final-sustain pause/resume, namespaced MXL
  manifests, declared XML encodings, selection/save races, untitled filenames,
  asynchronous Play races and suspended audio clocks during integration.

## Source and scope limits

The first library entry is **Phoebe Bridgers — I Know the End**, awaiting a
MusicXML/MXL upload. Edgar Roock's public arrangement video
<https://www.youtube.com/watch?v=qjnUrgG_hv4> links genuine MIDI and PDF. The MIDI
contains performance timing and cannot preserve authored readable notation;
the PDF has no embedded native score. Neither was scanned, quantized or published
in this repository. The initial entry does not pretend to contain the song.

The immediately playable conversion test is Michael Cuthbert's explicitly
public-domain NoteWorthy fixture, converted to MusicXML with all 20 notes checked.
Its unchanged source text and attribution are included with the test score.

This first lesson grades pitch and note onset (timed window ±180 ms), not hold
length. Repeat/navigation notation is shown, but practice follows written order
once with a visible warning. Grace/cue notes are displayed and explicitly
excluded. Unsupported transposing/microtonal/unpitched scores are rejected
clearly. These limits do not establish universal lossless notation support.

## Publication

Local implementation and verification are complete. Source publication, live
workflow status and actual browser geometry are recorded separately after they
are observed; this checkpoint does not yet claim a successful deployment.
