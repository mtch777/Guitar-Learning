# External pipeline comparison — 2026-10-16

Baseline main 211fcda. User requested execution, following feedback that the
consolidated batch had identical openings, folk/game-like melodies, weak harmony
and little source identity. Preserve all earlier outputs. Do not mistake a
model name, import, score export or metric for musical success.

## Acceptance checklist

- [x] Audit the exact Sweet review IDs 1/2/6/11 and cross-family opening reuse;
      compare note content rather than GP titles/hashes.
- [ ] Run upstream Yin-Yang generator/refiner/selector orchestration with actual
      source motifs and matched seeds; retain upstream revision/config/output,
      projection losses, inference logs and failures. Compare supplied form
      against prior learned-form/cached-pool baseline without claiming form was learned.
- [ ] Run an actual external contextual accompaniment model on fixed melodic
      controls, or record concrete checkpoint/runtime blockers and investigate
      alternatives. Verify control identity rather than accepting nominal conditioning.
- [ ] Export successful outputs as real GP and MIDI, independently import with
      alphaTab, report any quantization/fingering/track losses. Preserve raw output.
- [ ] Screen duplicate openings and source copying; use matched passage lengths
      and consistent preview rendering; keep source-bearing review artifacts private.
- [ ] Package a small review set with conditions/provenance concealed until
      judgment; human quality/style judgments remain unfilled.
- [ ] Run Python/JS/build checks as applicable, commit/push source and aggregates
      to main without concurrent overwrite; verify Pages for website changes.

## Execution log

- Clean clone fetched and fast-forward checked before edits; main 211fcda already
  current. Existing upstream Yin-Yang source, all three official weights and
  private GP sources available. No new source material or artist corpus supplied.
- Scope: faithful upstream contextual phrase generation plus one runnable
  external accompaniment implementation; do not silently replace either with a
  home-built sampler. WholeSong remains a form reference unless its complete
  required checkpoints and inference path can be verified.
- Confirmed exact first-four-second melody reuse in prior cases 01/02/06/11
  (Sweet) and 03 (Cloud), plus 05/09. Only 02/03 still match over eight seconds;
  the four reported Sweet cases are not identical full pieces. Audit explicitly
  checks zero-based MIDI melody channel 2 and rejects empty streams. An initial
  private channel-3 diagnostic was invalid and is superseded by opening-audit-v2;
  no empty-stream equality is treated as musical evidence.
- Yin-Yang upstream revision 59a2a001884a1f235ef9a0313565487874f6e3b9,
  generate.py SHA b43f12c0e2288e94341bf746bc8b1695df5f4b76259424fc11e2cc30e89b715f.
  Official orchestration executed unchanged with safe strict local weight
  loading, source motifs, supplied ABA/ABC, three phrases per section. Per family:
  selector-on ABA 15 generator / 16 refiner / 30 selector calls; selector-off ABA
  3 generator / 4 refiner calls; ABC adds one new-section refinement. Different
  candidate budgets are explicit, not a compute-matched selector ablation.
- Installed miditoolkit 1.0.1 in the isolated venv after an actual missing import;
  copied upstream numeric key-profile asset into each private working directory
  after inspecting its pickle globals. No upstream source code or model asset is
  vendored in Git. YAML/source data and raw predictions remain private.
- AMT official source revision af37397922665a0fb8d474d7988b0f3755a38d45;
  official small model revision fa800530aa1126dd6b58b38f3bdb8fcec9c9d4f5,
  512,433,185-byte weights SHA 45af5006d529a19af3654c729192c072f3aeb9e7e13e9eaf92c19bfd7c87e4d8.
  Model card declares Apache-2.0; underlying Lakh score rights are distinct.
  Weights loaded with weights_only=True, exact parameter matching after documented
  base-key prefix and tied-output-embedding conversion. No random missing weights.
- Initial Cloud source motif at bar 5 had silent rhythm/bass. Retained as a
  negative input-context experiment (zero distinct support output); main v3
  protocol picks the first representable motif with >=4 attacks in each support
  part: Cloud bar 13, Sweet bar 9. Key/mode labels are estimates from that motif,
  not adjudicated global source keys. Projection excludes other chord tones,
  voices, grace notes and tie continuations; it does not retain full performance.
- Bridge-style AMT future-input and instrument-mask exploratory runs were sparse;
  the long uncontrolled bridge continuation was stopped and its logs preserved.
  Main accompaniment comparison uses the upstream accompaniment controls API,
  five-second source history, fixed source lead, matched seed and future melody
  supplied vs absent. Post-composition lead preservation is explicit rather than
  a claim that the model itself reproduces locked notes. Cloud future-control run
  completed: 103 sampling calls, 44 new support attacks after the five-second
  source prefix. Other conditions continue independently.
- Generated GP export supports rational polyphonic lanes and real cross-bar
  ties, retaining unprojected raw MIDI separately. AMT support is quantized to
  1/8 quarter; native tuning/range octave changes and omitted percussion are
  counted. Lead timing comes from the rational source projection. Physical
  multi-voice string conflicts are not certified by this exporter.
- Current regression check: 105 Python tests and 16 JS tests pass. External
  inference dependencies stay optional; source-free CI does not load weights.
