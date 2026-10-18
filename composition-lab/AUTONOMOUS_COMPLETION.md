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
