# Critique / fix ledger

1. Requirements review: accepted with explicit mixed-audio labels, actual donor/reference identity, downstream draft application, phone reachability as a delivery requirement, and server safety requirements. Added all clarifications.
2. Seed/scaffold code review: source carry-in notes were being retriggered and source timing failures could masquerade as silent reference audio. Fixed preview to deduplicate actual source occurrence IDs, refuse unsupported starting holds or incomplete timing, and expose precise unavailable reason. Full note tails retained.
3. Server contract review: previous result lacked applied settings. Added previous applied snapshots; do not replace useful prior result with an empty error. Six independent session tests pass.
4. MIDI review: removed rotating channels; one riff instrument channel with exact note events. Independent MIDI tests pass. Overlapping same-pitch receiver interpretation remains a real MIDI limitation, not silently altered.
5. Rhythm integration: independent full-corpus parity test of both methods matches original engine exactly. Upstream objects and repeat timings preserved.
6. Frontend review: fixed blocked prerequisites, strict export gating, initial dataset-loading retry, deeply nested draft comparisons, upper-stage draft isolation, audio unavailable reason, actual reference boundaries, and stopped-state stale controls.
7. Opening pitch stage: full-corpus run preserves rhythm bytes and all earlier results; no initial tonal restriction or transposition. Independent critique pending.

Browser testing and phone access remain open until actual deployment verification. No perfect/readiness claim.
8. Remaining pitches review: removed no engine behavior; adapter uses the already chosen rhythm at every phrase, independently checked every slot, exact repeats and first pitches. Full 11-phrase runs succeeded before and after pitch regeneration.
9. Cascade review: actual regenerate steps 2, 3, 4 and 5 preserve all upstream stage results. Eight fixed random trials: seven completed; one retained five pitched phrases and explicitly stopped on phrase-six carry-in mapping. No failures resampled.
10. Blocker review: replayed an actual previously chosen chromatic opener; the unchanged strict scale policy stops clearly with its notes intact. Complete-to-blocked real rerun retains previous full audio but provides no stale current MIDI.
11. Frontend density review: collapsed complete phrase lists, no top-N limit, explicit scaffold repeat links, compact identities, rounded similarity, and real completed/total phrase progress. Kept audio and Generate nearby.
12. Race review: added refresh sequence/mutation epoch/version checks; delayed pre-generation response and same-version response ordering tests pass.
13. HTTP/API review: same-browser cookie identity, cross-origin rejection, fixed static routes, no raw engine state leakage, and stale MIDI version rejection verified in-process. No public filesystem endpoint.
14. Deployment review: Windows Library helper cannot apply xattrs and removes temporary ZIP. Public Git source push was denied for missing explicit publication approval; no bypass attempted. Testing supported native private Library download next. Browser/phone QA is still pending.
15. Native download route review: desktop has no enabled signed-in browser session. No fallback credential extraction, public push retry or security setting changes. Final delivery is source archive plus explicit deployment blocker, not a claimed live site.

16. Recovery/publication: direct user approval obtained for source-only branch. Recovered exact v3 Library archive after cloud rollback; verified hash. Same Git push passed review but lacked local authentication. Supported authenticated GitHub publication completed and Git fetch/diff confirmed exact source parity. Fresh app 10 tests and frontend scheduler/race/unit checks pass. Desktop deployment and independent browser critique resumed.
