# Musical iteration after the October 27 status review

User authorization: iterate autonomously with ProjectPlanner3000 on the path
to meaningful, reversible musical creation. No request to restart schedules.
Starting HEAD: 77ba3c8; origin/main matches. Unrelated WIP and private baselines
are preserved. Previous negative voicing trials remain recorded, not replaced.

## Acceptance checklist

- [x] Read handoff/context/current code and previous failed real-song proposals.
- [x] Planner START: choose a musical relationship improvement, with explicit
  evidence, inverse ownership, locks and refusal conditions before implementation.
- [x] Remove the known pick-scrape ownership blockage without calling a scrape
  an ordinary pitched note or claiming its acoustic execution is understood.
  Accept: exact typed declaration recovery; malformed shapes refused; contextual
  pitch/voicing claims involving scrapes remain excluded; approved detectors unchanged.
- [x] Implement the agreed musical relationship and contrast tests. No song IDs,
  manually chosen pitches, forced changes or separate inverse/generator.
- [x] Planner MID: inspect actual evidence and challenge missing dependencies.
- [x] Run existing frozen songs as development regressions; retain every refusal.
- [x] Freeze a new random Songsterr capture before analysis and run unchanged code.
- [ ] Gate 2: isolated pair/composed reversal, complete independent source check,
  zero locks and actual nonzero inverse where an admissible alternative exists.
- [ ] Gate 3: meaningful relationships, contradictions/ambiguity and source-backed
  choices independently checked; no musical-quality claim from serialization.
- [ ] If an actual admitted pitch change exists, export/reopen/render and verify
  unchanged dimensions. Do not manufacture a demo from an unchanged output.
- [ ] Planner END, relevant full regressions, explicit remaining limits and delivery.

## Decisions and evidence

Previous exact physical-string paths are evidence of written fingerboard motion,
not established musical voices. Whether their exact witness requirement is the
right musical abstraction must be investigated, not silently removed for success.
Any changed scope is named and independently tested. Musical preference and
human listening acceptance remain separate from formal feasibility.

Commands/results/next action will be recorded below as work completes.

## Agreed START scope: coordinated source voicing sequences

Planner rejected relaxing physical-string witness requirements. Instead, a named
`source_gesture_context` choice edits multiple consecutive coattack groups at once.
Discovery enumerates maximal matching pitch-class/rhythm/meter runs, including
all source groups so a refused event cannot be skipped. Target and donor runs
must be disjoint; no fixed musical excerpt length is chosen. A declared computation
limit refuses exhaustive runs rather than silently truncating the population.

Each group retains its own original bass anchor, occurrence PCs/multiplicities,
duration, meter, expression and execution pins. Only observed spacing definitions
and their source-supported strings are released jointly. ALL before/after incident
paths use the SAME witness predicate and one union of excluded source neighbors.
Old policies and their failed results stay unchanged. This is a local sequence
operation, not accepted phrase recognition or an artist-preference model.

Atomic `choose_many` uses the ORIGINAL definition pool and prunes once after all
assignments. This prevents order-dependent loss when choices exchange definitions.
Actual inverse results must preserve approved pedal outputs and coattack classes.
The worker bundles the unchanged detector functions so this guard is enforced
inside the source-denied run as well.

Initial checks: 38 focused coverage/context tests passed. A subsequent 46-test
regression passed after the atomic ownership refactor. Controlled sequence test
proves BOTH individual changes refuse while their coordinated version has
independent source path witnesses. Isolated zero/nonzero reconstruction passes.
These authored examples test logic; they are not real-song musical acceptance.

Pick-scrape ownership is now a typed string declaration, reversible without
assuming an acoustic pitch trajectory. Malformed types/structures still refuse.
Musical role and voicing checks explicitly quarantine scrape sounding pitch.
Approved detector code and GP exporter are untouched.

## Frozen real-song iteration 1

Private evidence: `local-artifacts/musical-iteration-v1`. A 483-file Python source
archive and hashes were frozen before the new draw. Seed3732629407114133657,
155 previously observed IDs excluded; existing alphabet/first100 public-search
sampling selected Pride And Joy, song240/revision7989414, four tracks. This is
one new draw, not uniform catalog sampling. No rejected song was replaced.

| Capture | Use | Note occurrences / typed facts recovered exactly | Candidate runs | Admitted distinct realizations | Pitch changes |
|---|---|---:|---:|---:|---:|
| Over The Hills And Far Away | Fixed development replay | 9,713 / 82,140 | 366 | 341 | 0 |
| Wasted Years | Fixed development replay | 9,023 / 80,080 | 492 | 432 | 0 |
| Zero | Prior failed capture, coverage repair replay | 4,758 / 43,443 | 44 | 40 | 0 |
| Pride And Joy | New random capture | 4,526 / 42,139 | 96 | 88 | 0 |

All 901 admitted realizations reproduce the existing voicing. All 4,888 supporting
source-run links remain in the ledger. The complete maximal-run population was
checked by Planner's independent diagonal enumeration against raw-derived units.
No changed choice was admitted, so no real-song nonzero worker or audio render
was presented as successful. `ALL-draws.json` is empty on those runs; the 0/50/100
empirical draw tests passed on controlled examples, not these real songs.

Gate1 passes on the new capture within declared coverage. Gate2 passes for actual
isolated pair and composed zero reconstruction, independently compared to ALL
captured JSON facts (28,020 occurrences / 247,802 facts across four runs). The
worker is reviewed Python with an audit boundary, not an OS security sandbox.
Gate3 verifies the stated recurrence/spacing relationships and controlled positive
and negative contrasts. Musical usefulness, real nonzero creation and artist fit
remain UNPROVEN; do not report full Tier2 or lever acceptance.

Observed refusals: impossible translated frets, changed open-string behavior,
unresolved overlapping execution, tie/let-ring/brush dependencies, missing
independent entrance/interior/exit motion, and overlapping source runs. Counts
overlap; they are not independent percentages or all necessarily root causes.

Actual commands:
- `.venv/Scripts/python.exe -m unittest discover -s composition-lab -p 'test_*.py'`
  -> 1,162 run, 1,161 passed, one optional skip, 66.638 seconds.
- `run_voicing_gesture_qa.py <capture> <new-output> <freeze.json>` for each row
  -> four `PASS_BOUNDED_GESTURE_QA`, zero `SUPPORTED_PITCH_CHANGE`.
- Node `--test tests/*.test.mjs composition-lab/test_source_inspector.mjs
  composition-lab/songsterr_automation/songsterr_api/test_restore_dead_ties.mjs
  composition-lab/songsterr_automation/songsterr_api/test_bend_fidelity.mjs`
  -> 43 passed. Node `node_modules/vite/bin/vite.js build` -> passed.

Early invocation errors (wrong working-directory Python path, nonexistent test
module name, and a legacy list-shaped selection manifest) were corrected before
the successful commands above. The first freeze attempt did not create a freeze
or select a song; the subsequent immutable freeze is the one used for every run.

Next action: independent Planner outcome audit and a causal test of the failed
real-song candidates. Do not repeat negative studies blindly, weaken locks to
manufacture an audio example, or promote this local operation into a phrase tier.
