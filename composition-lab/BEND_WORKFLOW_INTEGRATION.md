# Routine bend-companion integration — 2026-10-18

Acceptance checklist:
- [x] New corpus exports create matching GP and exact-model-bend companion by default.
- [x] Catalog copies carry companions beside renamed GP files and verify matching bytes.
- [x] Passage rendering discovers adjacent companions without per-job wiring.
- [x] Mismatched companions fail instead of silently falling back to lossy playback.
- [x] Verify default export → renamed catalog copy → automatic renderer on a real copied score.
- [x] Run regression tests and independent QA.
- [x] Commit/push and verify remote CI.

Existing native exports and baselines are never silently regenerated. Upgrade a
private copy with `--recheck`. Explicit `--native-bends-only` retains native-only
export; renderer jobs may use `exact_model_bends:false` for native comparisons.
The former `--exact-model-bends` flag remains compatible but is no longer needed.
Already exported valid pairs can resume without changing either file. Native GP
roundtrip failures remain failures; companions preserve pre-export model curves,
not missing raw API precision or standalone native Guitar Pro playback fidelity.

## Verified results

- Full copied corpus:98GP+companion exports,866restored model curves;98renamed
  catalog pairs;98native-reader successes;98regular-source comparisons with zero
  differences. Original98GP hashes unchanged.
- Native detailed roundtrip remains74/98, with zero regressions against the old
  baseline. QA caught a temporary loss of the existing native simplification
  step; exact capture now occurs before that step, and original curve arrays
  are restored after native serialization. This preserves both paths.
- Real copied-score automatic passage render restored3curves without a job
  override. Synthetic automatic full-instrument render restored1curve. Both
  produced finite, nonzero, unclipped audio; no listening judgment inferred.
- Safe resume revalidates existing pairs. Native-only re-export refuses an
  existing companion before writing, avoiding stale pairs. Catalog mismatches
  preserve existing files; present bad companions never silently fall back.
- Local regression:415Python tests run,414passed/1optional skip;39JS tests pass;
  Vite build passes. Independent QABot review found no remaining blocker in the
  scoped workflow. Implementation hashes/counts: results/bend_workflow_integration.json.

The ready private working corpus is `local-artifacts/bend-routine-corpus-v1/`;
its `gp-files/` contains named GP+companion pairs and catalog.csv records both
paths. Original `invent-animate-corpus-v1` and earlier review outputs are intact.
This completes routine integration. Further standalone-native bend repair stays
parked; no new human feedback gate is introduced.

Delivery: `ce1f2d6` pushed to main; GitHub Actions
[39194995638](https://github.com/mtch777/Guitar-Learning/actions/runs/39194995638)
succeeded, including pinned alphaTab tests. No website files changed.
