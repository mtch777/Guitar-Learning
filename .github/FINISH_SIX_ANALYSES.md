# Six-song recovery and usable tiered corpus — complete

## Verified result (2026-11-03 UTC)
All 308 frozen Songsterr catalog entries have a successful full analysis, and all 308 selected encrypted archives have now been downloaded, decrypted and indexed locally. The previous 302 successful analyses were preserved without rerunning them.

- Invent Animate: 72 / 72
- Currents: 103 / 103
- ERRA: 133 / 133
- Encrypted archives: 9,039,346,749 bytes; every selected ZIP size and SHA-256 matched GitHub release metadata.
- Extracted payloads: 236,482,951,749 bytes.
- Every recovered entry passed source-identity consistency and contains original status=verified and qa.status=pass.
- Final index: 308 exact frozen IDs; 1,856 local links checked; no missing or blocked entries.

## Acceptance checklist
- [x] Previous-expanded-boundary correction and collision regressions committed at b179d67723874fd67fc0dfece535906d710cb715.
- [x] Real repository regression tests: 36 pass on a complete pinned source snapshot; the recovery workflow also passed the same tests.
- [x] Full build_tiered_song.py AND verify_tiered_song.py for exactly the six remaining IDs.
- [x] All six complete verified outputs, preserved source revisions, encrypted uploads and matching sizes/SHA-256.
- [x] Zero Actions artifacts in the recovery run.
- [x] Original key supplied locally; derived public key matched the original certificate; actual CMS decryption succeeded. No key contents published.
- [x] All 308 original selected archives downloaded and locally hash checked.
- [x] All 308 decrypted outputs, saved QA/status receipts and identities inspected.
- [x] Tested local recovery tooling and usable HTML/JSON/CSV corpus index delivered.
- [x] Temporary transfer links replaced by receipts; transfer helpers made manual-only; zero transfer/cleanup Actions artifacts.

## Production evidence
Full recovery run: https://github.com/mtch777/Guitar-Learning/actions/runs/41564106311
Analysis commit: 90cdd87771ee4bc1a7a45b42c3bc69ea17d4a7d8 (production code unchanged from the tested fix).
Draft result release: https://github.com/mtch777/Guitar-Learning/releases/tag/untagged-31adfd0f72e1ff5c2b73

| Songsterr ID | Captured revision | Build / verifier / final status |
|---|---:|---|
| 1817932 | 9885745 | completed / pass / verified |
| 993568 | 1320385 | completed / pass / verified |
| 1511882 | 4540687 | completed / pass / verified |
| 6028811 | 8322146 | completed / pass / verified |
| 4248474 | 5561199 | completed / pass / verified |
| 3165226 | 4189601 | completed / pass / verified |

The selected corpus is 296 original successes + 6 corrected-identity successes + these 6 recovered successes. Earlier failed and diagnosis-only outputs remain historical evidence and are not selected.

## Local delivery
Private, Git-ignored root:
`G:\Chat GPT\Guitar-Learning\composition-lab\local-artifacts\corpus-recovery-2026-11-02\`

- `INDEX.html`: searchable artist/song index with links to actual files.
- `CORPUS_INDEX.json` and `CORPUS_INDEX.csv`: machine-readable registry.
- `encrypted/`: 308 unchanged original ZIPs.
- `readable/<song_id>/`: recovery receipt and complete decrypted payload.
- Each payload includes `tiered/song.tiered.json`, `tiered/existing-outputs.json`, `tiered/qa.json`, source capture and status.
- `tools/`: tested download, recovery and index utilities; local dependencies only.
- `transfer-closure.json`: private-link cleanup receipt.

Independent delivery audit:
`C:\Users\User\.codex\visualizations\2026\10\30\01a18abb-8452-7f31-814f-a897fa831f1d\riff-research\recovery-six-2026-11-02\delivery-audit.json`

## Verification scope
This is recovery of the existing source-preserving tiered analyses, not new creative-tier completion or a listening judgment. The technical JSON schema layers must not be confused with creative T0–T6 exit gates.

Archive checks included trusted ZIP hashes, CMS decryption, gzip integrity, safe extraction, payload file hashes, identity checks and actual QA/status parsing. Large JSON from already hash-matched archives was not needlessly reparsed; those 551 files are explicitly marked `not_reparsed_trusted_archive`. Another 2,792 JSON files were syntax-validated. The saved analysis QA was inspected, not rerun locally.

All source archives and the original certificate are preserved. No private key or decrypted notation was published.
