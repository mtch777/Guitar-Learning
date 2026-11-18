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

### Current correction — repository song library and playable Phoebe

The user explicitly requires the Phoebe song to be uploaded and all song uploads
to persist on GitHub. This supersedes the earlier browser-only storage choice and
the placeholder decision. Convert the existing MIDI note events, retain the
unaltered original, and disclose notation timing adjustments.

- [x] Convert the complete Phoebe MIDI; compare all source pitches and attacks.
- [x] Publish the original, MusicXML and conversion provenance in the repository.
- [x] Load Phoebe on a fresh visit; keep the last selected song on later visits (integration verified).
- [x] Read the shared song catalog from the deployed repository on every device (fresh-device integration verified).
- [x] Route uploads through GitHub's authenticated file upload page.
- [x] Regenerate the catalog and normalized MusicXML automatically during publish (prebuild verified).
- [x] Preserve previous device-only scores with a download/migration route.
- [x] Verify genuine XML/MXL indexing, bad-file isolation, shared-library reload,
      full Phoebe rendering, and both lesson modes; then verify live deployment.

Original uploads are committed to main under `public/piano/learning-songs/uploads`.
The existing build validates them with the same parser used by the lesson and
publishes normalized scores plus the catalog to the existing gh-pages branch.
No token is embedded in the site and no browser-only save is presented as shared.

### Initial release record

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
- [x] Inspect the deployed page, score and controls in a real browser.

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

## Initial release source decision (superseded below)

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

## Initial publication record

Source release `c3c1f0a4879a22b6cb3a79e4c9871b4de1b378b3` is on main.
Build/test/publish run 44210272476 and Pages deployment 44210377614 both succeeded.
The live page at <https://mtch777.github.io/Guitar-Learning/piano/learning-songs/>
was then inspected in the cloud browser, with sound disabled.

Observed UI results: first Phoebe entry requests its missing score; selecting the
conversion test renders its 20 source notes/19 attacks. A wrong C4 did not
advance; D4, G4 and G3 completed the first chord and produced 3 green hits.
Timed mode counted in, played through and marked 19 unplayed attacks missed.
The page itself has no horizontal overflow at the inspected 1348px viewport.

A 10px internal score overflow was traced to horizontal container padding being
included in OSMD's initial width measurement. The follow-up removes that padding;
normal engraving margins remain. Browser sizing controls did not provide a
narrower viewport, so mobile geometry is not claimed as visually verified.
Physical MIDI hardware and audible musical quality remain separate user checks.

The follow-up source `9912b4dfad22` also passed build and Pages deployment.
Actual browser file-chooser tests opened a genuine `.mxl` and the converted
Bach BWV939 `.musicxml` together. Both entered the library. Reload restored the
Bach score, selection, timed mode and muted sound preference without re-upload.
Longer scores reveal a second width dependency: the vertical scrollbar appears
after engraving. Reserving its gutter before rendering keeps that width stable.


## Repository-persistence correction — verification

- Source MIDI has 1,396 note occurrences. Every pitch and occurrence is retained
  in the full 128-measure, 323.957-second piano score. Nine starts shift by at most
  1.667 ms and 115 releases by at most 36.667 ms for notation. The original MIDI
  and exact events are preserved; the derived MusicXML is not claimed timing-lossless.
- Actual OSMD maps all 1,622 notation items, with no model or renderer warnings.
  All 1,396 practice attacks match the conversion event evidence. MusicXML 4.0
  XSD passes. The converter reproduces identical hashes.
- `node --test tests/piano-*.test.mjs`: 66/66 pass. Added actual XML/MXL indexing,
  source-byte preservation, deterministic catalogs, invalid-upload isolation,
  filename encoding, hash checks and deployed/GitHub fallback tests.
- `npm run build`: passes and generates the repository catalog before Vite.
- Updated integrated app helper passes 11 checks across five fresh page/module
  boots: actual Phoebe, both modes, native-upload link without a fake save, shared
  catalog additions, failed-refresh recovery, last selection and independent
  device, legacy ID collisions and migration, plus existing MIDI/audio controls.
- Migrated the genuine Bach MusicXML and MuseScore MXL from the earlier browser
  upload checks into the GitHub uploads directory. The normal build discovers
  both automatically; the shared dropdown contains four songs.
- The upload page requires GitHub sign-in and its Commit changes step. Opening
  the link alone never claims an upload succeeded. No page token or secret exists.
- Source release `072a8a1b0c5095300f9e447943a97a4c8f2ab617` is on main.
  Build/regression/publish run 44215057246 and Pages deployment 44215183143 both
  succeeded. Published catalog independently shows all four shared songs, zero
  import errors and the verified Phoebe score hash.
- Live browser shows build `072a8a1b0c50`, full Phoebe notation and 1,396 attacks.
  Wrong C4 leaves the first chord in place; C-sharp4 then C-sharp6 turn two heads
  green and advance. Continuous mode advances and marks missed notes red
  (49 misses/49 red heads observed). Sound remained off throughout QA.
- Refresh reports four songs saved on GitHub. Reload restores Phoebe and saved
  preferences. Older browser copies remain explicitly marked device-only for
  recovery. The opening score has no horizontal overflow at the tested width.
  The live tab is left on Phoebe, Wait for me, reset and ready to practice.
- Original-file GitHub writes were performed and verified through the authorized
  connector. The native upload destination is in the live UI; the browser did
  not simulate or claim an authenticated GitHub commit. Future uploads require
  the normal GitHub Commit changes step, then automatic publishing.

## Approved lesson cleanup — 2026-11-17

Scope: apply the user's confirmed eight-category clutter inventory to the existing
learning-songs page. Ultimate Guitar Chords v2 remains deferred while its chart is
unavailable. This task does not change score contents or grading behavior.

- [x] Remove slogans, decorative symbols, repeated headings, and excess spacing.
      Keep the song selector, upload formats, sheet music and functional controls.
- [x] Replace repeated playback/storage coaching with brief states and actionable
      errors. Move attribution and meaningful grading limits into collapsed details.
- [x] Hide only known test fixtures and duplicate local copies from the normal
      song selector; preserve source files and genuine device-only uploads.
- [x] Verify actual score rendering, both lesson modes, retained controls,
      remembered selection and failed-load recovery with silent checks.
- [x] Build, publish to the existing GitHub Pages URL, and verify live content.

Acceptance counterexamples: removed DOM elements must not break startup; a real
upload must remain available even when its title resembles a test; a remembered
hidden test must fall back to Phoebe; failed refresh/score load must preserve the
previous playable score. No audible playback during assistant QA.

Local verification:

- `node --test tests/piano-*.test.mjs`: 69/69 pass, including exact-content hiding,
  offline fixture filtering and preservation of genuine same-title uploads.
- `node tests/helpers/piano-app-check.mjs` with the existing render dependencies:
  15 checks across seven fresh app boots pass. Actual Phoebe chord waiting,
  timed colors, pause/restart, failed load/refresh recovery, remembered hidden
  test fallback and local-to-shared duplicate selection are covered silently.
- `npm run build`: passes. Four catalog records and original files remain;
  only Phoebe appears in the normal selector because three records are tests.
- Independent diff/DOM review passes. All 14 tracked score/provenance/original
  upload files match their preceding Git blob hashes. Parser, renderer, lesson
  engine, audio and upload parsing are unchanged.
- Source release `91a99a037db8d7de7d7a3bc776081ef315aa08e9` is on main.
  Build/test/publish run 44221357866 and Pages deployment 44221452110 both
  succeeded. Published branch commit: `1299245df651d013b274e941ee85196f565d10d9`.
- Live browser verified build `91a99a037db8`: actual Phoebe score renders, the
  selector contains only Phoebe (old device-only test copies are also hidden),
  concise mode names and functional controls remain, and Details opens to the
  arranger attribution and note-length grading limit. Page scroll/client widths
  both measure 1348px. Details is closed and playback is reset/ready with sound
  off. Screenshot captured after the cleanup. Mobile/hardware MIDI checks were
  not part of this presentation-only verification.

## Responsive score and song-range keyboard — 2026-11-17

User request: fit sheet music to screen width; show the keyboard from the song's
lowest to highest note; highlight notes during playback; provide Show/Hide with
the keyboard shown by default.

- [x] Remove fixed score/page width limits and verify actual engraving fits
  narrow and desktop widths, including resize with existing grades/cursor.
- [x] Draw the complete chromatic song range, including black-key endpoints and
  single-note scores; retain MIDI, touch and computer input.
- [x] Highlight sounding notes through their full durations (including ties and
  overlaps), and show current required pitches in wait mode.
- [x] Add an accessible Show/Hide control, shown by default, without changing
  playback or grading when the visual keyboard is hidden.
- [x] Run relevant renderer/application checks, build/publish, and inspect the
  live layout at desktop and narrow viewport widths silently.

Counterexamples: Phoebe's actual range has black endpoints (MIDI46–97); its first
low note sustains while the upper notes change. A narrow page must not clip bars,
and a hidden keyboard must not stop MIDI grading. Preserve all score source data.

Local verification:

- `node --test tests/piano-*.test.mjs`: 73/73 pass, including four new keyboard
  range/timing tests using both authored boundaries and the actual Phoebe score.
- Existing silent application helper: 17 checks across seven fresh boots pass.
  Full range/black endpoints, fixed display during input-octave changes,
  sustained lower notes with changing upper notes, pause/resume/restart, hidden
  MIDI practice and remembered visibility are exercised.
- Existing actual-renderer helper: full Phoebe score maps all 1,622 notation
  items at 390/320/280/1348px. SVG/head bounds, minimum non-overlapping measure
  widths, cursor/grade preservation and observer lifecycle pass. These helper
  sizes are engraving checks; live browser geometry is recorded separately.
- Initial integration assertion exposed CSSOM percentage rounding
  (97.9752% + 2.02482% = 100.00002%); the mathematical layout fits exactly.
  Corrected the CSS-string assertion to allow subpixel serialization rounding.
- `npm run build`: passed. Source release
  `ec67ab24a7e9f0065582e9e3ce5aa5ac02cb4b5b` is on main. Build/regression/publish
  run 44224777250 and Pages deployment 44224880944 both succeeded. Published
  branch commit: `32fffce8296ce7f04133eaf44b409f37debaee05`.
- Live browser verified build `ec67ab24a7e9`. At a 337px CSS viewport, score
  client/scroll widths both measure 307px (previous release scrolled to 590px).
  Page client/scroll widths both measure 337px. The keyboard has 52 keys spanning
  MIDI46–97 (A-sharp2 to C-sharp7), fits within 287px, and both black endpoints
  are fully inside its bounds. Narrow inspection used ordinary 400% browser
  zoom; this is viewport verification, not physical-phone testing.
- At normal zoom, page client/scroll widths both measure 1348px and score
  client/scroll widths both measure 1299px. The score uses the available width.
  Show/Hide updates visibility, button text and aria-expanded. Silent continuous
  playback lights C-sharp4/C-sharp6; pausing leaves zero playing highlights.
  Reset wait mode highlights the same first required pitches. Live screenshot
  captured; tab left ready, keyboard shown, Sound off, zoom restored to 100%.
- Independent review found no blocking issue; all 14 tracked score/provenance/
  original-upload files retain their prior contents. Physical MIDI hardware and
  listening acceptance were not exercised. No remaining blocker for this UI task.

## Compact two-row playing view — 2026-11-17

User request: show only the current and next sheet-music rows in a shallow
window, remove titles/legend/Details, put the keyboard directly underneath,
move MIDI/Show-Hide buttons below it, remove computer-key/range/octave controls,
and keep the complete playing interface on screen without scrolling.

- [x] Window the actual engraved current+next systems, advancing at row boundaries
  and showing only the final system at the end; remove printed titles/credits.
- [x] Fit notation to both available width and height while preserving complete
  staves, ledger notes, ties, cursor and individual grading colors.
- [x] Make the screen layout compact with a height budget, immediate score/keyboard
  adjacency, bottom MIDI/Show-Hide controls and no removed-UI remnants.
- [x] Preserve shared uploads/selection, both lesson modes, MIDI/touch grading,
  full song-range keyboard, sustained highlights and remembered visibility.
- [ ] Verify renderer/application behavior and realistic portrait/landscape
  geometry silently, build/publish and inspect the actual live release.

Counterexamples: a partial third system or clipped high ledger note does not
satisfy two rows; hiding overflow does not prove that bottom controls fit;
height-only resize and hiding the keyboard must refit the score; reset returns
the first pair; a failed replacement retains the previous playable score.
Root owns layout/integration, with separate renderer and application ownership
and independent scope review. Source notation and previous lessons stay intact.

Local verification:

- `node --test tests/piano-*.test.mjs`: 89/89 pass.
- Actual renderer helper passes with all 1,622 Phoebe notation items at widths
  390/320/280/1348 and a 300px height budget, plus 844px width/175px height.
  Every system boundary is visited: full current+next bounds, no previous/third
  row, final single row, restart, pitched heads/stem bounds and zero scrolling.
  Height-only resize 300→140 preserves beat 123 and hit/miss colors; source
  title/credits are absent. Existing failed-load/chord/tie/unison checks pass.
- Final application helper: 18 checks across seven fresh boots pass using actual
  OSMD and simulated MIDI/audio. Both real MIDI-handler input and timed playback
  move the actual Phoebe window from rows 1–2 to 2–3; restart restores 1–2.
  Score/document scroll offsets stay zero. Existing shared-library, recovery,
  both modes, sustained highlights, hidden-keyboard grading and preferences pass.
- `npm run build`, script syntax checks and `git diff --check` pass.
- Independent layout and renderer reviews found no blocker. Live cursor pixel
  bounds and actual viewport fit remain the final deployment checks.
- Live baseline at 1348×936: page height 1380px, score height 660px, keyboard
  bottom 1338.6px and MIDI button bottom 1159.6px, both beyond the viewport.
- First source release `0be815445271514212637e71cc7c3079cee45665` passed build/
  regression run 44228988973 and Pages deployment 44229086112, but the live
  renderer rejected its fit after eight passes. The actual 1345×300 score budget
  and whole-page layout fit correctly; the failure is in the browser SVG-bounds
  branch absent from jsdom. Do not treat that release as accepted. A temporary
  failure-only console diagnostic records native and browser bounds per pass
  to determine the mismatch before correcting it.
