# Source-grounded corpus analysis

Scope: repeatable analysis of the captured notation, not new composition or a listening-quality claim.

- [x] Inventory provenance and availability. Acceptance: all captured revisions accounted for; AI/junk flags, exact-content duplicates and conservative candidate work families reported separately; no silent exclusions.
- [x] Preserve exact occurrence observations. Acceptance: rational written timing, track/voice/string/fret, ties, raw effects and section-instance identity; grace notes explicitly separated; malformed timing is reported rather than silently repaired.
- [x] Measure techniques at corpus/song/track/section scales. Acceptance: explicit numerators/denominators and conditional duration/register/metrical-position/co-occurrence views; no marker absence interpreted as performance absence.
- [x] Extract source-located identification examples and counterexamples. Acceptance: close dyads use exactly one semitone; power/extended-power definitions share the existing classifier; HOPO direction requires a contiguous same-string transition and remains a source-marker interpretation; pedal patterns remain candidates.
- [x] Verify deterministically. Acceptance: adversarial fixtures for ties, rests, grace, polyphony, changing meter, missing pitch, section instances and duplicate provenance; run full Python suite and JS tests/build; run the entire private corpus and reconcile counts.
- [ ] Deliver. Acceptance: private reports and occurrence evidence remain ignored; only code, tests and source-free aggregate evidence committed/pushed to main; remote CI verified. Document remaining interpretation/listening limits.

2026-10-17: main clean at 2b563b5; `git pull --ff-only origin main` already up to date. Read current handoff/context, raw-source analyzer, shared technique definitions, converter HP handling and CI. Existing acquisition preserved. No website changes planned.

2026-10-17 analysis execution: analyzer + evidence builder completed on98entries/495tracks;339385written guitar/bass segments and316030attacks reconciled with prior inventory.18candidate title families/42entries; no exact notation hashes duplicated.55voice/bar overflows/25tracks quarantined only from temporal candidates.88source-located cases/2904context-control occurrences read back against raw notes/beats. Read ANALYSIS_RESULTS.md for counts, denominator definitions and caveats. Main Python183tests (182pass/1optional skip); isolated corpus14pass; JS16pass; direct Vite buildpass. Private artifacts remain ignored. Awaiting push/remote CI before delivery acceptance is checked.
