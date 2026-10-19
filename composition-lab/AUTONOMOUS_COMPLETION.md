# Autonomous completion ledger

User directive (2026-10-18): complete all independently achievable work across
steps 2–8, self-QA with an independent QABot3000 reviewer, without requesting
routine input or another authored listening exercise. Pedals are approved/closed.
Never manufacture human musical judgments or claim perfection from parser tests.

## Execution gates

- [ ] 2: Audit remaining source-technique families against definitions, raw source
  and independent import. Preserve accepted pedals and bend baselines by hashes.
  Require reconciled denominators, unknowns and negative fixtures.
- [ ] 3: Fit artist profiles on development work families only. Preserve provenance
  and fidelity exclusions. Provide song-balanced and pooled distributions,
  contextual technique relationships, held-out scores and simple baseline scores.
  Test invariance to held-out note/technique perturbations in the fitted profile.
- [ ] 4: Derive reusable context-conditioned methods from observations, rather
  than authored technique rates. Record support, fallback and unsupported cases.
  Require zero invented source occurrences and traceable training provenance.
- [ ] 5: Execute exact recreation and contextual transfer on genuine passages.
  Preserve rational time, strings/voices, tuning, ties and technique metadata.
  Verify independent GP reimport and measurable permitted/locked changes.
- [ ] 6: Reconcile all controls with literal 0% locks and 100% freedom from direct
  reference values. Test perturbation invariance and measurable intermediate
  behavior; reject conflicting controls instead of silently violating locks.
- [ ] 7: Integrate profile-conditioned phrase/role generation and export actual GP
  files. Verify bar coverage, playable positions, role relationships, source-copy
  checks, diversity and comparison with preserved prior engine outputs.
- [ ] 8: Run held-out/source-copy/control regressions, independent imports, finite
  non-silent playback checks, UI QA when relevant, and QABot3000 review. Publish
  only verified source-free code/results/logs to main and verify CI/Pages.

## Reviewer contract

QABot3000 is an independent agent, not simulated listening evidence. It audits
implementation, metrics, tests, claims, leakage and preservation, reports concrete
issues, and reviews repairs. Human listening/physical performance remains an
explicit unverified gate where it cannot be established by scripts. A blocker
does not stop independent work in later steps.

## Progress

- Main synchronized at 0665fd4; read latest context and active implementation.
- QABot3000 dispatched read-only audit of steps 2–8. No pedal changes authorized.
- Known legacy gap: engine_controls.py still targets percent differences and
  deliberately excludes original pitches at 100; it cannot be advertised as
  satisfying the newer reference-freedom contract. Preserve as historical module
  until a separately tested replacement is ready.

## First integration checkpoint (work continues)

- Added development-only conditional annotation profiles with connected-family
  split verification, pooled/song/family weighting, explicit per-feature unknown
  masks and backoff counts. 190,890 eligible attack groups; 20 temporal-ineligible
  guitar/bass tracks excluded. Training:146,159 events,72 entries,56 connected
  families. Held-out scoring covers9 eligible entries. Mutating held-out outcomes
  and contexts cannot change the fitted model.
- Conditional aggregate NLL0.1187101483 vs unconditional0.2127248967, equal-song;
  these are annotation-model diagnostics, not musical accuracy. Double-stop
  gains partly reflect its cardinality definition. Finger-vibrato has zero
  positive held-out annotations and conditional NLL is worse than unconditional;
  no claim of validated vibrato prediction or artist generality is made.
- QABot3000 independently found and drove repairs for beat-level vibrato,
  unknown pedal coverage, order-sensitive onset groups, duplicate-sensitive
  smoothing, dead/unknown-pitch exclusions and misleading backoff reporting.
  Eleven profile tests independently pass. Private profiles-first/v2 are
  superseded diagnostics; profiles-v3 is hash-sealed and current.
- Separate new-score freedom layer preserves literal0 and allows coincidence at
  100; incompatible topology fails closed. QABot found MIDI/tuning/program/tie/
  span validation holes; repaired. Nine independent control tests pass.
- Pitch proposer receives a whitelisted context with no source pitches/frets/
  strings. Actual GP controls:13 variants, zero byte-identical and full-freedom
  reference perturbation invariant. Per-event retry/cache hardening reduced
  rejected whole-score proposals from82 to0 in the measured batch.
- New empirical corpus composer preserves legacy engine. Learns source meter,
  rhythm, voicing intervals, root steps and contour-sensitive bar recurrence;
  handles rejected/tied bars without fabricated continuity. QABot independently
  caught rejected-bar leakage, recurrence omissions, biased plan sampling, stale
  motif endpoints and joint-offset event weighting; repaired.
- Three-role joint version uses aligned source configurations and observed
  simultaneous root offsets, balanced by family then song. Written minimum pitch
  is not an inferred harmonic root. Held-out benefit of this conditioning remains
  to be measured; counters are not acceptance evidence.
- Twelve32-bar independent-role baseline GP files and twelve32-bar joint GP
  files exported, independently imported and rendered finite/non-silent/unclipped.
  All13 current pitch-control GP files also independently imported and rendered.
  Native checks cover pitch/local timing/tuning/physical string/fret/meter/program/
  tempo. Fractional-tempo137.1234 in7/8 independently passes after precision fix.
- Composer is still an empirical prototype: no learned phrase intent, physical
  technique acceptance, fully integrated performance methods or originality verdict.
  Source-copy/diversity checks, joint held-out comparisons, performance integration
  and broader controls are next independent work; do not request listening yet.

Private outputs: local-artifacts/artist-pipeline-v1/{profiles-v3,compositions-v2,
compositions-v3,controls-v2,fractional-tempo}. Commercial source, learned note-level
models, GP/audio and private provenance are never published. No pedal code changed.

## Performance integration and independent validation (work continues)

- Foundations committed/pushed as202706072f4cb96cb073d15004e8f0f019e066a7.
  GitHub isolated GP7 CI succeeded: actions/runs/39166644468. No website change;
  Pages was not triggered. Latest main pulled safely before this continuation.
- Added per-technique eligible-opportunity models:134,606 development observations.
  Each feature fits its own family/song-balanced denominator; unrelated notes do
  not dilute open-string transition rates. Unknown natural pitches, ties, grace,
  dead/harmonic events and cross-voice monophony are handled explicitly. Full
  annotation inventory remains separate from this restricted generation scope.
- Held-out eligible annotation prediction is mixed: hammer-on-from-open NLL
  0.77588 conditional vs0.99579 unconditional; pull-off-to-open0.65929 vs0.90356.
  Bend0.03098 vs0.02971 is worse; vibrato has zero positive held-out annotations.
  No parameter tuning/promotion or expressive-intent claim from these outcomes.
- Same-artist/source training provenance checked; all outputs preflight against
  overwrite. QABot reproduced and drove repair of playback-sidecar overwrite,
  wrong denominator, cross-voice and grace-context mismatches. Unsupported source
  techniques stay locked. Supported100 proposals hide original annotations;
  zero remains byte-identical and intermediate masks are nested.
- Independent playback found two real bend incompatibilities in AlphaTab1.8.4:
  displacement truncation to half-semitones and removal of some interior curve
  points. Never round silently. Retain251 compatible raw source templates;
  exclude69 resolution,320 normalization/encoding and2 zero-displacement cases.
  This is a playback compatibility subset, not the artist's entire vocabulary.
- performed-v1/v2/v3 are rejected/superseded diagnostics. performed-v4 contains
  36GPs:12 baselines each at0/50/100 performance freedom. All36 independent
  imports preserve pitch/timing/tuning/string/fret/program/meter/tempo; all36
  directed-HOPO/vibrato checks pass;108 track-curve checks pass with zero measured
  error. Twelve100% native previews finite/nonzero/unclipped; never listened by
  the agent. Full-freedom selected annotations:71 bends,4 vibrato,20 open hammer-ons,
  12 open pull-offs. These counts are engineering outcomes, not musical acceptance.
- QABot independently checked every GP/code/audio hash and native log; approved
  this bounded checkpoint. Human musical quality and physical legato remain open.
- Added known-corpus relative attack-window audit with rational timing, tied
  sustain lengths, numeric pitch normalization, stratified examples and all-track
  openings.12 generated pieces have no identical attack content/shared8-attack
  relative openings. Matches:157 varied8-event,9 varied16-event,zero varied32-event;
  constant patterns separately520/38/1. All9 varied16-event matches contain two
  pitch sets, one minimum-pitch change and one note length. Supplied-corpus only,
  within-voice attack content, not complete sounding texture or originality proof.
- Held-out written-root comparison: bass joint NLL2.522 vs absolute3.527 and
  shuffled4.829; melody joint4.547 vs absolute3.779 and shuffled4.657. Roles are
  heuristic and roots are minimum written pitch. Joint melody is not superior;
  no claim that this validates generated harmony or source feel.
- Python regression322 run/321passed/1 optional skip before final added template
  test; all24JS tests and Vite build pass. Final complete suite repeated before
  committing. Public source/log only; learned models, source occurrences, scores
  and previews stay ignored. No approved pedal code/UI changed.

Next independent work: broaden rhythm/form/instrumentation controls without
violating literal locks; improve phrase/role methods against development baselines;
reconcile remaining source-technique/control coverage. Musical acceptance remains
a later human gate, not a reason to interrupt independent implementation now.

## Rhythm control checkpoint (work continues)

- Performance/copy/joint diagnostics committed/pushed as78361d72a66cad0fde254c71e32dbb7adda2f628.
  GitHub isolated GP7 CI succeeded: actions/runs/39169062040. No website changes.
- Reproducible performance-v5 fit matches performance-v4 model/shapes/evaluation
  exactly; fitted code/source hashes recorded privately. Ten technique tests pass.
- New rhythm proposer sees only role, meter and locked event cardinalities, never
  reference note timings. Uses family→song→compatible-pattern sampling; no forced
  difference.0 literal canonical identity (GP byte-copy in runner),100 invariant
  to reference timing perturbation;25/50/75 nested release masks. Unsupported
  event/rest/voicing topology fails closed. Tempo, meter, pitches, voicing and
  event count remain locked. Changed timing can change intertrack simultaneity;
  this is explicitly not an independent lock of sounding chord relationships.
- rhythm-v1 superseded by hardened rhythm-v2:60GPs (12pieces×5strengths). All60
  independently imported with exact pitch/timing/tuning/fret/string/meter/tempo.
  Released bar-voice units at25/50/75/100:264/648/960/1152; actual changed units
  54/137/206/250. Coincidence is allowed, so100 does not force every unit to differ.
  Twelve100% previews finite/nonzero/unclipped. No listening judgment fabricated.
- QABot approved bounded rhythm logic; empty voice opportunities and0% role
  validation hardened. Three dedicated rhythm tests pass. All prior outputs and
  pedal modules remain unchanged. Broader form/instrumentation controls and
  phrase/role modeling remain incomplete; do not mark the roadmap finished.

## Development-selected role-pitch checkpoint (work continues)

- Rhythm controls committed/pushed as29dc7664f920901679f494a7b77ef3952b50e140;
  isolated GP7 CI succeeded: actions/runs/39169251245. No website changes.
- New normalized128-pitch model compares absolute written pitch, contiguous
  within-bar motion and harmony-relative alignment. Five inner development
  connected-family folds select among15 convex mixtures, equal-family then
  equal-song within family.44,419 development observations; no outer outcomes
  used for selection. Source-composer semantic hash binds exact training input.
- Selected weights absolute/motion/alignment: melody0/.75/.25, bass0/.5/.5.
  Outer diagnostic4028 observations: melody2713 across8songs, bass1315 across2.
  Melody selected NLL3.03247 vs absolute3.83756, motion3.02956, alignment3.96730;
  the mixture is NOT better than motion alone. Bass1.10098 vs absolute3.52963,
  motion1.42467, alignment2.59369. These are teacher-forced written-root scores,
  not generated rollout, harmonic-function, artist-feel or musical-quality proof.
  Outer songs were already examined in earlier diagnostics, not pristine tests.
- QABot found nonfinite-weight acceptance, inconsistent within-family selection
  weighting, multivoice harmony ambiguity and weak source revision provenance;
  repaired/tested. Five model tests and four transfer tests independently pass.
- Controlled transfer hides original target pitch/fret/string and arbitrary
  metadata; locked harmony, event timing/count, form, tuning and instrument data
  remain available. Model conditions on generated previous notes. Playable roots
  are sampled with normalized restricted support; source voicing cardinality
  unsupported after50tries fails closed. No forced difference. Main-voice only;
  multivoice source input fails closed instead of arbitrary voice projection.
- role-pitch-v1/v2 superseded by reproducible role-pitch-v3. role-transfer-v1 is
  unsealed diagnostic (code-change guard fired during QA); role-transfer-v2 is
  final bounded batch:36GPs at0/50/100. All36 native imports preserve expected
  pitch/time/tuning/string/fret/meter/program/tempo. Twelve100% renders finite,
  nonzero/unclipped. QABot independently checked allGP/code/model/audio hashes
  and approved. No listening judgment fabricated.335Python tests run/334pass/
  1optional skip; prior24JS/build remain green (no website changes).
- Prior external benchmark is already completed, not currently login-blocked:
  benchmarks/RESULTS_2026-10-15.md documents official AnalysisGNN weights/inference,
  exact Sweet grace timing repair and model disagreement measurements. Existing
  .local/models/analysisgnn-official/model.ckpt stays private. EXTERNAL_COMPARISON.md
  documents actual Yin-Yang and AMT runs and their failed/limited gates. Preserve
  those results; the current Invent Animate corpus pipeline is a distinct method.

Next: combined role-pitch/performance exports and source-copy screens; remaining
technique/style and form/instrumentation control coverage. Independent engineering
continues without reopening approved pedals or requesting another tiny review.

## Integrated performance, palm muting and metadata checkpoint

- Role models/controls committed/pushed as9e13f6d8ee6cab86f0229e44a5d68cf5756c3225;
  isolated GP7 CI succeeded: actions/runs/39169744217. No website changes.
- integrated-performance-v1 combines12 full-freedom role-pitch cores with0/50/100
  learned performance:36native imports,36directed-link/vibrato checks,108curve
  checks pass;12fullfreedom previews finite/nonzero/unclipped. Updated known-corpus
  attack screen:97varied8-event,3varied16-event,zero varied32-event matches;
  constant repeats409/34/1. No identical attack streams/shared openings; no
  originality verdict. Relative-window screens exclude performance expression.
- Separate palm-mute model uses exact eligible natural untied regular coattacks.
  Shared group decision applies all notes together; mixed source groups are
  explicitly counted/excluded, never converted to all-muted truth. Matching
  numeric/string/fret guards and original-note-definition uniqueness required.
  OnlyPalmMuted property may change;0 byte-identity,100 reference-flag invariant.
- Raw eligible source inventory BEFORE flag filtering:development26732all-muted,
  134431none;held-out2758all-muted,14654none;zero mixed groups observed. This is
  not the fitted positive count. Held-out scored13952groups/2021positive;
  conditional annotation NLL0.19611 vs marginal0.41723. Not performed muting truth.
- Self-QA regression exposed missing propagation of vibrato playback settings;
  repaired before final render. palm-mute-v1 is superseded diagnostic. Final
  palm-mute-v2:36GPs,36native note-flag/pitch/timing imports,36HOPO/vibrato checks,
  108curve checks pass;12fullfreedom previews finite/nonzero/unclipped. All36
  preview sidecars retain360/.25 vibrato settings. Fullfreedom has1656 muted
  notes across12 outputs. QABot independently verified hashes and logs; approved.
- Global tempo/MIDI-program controls fit family→song source choices.0 literal
  canonical identity/GPcopy;100 invariant to original tempo/program perturbation;
  nested release masks. All quarter-note timing, note content, tuning, fingering,
  track/role layout and performance locked. This is NOT full tone/arrangement or
  expressive tempo-map control. Missing irrelevant support conservatively fails.
- metadata-v1:72actualGPs,72native imports pass;12program100 previews finite/
  nonzero/unclipped. Programs100 changes23track programs,tempo100 changes12tempos;
  coincidence allowed. QABot independently verified all hashes/code/import/audio;
  approved. Five palm-method/runner tests and three metadata-control tests pass.
- Source marker form baseline is deliberately unpromoted:38development forms,
  four held-out entries; conditional length NLL2.18378 vs marginal2.16376 (worse).
  Twelve32bar samples yielded zero returns and unchanged musical content apart
  from section markers.12native imports pass; no new listening study advertised.
  Labels/markers do not establish thematic identity. New conservative exact
  content recurrence experiment is underway, preserving marker-only baseline.

Next independent actions: finish exact-content form experiment/QA; consolidate
technical coverage and remaining failed gates; do not treat sample counts, parser
success or a clean commit as proof of musical correctness.

## Full-song form and annotation checkpoint (2026-10-18)

- Added development-family-selected content-form experiment. Exact source content
  identity includes rational timing, resolved ties, grace ornaments and known-pitch
  masks. Author boundaries remain inputs; identity is not inferred phrase intent.
- Rejected clean-bar-only recurrence evidence because it dropped tied/noisy sections.
  Unknown/static sections now abstain from identity evidence rather than becoming
  invented novel themes. No-supported-evidence models fail explicitly.
- Selected length mixture on five development-family folds. Outer diagnostic length
  NLL2.163736 versus marginal2.163756 is effectively tied, not a form-quality win.
- full-form-v3:four actual GP cores,131/108/118/152bars, with1/2/0/1sampled returns.
  Repeated generated sections preserve all roles; no forced return. Exact-clock
  bisect optimization matches linear oracle and previous deterministic replay.
- full-performance-v1 adds four learned technique families at0/50/100. full-palm-v1
  adds palm mute0/50/100 to those full-performance100 outputs. All12 final GPs pass
  independent native note/pitch/timing imports, palm flags, directed HOPO/vibrato
  checks and36track bend-curve comparisons. All12 retain approved360/.25 vibrato.
- Four final native-GM previews render completely at271.0/240.0/122.1/299.0seconds;
  finite, nonzero, unclipped. Explicit600second renderer limit; default120 unchanged.
  Original render attempt used incorrect soundfont path, failed without output;
  corrected to dist/soundfont/sonivox.sf2 and reran successfully.
- Added source/generated annotation comparison, clean pitched generated scores only.
  Source family-balanced versus generated equal-piece track mixtures are confounded;
  no aggregate style/quality score. Independent QA found incompatible-model and
  dead/unknown-pitch input assumptions; now rejected explicitly with regression tests.
- Twelve short integrated outputs:source/generated palm rates16.60%/7.51%, open
  hammer-ons2.10%/0.36%, open pull-offs1.19%/0.20%, close dyads1.03%/4.21%.
  These are diagnostic distribution gaps, not listening judgments. Fixing rates by
  arbitrary quota would conceal opportunity/arrangement mismatch; investigate that
  decomposition before adjusting generation.
- Regression:358Python tests run,357pass/1optional skip;24JS tests pass; diff check
  clean. No website edits; Pages deployment not triggered. Private scores/models,
  source analyses and rendered audio remain ignored and uncommitted.

Next: independent final-batch QA; commit/push this bounded checkpoint and verify CI;
then decompose technique opportunity versus conditional-rate mismatch. Musical
acceptance and independent arrangement/form controls remain open. Pedals unchanged.

## Proposal-versus-opportunity diagnosis (2026-10-18)

- Checkpoint8319749f24ecd5c8cc4739f6e2ed027451620895 pushed; GitHub isolated
  composition CI39183070860 succeeded. QABot independently approved final12GP
  exports/flags/links/36curve checks and four full WAV hashes.
- Added performance_sampling_audit.py:separate released eligible decision counts,
  probability sums, realized proposals and descriptive Bernoulli reference SD.
  Different opportunity units and weighting prevent treating these as note/style
  scores. No generation quotas introduced.
- Found legacy predictor boolean ORed fallback for every feature, even features
  absent from the specialized model. Thus fallback flags overstated unsupported
  contexts. Generator logging now uses requested-feature details; HOPO now logs
  its own fallback too. Probabilities, RNG draws and GP edits are unchanged.
- reporting-replay-v1 regenerated16short/full performance100 and16palm100 GP files.
  All32 outputs byte-identical to their verified predecessors. Earlier code hash
  seals remain historical evidence, never rewritten to pretend current-code hashes.
- Short-batch expected/selected: bends75.29/71;vibrato1.71/2;open hammer37.00/33;
  open pull16.42/20;palm722.35/742. Correct feature fallback counts0/6174,0/6174,
  18/137,10/124,6/9635 respectively. The old all-fallback reading was false.
- Only137open-hammer and124open-pull proposal opportunities across9635attack
  groups. The small realized total is consistent with these limited opportunities
  and conditional proposal probabilities. Not proof of equivalence to the source;
  source/generated arrangement distributions still differ. Treat arrangement/
  fingering opportunity formation separately from performance probability strength.
- Regression361Python tests run,360pass/1optional skip. Dedicated backoff regression
  proves unrelated missing features cannot mark supported bend context as fallback.

## Shared-context accounting and aligned-role experiment (in progress)

- Added exact rational descriptive decomposition on shared known notation contexts:
  generated-minus-source rate = context-mixture component +within-context component.
  Unsupported context masses reported separately; no invented rates/causal claim.
- QABot reproduced masked-feature weighting bug in initial implementation; repaired
  feature-specific known denominators, added run-level1/2vs1/101regression.4tests
  pass; final context-gap-v2 exactlyequals old result on fullyknown clean outputs.
- Shared source/generated coverage for performance features98.81%/99.94%. Palm gap
  -9.269percentagepoints decomposes to-9.630context-mixture +0.362within-context.
  This is coarse context accounting, not evidence that a single causal fix suffices.
- Reporting checkpoint0141e8223846073340a761d47bc178d762579ff4 CI39183308024 passed.
- Added opt-in aligned_patterns mode; defaultFalse path uses identical RNG sequence.
  All12 legacy default scores regenerated exactly equal to preserved canonical JSON.
  New12aligned32bar cores use222new recurrence cells with one observed song/bar
  bundle for allthree role rhythms/voicing intervals, four rejected proposals.
- Independent QA:6composer tests, actual duration/cardinality matching to source
  bundles,12core and36performance exports/nativechecks pass. Pitch RNG changes
  alongside rhythm: this is explicitly not an isolated pitch-locked experiment.
- Raw aligned performance/palm batches are diagnostics. Fairer comparison underway:
  aligned-role-v1 applies same frozen role-pitch model as integrated baseline, then
  aligned-integrated-performance-v1 and matching palm method. No model refit on
  held-out results. Source-copy and final distribution checks still running.
- Regression366Python tests run,365pass/1optional skip before final batch checks.

## Aligned integrated results (2026-10-18)

- Fairer stack retains the same frozen role-pitch model as the independent-role
  integrated baseline:36role0/50/100exports,12selectedrole100cores,36performance
  exports,36palmexports. Direct36role native imports and final36performance/
  36palm imports pass. Final36palmflagchecks,72link/vibratorrows and108curve
  checks pass. All12fullstrengthnativepreviews finite/nonzero/unclipped.
- QABot independently verified GP/model/code/audio hashes and exact rate claims.
  Close dyads4.213%→1.052%(source1.035%);palm7.512%→5.739%(source16.602%);
  openhammer0.363%→0.323%(source2.102%);openpull0.198%→0.132%(source1.189%).
  No promotion: mixed results and altered pitches/fingerings are explicit.
- Raw aligned-core supplied-corpus screening:9284eight-attackwindows with222varied/
  445constantmatches;8996sixteen-attackwindows with38varied/21constantmatches;
  8420thirtytwo-attackwindows withzero matches. No identicalgeneratedattackstreams
  or sharedrelativeharmonyopenings. Finalintegratedcopycheck remains inprogress.
- Existing independent generator remains default; regenerate all12preserved
  compositions-v3canonical scores exactly. Approved pedals unchanged.
- Final aligned-integrated supplied-corpus screen completed:9284eight-attackwindows,
  148varied/310constantmatches;8996sixteen-attackwindows,3varied/11constantmatches;
  8420thirtytwo-attackwindows,zero matches. No identical generated attack streams
  or shared relative harmony openings. Not an originality/copyright verdict.
- Current366Python tests run,365pass/1optional skip.24JS tests passed earlier with
  no subsequent website changes. Pages is unaffected; source-only CI must verify
  the next pushed checkpoint. No human input requested and no listening invented.

## Combined controlled pipeline (2026-10-18)

- Added compose_controlled.py and CONTROLLED_PIPELINE.md. Eleven independent
  supported settings:harmony,melody,bass,rhythm,tempo,programs,bend,finger_vibrato,
  hammer_on_from_open,pull_off_to_open,palm_mute. This integrates existing fitted
  methods; no new artistic rates or source-note templates were invented.
- Bounded input:plain generated3rolecores with matching canonicalJSON. Rejects
  existing performed scores, unsupported notation/controls, extraZIPmembers,
  mismatchedVERSION or GPIF data(exceptScoresummary), and GP/canonical mismatch.
  All0copies wholeGPbytes withoutmodelrequirements; nonzero rewriting can alter
  ZIPtimestamps, so deterministic musical replay compares archive membercontents.
- Stage order:rhythm→harmony→melody/bass→metadata→fourperformancefamilies→palm.
  Unrequested dimensions remain locked. Harmony stage samples only harmonytrack,
  so it does not demand vocabulary support for unrelated locked roles. Form,
  meter,tuning,trackcount,event/rest topology remain fixed. Pitches/timing can
  alter simultaneous harmony and performance opportunities; independence is of
  declared data permissions, not perceptual effect or inferred emotional purpose.
- QABot found actual palm-only failure with multiartist source model; repaired
  explicitartist API/config and cross-model consistency guard. QABot also found
  extraarchiveentries could be discarded; strictarchive guard and regression
  added.7integration tests pass, including harmony-only partialsourcevocabulary.
- pipeline-integration-v1/v2/v3 are preserved diagnostic iterations. v2failed a
  byte-replayassertion because gp_author stamps changed exports with currentZIP
  timestamps. Membercontents were equal; all0byteidentity was unaffected. No
  musical difference was hidden by ignoring this failure.
- Finalpipeline-integration-v4:17cases cover11standalonecontrols, all0, metadata/
  performancegroups, combined50/100 andharmonylocked withother10at100.17native
  imports,17palmflagchecks,34link/vibratorrows,51trackcurvechecks allpass. Five
  combined/performance/palm/harmonylocked previews finite/nonzero/unclipped.
- core-lock-proof.json verifies allrequested0corefacets,tempo/program/tuning in
  all17cases. pipeline-reference-invariance-v1 changes1392referencepitches/frets,
  timing in88voicebars,all3programs andtempo. All11controls100produce exactlysame
  GParchive MEMBERcontents as originalreferencecombined100; metadataZIPtimestamps
  are outside that comparison. This is one integrated perturbation, not universal
  validation of everypossible arrangement or perceptual similarity.
- Finalregression373Python tests run,372pass/1optional skip. Native actualfiles
  and source-free code changes are distinct from musical acceptance. Original
  source scores, profiles, feedback, intermediateGPs and audio stay private.

## Multi-core integration sweep and reproducible batch runner (2026-10-18)

- Committedd2d45d350e55322f7ae0e961a1b755ad762960d8; GitHubCI39185162321passed.
- pipeline-corpus-v1:12preservedcores×all11controls0/50/100=36GPexports,zero
  rejected proposals. All12zero outputs retain complete originalGPbytes.
- Independentnative36,palmflags36,link/vibratorrows72,bendcurvechecks108 pass.
  All12fullyunlocked nativeGMpreviews finite/nonzero/unclipped. QABot independently
  verified every output/code hash,zero identity, native checks andWAVhashes.
- Finalunlocked sourceannotationrates remain mixed:palmmute6.241%(source16.602%,
  priorintegrated7.512%);openhammer0.284%(2.102%/0.363%);openpull0.180%(1.189%/
  0.198%);closedyads1.963%(1.035%/4.213%);powerchords8.774%(9.014%/8.161%).
  Fixed3role versus source-track mixtures remainconfounded. No claim of better
  style, musical quality, emotional meaning, sourcefeel or originality.
- Added public run_controlled_batch.py instead of relying on an uncommitted
  one-off experiment script. Supports selected dimensions/strengths; records each
  failure, preserves partialfolders, continues independentcases, exitsnonzero
  for incompletebatch. Cross-case implementation/modelhash consistency required.
- Two batch regressions verify schema/failclosedbehavior and an invalidfirstinput
  cannotprevent a subsequent independent allzero export. Actualwrapperreplay:
  2cores×0/50/100=6outputs; allarchive MEMBERcontents match the corresponding
  previouslyverifiedsweep. Native6/flags6/links12/curves18 independentlypass.
- Current375Python tests run,374pass/1optional skip. No website code changed;
  Pages deployment is unaffected. Private scores/models/annotations/audio are
  ignored; only code, tests, documentation and aggregate progress are published.
- Important control contract: nestedrelease masks apply to fixed stage inputs.
  Combined upstreamchanges can alter downstream proposals/eligibility. Combined
  outputs are not globallynested percent-difference or perceptualstrength sets.
- QABot caught missingcross-strength sourcehash guard in initialbatchwrapper.
  Repaired per-source GP+expectedJSONseals; regressionproves changedinputinvalidates
  comparison while retainingthefirstvalidcase.3batchtests pass; current376Python
  tests run,375pass/1optional skip. public-batch-wrapper-v2 sixoutputs/twoinputseals
  matchv1 archive membercontents exactly; actualv2native6/flags6/links12/curves18
  pass. QABot independently approved repairedwrapper andsixoutputreplay.
- No humanmusical verdict requested or fabricated. Broadremainingwork includes
  independentform/tuning/track-layout freedom, richerartist/phrase/stylevalidation,
  and humanlistening acceptance. These boundedengineering approvals are not
  completionofeveryroadmapgate; preservebaselines and currentrejectedexperiments.

## Next integration gap: retain explicit generated thematic returns

Existing controlpipeline preserves sectionlabels/counts but independentlyfree
pitch/rhythm proposals can destroy actualreturningmaterial. Labels are not theme
identity. Do not advertise fullformalpreservation from staticmarker preservation.
Acceptance checklist for the next opt-in integration:
- [ ] Accept explicit generatedsectionplan only; validate exactbarcoverage,
  prioridentity/length, labels, voice/event/rest/cardinality topology andmeter.
- [ ] Reuse newlygenerated firstoccurrence material for returns; do not consult
  originaltarget pitches to manufacture100%proposals or infer unmarked themes.
- [ ] Assert all0pitch/rhythm facets remainliteral. Reject unsupportedintermediate
  pitch/rhythm release conflicts instead of overriding masks or weakening locks.
- [ ] Preserve all0GPbyteidentity anddefaultpipeline behavior when no plan supplied.
- [ ] Test sourceplan/score mutations, rawreturnmaterial, independentGPimport,
  longformfullrender andQABot review before claiming this mode verified.
