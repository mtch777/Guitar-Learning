# API field coverage audit

- [x] Discover every nested field path in all98 captured metadata records and495 track responses, including arrays, false/null values and rare fields. Acceptance: recursive counts reconcile with fixtures; raw values are not published.
- [x] Map each observed path to analyzed, retained only, unsupported, or not applicable. Acceptance: partial consumption is explicit; unknown fields fail closed to retained/review-required; raw capture is never counted as analysis.
- [x] Produce a readable complete matrix and machine-readable aggregate plus private per-source coverage. Acceptance: all observed paths accounted for; source IDs/values remain private; analyzer code hash records the assessed implementation.
- [x] Test field discovery, denominator semantics, rare/unknown fields, partial bend/technique handling and privacy; run project Python tests and JS/build checks.
- [ ] Push verified code, tests, coverage and progress to origin/main; verify GitHub CI. No public website changes are planned.

2026-10-17: main5244d9a clean; safe pull already up to date. Read current handoff/context and source analyzer. Initial recursive discovery found218 distinct paths. Important distinctions to preserve: technique marker presence vs value interpretation; bend points.position is used while precisePosition/per-point vibrato are not; tempo/sound automation is hashed but not functionally modeled; whole-rest and repeat flags are not expanded.

## Reproduce and verification

```powershell
.\.local\songsterr-venv\Scripts\python.exe composition-lab/songsterr_automation/songsterr_api/audit_api_coverage.py composition-lab/local-artifacts/invent-animate-corpus-v1/songs --json composition-lab/songsterr_automation/results/api_field_coverage.json --markdown composition-lab/songsterr_automation/API_FIELD_COVERAGE.md --private composition-lab/local-artifacts/invent-animate-corpus-v1/api-field-coverage-by-source.json --strict
```

Strict mode writes the audit but exits2 when any observed field lacks a reviewed mapping. Unknown children do not inherit an analyzed parent's status. It inventories the captured responses, not all possible upstream API fields. One declared analyzer field, beat-level leftHandVibrato, was not observed in this corpus.

2026-10-17 evidence: all98 entries/98metadata/495track responses audited;218paths=65analyzed(at varying depth)+83retained_only+54unsupported+16not_applicable,0unmapped. Public/private coverage union, all denominators/type counts and assessed analyzer hash reconciled. Values and per-source identities remain only in ignored local artifacts. Analyzed includes containers, provenance and marker-only handling; it does not mean65fully interpreted musical parameters. New gap findings include unconsumed precise bend positions/per-point vibrato, brush mechanics, whammy curves, tempo/sound changes, repeat/rest/pickup semantics, vocal flags/revision consistency and raw marker-layout leakage. No analyzer behavior, source score or playback baseline was modified.

Tests: main venv `python -m unittest discover -s composition-lab -p 'test_*.py' -q`:190tests,189pass/1optional PyGuitarPro skip. Isolated corpus env `-p 'test_songsterr*.py'`:21pass, including optional serialization. Native Node tests16pass; direct Vite buildpass. Tests cover false/null/zero/empty arrays, nested parent denominators, distinct source counts, new child fields, parent-marker vs child-value distinction, hash-only fields, analyzer marker registry and public-value privacy. TEMP/TMP pointed to ignored .local/test-temp for Windows sandbox compatibility. No website changes; Pages deployment not applicable. Delivery/CI verification pending below.
