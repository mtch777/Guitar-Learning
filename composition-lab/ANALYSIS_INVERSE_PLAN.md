# Analysis engine + blind inverse: execution gates

Agreed planning direction, 2026-10-20. This document defines next work; it does
not claim an inverse is implemented or authorize silent removal of existing code.
User asked that post-analysis attempted recreation eventually be archived so the
active focus becomes the analysis engine and its inverse. Reviewed with
ProjectPlanner3000 at start, midpoint and completion.

## Goal and architecture

GP -> complete structured musical analysis -> inverse -> GP.
The same representation and explicit musical relationships must subsequently
support controlled variation. No second independent composition rulebook.

1. Source facts: exact written events, performance/notation parameters, structure,
   metadata and stable identities sufficient to reconstruct the source.
2. Musical relationships: explicit links, repetition/variation, contexts and
   constraints; observed, inferred, candidate and unknown meanings distinguished.
3. Inverse: constructs output from serialized analysis alone, without reading
   source files or using source overlay/replay as a substitute for construction.
4. Later variation: edits permitted coherent units in this representation using
   those same supported relationships. The inverse remains the output path.

One representation does not mean one monolithic source file. Decoders, schema,
relationship analysis, validators and writers can remain separate modules.
Exact event reconstruction is necessary but does not alone prove musical logic.
An embedded GP/GPIF/MusicXML blob, old-output lookup, copied archive or serialized
opaque whole importer model does not satisfy this contract. Explicit individually
scoped unknown notation values may be retained as typed extensions; they must not
be disguised as understood musical relationships.

## Immediate focus

- Freeze NEW disconnected recreation/generation experiments as active development.
- Preserve all existing source, outputs, failed findings and accepted analysis.
- Do not physically archive anything in this planning change.
- Next executable gate: A, dependency and field inventory. Then B contract, C
  surgical archive, D blind reconstruction. Do not jump back to generation.
- Pedal identification/continuation remains accepted and closed. Pedal analysis
  records are treated like other relationships, without special priority.
- Schedules remain paused. ProjectPlanner3000 is the only planning agent; check
  at endeavor start, midpoint and completion. QABot3000 remains retired.

## Ordered gates and acceptance checklist

These are evidence gates, not time estimates. Set an active-work checkpoint
when each endeavor starts. Complete and report its evidence before advancing; failed gates produce named
mismatches and the next targeted investigation, not another unrelated experiment.

### A. Inventory the real dependencies and source fields

- [ ] Freeze current origin/main SHA and existing private corpus/baseline manifests.
- [ ] Classify every proposed archive file and each of its incoming/outgoing
      imports, CLI callers, workflow/test references and dynamically loaded paths.
- [ ] List shared helpers that active analysis, inspection or verification needs.
- [ ] Inventory original GP archive/GPIF fields versus current extracted records;
      distinguish source GP facts from API-capture facts and later derived reports.

Deliverable: versioned dependency manifest + field preservation/meaning matrix.
Acceptance: every proposed move has a disposition and caller evidence; each
observed source-field family is marked preserved, transformed, opaque or missing.
Static imports alone are not a complete dependency audit. No physical moves yet.
Scope: entire proposed legacy set, not just files with recreation in the name.

The stable roadmap remains the reporting scaffold:

| Gate | Roadmap work served |
|---|---|
| A inventory | 2 analysis; 8 verification |
| B representation/inverse contract | 2 analysis; 3 connected profiles; 6 controls; 7 engine; 8 verification |
| C safe archive | 4 methods; 7 engine; 8 workflow/regression |
| D blind pilot | 2 analysis; 5 controlled experiments; 7 inverse; 8 validation |
| E corpus verification | 2 analysis; 5 experiments; 8 validation |
| F relationship usability | 2 analysis; 3 profiles; 4 methods; 7 engine; 8 validation |
| G one measured control | 4 methods; 5 experiments; 6 levers; 7 engine; 8 validation |
| H expansion | 3 artist profiles; 4 methods; 5 experiments; 6 levers; 7 engine; 8 validation |

These gates do not replace roadmap 2-8 or silently close its original requirements.

### B. Define the analysis/inverse contract and verification protocol

- [ ] Version schema, occurrence identities, exact rational timing, track/staff/
      voice/beat order, tuning/transposition/capo, pitch/fingering/rests/graces,
      ties/slides/HOPO, expression curves/markers, dynamics/automation, tempo/
      meter/repeats/endings, sections and other musically operative notation.
- [ ] Define written versus sounding time and repeat-expanded playback explicitly.
- [ ] Define relationship record IDs, source evidence, endpoints/membership,
      support, interpretation status and uncertainty; no invented roles/phrases.
- [ ] Define metadata, layout/resource/unknown-field preservation and the boundary
      between musical identity and archive/serialization byte identity.
- [ ] Specify inverse input allowlist and independent comparison exclusions BEFORE
      examining outputs. Never exclude a mismatch simply to obtain a pass.

Deliverable: schema + coverage matrix + concrete source-free expected fixtures.
Acceptance: every field found at A has an explicit treatment and verification
method. Unsupported musical fields remain open blockers, not silent defaults.
Original GP is the round-trip authority: API-only facts cannot be claimed as GP
facts; pre-existing API->GP loss is reported separately, not repaired by guessing.
Byte-identical ZIP serialization is not required by the current interpretation;
exact musical/performance/notation content is. Ambiguous substantive boundaries
must be explicit before claiming success.

### C. Archive separate recreation experiments safely

- [ ] Review the A manifest against B; seal rollback SHA and private output hashes.
- [ ] Move only exclusive experiment orchestration/methods into a dated legacy
      area; include README, original entrypoints, evidence and migration mapping.
- [ ] Keep or extract shared pure readers, source analysis, geometry, export,
      rendering and verification helpers with before/after behavior checks.
- [ ] Update active entrypoints/docs/imports/CI references; retain legacy tests
      explicitly where appropriate. Do not delete failing tests to get green.
- [ ] Run affected tests, original CLI smoke checks, active source-inspector/
      analysis checks and import/reference audit. Verify no baseline is overwritten.

Acceptance: archived experiments are no longer active defaults; retained analysis
and review work identically, legacy code/evidence remains recoverable, no dangling
callers. Archive incrementally at this gate; do not wait for the entire inverse
project to finish, and do not leave accidental legacy generator dependencies in
new analysis. Shared helpers can stay in place until proven safe to separate.
This is a functional archive, not deletion of copyrighted/private local baselines
or publication of their contents. Actual file moves await this gate's inventory.

### D. Prove blind exact reconstruction on a bounded pilot

- [ ] Build a source-free fixture set covering every declared B field/relationship,
      including polyphony, multiple voices/staves, rational tuplets, rests, graces,
      techniques/curves, ties and repeat/tempo changes; negative/unknown cases too.
- [ ] Select ONE actual technique-rich GP by observed feature coverage, not by
      whether it already passes. Freeze input hash and supported-field manifest.
- [ ] Export serialized analysis; run inverse in a fresh isolated input directory
      containing only that analysis and explicitly declared non-source resources.
      Enforce and log the read allowlist, including dependencies and dynamic reads:
      a clean working directory alone is insufficient. Use a copied isolated test
      environment where original paths are inaccessible; do not move/delete live
      private inputs. No source GP, raw capture, prior output or source-derived
      sidecar read by inverse. Source reference is available to evaluator only.
- [ ] Construct GP from records; independently compare native imported output
      and source, source notation fields, event counts/IDs/order, exact time,
      fingering, technique parameters/curves and playback/structure metadata.
- [ ] Reanalyse and compare preserved facts and relationship invariants. Protect
      against shared-parser errors with independent native/notation checks.

Acceptance: zero unexplained musical/notation/performance differences for declared
pilot coverage; missing/unsupported fields visibly fail the gate. Valid ZIP/parser,
self-consistency or replaying a source archive is insufficient. Actual GP output
retained locally. Listening can identify playback differences; no invented verdict.

### E. Expand reconstruction coverage across the frozen corpus

- [ ] Run the same blind procedure over all manifest entries (currently 98 catalog
      GP files); record every attempted, passed, failed and unavailable entry.
- [ ] Publish source-free counts by source-field/technique/format/track features;
      retain private per-occurrence differences and reproduction commands.
- [ ] Resolve failure clusters with small source-free repros; rerun the full
      reconstruction regression after each relevant fix. Never silently exclude.

Acceptance: every manifest entry accounted for and exactness passes on claimed
coverage. Partial support must be named; no whole-corpus completion from selected
examples. A local 98-song catalog does not prove general GP-format support.

### F. Verify that relationships are usable, not decorative

- [ ] For existing relationship types, verify endpoint membership, timing,
      conditions, provenance, repetitions and consistency against source facts.
- [ ] Select one supported relationship and a controlled changed context. Prove
      which consequences are required, forbidden, compatible or unknown.
- [ ] Demonstrate inverse construction and independently verify those consequences
      without inventing new source semantics. Preserve other literal locks.

Acceptance: relationship drives a testable construction/change rather than merely
being copied into JSON. Unsupported interpretation is retained as unknown/refusal.
This verifies the user's musical-analysis goal beyond lossless event storage.
It does not reopen accepted pedal detection or grant that technique priority.
Relationship schema/fixture checks may proceed alongside E failure localization;
variation still waits for the declared zero-change reconstruction coverage gate.

### G. Add one measured 0/50/100 variation control

- [ ] Define one coherent eligible opportunity unit, relationship constraints,
      allowed context and locked dimensions before sampling.
- [ ] 0: exact original controlled content; whole pipeline at all-zero must satisfy
      the reconstruction contract, not just bypass computation/copy original GP.
- [ ] 50: release probability .5 per declared opportunity; frozen seeded trials
      verify release frequency against a predeclared statistical tolerance.
- [ ] 100: release every eligible opportunity; directly hidden unlocked target
      values cannot influence proposal. Same supported source/style rules apply.
- [ ] Record eligible/released/changed/unchanged/refused counts separately, enforce
      relationship constraints and other locks with independent output checks.

Acceptance: source target perturbation cannot alter 100 proposals except through
explicitly permitted locked context; same frozen rules at 0/50/100. Chance of
permission is not identical to chance of actual difference. Original outcome may
occur legitimately; never force difference just to satisfy a percentage.
No guarantee of artist feel solely from probability/structural checks.

### H. Expand controls and artist logic on the same foundation

- [ ] Connect supported multi-song/family/context observations to relationship
      rules, support/missingness and cross-track interactions in the same schema.
- [ ] Extend controls one at a time with G checks and compatibility/refusal tests.
- [ ] Preserve held-out splits, baseline outputs, originality checks and native
      playback comparisons; prepare clear source-relevant listening examples.

Acceptance: measurable coherent changes, supported artist relationships and user
listening acceptance at the appropriate musical gate. No independent post-analysis
heuristic generator is introduced to compensate for an incomplete representation.

## Observed archive boundaries (initial inspection, not final move manifest)

| Existing component | Observed behavior | Initial disposition |
|---|---|---|
| songsterr_automation / analyze_relationships.py / source_semantics and relationship helpers | Source acquisition and deterministic source observations | Retain; adapt only against contract |
| exact_score.py | Imports checkpoints.2026-10-14.extract and music_events | Retain dependency; do NOT archive checkpoint wholesale |
| gp_io.py | Copies every archive entry including GPIF for round-trip | Retain inspection utility; NOT proof of blind inverse |
| gp_author.py | Generated-score writer; rejects unsupported source techniques; limited staff/channel coverage | Evaluate reusable pieces; NOT assume generic inverse |
| compose_controlled.py / controlled_generation.py / corpus_composer.py / generate_composition.py | Existing composition/variation orchestration | Freeze; archive candidates after caller audit |
| recreation_pilot.py / recreation_window.py | Source redaction/replay/overlay + learned comparison | Freeze; archive candidates, not new inverse |
| engine_contract / exact_score / technique_edits / reference_levers | Shared dependencies of experiments, checks and source operations | Classify helper by helper; no whole-module assumptions |
| renderers / native validators / source inspector / accepted analysis | Playback, independent evidence and source visibility | Preserve functioning |
| tests, historical study reports and private outputs/models | Evidence, baselines and reproducibility | Preserve; label historical, retain licensing/privacy boundaries |

## Status and next action

ProjectPlanner3000 read the full plan and approved it with three corrections,
now applied: stable-roadmap mapping, enforced input isolation and evidence-gate
wording. This is planning approval only. Gates A-H are
PENDING; initial code observations above are not a completed dependency inventory.
No files archived and no inverse/reconstruction success claimed in this change.
Next execution: A, then B, then C. If source handling is blocked, complete other
inventory/schema work; do not restart unrelated generation experiments.
