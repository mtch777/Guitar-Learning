# Analysis repair pass 2 — 2026-10-18

Continue the remaining slide, bend, unpitched-tie and local-timing gaps from
ANALYSIS_UNBLOCK_RESULTS.md. Source scores, prior outputs, private annotations
and approved pedal algorithms remain unchanged.

## Acceptance checklist

- [x] Slides: explicit type-specific endpoints and unresolved reasons, exact
  voice/string/time identity, grace/tie/rest/dead/same-fret negative tests.
- [x] Slides: actual corpus counts and independent reader link comparison.
- [x] Ties: distinguish explicit unpitched continuity from pitched sounding
  sustain; never automatically join dead-to-pitched transitions.
- [x] Timing: expose safe local regions without trimming source notes or
  allowing relationships to cross invalid timing boundaries.
- [x] Bends: opt-in exact model-curve preservation with hash/identity-bound
  sidecar and independently reopened MIDI comparison; no global upstream patch.
- [x] Bends: explicit warning that native GP bytes alone remain lossy and that
  preserving a supplied model does not prove fidelity to every raw API curve.
- [x] Integrate additions without changing accepted existing detections.
- [x] Relevant tests, JS tests/build and independent QABot review.
- [x] Commit/push verified changes to main and confirm GitHub CI.

Three authorized agents own independent helpers: slides, bends, and tie/timing
semantics. Parent owns analysis integration and delivery. Existing unrelated
uncommitted composition work is preserved and excluded from this delivery.

## Results

| Requirement | Observed result | Remaining boundary |
|---|---|---|
| Slide endpoints | 2,553 clear written targets independently match native reader 2,553/2,553. Typed records include exact transition time, direction, written interval and source IDs. | 110 grace origins,106 tied origins,24 dead/unknown pitches,17 gap/overlaps,4 same-fret events and1 tied-continuation target remain explicit exceptions.78 entry and166 exit gestures intentionally lack one pitch. |
| Unpitched ties | 18 exact dead-to-dead written links classified inside safe regions. | Three dead-to-pitched transitions unresolved; old sounding chains/warnings unchanged. |
| Timing containment | 610/626 bars in four timing-excluded guitar tracks fit conservative all-voice safe regions.12 bad bars plus4 following intrusion bars excluded.974 additional local coattack groups pass independent pitch-set and boundary checks. | Additional local output is separate from global detector fields; artist fitting does not silently consume recovered regions. |
| Model bend preservation | 98/98 bridge models accepted,866 curves across63 entries restored. Nine synthetic tests preserve curves and note-bend MIDI; three real streams match1,126/666/6,531 events. | Native GP alone remains lossy; API precision already lost before model creation is not recovered; whammy/full-song MIDI fidelity not claimed. |
| Practical playback path | Opt-in exporter writes GP+sidecar; passage renderer explicitly loads matching pair. Real copied-score integration restores3curves; direct source differences0. Native and restored one-bar audio are finite, nonzero, unclipped and hash-different. | This is engineering playback evidence, not listening acceptance or native Guitar Pro certification. |

Existing source records, source files and frozen reports remain untouched. New
track output is `relationship_details`; accepted coattack/HOPO/pedal fields and
global timing eligibility retain their original behavior. The fast full-corpus
audit is `songsterr_api/analyze_remaining_gaps.py`; its aggregate output is
`songsterr_automation/results/analysis_repair_pass2.json`. Private source IDs,
curves, audio, rendered scores and sidecars stay in local-artifacts.

## Commands

```powershell
.venv/Scripts/python.exe -m unittest discover -s composition-lab -p 'test_*.py'
node --test tests/*.test.mjs composition-lab/songsterr_automation/songsterr_api/test_restore_dead_ties.mjs composition-lab/songsterr_automation/songsterr_api/test_bend_fidelity.mjs
node node_modules/vite/bin/vite.js build
.venv/Scripts/python.exe composition-lab/songsterr_automation/songsterr_api/analyze_remaining_gaps.py composition-lab/local-artifacts/invent-animate-corpus-v1/songs --out composition-lab/local-artifacts/analysis-repair-pass2.json --aggregate composition-lab/songsterr_automation/results/analysis_repair_pass2.json
```

Local result:412 Python tests run,411passed/1optional skip;37JS tests passed;
Vite build passed. Full-corpus additive audit covers98entries/495tracks,
413guitar/bass tracks; zero failed checks. Native endpoint comparisons and model
bend corpus evidence are independently generated private probe artifacts, not
inferred from passing unit tests. CI additionally installs pinned alphaTab1.8.4
and exercises the source-free bend integration tests.

QA found and corrected one preservation hazard: exact-bend export refusal used
to replace an existing validation report with an error. The refusal now happens
before report mutation. An end-to-end source-free subprocess test verifies the
existing GP, sidecar and report remain byte-identical on refusal. A timing-gate
test also covers an unsafe slide target beyond a tied continuation; all endpoint
and interval claims are cleared while the candidate identity stays inspectable.

Delivery: implementation commit `0f7886a` pushed to main. GitHub Actions run
[39193193897](https://github.com/mtch777/Guitar-Learning/actions/runs/39193193897)
succeeded, including pinned alphaTab installation and the actual bend-adapter
tests. No website files changed; no Pages deployment was required. Current
remaining limits are the explicit exceptions above, not silently repaired source.
