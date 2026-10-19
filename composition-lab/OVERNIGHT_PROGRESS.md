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
- [x] Inspect unfinished theme-return code/artifacts and distinguish validated work.
- [x] Add reusable, tested source/generated style-gap diagnostics if missing.
- [x] Run targeted generation experiments; retain baseline and candidate GPs.
- [ ] Integrate only experimentally supported improvements.
- [x] Verify literal locks, leakage guards and native serialization independently.
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

## 2026-10-19 resumed verification

- `git pull --ff-only`: main already current; unfinished files preserved.
- `python -m unittest discover -s composition-lab -p 'test_*.py'`:442 run,
  441 passed,1 optional skip. JS39/39 passed; Vite production build passed.
- `style_diagnostics.py`:7 focused tests and independent QABot3000 approval.
  Rejects nonfinite/bool/out-of-range rates; reconciles eligible counts and
  source-family versus generated-piece weighting. Private frozen snapshot is
  explicitly older than current source repairs. It is an accounting diagnostic,
  not an artist-quality score or causal explanation.
- The isolated tuning-relative proposal produced36 private GPs. Better marginal
  technique rates did NOT justify promotion: bass interval divergence worsened
  (.115 to .400 bits), harmony mean leap increased (2.95 to9.07 semitones).
  Defaults unchanged. Need connected-context tests, not artist-wide rate quotas.
- Connected profile v2:70 development scores/54families,328tracks,
  147103attack groups,12247approved pedal cycles.15focused tests pass after
  independent QA fixes to feature denominators, unknown masks, full-member
  rhythm geometry/meter and unknown harmony contexts. Further provenance and
  held-out coverage review remains; no style-fidelity claim.
- Theme fresh v4 replay:7 outputs; last case correctly refused code mutation
  during parallel edits. Preserved failed batch. Fresh v5 replay underway with
  stable files. Do not call v4 complete.
- Agents subsequently hit account usage limits; no work is claimed during
  unavailable execution. Continue from actual files, not elapsed clock time.

Next: finish current-sealed theme replay/native checks; audit connected profile
input identities and held-out support; commit verified isolated components,
push main and verify CI. Private models/scores/evidence/audio stay ignored.

### Theme-return gate completed (bounded explicit plans)

Fresh v5 batch:8/8 final GPs, no failures, current code/model/input seals.
All4 zero-strength outputs preserve source bytes. All24 intermediate/final GP
musical archives equal prior v3 archives. Independent alphaTab import validates
all8 final pitch/timing/tuning/program/tempo/meter expectations; flags8/8,
directed technique links8/8, bend curves24track checks with maximum error0.
Prior verified full-render evidence applies to identical archives/profiles;
no new listening verdict. Explicit returns work; theme discovery/development,
transitions and artist feel remain unproven. No default behavior change without
an explicit generated form plan. Intermediate core freedoms with returns are
explicitly unsupported rather than silently weakening locks.

### Connected profile prediction gate

Fixed-prior evaluation now compares each Boolean context model against its
feature-only marginal with the same eligible family/song weights. Missing
contexts back off; unsupported features are not scored as negatives. Five focused
tests pass; QABot independently reproduced all57 v2 metric rows. Cardinality-defined
labels are explicitly flagged as definition-coupled: they are not novel artist
discoveries. Palm/context log-loss gain .16962 and Brier gain .05639 on the
previously examined eight-score/six-family holdout are predictive notation
diagnostics, not causality, listening or a basis to promote the generator.

New sealed build CLI/tests hash source, accepted pedal artifact, canonical program
records and consumed implementation before/after fitting; fresh private output
only, strict duplicate-key/nonfinite JSON rejection, explicit unknown programs,
completion manifest only after verified products. Five runner tests pass;
QABot input-edge review continues. Profile join identity validation is in progress.

Delivery: 9ab5eba and707a44e pushed to origin/main. Composition Lab CI run
39226158459 succeeded. No website files changed; no new Pages deployment claimed.

### Current connected-profile build completed

Fresh `relationship-profiles-v3` completed with pre/post frozen input/code hashes
and product manifest.70dev/54families;8held/6families. New1462song-feature and
32536localtrack/source-section-feature summaries use explicit regularattackgroup
units.20profile,7predictiveevaluator and6runner tests pass. Input audit preserves
420119occurrences and accepted6249untagged context members; no source/detector
rewrites. Independent final artifact QA pending before commit.

Predictive context gain is positive for palm mute in6/6heldfamilies, openpull6/6,
openhammer4/6,bend5/6. Family sensitivity is descriptive, not uncertainty intervals
or evidence of musical quality. Current sourceprofile refit retains generation
rate gaps: palm−10.333pp, extendedpower−2.203pp, openhammer−1.779pp,openpull−.986pp.
Do not solve by marginal quotas: the connected sequence experiment is underway.

### Connected-profile independent acceptance

QABot3000 verified ALL frozen input/dependency hashes and four product hashes.
Independent exact-Fraction recomputation reconciles4125development/2006heldout
conditional tables (maximumfloatdifference7.82e-14). All outcome/song/eligible
counts reconcile.32536development/3202heldlocal summaries sum to1462/168song
summaries. Saved prediction exactly matches rerun; equal-family/equal-song
improvement matches aggregate within1.95e-16. Full accepted-join audit passes.
This closes the bounded written-relationship profile and diagnostic engineering
gate. Artist feel, complete physical execution, general phrases and musical
quality are NOT accepted by these checks. Profile scope doc records remaining
requirements instead of treating all of step3 as complete.

Latest local regression after the additional sequence-mask adversarial case:
466 tests run,465 passed,1 optional skip. This includes uncommitted experiments;
remote committed CI is recorded separately after push.
