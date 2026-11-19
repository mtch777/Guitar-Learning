# MuseScore URL → piano lesson import

Acceptance target: after one-time browser helper installation, paste a MuseScore score URL into the lesson and press Import once; automatically return with the score queued, convert its MIDI into MusicXML, publish both, and select the new song without another tap.

- [x] The lesson starts an auto-import from a valid MuseScore URL, with no bookmarklet or manual tab switch (implemented and unit-tested).
- [x] The browser helper detects signed MIDI links from `performance`, `fetch`, or XHR and returns automatically (mocked browser-session tests passed).
- [x] The fine-grained token with **Contents: write** dispatches conversion; no Actions permission is needed for the tablet (GitHub's documented `repository_dispatch` permission).
- [x] GitHub workflow saves MIDI and MusicXML, writes a per-import receipt, and explicitly dispatches the Pages deploy; the lesson polls and selects by receipt (implemented; live run not yet verified).
- [x] Focused JS tests, conversion smoke test with `music21==9.9.1`, and `npm run build` passed.
- [ ] Real MuseScore URL → complete live Pages import is verified on a compatible Android browser. Do not mark this done from synthetic tests.

Local evidence: `node --test tests/piano-midi-import.test.mjs tests/piano-musescore-helper.test.mjs` (12/12 pass); `python scripts/piano/import-midi-url.py --file tests/fixtures/piano-midi-import-smoke.mid --title 'One click smoke score' --library <temp>` (pass, MusicXML includes title); `npm run build` (pass). Full-repo tests fail due unrelated missing historical generated fixtures in this checkout. Local Chromium end-to-end test could not start because the executor denies the browser process its Unix socket.

Remaining: real GitHub workflow execution plus end-to-end testing in an Android browser with the helper installed. Native Android Chrome cannot install userscripts. The UI recommends Quetta (a Chromium-based Android browser with extension support) plus Violentmonkey; verify that its Web MIDI input works before replacing the current Chrome practice setup. Firefox for Android supports add-ons but Web MIDI compatibility is unreliable. Do not claim a live Android test without one.
