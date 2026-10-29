# Time Solo playback progress

## Acceptance checklist

- [x] Upload the original complete `time.gp`/`time(4).gp` and derive measures 94–143 (inclusive) from the loaded score's playback lookup; keep the private source out of Git.
- [x] Play and Stop stay inside that passage; playback stops at its end.
- [x] The scrubber displays 0:00 through the solo duration and seeks within those bounds, including tempo changes.
- [x] Space toggles pause/resume without scrolling; Left/Right seek backward/forward within the solo, regardless of focus on player controls.
- [x] Other lessons and non-Time uploads retain their full-song behavior.
- [x] Run focused transport tests, JS tests, build, and a browser upload/playback check against the private original file.

## Evidence log

- 2026-10-29: Fresh clone at `fb8aeb8`. `npm ci` succeeded. Private `time(4).gp` matched Library `time.gp` byte-for-byte (SHA-256 `bd656f927c89b00fbc366b8659879d606937e4ff33fef60367023802c53aa89b`). Never commit either source.
- Parsed the private file with alphaTab 1.8.4: 209 master bars, 15 tracks, 960 ticks/quarter; bar 94 starts at tick 357120, bar 143 ends at tick 549120. Tempo changes exist, so the UI must convert ticks through the actual tempo map.
- Derived from the original score: start 179405 ms (~2:59), end 270385 ms (~4:30), duration 90979 ms (~1:31). User's 3:01/3:02 beginning is approximate; measure 94 has an immediate solo guitar attack, so retaining that measure avoids truncating the phrase.
- `node --test tests/*.test.mjs`: 26/26 passed; `npm run build`: passed. Focused transport test exercises Play/Stop, relative scrubber, Space, arrows, and tempo changes.
- Published source commit `832c61fd79650d39ec5c43371fdcba1d01e59894` on `main`; GitHub Pages workflow run `40916179333` succeeded. The browser loaded new `main-Cno8-O8K.js` and uploaded the original `time(4).gp` without publishing it. Solo guitar was selected; transport displayed `0:00 / 1:31`. Play advanced from 0:00; Space paused/resumed from focused button and slider; Right advanced about five seconds, Left reversed about five seconds; halfway scrub showed `0:45`; end scrub showed `1:31`; Play from end returned to `0:00`; Stop returned to `0:00`.

## Next action

2026-10-29 speed-regression follow-up:

- [x] Reproduce user sequence on the published site: upload `time(4).gp`, select 0.75× before Play. The UI jumped from `0:00` to `1:00` before playback because alphaTab scales its millisecond position on speed changes.
- [x] Use score ticks for solo-relative display and seeks; add the inverse tempo-map conversion. Do not reapply an unchanged speed at Play.
- [x] Test changed speed before and during Play, keyboard seeking, tempo change conversion, and other lesson fallback. All 26 JS tests and Vite build passed. Original private file: start/mid/end tick-to-time conversions match within rounding.
- [ ] Publish fix and verify both speed-change orders, playback notes, scrubber, and keyboard controls live with the original file.

Next: publish the bounded fix and complete the live regression check. Keep the private GP file outside Git.
