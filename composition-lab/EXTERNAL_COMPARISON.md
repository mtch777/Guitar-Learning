# External pipeline comparison — 2026-10-16

Baseline main 211fcda. User requested execution, following feedback that the
consolidated batch had identical openings, folk/game-like melodies, weak harmony
and little source identity. Preserve all earlier outputs. Do not mistake a
model name, import, score export or metric for musical success.

## Acceptance checklist

- [x] Audit the exact Sweet review IDs 1/2/6/11 and cross-family opening reuse;
      compare note content rather than GP titles/hashes.
- [x] Run upstream Yin-Yang generator/refiner/selector orchestration with actual
      source motifs and matched seeds; retain upstream revision/config/output,
      projection losses, inference logs and failures. Compare supplied form
      against prior learned-form/cached-pool baseline without claiming form was learned.
- [x] Run an actual external contextual accompaniment model on fixed melodic
      controls, or record concrete checkpoint/runtime blockers and investigate
      alternatives. Verify control identity rather than accepting nominal conditioning.
- [x] Export successful outputs as real GP and MIDI, independently import with
      alphaTab, report any quantization/fingering/track losses. Preserve raw output.
- [x] Screen duplicate openings and source copying; use matched passage lengths
      and consistent preview rendering; keep source-bearing review artifacts private.
- [x] Package a small review set with conditions/provenance concealed until
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

## Completed technical comparison

The two concrete external implementations run: official Yin-Yang contextual
generation/refinement/selection and official AMT sampling. This is not a claim
that every researched repository was integrated, that published experiments
were reproduced, or that artist-specific training/global form was solved.
WholeSong/SFS remain references, not executed models in this package. Supplied
ABA/ABC versus the old failed learned-form/cached engine is a component pilot,
not a controlled demonstration of learned whole-song structure.

| Evidence | Actual result |
|---|---|
| Source windows | Cloud starts at bar 13; Sweet starts at bar 9. Source lead projection + estimated motif key/mode, explicit 120 BPM / 4/4 benchmark. No artist fitting. |
| Upstream melody runs | Eight main v3 runs: ABA selector on/off and ABC selector on for each family at seed1701; paired Cloud ABA on/off retry at seed1702. All call real upstream orchestration. |
| Invalid output gate | Cloud selector-off seed1701 emitted one negative duration despite successful inference. Retained raw; no GP fabricated or duration silently repaired. Both seed1702 paired predictions pass timing/export. |
| AMT future-control runs | Cloud 103 sampler calls, 44 new supporting attacks after 5 seconds; Sweet 68 calls, 23 new supporting attacks. Lead reinserted explicitly, extra sampled lead excluded. |
| No-future controls | Cloud failed at 300.36s (guard count125); Sweet at guard count129 / 276.20s. Bounds: 300s or 128 sample attempts. Bounds were chosen after exploratory bridge pilots, not preregistered confirmatory criteria; do not infer a general quality/runtime advantage from two failures. No failed-control audio was invented. |
| Other AMT experiments | Bridge future-input and explicitly instrument-masked variants retained as diagnostics. Masked runs yielded 10 / 0 new support attacks; masks are local engineering constraints, not learned role control. They are exported separately, not substituted for the official main API comparison. |
| GP exports | **19 actual GP files**, independently imported by alphaTab with pitch, local timing, tuning, instrument and bar checks. Includes seven valid full upstream melody outputs, matched excerpts, baselines and masked diagnostics. Three failure/rejection records are not counted as files. |
| Projection losses | Zero octave changes in these 19 exports. Cloud AMT support maximum timing change .01 quarter; Sweet zero. One melody note clipped at the matched excerpt boundary. Real cross-bar ties retained. Full raw MIDI available. Physical multi-voice guitar fingering remains uncertified. |
| Review studies | **Six phrase cases** (3 per source) and **four arrangement cases** (2 per source), all eight bars / 16 seconds. Shared initial 4s phrase motif / 5s arrangement prefix are intentional. Main arrangement lead matches exactly across conditions, including an independent MIDI sustain/timing audit. |
| Distinctness | All post-prefix event streams differ, normalizing MIDI channel allocation to instrument program. Phrase pair non-shared exact onset/end/pitch events range 91.1–100%; this is event difference, not perceptual calibration. |
| Copying screen | After excluding only the initial supplied motif, two Sweet ABA conditions each contain a 16-event source-relative match; later motif returns are deliberately counted. Cloud and Sweet ABC have no 16-event match. Short 8-event source/folk matches also occur. This is not proof of originality or a quality verdict. |
| Preservation | All **757** earlier frozen files rehashed unchanged. Original review and its existing ratings were left intact. New review versions have blank human ratings. |

Raw outputs, configurations, logs, models and source-bearing excerpts remain in
ignored local storage. Source-free measurements are in
[external_comparison_results.json](benchmarks/external_comparison_results.json)
and [external_copying_results.json](benchmarks/external_copying_results.json).

### Review package

Private output folder: `local-artifacts/external-comparison-v3/`.
`External_Pipeline_Comparison.zip`: **101,648 bytes**, 37 unique entries, CRC
verified, SHA256 **9bd98f396cdf8575174c6377303c6faeffd6d91867986ee0fb0c3d995361eb57**.
Contains 19 GPs, raw MIDI, the two review bundles, aggregate and copying reports,
and README. It includes source excerpts; do not publish it. No weights, private
human feedback or complete original commercial source GPs are packaged.

The two live review tabs use the existing deployed private-bundle UI:

- `composition-ablation-review.html?study=final&comparison=external-phrases`
- `composition-ablation-review.html?study=final&comparison=external-arrangement`

They are preloaded, with zero human judgments entered. After reload, load the
matching `phrases-review.json` or `arrangement-review.json` again; file-picker
fallback supports paste JSON. These are 16-second excerpts, not full-song
endings. Browser previews still use the same fixed-gain simple synthesizer;
judge instrument rendering in Guitar Pro/raw MIDI, not from sine timbre. An
optional offline SoundFont experiment produced nonfinite/clipped samples and
was not shipped; its diagnostic stays private.

### Reproduction

Use fresh private output directories and preserve failed attempts. The exact
upstream revisions and model hashes above are part of the protocol. Commands at
repo root (local paths stand for already authorized inputs, not hidden downloads):

```text
python composition-lab/benchmarks/external_yinyang.py --upstream .local/yinyang --models .local/yinyang-models-verified --out composition-lab/local-artifacts/FRESH --prepare
python composition-lab/benchmarks/external_yinyang.py --upstream .local/yinyang --models .local/yinyang-models-verified --out composition-lab/local-artifacts/FRESH --family cloud --selection on
python composition-lab/benchmarks/external_yinyang.py --upstream .local/yinyang --models .local/yinyang-models-verified --out composition-lab/local-artifacts/FRESH --family cloud --selection off
python composition-lab/benchmarks/external_yinyang.py --upstream .local/yinyang --models .local/yinyang-models-verified --out composition-lab/local-artifacts/FRESH --family cloud --form ABC
python composition-lab/benchmarks/external_amt.py --upstream .local/anticipation --models .local/amt-small --out composition-lab/local-artifacts/FRESH --family cloud --condition future --api controls
python composition-lab/benchmarks/external_amt.py --upstream .local/anticipation --models .local/amt-small --out composition-lab/local-artifacts/FRESH --family cloud --condition prefix --api controls
```

Repeat for Sweet, and the documented paired Cloud seed1702 retry. Also retain
the masked diagnostic (`--roles masked`, bridge API default). Packaging expects
these named conditions; missing predictions fail instead of becoming placeholders.
Use `--attempt` to retain an unsuccessful run directory when retrying.

```text
python composition-lab/benchmarks/package_external_comparison.py --workspace composition-lab/local-artifacts/FRESH --stage export
node composition-lab/verify_gp.mjs ALPHATAB_MODULE ALL_EXPORTED_GP_FILES
python composition-lab/benchmarks/external_copying_audit.py --workspace composition-lab/local-artifacts/FRESH --out FRESH_COPYING_REPORT.json
python composition-lab/benchmarks/package_external_comparison.py --workspace composition-lab/local-artifacts/FRESH --stage bundle --aggregate FRESH_AGGREGATE_REPORT.json --copying-report FRESH_COPYING_REPORT.json
```

Latest local verification: **106 Python tests, 16 JS tests, Vite build pass**.
Independent imports checked every actual GP, not just a parser smoke fixture.
Browser A/B decoding is 16s, B piano roll follows B, both studies load without
console errors, old ratings preserved, and new human judgments remain blank.
No website source changed; the current Pages UI was reused rather than
publishing private musical content.
