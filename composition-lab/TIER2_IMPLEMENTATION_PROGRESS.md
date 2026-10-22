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


## Temporal inference endeavor — approved input/method contract

Source declaration checkpoint70159ef pushed; remoteCI39823243632 SUCCESS.
Planner/parent feature audit REJECTS forcing native AnalysisGNN checkpoint into
currentT1: consumes meter/measure timing, pitch spelling, and key-signature embedding
with no unknownclass. Native localkey can only be evaluated with genuine required
inputs; missing signature/spelling must not become0/C/4-4. No modelinference run.

Alternative installedprimary method audit: music21 9.9.2 floatingKey uses per-measure
AardenEssen (NOTKS) duration-weighted correlations and defaultwindow4 inverse-distance
weights1/(abs(distance)+1). Primarycode cachealias bug confirmed by Planner fake
scorevector probe; repeated smoothing changes cached rawvectors/order results.
DoNOT adopt buggy implementation or claim complete nativeparity. Implement named
AardenEssen measure evidence + IMMUTABLE inverse-distance smoothing, rawscores
verifiedagainstmusic21, temporal sums against independent statelessoracle. Empty
frames retainall24unknownscores; invalidtiming excluded. Offlinefuturecontext is
explicit. Windows0/4 predeclared, no tuning on reference results, no keytruthclaim.

Reference selection frozen BEFOREpredictions: temporal-tonal-reference-v1/selection
seed1602012989824021803,19candidateanalyses excludealreadyinspected001, choose
004/BWV86.6,010/BWV38.6,014/BWV184.5. Analysis+scorehashes frozen; no predictionsyet.
Namedanalysts/proofreaders recorded after selection. Annotationmaterial PRIVATE
EVALUATIONONLY, no redistribution/traininglicense assumed frommusic21code license.
Referenceannotations cannot enter analysisinput. Alignment mustpass beforescoring;
retain failures, no easierreplacement. Classicalreference support is not artistproof.

Geometry prerequisite acceptance (small commoninput extension, notanothercodec):
- canonical source-derived frameowner: true sourceordinal/label/start/span/meter
  provenance +partmembership. Acrosspartalignment validated, conflictsnotforced.
- sourcepickupdeclaration separatefrom observedshortspan; witnessrequired; no guessed
  shortening or invented4/4. Empty/rest-only actualframes preserved.
- written-onset measure allocation (whole notated duration, not clipped acousticsustain)
  explicit; grace/crossframe/invalidtiming accounting notsilent.
- keydeclarationsNone=outsideownedreference scope, []=verifiedownedabsence. MusicXML
  adapter mustnot fabricate Songsterr sourceobjects/pointers. Inputorigin typed.
- sourcekeysummary inventory derivedfrom/crossvalidatedagainstcanonicalgeometry;
  higherkeycontexts reference it, no competing inventoryowners.
- SAMEstart/advance and metricunit relations; no separate compression project.
- input/parity/oracle+freshSongsterr+exactinverse+annotatedtemporal evaluation and
  Planner midpoint/completion required; geometry alone is not musicalprogress.


## Temporal Tier2 implementation — 2026-10-22, active

Acceptance checklist (bounded slice; full Tier2 remains incomplete):
- [x] T1 schema3 owns actual measure geometry, real meter provenance/part membership;
  source key None=outside scope, []=owned absence. One canonical geometry inventory.
- [x] SAME metric-unit/start/advance relations reconstruct exact geometry; shared
  note/tonic/chord coordinate helper supports global AND timed candidates.
- [x] AardenEssen measure evidence + immutable distance smoothing, published window4.
  Actual empty frames retain24 null candidates. No fake key, no source reread.
- [x] Private frozen annotated004/010/014: literal XML pitch/time multiplicity,
  measure labels/spans/meter declaration/inheritance and part inventory checked.
  Adapter initially lost source suffix4a/8a; independent oracle caught it; fixed
  via actual source measureNumberWithSuffix. No source event mismatch.
- [x] Actual isolated SAME-core inverse on all3 references; native AardenEssen raw
  correlations and independent immutable sums matched3120/3120/4080 values.
- [x] Planner midpoint challenged annotation alignment. Initialreferencev1 retained:
  004clock41vs40blocked;014uncorrected numbers INVALID edition coordinates.
  Independent all-labelled downbeat audit passed;004only trailing1q unsupported.
  014annotation-to-source +7 supported49/59 exact sonorities across song,1 at0,
  nine match no shift. q37 contradiction retained. Planner approved evaluator-only
  fixed alignment assumption, not proof every label correct. Frozen before rerun.
- [x] Referencev2 common support: strict unique duration agreement window0/window4/
  globalKS/TKP:004=57.5/52.5/52.5/52.5%;010=42.31/69.23/61.54/61.54%;
  014=80.36/94.64/75/75%. No tuning, no selective exclusion. This is agreement
  with analyst labels on3 classical references, NOT universal/artist key accuracy.
  11of16labelled keychanges inside physical measure: granularity limit explicit.
- [x] Existing32+new5targeted tests PASS. Synthetic immutable sum corrected to
  [1.05,.95] for [.9,.1],[.2,.8],[.8,.2] center/window1; old prose .9/.6 wrong.
- [x] Full suite:825tests,824PASS/1optionalSKIP,21.981s.
- [ ] New random Songsterr whole-scope run complete + Planner finalreview.
  Frozen seed18332795165358390742/queryw selected America25201/rev7475088,
  A Horse With No Name,10tracks105frames. Firstactualrun temporal/source/inverse
  checks passed but overallFAIL because I edited imported evaluator during run.
  Failure retained; rerunning SAMEcapture/code, no replacement/reroll.
- [ ] Positive1221source-declaration regression, source/schema contract docs,
  verified commit/push and CI.

Commands/results: unittest test_musical_tier2 test_temporal_tier2 -q ->37PASS;
run_temporal_tonal_reference.py selection.json reference-qa-v1 ->1clockblocked,
2technicalPASS but alignment invalid/unverified; reference-qa-v2 --alignment
approved-alignment-v1.json ->all3technicalPASS, scored limitations above.
run_musical_tier2_qa.py REMcapture temporal-rem-v1 ->PASS declared scope,
139frames/80064independent temporal comparisons. Freshv2 andChopSuey running.
Persistent private outputs under local-artifacts; no scores/annotations published.
Next: finish independent gates, Planner completion, source-only commit; then use
actual disagreement evidence to choose next musical step. No fullkey/style claim.


Temporal delivery verification: freshv2 actualPASS,105frames55440scorecomparisons;
positiveChopSuey actualPASS,111frames63936comparisons+1221declarations. Both exact
isolated inverse, independent source comparison and all5denial challengesPASS.
Full825tests824PASS1optionalSKIP21.981s; bundledNode Vite productionbuildPASS.
All source/analysis/caches remain private. Planner endreview requested on actual
files, not inferred from earlier partial results. Continuing into sub-measure
harmonic context after recording this checkpoint; no user input needed.

Planner completion verdict (actual final files read): APPROVED bounded temporal
slice. FreshAmerica14414occurrences/105frames/55440scorecomparisons. Positive
ChopSuey8719occurrences/1221declarations/111frames/63936comparisons. Allsource,
isolation,5denialchecksPASS. Scope uncertain timed candidates + exactdeclaredT1,
NOT established keys/modes/functions/fullTier2. Nextendeavor contract: investigate
published Pardo-Birmingham joint chord segmentation+labelling using noteon/off
candidate boundaries and DAG path, compare instantaneousbaseline on arpeggios,
passingnotes/repeats/heldchanges; preserve alternatives/unsupportedcases. No
chord=key or cartesianlabelinflation. Audit published score/vocabulary/ties first.


Delivery4c9c27f pushed. CI39829042803 failed dependency-free discovery: new research
helper imported music21 at module load through runner imports. Fixed by lazy
imports inside research-only functions (no runtime musical math change). Actual
-S focused37PASS; -S full825tests823PASS/2optionalSKIP18.560s. Repeated frozen
referencev3 alltechnicalPASS and identical metrics. Fix commit pending. Temporal
full-installed suite previously824PASS/1skip. Next bounded harmonic query WIP is
uncommitted and not included in the dependency-only repair.


## Bounded harmonic-span refinement — active
Acceptance checklist:
- [x] Read primary Pardo-Birmingham2002 paper, renderedFigure3: published six
  families/72roots, S=positive-negative-missing, note-cell count NOTduration;
  fullDAG maxsum. Declared no-tiebreak variant; no corpuspriors/dimresolutionrules.
- [x] Explicit rational interval+part/ensemble request; heldstarts clipped without
  newattack; no barforcedcuts; operational edgecap returnsNOT_RUN, never truncates.
- [x] EightinitialanalyticalcontrasttestsPASS inclalloptimalpaths compared to
  independent exhaustiveenumeration, paper6pointtie, arpeggio/repeats/heldchange.
- [x] Planner midpoint caught MATERIAL unknown-boundary leak: unknown/percussion
  interval1..2 multiplied heldC/E/G score3->9 despite excludedpitch. Corrected:
  onlyeligibleintegerpitch intervals form scoringgrid; unknownintervals preserved
  separate exactoverlays, edge/notecontext partialflags. Newinvariance regression
  passes; source records retained. Nineharmonic tests nowPASS;46combinedPASS.
- [x] Same _chord_coordinates nowserves writtenstart/overlap/inferredspan contexts;
  heldC becomesrootunderC, fifthunderF. Explicit optimaledge selection, no hidden
  preferredpath. Staleanalysisrefused. QueryisdeterministicT2refinement, not anew
  pitchowner/generator or completedhigher-level abstraction.
- [ ] Frozenreference+newrandom actualsource/DAGoracle/isolation andlabels.
  Newseed6105411479077065199/queryx selectedStaticX TheOnly54387/rev9800793,
  7tracks. Requests frozen BEFORETier2analysis:part0+ensemble, first8 actualsource
  frames0..31q, max50000edges. No easierreplacement onunsupported/resourcecase.
  Primary3annotatedreferences retained with qualifiedfrozenalignment assumptions;
  reuseddiagnostics, not newheldoutaccuracyclaim. No methodparameter tuning.
- [ ] Plannercompletion/fullsuite/verifiedsourcecommit+CI.

Temporaldependencyrepair5734bde pushed; actualCI39829621412SUCCESS.
Harmonicprivateactualrun musical-tier2-harmonic-qa-v1 isrunning. Independentraw
oracleimports noTier2/extractor andchecks ALLcandidateedge scores/optimalpredecessors;
actualworkerrecomputesquery+exactinverse fromstrippedT2only. GoldonlyparentQA.


Harmonicv3 actualPASS with preloadedtransitivelocalcodefreeze+complete declared
source/plans endrehash. Oraclemetricrenamed independently_computed_template_scores:
it computes72peredge andcompares wholeDAGoptimum/predecessors pluscanonicaledges,
NOTevery producerrow. Plannerrequestedprecision; oldv2retainedlimitedfreeze.

Next approved bounded refinement: actualStaticXensemble has22799473113563136
optimal BOUNDARYpaths (not full labelassignments),part0has108. Preserve allpaths
compressedDAG, notenumeration. Added mandatoryboundary prefix*suffixcount and
percelllabelunionover ALLterminalreachableoptimaledges+no-pitchedpossibility.
Repeatedtriad4boundarypaths butunanimousCmajorunderobjective.11harmonictestsPASS,
including exhaustiveconsensus/mandatory/no-evidence cases. No confirmedchordclaim.
BEFOREreferencev4 results: consensus diagnostic strictdurationcredit only ifunion
hasonecorrectlabel andnounknownoption; fractionalcredit1/numberalternatives ifgold
included, unknownoptioncountsasalternative. NOTprobability. Allunsupportedgold
labels andsourceunknownsremainindenominator. Canonicalmetrics unchanged/qualified.


Harmonicv5 actualtechnicalPASS; all3references+newStaticX requests, source/code
endhashesunchanged; frozen preloadedlocalmodules copiedprivately forreplay. All
rawsource and isolatedquery+sameinversechecksPASS. StaticX4181occurrences,
401deadpitchunknown/1743unusablepitchedmapping(includingpercussion) retained.
Part0/ensemble31q requests have108/22799473113563136 optimalBOUNDARYpaths;
part0unanimity0q, ensemble91/4q(73.39%) underobjective, not truth/confidence.
Canonicalstrictannotationduration00487.5/01086.54/01474.11%; instantaneousexact
76.875/84.62/71.875%. Allpathconsensusstrict86.25/81.73/72.32%. 014outsidevocab3q
keptindenominator. Exactcanonicalboundary P/R90/92.31%,90.70/92.86%,85.96/90.74%;
mandatory00489.74/89.74%,otherssame. No tolerance/modeltuning/goldpathselection.
Planner actualv5review: APPROVED boundedharmonicspanmethod; independently12tests
PASS. Full837tests836PASS1optionalSKIP18.866s; bare-S837tests835PASS2skip18.875s.
No source scores/annotations/audio published, no new UI/audioquality claim.

Nextendeavor approveddirection: audit Raphael-Stoddard jointprobabilistickey/
harmony model parameters/inputs/availability beforeimplementation. Preserve span
alternatives; testunchangedchordwithdifferentcontext, secondarydominant, actual
keychange. ConditionalRoman-degreecoordinates distinctfrominferredfunction.
Nevermultiply uncalibrated chordscore/keycorrelationasindependentprobabilities.
Need unknown/outofvocab +unchangedexactsourceinverse. No inputneeded yet.


Delivered harmonic671b299 main, actualCI39832378837SUCCESS. UnrelatedWIPintact.
Jointcontext audit is complete withoutinstallation/inference. McLeodpinned
b257424fcb049bb318fe05c22c0ae9318d6e2a0f; BOTHreleasedfamilies14hparams allTPC0,
ASTenumTPC0/MIDI1; safeYAMLnodecompositiononly. CurrentsemitoneT1 lacks authored
letterspelling. Explicittonicization/modulationconflation inREADME. Planner
independentlyverified and rejectedforceddeployment; notclaimingweightsdefective
orunavailable. Raphaelmissingverifiedparameterartifact; Rameaufirstchordkeynotfit.
SeeTIER2_JOINT_CONTEXT_AUDIT.md. Stop methodshopping; continueindependentmusical
note-role evidence (unambiguous sourcevoice, motion+harmoniccontext, allpathconsistent
alternatives, knownunknown/refusals, exactsameinverse). No userinputneeded.


## Conditional note-motion/context evidence — START, before implementation/results
Plannerstartcontract: consecutive OWNEDsourcepart/voice occurrences, positive
notateddurations/exactcontiguity. T1doesnotownrest/tie/attacktruth. Keepgaps,
overlaps,grace/unknownrefusals; no inventedmelodicline. No diatonicstepthreshold.
Monotonic+T/F/TdoesNOTprovepassing: octaveleapcounterexample mandatory. Passing/
neighbor/intentidentification staysunresolved. Querysameheldoccurrence attwo
halfopeninteriorclocks forcontextchange, preserveoriginalonset.

Acceptancechecklist:
- [ ] One sharedpureT2 motion/context query, explicitsourceIDs/clocks/refusals.
- [ ] Path-consistent3slotmembershipDP overexistingoptimalDAG, SAMElabel forall
  queriedpositionswithinoneedge, allfeasiblevectors+onepath/labelwitnesseach;
  noindependentunion/cartesianincompatiblecombos, no probabilities.
- [ ] Freezecontrasts now: C4-D4-E4 underheldC3/E3/G3 v G2/B2/D3; heldC4
  underCmajor->Gmajor; sameonsetpolyphonyrefusal; octaveleapC4-D5-E6 under
  Cmajor notcalledpassing; unknown/no-evidence andhalfopenboundary cases.
- [ ] Independentexhaustivesmallpaths+labelassignmentsverify allvectors; real
  source regression/newrandomfrozen beforeanalysis; actualisolatedsameinverse.
- [ ] Planner midpoint/end, requiredfulltests, verifiedcommit/push/CI.
No newmodelinstallation, keyclaims, stylelevers or UI. Next implementcorequeries
and frozenanalyticaltests. No human inputneeded.

Conditional note-context iteration: added SAME relation motion + path-consistent
membership queries. Planner midpoint caught fractional-pitch/nonmember inconsistency;
fixed to explicit unknown domain. Query-clock partial evidence and supporting-edge
partial evidence separated. All-path joint memberships preserve incompatible labels
instead of independently mixing per-note alternatives. Passing/neighbor/key/mode
identification remains unresolved. No nonzero style generation claim.

Frozen BEFORE Tier2 analysis: random Songsterr91316 Numb Fingerstyle rev5925322,
seed9337869460305403329/queryl; first8frames0..32q; ALL sourcepart/voice denominator,
sole voice63 occurrences, exact first3 IDs retained. Actual QA-v1 FAIL caught source
sequence bug: retained extractor appends grace notes, so realization_order is storage
order, not original musical order. Fixed ONLY new motion helper to use owned source
bar/beat/note addresses; inverse/storage data unchanged. Regression proves this.

QA-v2 PASS but0membership vectors because first3 contains grace; NOT melodic coverage.
Planner approved separate positive-duration queries of SAME frozen first3, grace
explicitly unqueryable, no later replacement. QA-v3 PASS; Planner challenged checker
vacuity/nonoptimal boundary witnesses. Added terminal-reachable optimal-DAG, exact
queryIDs/clocks, nonempty/unique vectors, vectorlength guards + mutationregressions.
QA-v4 PASS:655/655 raw notes,67896 independent harmonic scores/44partitionpoints,
1joint vector/8witnessedges, raw motion/refusal checks, actual stripped isolated
same-query+inverse PASS. Code/source hashes unchanged. First triple remains refused
as unique melody;2normalnotes conditional membership only. All private artifacts
retained under musical-tier2-notecontext-qa-v1..v4; no raw scores published.

Commands: .venv/Scripts/python.exe -m unittest discover -s composition-lab
-p test_note_context_evidence.py =>10PASS. run_note_context_qa.py fresh outputv4
=>technicalPASS; Planner final review requested, full installed/bare tests running.
Next: final Planner acceptance/fulltests/commitpushCI, then next independent Tier2
musical-context task. No human input needed; do not stop at this bounded slice.

Planner end review: APPROVED bounded conditional note-context slice after actualv4
artifact inspection and independently10testsPASS. Full847tests:846PASS1optionalSKIP
21.059s; bare-S847tests845PASS2skip21.023s. Both commands exact discovery above.
Next recommended: narrowly connect owned source tie declarations/validated written
continuations to musical contexts; no acoustic sustain/attack inference, no broad
metadata codec project, no reopening pedals. Start review before implementation.

Delivered notecontext8c553ee main; CI39835747211SUCCESS. No Pages changes.

## Written tie-context endeavor — START, before implementation
Planner approved narrow ownership: T1 exact tie/string/fret/dead declarations,
only instrument/tuning/capo settings required by accepted predicate. T2 refs existing
occurrences, no second pitch/time stream, exact true flags elevated to links/unresolved.
Do not remove destination coordinates yet. No acoustic attack/sustain claim, no
codec revival or generic metadata expansion. Preserve old detector behavior.

Acceptance checklist:
- [ ] Inventory actual fields consumed by accepted written-tie predicate.
- [ ] Factor pure eligibility shared with existing detector; differential tests.
- [ ] Optional exact T1 notation/settings -> T2 tie graph, same shared equations
      and strict typed declarations roundtrip; all current schemas unaffected.
- [ ] Named written-chain context vs existing written-occurrence context; tied
      segments vs untied repeats, gaps/voice/dead/unknown/ambiguity contrasts.
- [ ] New random song frozen preanalysis + actual-source chains/unresolved checks;
      stripped isolated same inverse, independent Planner midpoint/end.
- [ ] Full tests, commit/push verifiedsource, actual CI. Never publish raw scores.

Fresh frozen Muse Time Is Running Out87577/rev9575540,10tracks. Acquisition initially
assumed metadata tracks own partId, failed. Public CLI uses CDN enumerated indices;
resumed SAME revision/no reroll, raw metadata unchanged; failure retained privately.
No Tier2 analysis on new capture yet. New capture selection/source private under
musical-tier2-tie-fresh-v1. Numb655has0ties; StaticX4181has113true;REM11205has1217;
ChopSuey8719has138. Missing declarations remain distinct from acoustic attacks.

Written tie field inventory established: accepted predicate consumes lane(track,
voice,string), nominal position(tuning+capo+fret with percussion domain exclusion),
position validity(nonnegative fret), explicit dead equality, explicit true tie,
positive duration, exact adjacency and unique neighboring lane-onsets. Source
bar/voice membership and pitch/time already owned; only physical/declaration facts
added. Pure written_tie_edges factored into shared core; legacy caller retains
existing solve_links validation and exception compatibility. No coordinate removal.

Optional T1 schema4 exact raw parts settings and note fields -> T2physicalchoices
plus trueflags elevated to links/unresolved; inverse reuses same sharedpredicate,
restores exactflags; missing/null/false/numeric1 distinguished. Shared physical
position/basepitch consistency; source occurrence coordinates unchanged. Named
written_tie_chains derives originalIDs/endpoints/nominalextent, preserves unresolved
incoming origins and timing uncertainty, never verified attacks or acoustic sustain.

Planner midpoint independently6new+10legacytestsPASS, architectureapproved.
Requested timingquarantine + independent raw added-fieldpresence/type/value checks.
Added both;8newtestsPASS. Initial actualtie QA-v1 PASS: freshMuse7629notes,
183trueflags183resolved63chains; StaticX4181/113/113/107; REM11205/1217/1217/1189.
All stripped isolated sharedinverse+chainquery and rawsource checksPASS, code/source
unchanged. No actualunresolvedcases in these3; notclaimed. Added prior targeteddead
regressions1161150 and959603 to v2 (originalprobe rawcaptures, no source mutations),
run now. No human inputneeded. Next explicit note-to-chain/context relationship,
then final QA/Planner/fulltests/commit. Preserve existing written contexts.

Planner timingquarantine and independent literal presence/type/value checks added;
8newtestsPASS. Actualtie QA-v2 technicalPASS, allcode/sourceunchanged.5captures:
Muse7629notes183true63chains;StaticX4181/113/107;REM11205/1217/1189;
deadprobe11611503918/267/244;deadprobe9596032302/56/55. All1836true flags
mechanically resolved under acceptedpredicate;0actual unresolved in these5, not
claimedotherwise.13deadnotation chains retained explicitlyunpitched. Total29235
originalnote occurrences, no coordinatesremoved. Alladdedphysicalsettings/occurrence
fieldpresence/type/value independently compared to rawsource. All chain endpoints
and extent independently compared, actualstrippedsource workerreconstructs T1+
chains with SAMEcode. v3 adds actual5I/Odenialchallenges onnewcapture; running.
Fullinstalled/baretests running. No needforuserinput.

Full855tests exposed13historical-isolation regressions (6failures/7errors): old
worker explicitstaging omitted newpurepredicate dependency musical_tier2.py.
Original failures retained ties-full-tests.txt/ties-bare-tests.txt. Planner chose
minimal exactstaging/readallowlist/hash fix, not newcodegenerationlayer. Added
ONLY musical_tier2.py to legacy stagedfiles/workerreadallowlist/corpuscodehashes;
parentrecords exactstagedcodehashes. No broaderrepo/source/cache/networkaccess.
Targeted8legacytierQA+7corpusQA tests nowPASS. Fullretets/v4real-source rerun
withall5captures nowactive. No musicaleligibility changed. No userinputneeded.

Written tie slice final: PlannerAPPROVED actualv4 + independently8testsPASS.
v5replay after EOFwhitespacecleanup also technicalPASS all5captures, source/code
unchanged;5actualI/OdenialsPASS. Full855tests854PASS1optionalskip22.068s;
bare855tests853PASS2skip22.064s. All13historicalregressions repaired, retained
originalfailures. gitdiffcheckPASS. Originalfields/techniques/pedaldetectors intact.
No acoustic/listening/artistquality claims. Allsource-derivedartifacts private.

Acceptance checklist closure: fieldinventory/sharedpurepredicate/exact schema4
sourcefacts+sameinverse/namedwrittenchains+timingquarantine/frozenactualnewsource
and4regressions/Plannerend/fulltests DONE. Commitpush/CI next.

Planner nextstartcontractapproved: pure chain-to-existingharmoniccontext query,
1..3explicitclocks -> originalconstituents -> SAMEjointmembershiphelper; halfopen
unique mapping, preserveclockorder+origin+constituentIDs. Wholechain quarantine
fortiming/dead/unresolvedincoming; nochaindoesnotproveattack. Compatibleharmonic
scope/resourceoutcomes retained, no newweighting/keyclaim/techniquecodecs.
Fresh random PinkFloyd Money15761/rev9854033,11tracks,seed15116332956693008344,
querym frozen anddownloaded BEFOREnewchaincontextimplementation, no reroll.
Do not implementnextuntilcurrentcommitCI verified. No humaninputneeded.

Written-tie delivery164e981 main CI39837869218SUCCESS. Plannerapprovedclosure.

## Chain-to-harmony context — START and midpoint
Preimplementation Plannercontractapproved: up to3explicitclocks map uniquely to
originalchainconstituents; wholechain/part harmoniccoverage, preserveclockorder,
wholechain quarantine timing/dead/unresolvedincoming, nochaindoesnotproveattack.
No harmonicweightingchange. Exactcontinuity and chordmembership distinct.

Added tied_harmonic_context using SAME harmonic_membership_evidence. Controlled
C4 tied acrossCmajor->Gmajor changes membership(member,nonmember) while original
2writtenoccurrences retained. Untiedsamepitches have SAMEmemberships butNOchain;
no manufacturedlabeldifference.6testsPASS including reverserequestorder, endpoint,
part/time/stale/rootrefusals, dead/orphan/timingquarantine, resourceoutcome.
Planner midpoint independently5testsPASS then caught orphan-onlytrue declaration
being collapsed into NO_DECLARED_CHAIN. Fixed distinct unresolved-declaration
status + exactreason/ref;6thregressionPASS. No inventedlink/attack.

Frozennewrandom Money15761/rev9854033 seed15116332956693008344/querym11tracks,
chaincontextplan frozen BEFOREcode/results. Everypart ALLchainorigins+unresolved
inventory; firstsourceaddresschain, no quarantine/easierreplacement; first/last
constituentmidpoints; ensembleH wholechain,50000cap. Source/codefreeze runner
executes actualsharedquery+wholeT1inverse stripped andisolated. Independentraw
source fields/ties/clockmapping and existingindependentharmonicDAGlabels verify
jointwitnesses, notseparategenerationlogic. v1 newMoney+retainedMuse running.
Acceptance pendingactualsource/Plannercompletion/fulltests/commitCI. No userinput.

Chaincontext v1 interrupted beforecase completion for targetedprofiling; recorded
asINTERRUPTED, not mathematicalfailure. SameMoney preserved, no reroll. Fullquery
profile: extract0.14s,analyze5.11s,279chains8.13s; all11partchainqueries92.56s.
Trace shows repeatedpublicfullsongvalidation, not harmonicDAG explosion. Planner
approved smaller runner-only change: study consumesstrippedT2 justlikeisolatedworker;
publicvalidation staysenabled, no privatealreadyvalidated bypass. ActualfixedMoney
part0firstchain event:15761:0:20:0:2:0 clocks1031/8,259/2: full9.125s,
stripped8.640s, STRICTOUTPUTEQUAL. Modestimprovementonly; notgeneralbenchmark.
Syntheticstrip/full equality and invalid stripped/stale rejection testsPASS.
Full schema4 inverse stillcompares completeexpectedT1 heldonlyinparent.

v2 actualMoney+Muse source/context/isolatedQA running; scope first/lastmidpoints
only, entirecandidate/refusal denominatorretained. ExistingindependentharmonicDAG
oracle extended tovalidatejointpathwitnesses usingitsOWNcomputed72labels, not
producerhelper. Sourcecheckerrejectsomittedeligiblemembership/invalidquarantine.
No humaninputneeded; next fulltests/endPlanner/commitCI afterrealartifacts.

Chaincontext sealedv2 completedtechnicalPASS code/sourceunchanged:Money7411notes,
325true flags279chains11distinctparts:7selectedqueries4nochain;3of7membership
changes(2member->nonmember,1reverse). Muse7629notes183true63chains10parts:
4selectedqueries6nochain. All sourcefields/tiegraph/clock-to-original-constituent
mapping/independentoptimalDAG+jointwitnesses andactualisolatedwholeT1+queryPASS.
No annotatedkey/suspension/functionaccuracy claimed. Midpoints only, notallchain
musicalchanges. No actualquarantinedfirstchain inthese2cases; syntheticcoverage.

Planner caught checker denominatorgap; targetednegative testreproduced duplicate
partrow incorrectlyPASS. AfterSEALEDv2 completed: requireexactuniqueIDinventory
andcompleteperpart unresolvedsubset fromalreadyrawvalidatedgraph.8testsPASS,
includingdup/missingpart/omittedunresolved. PerPlanner, no repeatunchanged180s
producer/inverse solelyforvalidatorrepair. Repeatable reaudit_tied_harmonic_context
validatesBOTHoriginalsavedstudies/upper/source, exactstagedcode/inputhashes and
actualworkeroutputstudy equality, core+producerstudyfunctionunchanged, separate
validatorversionhashes; originalverdictunmodified. Correctedreaudit-v1PASS6.69s,
allinputs/source unchanged. DoesNOTclaimnewinverseexecution. Originalred retained.
Planner finalreviewrequested; fullcurrenttests running. No userinputneeded.

Chain-to-harmony finalPlannerAPPROVED bounded slice afteractualsealedv2+corrected
reaudit inspection, independently8testsPASS. Full863tests862PASS1optionalskip
23.372s;bare863tests861PASS2skip23.373s. DiffcheckPASS. NextverifiedcommitpushCI.
No source/annotations/audio published; no acoustic/key/function/artistclaim.

NextPlanner direction: explicitexistingtonalcandidate -> optionalreferencecollection
degree/register viaSAMEintervalrelations; compareidenticalnotes underparallelmajor/
naturalminor; eligibleconsecutivepairs differentiatechromaticdistance vsadjacent
scaledegree. Outsidecollectionunmapped; no nearestdegree/authoredspelling/chordmode/
inferredkey. ReusecontextIDs, no bulknote*candidate products. Startcontractbeforecode.

Delivered chaincontext f255003 main, CI39840366808SUCCESS.

## Conditional reference-collection degree — START beforeimplementation
Plannerstartcontractapproved: exactinteger degree1..7/register integer, signed
7*octavedifference+degreedifference; adjacencyabs1 includingoctavecrossing.
Preserve chromaticdistance, outside/unknownunmapped; no nearestdegree, authored
spelling, chordmode, selectedtruekey/function or nonzero generation. Existing
motioneligibility handlesgrace/polyphony/gaps withoutskips. SAMEequation bothways
forMAPPEDmembers; outside pitches retainexistingexactrealization. No bulkproducts.

Fresh frozen Nirvana Aneurysm14355/rev9766773,6tracks, seed13554092013439674791,
queryn BEFOREcollectioncode/analysis. collection-plan.json frozen1e-12 KS maximum
numeric tie tolerance; uniquehighestfinite pooledKS is QUERYREFERENCEONLY, original
scoresretained + bothparallelmajor/naturalminor candidates. Tied/undefined maxima
inconclusive no arbitrarywinner. Everypart/voice first3originalsourceaddresses,
no grace/unknown/polyphony/rejectedsequence replacements. Native music21oracle
explicitnaturalminor +pitchclassonly, registerequation separatelychecked.

Acceptancechecklist:
- [ ] Sharedpuredegree/registerequation solvedforward/backward, stricttypes.
- [ ] Existingglobal/temporalnotecontexts exposeoptionaldegree usingSAMEhelper.
- [ ] Candidate-conditional motion distinguisheschromaticdistance/diatonicadjacency;
      preserve sourceeligibility/refusals, outside/unknown no guesseddegree.
- [ ] Frozenparallelcollectioncontrasts/octavecrossings/leaps/strictnegativecases.
- [ ] Newrandomsource +independentnativeScale/raworacle, strippedsamequery+T1inverse.
- [ ] Planner midpoint/end, fulltests, ownfilescommitpush, actualCI.
No human inputneeded. Next implementboundedcore+tests, thenactualsourceQA.

Collection actualv1PASS9254rawoccurrences/actualstrippedwholeT1+queryinverse,
3072nativeScale checksall12tonics MIDI0..127. Strengthenedv2 adds independentnative
KS/TKPprofileoracle336scores, exactquerywinner/tolerance/tiedmaxima/parallelmetadata
checks+negativeunit; no musicalcore changes. v2technicalPASS/code+sourceunchanged.
12parallelcontexts36candidate-noteevaluations25mappedshared-degreeinverses;
unmapped/unknownretained.6triples:3sourceeligible3refused, no replacements.
ExplicitqueryrefBminorKS0.7702642669585642 vsparallelBmajor0.3999940666498063;
NOTestablishedkey/mode. Actualpart2notesdegree7undermajor vsunmappednaturalminor.
Nativeoracle comparisonpitchClass, no inventedauthoredspelling; sourcewarning
provenance remainsacceptedwarninggenerator, notnewindependentwarningvalidation.
PlannerfinalAPPROVED afteractualv2/source/oracleinspection+independently8testsPASS.
Fullsuite results next; no audio/listening/stylequality claim. No userinputneeded.

NextPlannerapproveddirection: one explicitreference+existingharmoniccontext query
connects outside-reference vschordmember distinction. Preservejointpathalternatives;
no newscore/vocab/candidateproduct. Authoredcontrast unchangedA# outsideBnaturalminor
butmemberF#major; actualsource maydisagree/unknown, preserveit. DoNOTinferharmonicminor,
tonicization,function,chordmode orkey. Implementaftercurrentcommit/CI gate.

Collection full871tests870PASS1optionalskip26.104s;bare871tests869PASS2skip26.102s.
Acceptancecheckboxes core/global+temporal/motion/contrasts/native+raw+isolated/
Plannerfulltests DONE. NextcommitpushCI. Existinglockedsource/techniques untouched.

Collection8bfe08e deliveredmain, CI39842382929SUCCESS.

## Explicit reference + harmonic context — START contract / midpoint
Plannerstartapproved and jointreference-plan.json frozenBEFOREimplementation:
EricJohnsonCliffsOfDover6701/rev9071983,3tracks,seed11284217123988564840/queryd.
UniqueKSqueryreference1e-12 tiepolicyONLY. Everyownedpartvoice first3sourceaddresses,
positive-durationmembers atmidpoints, graceexplicitunqueryable, no replacements.
Hensemble coversfullminstart..maxend,50000cap. Resource/unknown/timingretained.

Contract: ALLmarginalcoveringlabels retained (notCartesianjointassignments);
existingjointmembershipvectors unchanged +onewitness each(existence,notuniqueness).
CompleteHpackage/DAG/scoring inputs storedONCE withcanonicalSHA256/requestref.
Global/partreferences respectpartscope; temporalreferences enforceactualqueryclock
inframe. SAMEdegree/rootrelations, nonewscore/vocabulary/keyproduct. Controlled
A#outsideBnaturalminor canbeF#majorchordmember; explicitF#minortheorynonmember
isNOTassertionminorwins afteraddingA#toobservedsource. No function/modeinference.

Acceptancechecklist:
- [x] Purejointquery+stablecompleteHreference, scopes/unknowns/nonrunexplicit.
- [x] Sharedpitch/chordmembershiphelper factored withouteligibilitychange;
      jointMunchanged andallmarginals;5authoredcontrast/ambiguity/scope testsPASS.
- [ ] Newfrozencapture source+nativeexplicitreference/independentHjoint checks.
- [ ] ActualstrippedwholeT1+samequeryinverse, producer/sourceintegrity.
- [ ] Planner midpoint/end +fulltests +owncommitpushCI.
No humaninputneeded; nextsourceQA. Existingtechniquedetectors/conversionunchanged.

Joint-reference v1 actual PASS, source/code unchanged. Fresh Cliffs Of Dover
6701/rev9071983:3842source occurrences,192native profile comparisons, all3fixed
ownedvoice triples. Pitched selected notes inside reference ANDchord; percussion
unknown retained. Outside-reference/chordmember contrast controlledtest only.
312resolved/11unresolved ties retained. Complete independent DAG+ALLfeasible
jointvectors/marginals+native reference/sourceclocks/hash checks PASS.
Actual -I -S worker, no source/lower input, reconstructs ENTIREownedT1 +SAMEstudy.
Planner final independently rehashedfreeze/worker equality and5testsPASS:
APPROVEDboundedQA3, no newblocker. No truekey/mode/function/audio/styleclaim.
Full876tests875PASS1optionalskip26.449s;bare876tests874PASS2skip21.144s.
Allremaining acceptance boxes above DONE except delivery commit/CI, next.
