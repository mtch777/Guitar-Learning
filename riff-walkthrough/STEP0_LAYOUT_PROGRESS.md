# Step 0 and generation layout

- [x] Central stage parameters/weights under Step 0, generation outputs free of parameter controls.
- [x] Auto-open newest running/completed/blocked step; manual idle expansion retained.
- [x] Each collapsed header retains honest progress: unknown running is indeterminate, real phrase counts use fractions, errors/blocked never completion.
- [x] Scroll on stage/status/version transitions only, not every poll.
- [x] Preserve input validation and draft vs applied status.
- [x] Playback restoration integration hooks prepared.
- [ ] Merge playback agent Review/Kontakt settings helpers and selective regeneration focus.
- [ ] Integrated QA and user-device visual verification.

Verified all eight frontend suites on isolated worktree, 2026-11-14. No deployment or service changes. Stage 6 copies stage 5 music and validates export; initial note/timing output is the same, but Review edits may diverge.
