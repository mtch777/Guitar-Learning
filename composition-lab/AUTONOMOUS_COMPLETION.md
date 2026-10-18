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
