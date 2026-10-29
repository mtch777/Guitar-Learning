# Time Solo playback progress

## Acceptance checklist

- [x] Upload the original complete `time.gp`/`time(4).gp` and derive measures 94–143 (inclusive) from the loaded score's playback lookup; keep the private source out of Git.
- [x] Play and Stop stay inside that passage; playback stops at its end.
- [x] The scrubber displays 0:00 through the solo duration and seeks within those bounds, including tempo changes.
- [x] Space toggles pause/resume without scrolling; Left/Right seek backward/forward within the solo, regardless of focus on player controls.
- [x] Other lessons and non-Time uploads retain their full-song behavior.
- [ ] Run focused transport tests, JS tests, build, and a browser upload/playback check against the private original file.

## Evidence log

- 2026-10-29: Fresh clone at `fb8aeb8`. `npm ci` succeeded. Private `time(4).gp` matched Library `time.gp` byte-for-byte (SHA-256 `bd656f927c89b00fbc366b8659879d606937e4ff33fef60367023802c53aa89b`). Never commit either source.
- Parsed the private file with alphaTab 1.8.4: 209 master bars, 15 tracks, 960 ticks/quarter; bar 94 starts at tick 357120, bar 143 ends at tick 549120. Tempo changes exist, so the UI must convert ticks through the actual tempo map.
- Derived from the original score: start 179405 ms (~2:59), end 270385 ms (~4:30), duration 90979 ms (~1:31). User's 3:01/3:02 beginning is approximate; measure 94 has an immediate solo guitar attack, so retaining that measure avoids truncating the phrase.
- `node --test tests/*.test.mjs`: 26/26 passed; `npm run build`: passed. Focused transport test exercises Play/Stop, relative scrubber, Space, arrows, and tempo changes.

## Next action

Publish source changes, then perform the browser upload/playback check. The private GP file must stay outside Git.
