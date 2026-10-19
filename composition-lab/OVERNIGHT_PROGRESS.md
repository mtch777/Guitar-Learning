# Overnight development — steps 3–8

Session: 2026-10-18 evening America/Denver; user extended end to NOON
2026-10-19 Denver (18:00 UTC). Maximum autonomous progress without feedback.
Do not reopen steps1–2, approved pedals or parked standalone bend research.

## Continuation

App heartbeat `composition-lab-overnight-development` is ACTIVE: continuation
attempt every15minutes until the cutoff above. This is the app
scheduler, not a separately provisioned external service. Delivery/retry through
usage exhaustion is not guaranteed. Keep the local computer/app available.

Three initial agent dispatches failed with an account usage-limit error.
No overnight implementation from those dispatches is claimed. Their task scopes
below are the next concrete work when execution becomes available. Do not change
billing, expose credentials or try to bypass usage restrictions.
User subsequently confirmed limits reset; all three assignments were re-dispatched.

## Priority and acceptance

Latest user steering: spend MOST effort on artist profiles. Connect observations
into supported relationships and sequences across songs, sections/local regions
and tracks. Generation work is a test bed for those profiles, not the main time
sink. Use existing accepted data; this does not authorize reopening analysis2.

| Order | Step | Deliverable / acceptance |
|---|---|---|
| 1 | 3. Artist profiles | Build connected profiles: conditional technique/rhythm/register/harmony relationships, transitions, call/response, repetition/variation and track interactions where measured data supports them. Include song/family/section/local-region variation, support, missingness and uncertainty. Validate held-out families against simpler profiles. Rank generation gaps without confusing marginal counts or heuristic roles with artist style. |
| 2 | 4. Generation methods | Test small source-conditioned alternatives for the largest supported gaps, starting palm-mute/open-HOPO placement. Preserve defaults and baselines; no fixed artist rates or copied riffs. |
| 3 | 5. Controlled experiments | Freeze inputs/seeds/model/code hashes; compare baseline and candidates on held-out material. Save actual GP outputs, measured distributions and finite/unclipped previews. Record failures and continue independent cases. |
| 4 | 7. Composition engine | Finish and validate existing thematic-return integration before broadening it. Explicit generated section plans, actual returning material and literal locks must agree. |
| Conditional only | 6. Levers | No separate lever project or expansion. Fix a control only if a specific experiment is blocked; preserve literal locks and reference independence. |
| Built into each task | 8. Validation | Required tests/native GP checks, independent QA, leakage checks and CI belong to the four priorities, not a separate research workstream. No invented listening verdicts. |

## Persistent checklist

- [x] Create recurring continuation attempts and bounded cutoff.
- [x] Dispatch independent QA/profile/method tasks; record usage failures honestly.
- [ ] Inspect unfinished theme-return code/artifacts and distinguish validated work.
- [ ] Add reusable, tested source/generated style-gap diagnostics if missing.
- [ ] Run targeted generation experiments; retain baseline and candidate GPs.
- [ ] Integrate only experimentally supported improvements.
- [ ] Verify literal locks, leakage guards and native serialization independently.
- [ ] Run relevant tests/build; commit/push verified work; verify CI/Pages as applicable.
- [ ] Morning report: delivered commits/files, measured changes, rejected ideas,
  remaining uncertainty and specific listening questions.

## Existing work to preserve

Current main f2807b3 includes completed routine bend integration. Private paired
corpus: local-artifacts/bend-routine-corpus-v1; raw analysis remains authoritative.
Uncommitted theme work exists in form_returns.py, compose_controlled.py,
run_controlled_batch.py, their tests, CONTROLLED_PIPELINE.md and
AUTONOMOUS_COMPLETION.md. Do not discard or blindly stage it.

Assigned agent scopes: QABot3000 audits theme-return work read-only; profile agent
may add isolated style_diagnostics.py/tests; methods agent may add isolated opt-in
candidate experiments. None completed because their initial dispatches hit usage
limits. Re-dispatch after limits allow execution; parent integrates and commits.

Every continuation must safely pull main, inspect this checklist/current code,
make concrete progress and append commands/results/next action. Quiet periods
are not progress. Final listening and artist-feel approval remain human work.

## First resumed findings

Profile diagnostics and6tests exist uncommitted; frozen profiles-v3 predates the
analysis repair and excludes20tracks. It must not be called a current refit.
Existing12-piece discrepancies are strongly associated with context/role mixture;
increasing independent technique probabilities would obscure that issue.
An isolated tuning-relative proposal and4tests exist uncommitted with3private GP
candidates. They are mechanistic trials, not approved musical improvements.
Theme QA found no blocker in the bounded prior8casebatch, but requires fresh
current-sealed replay before delivery. Agent reports/outputs remain private.
