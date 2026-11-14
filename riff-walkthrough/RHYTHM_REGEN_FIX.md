# Selective rhythm regeneration fix

## Cause
The weighted lookup admitted donor phrases with exactly the current note timing, then reported a new revision even for an audible no-op. In the reported saved example, 241 of 255 shape-compatible donors used the current timing (count share, not weighted probability).

## Change
- Exclude exact current start/end timing (rational, order-independent, includes simultaneous event multiplicity), not merely donor identity.
- Exclude out-of-window or carry-in candidates before drawing.
- Preserve weights among viable alternatives, ordered pitch groups, linked repeats, and untouched phrases.
- If no distinct rhythm fits, report that explicitly without committing a revision.
- Existing strict scale and carry-in edit restrictions remain unchanged.

## Verification
- [x] 61 Python tests passed (including Review-copy and cookie isolation).
- [x] Six frontend suites passed; private-artifact visual fixture test skipped because absent.
- [x] Twelve consecutive edits of a private copy of the reported snapshot each changed timing while preserving pitches and unselected phrases.
- [x] Isolated HTTP open/plan/regenerate and companion recreation retained exact revision/output.
- [x] Separate latest Review-copy service imported the captured output exactly; test edit changed MIDI and rendered through Kontakt silently.
- [ ] Physical Android/browser visual testing not performed.

## Safe activation
The original generator and companion are intentionally not restarted. Companion restart would preserve saved editor data but invalidate in-memory Kontakt render-job URLs. `app/review_fork.py` runs a separate Review-only copy with isolated cookie/storage; earlier generation is rejected because saved public snapshots omit internal upstream data. It accepts a saved editor workspace, separate MIDI repository, and port. The launcher defaults to a distinct riff_review_fix_session cookie and rejects the known original cookie names before imports. No original session calls/writes are performed. Localhost-only binding by default. LAN exposure requires authorization.

The original existing service remains unfixed until an approved safe reload. Source publication does not imply it has changed.
