# Tier2 implementation â€” active authorization

2026-10-22. User explicitly authorized resolving the Tier2 interface with
ProjectPlanner3000, implementing SAME relationships forward/backward, and running
all three gates. Earlier design-only pause no longer blocks this bounded work.
Preserve accepted detectors, conversion, private source/baselines and unrelated WIP.

## First musical boundary and acceptance checklist

- [x] T1 input: exact identified written-base pitch occurrences/rational time/part/
  voice/address from retained extraction; not a claim of full GP/performed fidelity.
- [x] T2 physically nests its sole T1 input once, owns real literal-sonority,
  chord-compatibility/ambiguity, voicing and conditional note relationships.
- [x] Fixed published theory definitions, not artist preference rules or guessed
  unique chord/key/mode; unknown and out-of-vocabulary material retained.
- [x] Shared relation code solves analyzed coordinates and removed lower pitches;
  no second musical generator or hidden source/cached note stream.
- [x] Realization parameters have explicit musical roles/owners; no raw absolute
  pitch duplicate per member; identities/timing/notation addresses kept exact.
- [x] Pairwise stripped-input isolated inverse and independent raw-source comparison.
- [x] Real context intervention propagates or rejects incompatibility; locked
  dimensions unchanged; no percentage/style control claim from manual edits.
- [x] Source-backed chord/ambiguity/part-vs-ensemble contrasts and real-note trace.
- [x] New frozen random Songsterr capture, unchanged logic, retained failures.
- [x] Planner start/midpoint/end reviews and explicit all-three scoped verdicts.
- [x] Relevant/full tests, safe commit/push and actual CI check.

## Current decisions

Planner start review approves a meaningful bounded sonority/chord-alternative/
voicing/conditional-coordinate slice. Bass/register anchor is not chord root;
singletons and incomplete sonorities must not be forced into named major/minor
chords or pedals. Model agreement is not truth. Keys/modes/roles unsupported by
evidence remain explicit unknowns. Mathematical pitch factoring alone earns no
musical-abstraction pass. All gates must name their field/tier scope.

Next: freeze vocabulary from installed music21 theory definitions; implement
new shared relations and source-backed tests; no revival of the retired codecs.

## First completed boundary — 2026-10-22

- Shared equation `pitch = bass_register + voicing_interval`, solved both ways.
- Fixed music21 9.9.2 vocabulary (50 definitions), all compatible roots retained;
  no song-specific rules, no preferred chord guessed.
- Planner found and implementation fixed: opaque metadata cache loophole,
  unknown-pitch missingness, cross-bar clock collisions, misleading attack label,
  invalid typed identities/counts, arbitrary group partition, runner dependency
  freeze and failure exit behavior. Added adversarial regressions.
- Actual fresh random capture: 6311/revision5833929, 12 tracks, 6386 occurrences,
  seed12286640854968311033/queryz; 1294 unknown pitches retained, no timing warnings.
- Private runs fresh-qa-v1/v2 retained initial runner failure/misconfigured import
  challenge. v5 PASS exact raw fields, 6386-event audited blind inverse, five
  actual denial challenges; source and code unchanged. 4190 written-start groups,
  887 compatible, 3301 unresolved, 2 grace-timing unresolved. Not all notes have
  identified harmony. Worker uses Python audit, NOT OS sandbox/resource quotas.
- Beatles regression v2: 4050 events exact inverse/source checks. Actual q0.5
  part3 C/E/G compatible Cmajor; q7 part1 D/A power-only vs other part D/F#/A
  compatible Dmajor. No invented third; ensemble partial unknowns explicit.
- Planner independently verified both inverses/source checks and approved bounded
  Gate3: written-start theory compatibility/alternatives/bass/voicing/coordinates.
- Commands: `python -m unittest discover -s composition-lab -p test_*.py -q`:
  804 tests, 803 PASS/1optionalSKIP (19.354s). Further targeted isolated inverse/
  failclosed tests: 18 PASS. music21 vocabulary reproducibility PASS. `npm` absent
  from PATH; bundled node `node_modules/vite/bin/vite.js build` PASS (32 modules).
- Full Tier2 remains INCOMPLETE: no key/mode/function, acoustic sustain/technique/
  GP recreation or artist-style nonzero percentages. No musical audio claim.

## Next boundary — nominal written-duration overlap

Planner recommends and verifies actual q123 Beatles: E-only written starts versus
C/E/G nominal overlaps. Implement event-boundary half-open intervals using ONLY
previous T1 exact pitch/time/IDs through existing SAME relations. Preserve group
ownership/inverse; derived spans reference occurrences, no copied raw pitches.
Distinguish newly starting from continuing written occurrences. Grace/invalid
source timing stays uncertain. This is nominal notation, not ties/let-ring/acoustic
sustain. Keys/modes/functions remain open. Acceptance: independent raw-source
interval checker; held-note/context-change regression; all three gates again with
new frozen random capture, Planner midpoint/completion. No source reread in core.

## Nominal-overlap completion

- Added reference-only half-open nominal written-duration spans with part/ensemble
  contexts and starting/continuing occurrence references. `note_context_at` answers
  candidate-relative intervals for an actually present note at an exact rational
  time. All contexts recomputed/validated from SAME equations; queries validate
  nested input consistency. No duplicated absolute note stream in derived spans.
- Planner midpoint independently tested rational boundaries, zero-duration exclusion,
  unknown members and exact inverse. Fixed coordinate API mismatch and validation
  entry requirements. Planner completion independently checked both actual artifacts,
  20 local code seals and raw-overlap oracles; bounded Gate3 APPROVED.
- Fresh random Poison1197/revision9454504, seed17489552411630729654/queryc,
  8 tracks/6101 occurrences/1082 nominal spans. Independent raw check and blind
  inverse PASS; 1409 unmapped pitches retained. No timing warnings. Actual five
  denial challenges PASS. All local transitive imports frozen before analysis;
  code/source unchanged. Latest artifact musical-tier2-overlap-qa-v3 adds nested
  lower-consistency validation; previous passing v1/v2 retained.
- Beatles nominal regression: 4050 occurrences/651 spans, exact source/inverse/
  denial/overlap checks PASS. q123 new starts E-only vs nominal overlap C/E/G;
  event22793:1:32:0:1:0 resolves interval16/mod12=4 under Cmajor alternative.
  No source-labeled key/mode or acoustic sustain claim.
- Added nested lower-payload mismatch rejection and regression; targeted21PASS.
- Full suite before last consistency guard:808 tests/807PASS1optionalSKIP17.345s.
  Final full-suite result recorded below after completion.
- Safe origin fetch: HEAD and origin/main identical before commit (0/0).
- Next candidate recommended by Planner: same-voice melodic motion, but only with
  genuine shared equation ownership; not report-only contour counts. Separate
  future acceptance scope before implementation. Keys/modes/functions stillOPEN.

Final full suite: `python -m unittest discover -s composition-lab -p test_*.py -q`
809 tests, 808 PASS/1optionalSKIP, 17.153s. Full active UI Vite build PASS; no
website source changed and no deployment claimed. All three gates approved only
for declared written musical contexts, not completed full Tier2.

Checkpoint delivered: commit091a1ea44573b50f147c9d6ff8142329ae0da59d pushed main.
Remote CI39818522356 completed SUCCESS: Python suite, source dead-tie guards,
source-inspector clock/occurrence joins, pinned alphaTab bend-fidelity check.
No website files changed; Pages deployment not required/claimed.

Planner next-priority correction: do NOT optimize melodic anchor removal now.
Prioritize evidence-backed tonal context (key/collection/diatonic relationships),
retain exact voicing choices, and do not force unvalidated harmonic boundaries.
Full Tier2 acceptance remains open; continued work does not require user input yet.

## Next endeavor contract — tonal evidence, not a guessed key

Planner start review: shared-core whole-song/per-part duration-weighted pitch-class
exposure, two published music21 9.9.2 profile families (KrumhanslSchmuckler and
TemperleyKostkaPayne), all24 tonic/major-minor scores each. Scores are uncalibrated
Pearson correlations, not probabilities or general modal inference. Keep established
key/mode UNKNOWN; retain competing scores, model disagreement and all evidence.
No handpicked weights/thresholds/votes. Per-note interval/octave/reference-collection
membership and chord-root coordinates must be conditional on exact candidate ID.
Minor reference collection explicitly natural-minor, not a prohibition on raised
6/7. New/unknown/grace timing remains explicit. No copied per-note pitch stream;
forward/backward must validate from SAME realized pitch/time equations. Three-gate
fresh capture, independent exposure/profile oracle, source contrasts, inverse and
Planner midpoint/completion required before reporting musical acceptance.

## Tonal candidate implementation and actual tests

- Shared-core tonal evidence: whole-song pooled and separate per-part scopes,
  nominal-duration PC exposure and explicit used/excluded IDs, two generated
  published profile families/all48 candidates per scope. No selected key/mode.
- Candidate-relative note interval/octave/reference-collection membership and
  chord-root coordinates carry exact candidate+local harmonic-context references.
  Same pitch/time equations regenerate/validate all evidence before inverse/query.
- Planner midpoint caught invalid timing mass and missing query scope/register
  convention; fixed and independently verified. Invalid durations excluded;
  undefined correlations null; unknown pitches/zero durations/fractional pitches
  partitioned explicitly. Profiles are order-invariant and doubling-sensitive;
  tests make those limitations visible instead of inventing musical understanding.
- New frozen random Last Nite19390/revision8733718, seed15100074186203114746,
  queryn,5tracks6152occurrences. Private musical-tier2-tonal-qa-v1: source/inverse/
  actual5denials/source+codeintegrity/context checks PASS. 4395 pitched members used,
  1757 unknown pitches retained. Independent raw-source music21 oracle matched
  all288scores within1e-12 (9.9.2 primarysource hash retained).
- Beatles tonal regression4050events allsamechecksPASS; independent384scoresPASS.
  Actual q123 E has conditional major-third membership under Cmajor hypothesis
  versus outside Dbmajor reference, with time/span/ensemble refs retained. This
  does not claim either hypothesis is established key or note function.
- Actual commands: `python -m unittest discover -s composition-lab -p
  test_musical_tier2.py -q`:26PASS. `build_tier2_theory.py` reproducibilityPASS.
  `run_musical_tier2_qa.py` fresh+Beatles; `check_tonal_profiles.py` both artifacts.
  Full unittest discover814tests/813PASS1optionalSKIP17.300s.
- Pending: Planner completion challenge/approval, commit/push/CI for this addition;
  tonic/local key/modulation, harmonic spans, general modes and functional roles
  remain incomplete. Exact reconstruction and published-method agreement do not
  prove those interpretations. No audio or stylistic quality claim.

Tonal final corrections: Planner independently found oracle scope omission and
set-based duplicate-ID blindspots; fixed exact raw-derived scope/candidate inventory,
finite typed scores, exact used/excluded reference multiplicity and corruption
regressions. Core tonal provenance now deepcopy-owned; input cannot mutate frozen
profile definitions. Actual final artifacts musical-tier2-tonal-qa-v2 and
musical-tier2-tonal-beatles-v2 have exact inverses/source/5denials/integrityPASS;
independent-tonal-oracle-v4.json compares288/384scoresPASS. Explicit limitation:
oracle takes quarantine warnings from accepted source_quality, not an independent
warning generator; both actual inputs have no warnings. Raw timing/field oracle
is independently run separately. Actual Econtrast in both final artifacts proves
Cmajor-reference membership TRUE/Dbmajor FALSE without changing note. These are
candidate-conditional coordinates, not source-key or note-function adjudication.
Full suite816tests/815PASS1optionalSKIP17.319s; final ownership-corruption tests
28targetedPASS. Final approval/commit status below.

Planner completion: independently28testsPASS; actual both v2inverses and
288/384oracle comparisons rerunPASS; Econditionalmembership contrast verified.
Bounded tonal Gate3 APPROVED; no further same-baseline runs recommended. No key/
mode/function truth claimed. Both prior gates PASS declared fields. Verification
suite816tests815PASS1optionalSKIP; commit/push followed after independent review.

## Tonal checkpoint delivered

Commitfb6272d01a2b257fbb4d23a55b82c3026ff55b12 pushed. RemoteCI39820275078
SUCCESS. Final suite816tests815PASS1optionalSKIP18.127s. No site source changed.

## Source-signature endeavor — contract and evidence

- Negative audit: four recent captures +495InventAnimate trackfiles lack measure
  keySignature. Three opaque top-level track.key strings are NOT tonal fields.
- Positive: retained ChopSuey3708/rev9044289 has1221measurefields on11tracks x
  111bars, exact{accidentalCount:2,mode:minor,transposeAs:b}. Primary client vendor/
  common source hashes recorded in output. Verified signedfifths from direction
  and abs(count), minor offset; missing inherits, null cancels, no Cmajor default.
  Instrument/display transposition remains unverified; no inferred tonic claim.
- Explicit T1 schema2: every present/null occurrence, sourcepart/bar/path/onset,
  complete trackmeasure/end inventory. Core reads T1 ONLY. T2 source_keys owns
  deduplicated signed-fifths/mode definitions plus minimal raw-count sign and
  zero-direction spelling gauges. No rawsourceobject survives in higherdefinitions.
  SAME equations recreate every declaration. TonicPC alone cannot invert spelling.
- Repeated fields retain every occurrence but are not independent votes/keychanges.
  Planner found formatting variants split contexts; fixed semantic state grouping
  by signedfifths+mode, retaining multiple format definitions for exact inverse.
- Unknown schema/enums failclosed, originalcapture/failure retained. Synthetic
  tests cover null/absence/change/zero/negativecount/type/format gauges; these are
  primary-client-backed tests, not claimed actual corpus coverage.
- Initial extractor syntaxerror caught/fixed before artifact run. Initial oracle
  checked firstbeat, not endclock; independent rawlayout API now checks both and
  handles empty/no-beat measures. Exact typed inventory list catches duplicates;
  query rejects bool/float/string part IDs. Existing raw arithmetic unchanged;
  optional include_layout exposes independent expected layout.
- Fresh random REM LosingMyReligion16245/rev8954603 seed7764154184538583810,
  querym,11tracks11205occurrences,0keyfields. Final musical-tier2-key-qa-v3:
  independent raw fields/keyabsence/clock, expandedT1 audited inverse, five actual
  denial challenges, source+codeintegrity PASS. Elevenunknown declarationcontexts.
- Positive final musical-tier2-declarations-positive-v4:8719notes+1221declarations
  exact; one definition/11contexts. All same raw/technical/inverse/denial checks
  PASS. Decoded notation Gpc7/minor is a declaration, NOT established concert key.
  Conditional profile query explicitly keeps frame compatibility unverified and
  asserts no agreement/conflict. No extra artist/musical-quality claim.
- Planner independently32targetedtestsPASS; reconstructed both final actualinputs,
  reran rawkey oracle, checked merge/typeguards/unknowns. Bounded Gate3 APPROVED.
- Fullsuite820tests819PASS1optionalSKIP17.435s. Commands: unittest discover
  test_musical_tier2.py; full test_*.py; run_musical_tier2_qa.py on freshREM and
  retainedpositive capture. All private artifacts remain under local-artifacts.
- Logging-only encoding error while appending this section truncated the progress
  file. Restored committed history from HEAD (legacycp1252), reconstructed this
  uncommitted source-signature log from actual commands/results, and normalized
  this file to UTF-8. Code/privateartifacts unaffected; prior history preserved.

## Next priority — inference, not more descriptors

Planner: stop extra affine/scale-list work. Timed tonal candidate inference must
live in actual Tier2 via T1-only adapter/frozen model, with reference alignment and
vocabulary verified BEFORE predictions. Existing AnalysisGNN localkey is a candidate
(tonkey is NOT globalkey; degree1 is NOT note interval). Compare existingprofiles
and order controls; retain help/hurt, unknown training overlap/classical-domain
limits. No unvalidated argmax/reference annotation promoted into truth. SAMEinverse
and actual context links required. Resolve model/runtime/inverse contract first;
no disconnected benchmark. No need for user input identified yet.
