# Source-grounded technique corpus

Current task: acquire every CSV-listed tab privately as reconstructed GP7, then test technique identification/relationships on actual source material. No authored 3/5-note pedal rules stand in for corpus evidence.

- [x] Parse all CSV entries, retain row/URL/selected-track provenance; deduplicate only identical Songsterr IDs. Alternate versions and AI/collaboration labels remain distinct.
- [x] Download current revision metadata and every track's notation; retain raw JSON, revision IDs, converter commit and warnings privately. Every row must resolve to a verified file or an explicit failure.
- [x] Reconstruct `.gp` files with all strings/tracks; independently reimport and compare note/timing/technique fields. GP5 alone cannot encode eight-string notes; validate the temporary split/merge bridge before batch use.
- [ ] Audit source-to-GP fidelity, especially HOPO, vibrato, bends, ties, dyads and exact rhythm. Distinguish unsupported notation/conversion losses from genuine absence.
- [x] Run existing scripted technique analysis; retain song/track/section occurrence evidence and corpus denominators. Candidate patterns are not validated musical functions.
- [ ] Build source-grounded identification examples and controlled transfer tests: exact recreation first, then changed context, then constrained novelty using measured source relationships. No claim of preserving feel without listening evidence.
- [x] Commit code, tests and source-free aggregate evidence; keep scores/raw notation/CSV/private annotations outside Git. Verify CI, preserve baselines.

Preflight: main pulled to 8700931. Read current usage guide, downloader/exporter and source validators. CSV has 98 entries. Upstream converter pinned locally to a5e6ec76bd30bb626f4381bb78baef7e20ec2c21 (songsterr-dl1.2.0), Python3.13.16 installed in ignored workspace environment. First song1627918 downloaded but GP5 write failed `negative shift count` for string8; invalid probe file is retained privately and is not accepted as a score.


2026-10-17 completion of acquisition: read CORPUS_RESULTS.md. 98/98 source captures and GP7 files; 495 tracks; all98 reopen in unmodified alphaTab. Tested roundtrip fields pass74/98;24 remain flagged. All98 regular written-pitch/string/duration/tuning checks report zero differences under their documented scope. Serialized-source comparator489pass/4differences/2errors. Raw source inventory completed for98 entries/415 guitar-bass tracks; this is a first inventory, not validated technique-function classification. Examples and feel-preserving recreation gates remain open.

Interruption/resume: earlier automatic approval review hit a usage limit after56 attempts/54 completed captures and rejected the restart before execution. User's next-turn status request resumed the authorized task once execution was available. Cached data preserved. Encoding/comparator/importer defects were diagnosed and retried; final98 captures succeeded. No private scores/raw notation/CSV/annotations are staged.

Commands/results and reproduction are in CORPUS_RESULTS.md. Full local suite172tests (171pass/1optional skip); isolated Python3.13 converter tests3/3pass. Source-free aggregate csv_corpus_acquisition.json. Pending: push verified code/evidence and confirm CI, then source-grounded identification/transfer gates above.

Delivery: c0621ec pushed; CI39045738118 successful. All98 files rechecked using reusable unmodified-reader CLI. Main JS tests16pass/buildpass. Source-grounded identification/feel gates remain pending, not silently marked complete.

2026-10-17: expanded raw-source relational analysis and88traceable evidence cases completed; read ANALYSIS_RESULTS.md/ANALYSIS_PROGRESS.md. This satisfies the scripted-analysis gate; musical-function adjudication, conversion-loss repair, controlled transfer and listening acceptance are not marked complete.
