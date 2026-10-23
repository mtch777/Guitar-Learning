# Tonal meaning implementation — active 2026-10-23

User authorized keys/chords/modes/note roles, shared forward/backward relationships,
all three QA gates, autonomous iteration with ProjectPlanner3000.

## Acceptance checklist

- [x] Read current HEAD/contracts and historical harmonic/key failure diagnosis.
- [x] Planner START: target the missing order-sensitive tonal relationship first.
- [x] Normalize structural key targets independently of applied chord tonicization;
  verify against pinned official parser; retain alternatives/repeat quarantines.
- [x] Freeze label-free feature schema, whole-work partitions and experiment plan
  before fitting; no test-driven hyperparameter changes.
- [x] Compare ordered tonal evidence with marginal and shuffled-context controls;
  report held-out-by-work help/harm, uncertainty, support and domain limitations.
- [ ] Connect supported key/chord context to explicit mode/degree/voicing and
  note-motion/role relationships, keeping ambiguous interpretation explicit.
- [x] Preserve ONE pitch authority and use SAME relationships in both directions.
  No source replay, raw-note residual, hidden caches or separate generator.
- [x] Gate1: frozen random Songsterr source; original failure retained and same
  source rerun after typed display-field correction (not first-attempt perfection).
- [x] Gate2: actual isolated worker reconstructs entire preceding source boundary.
- [x] Gate3 (bounded role/domain slice): Planner independently verified all24
  queried pitches against actual source and approved; not global key/mode quality.
  Annotated/context-sensitive positive/negative musical checks, not
  merely label arithmetic or a reversible data codec.
- [ ] Planner MIDPOINT/END, relevant/full tests, commit/push and verified CI.

## Frozen experiment plan (before any fitting)

Reuse pinned DCML Mozart corpus5337257a5318711e6302cfe85c3f1a6ade3c6271,
existing whole-sonata split11train/3validation/4test. Corpus support and examples
were previously inspected: held out by work, NOT pristine untouched discovery.
CCBY-NC-SA4.0: private noncommercial research only; no published scores, labels or
weights, and no product/deployment permission claim. Source license stays separate.

Observation: exact half-open source written-note-change cells, absolute PC bitmask
of all known active pitches, deduplicated across parts, rational duration and
source occurrence references. No target/chord/phrase label supplies a feature or
a cell boundary. Preserve empty and unknown-pitch cells; quarantine uncertain
repeat adjacency and conflicting/changing/unparsed analyst targets explicitly.
Encoded score order is not performed repeat traversal.

Target:24 structural local-key states (12tonics,major/minor), normalized from
actual globalkey+localkey fields. Applied relativeroot stays a SEPARATE target,
never changes the structural localkey. Alternative labels remain excluded from
single-target scoring; labels are analyst interpretations, not universal truth.

Candidate models:
- learned categorical pitch-set marginal P(mask|mode), tonic-relative;
- ordered P(current-mask|previous-mask,mode), BOTH rotated into candidate tonic;
- shuffled predecessor control: within training work, permute predecessor contexts
  while preserving current-mask/key marginals; deterministic seed9427.
All have4096possible PC sets. Dirichlet posterior backoff to learned marginal;
no handwritten cadence bonuses, preferred intervals or improvised music weights.
Key transition probabilities use relative tonic displacement and mode changes.
Learn transitions from source-cell target sequences, not absolute-key identity.

Validation grid (frozen): emission backoff strength1,10,100; transition symmetric
Dirichlet strength1,10,100. Choose by validation duration-weighted key-label NLL;
report separate method configurations and all validation results. Evaluate test
once after selection. Offline forward/backward smoothing is explicit. Compare
all methods on identical cells/durations and publish per-work outcomes, key-label
NLL/Brier/top-label duration agreement and emission predictive score separately.
Legacy profile scores remain a qualified baseline, never calibrated probability.
No automatic major/minor result becomes seven-mode inference or harmonic function.

Acceptance: retain/reject ordered factor by held-out performance versus marginal
AND shuffled control, with adverse works visible. Failure remains evidence; no
retuning on test, rerolling songs or claiming inference from inverse fidelity.

## Random source and setup correction

Selected before musical analysis: Queen Another One Bites the Dust371/rev9828955,
8tracks, seed1912590797035561867, queryq. No reroll.
Initial exclusion-inventory setup aborted on a historical selection.json ARRAY;
next command sampled from its empty inventory. Original sampling record preserved.
Independent after-capture/before-analysis reconciliation confirms371was absent
from every prior selection/exclusion/corpus ID. This chronology exception is
recorded in local-artifacts/tonal-meaning-exclusions-v1/novelty-reconciliation.json;
do NOT pretend exclusions were correctly frozen before this capture.

## Fixed study completed (2026-10-23)

Source-only cells:64,809 total,64,357 eligible. Official ms3 v2.6.5 parser
oracle agrees on248 distinct observed structural/applied-key cases. Five targeted
factor tests pass, including exhaustive posterior oracle and label-leak refusal.
Fixed validation selected ordered alpha100/tau1. Held-out key-label NLL
1.2381336 marginal ->1.2272952 ordered; shuffled1.4958577. Top-label agreement
81.4422% ->81.6407%. K310 deteriorates (NLL2.09306 ->2.30165). No retuning;
not an accepted general guitar key detector. Private outputs ordered-tonal-study-v1.

## Bounded note-role acceptance plan (before role implementation)

Planner reviewed: retain existing pitch authority; contextual constraints use
the SAME reconstructed observations/equations forward and backward. No inferred
role repairs notes. Complete topology must check consecutive voice events, rests,
ties, grace, overlap and uncertain sounding-pitch techniques. Retain every joint
harmonic membership alternative/witness, including disqualifying alternatives.

Freeze contrasts: C-D-E and E-D-C against C major support passing-like evidence;
C-D-C against C major supports neighbor-like evidence. A leap, rest/gap,
intervening note, simultaneous voice ambiguity, tie continuation, grace/zero
duration, bend/slide/harmonic uncertainty or unmapped degree must NOT become
an unqualified passing/neighbor label. Chord-member middle notes do not qualify.
Ambiguous harmonic paths retain both qualifying/disqualifying results. Authored
contrasts check definitions, not artist intention. Transposition must preserve
conditional outcomes. Altered/omitted contextual assertions must fail inverse.

Next: implement this bounded shared query, test contrasts, then frozen Queen
source with explicit whole-song denominators and bounded deterministic queries;
actual stripped-source worker plus independent complete-source comparison.

## Role/domain iteration results

Initial Queen portable failure retained in tonal-meaning-queen-baseline-v1:
19chord.width floats, whereas registry allowed integers only. Width is a display
choice, never chord inference. Added float to the existing exact typed owner;
fractional17.1240234375 regression verifies complete-source recovery.

contextual_note_roles evaluates explicit versioned occurrence/reference/time
queries using existing degree, motion and joint-harmonic equations. Optional
connected-T2 contextual_constraints are checked derived assertions. Stripped
inverse reconstructs existing pitch/source authority first, recomputes these SAME
queries, rejects changed roles/degrees/omitted alternatives. No role repairs notes.
Full harmonic packages deduplicated byhash; candidates/refs remain conditional.

Planner MIDPOINT found two gaps: inconsistent expression aliases and a clean
stored witness hiding another partial-evidence path. Fixed uniform note/beat
expression refusal and conservative incomplete-pitch possibility across ALL
terminal-reachable optimal supporting edges. This may over-refuse membership
vectors; it cannot certify them from one clean witness. Counterexample tested.

Sealed Queenv1:12evenly spaced queries allNO_QUALIFYING_ROLE. Sealed v2:
all8necessary-degree pairs likewiseNO before pitch-domain correction. Do not
replace either run or claim selected passages were a complete role census.

Planner approved pitch-domain prerequisite: source instrument1024is explicit
percussion per existing converter; GM0..127pitched; missing/unsupported unknown.
Existing complete schema4 owns these declarations; no new pitch owner. Known
percussion stays timed/reconstructable but does not enter harmony or unknown
pitched overlays. Dead/harmonic/unresolved events are not silently excluded.
Adding percussion invariance vs adding unresolved pitched uncertainty tested.

Final contextual-role-queen-qa-v3:
-3384source occurrences:2071pitched-domain,1313explicitnonpitched,0unknown-domain.
  A pitched DOMAIN does not imply its individual sounding pitch is known.
-3368consecutive sourcevoice triples;645preliminary topologyeligible.
-1290explicit Eminor/Emajor referencepairs:801notadjacentdegrees,481unmapped,
  all8remaining receive joint harmonic analysis. No role-outcome cherry picking.
-2conditional passing-like across all feasible membershipvectors:
  A3-B3-C4 bars15-16 and16-17.1ambiguous B3-A3-G3 atbar70.
-5doNOTqualify:4have chord-member middle notes;1has incomplete pitch support.
-All37953captured typed fields/containers recovered by actual -I -S audited
  worker with source/derivedcache/expectedanswers absent. Independent comparator
  zero mismatches. Retained technique/pedal result exact parity. Python audit is
  NOT an OSsandbox. Complete captured JSON equality is not GP/audio equality.

Commands/results:
`python -m unittest discover -s composition-lab -p test_contextual_note_roles.py -v`
10pass (main .venv).
`.venv/Scripts/python.exe -m unittest discover -s composition-lab -p test_*.py`
928run,927pass,1optional skip; private tonal-meaning-full-tests-v2.log.
`run_contextual_role_qa.py <frozen371capture> <retainedbaseline/tier2.json>
local-artifacts/contextual-role-queen-qa-v3 --selection necessary`
PASS_BOUNDED_CONTEXT_AND_FULL_SOURCE, frozeninputs/code unchanged.
Node existing deadtie/sourceinspector/bendfidelity suites19pass; Vitebuildpass.
Research NumPy inference tests explicitly optional in bare stdlib CI; full .venv
ran them (not hidden as skipped model accuracy).

Still open: reliable key inference across guitar material; modal-center evidence;
chord function/tonicization/resolution; other note roles. Ordered classical-domain
study is research only. Passing/neighbor observations are conditional, not artist
intent, emotional interpretation, general role accuracy or new music generation.
Next: Planner END review, verified commit/CI, then bounded chord-resolution work.

Planner END: APPROVED bounded QA3 after independent raw-source checks of all24
queried pitches and reconciliation of every domain/reference-pair count. No
positive neighbor example in Queen; authored neighbor contrasts only. Reliable
modal/key/function inference remains open. Next approved direction: conditional
temporary-target/resolution evidence with joint chord-label compatibility.

Bare runtime `python -S -m unittest discover -s composition-lab -p test_*.py`:
928run,924pass,4optional skips (including2research-only NumPy inference tests).
`rebuild_tonal_context_dataset.py local-artifacts/tonal-context-data-v1
local-artifacts/tonal-context-data-rebuild-v1`: all64809cells/54pieces regenerate
exact structured equality from hashed source-support cells. No refitting or
second test selection; original rows only comparator inputs after regeneration.
