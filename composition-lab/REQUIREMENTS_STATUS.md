# Requirements verification register — 2026-10-19

G0: reconcile requirements before changing the shared engine. Baseline main:
`fd78baf81b021488a975e36e9da6d89d9e92c58b`. This is a source/evidence review,
not a new inference, playback, accuracy or listening run.

The machine-readable companion [requirements_status.json](requirements_status.json)
preserves all16 original acceptance statements and recorded historical states
verbatim, with current evidence paths, remaining gates and roadmap mappings.
Original targets remain targets unless a later user instruction supersedes them.
Old numerical results are dated evidence, not current tests or final acceptance.

## Stable roadmap

2 Analysis;3 Artist profiles;4 Generation methods;5 Controlled experiments;
6 Levers;7 Composition engine;8 Validation/delivery. The16 original workstreams
are mapped into this scaffold; neither numbering system replaces the other.

## Original16 → current requirements

**Bounded** means a stated engineering/artifact gate has evidence, not that the
whole musical goal is complete. **Failed/open** preserves an unsuccessful target.
**Partial/open** means meaningful requirements remain. Evidence details and
original thresholds are in the JSON rather than hidden behind a green label.

| Original workstream | Roadmap | Disposition | What still prevents full acceptance |
|---|---|---|---|
| 1. Freeze/provenance|8|Bounded|Per-run seals exist; no single current global freeze covers every active WIP artifact. Preserve relevant hashes on each promoted run.|
| 2. Representation|2,8|Partial|Core occurrences preserved; timing exclusions, mixed ties and full sounding/physical interpretation remain.|
| 3. Corpus|2,3,8|Partial|External research corpus and guitar capture are distinct; original five-style/rights-appropriate breadth not demonstrated.|
| 4. Splits|3,5,8|Partial|Family guards pass; current outer split has been examined; pristine final test and pretraining overlap remain unresolved.|
| 5. Relationships|2,3,7|Partial|Written relationships implemented; general semantic phrase/motif/harmony/role truth and required contrasting-source coverage remain open.|
| 6. Structural validation|2,3,8|Failed/open|Historical boundaryF1 .571 versus .354baseline failed .70target. No later adjudicated result closes it.|
| 7. Architecture/research|4,7,8|Partial|Actual external paths ran; successful guitar integration/adaptation and relevant rights are not universally established.|
| 8. Phrase learning|3,4,5,7,8|Failed/open|Real inference exists; guitar adaptation failed. Annotation prediction is not a replacement for phrase learning/development.|
| 9. Form|3,4,6,7,8|Failed/open|Learned form failed its baseline; later length result effectively tied. Explicit returns work but do not prove learned form or development.|
| 10. Roles|3,4,6,7,8|Partial|Some contextual pitch benefits; heuristic roles, voice/bar restrictions and whole-piece interaction remain unaccepted.|
| 11. Playability|5,7,8|Partial|Mechanical fret/string/tuning/span checks do not certify human physical execution.|
| 12. Controls|6,8|Partial|Bounded11controls exist. Function+octave melody, general form/meter/tuning/layout/topology and broader intermediate behavior/combinations remain unverified; no perceptual calibration claimed.|
| 13. Compositions|5,7,8|Bounded artifacts|Historical100fullGPs and newer longform outputs exist; counts/imports do not establish coherence or artist fidelity.|
| 14. Originality|5,8|Partial|Known-corpus copying/diversity screens are limited; no universal originality or legal verdict.|
| 15. Musical validation|5,8|Open|Reviews/feedback exist; broad musical/source-feel failures remain unresolved. Original multi-listener/preference gate has no recorded later pass.|
| 16. Workflow|8|Bounded|Delivered CLIs/CI/review paths exist; local WIP and experiment-specific final checks are not delivered.|

No unknown historical requirement is silently parked or cancelled by this table.
The gate does not authorize collecting more data, rerunning all historical models
or reopening failed research merely to make the register green.

## Original five commitments: disposition

| Commitment | Recorded evidence | Still open |
|---|---|---|
| GP/MusicXML and actual AnalysisGNN benchmark | [2026-10-15 results](benchmarks/RESULTS_2026-10-15.md): Sweet grace timing corrected; actual official-checkpoint full/pitched inference ran | Predictions/disagreement are not accuracy or validated structure; weight redistribution rights not established |
| Exact relational representation | [Relational pipeline](RELATIONAL_PIPELINE.md), [analysis repairs](ANALYSIS_REPAIR_PASS2.md), [connected profiles](ARTIST_PROFILE_PROGRESS.md) | General phrase/role/harmony semantics, some timing/performance cases and complete sounding relationships |
| Four ablations and baseline comparison | [Actual benchmark/ablations](benchmarks/RESULTS_2026-10-15.md); baseline preservation recorded | Broad learned stylistic/coherent musical success not established |
| Phrase-aware multi-role engine and controls | [Current bounded pipeline](CONTROLLED_PIPELINE.md), [execution evidence](AUTONOMOUS_COMPLETION.md) | Functional melody semantics, broad arrangement freedom, learned development and musical identity |
| Held-out/originality/regression/playback validation | [Original16 evidence](EXECUTION_16.md), subsequent scoped reports and independent QA | Human musical acceptance, pristine final tests and general originality/style claims |

## Binding semantics and explicit boundaries

### Melody: exactness applies to the specified feature

[HANDOFF.md](HANDOFF.md) explicitly defines the intended reharmonizing melody
representation as **chord-relative function/degree plus relative octave**, with
contextual non-chord roles. Later literal0 instruction strengthens exactness; it
does not redefine that feature as absoluteMIDI.

- When harmony changes and melody-function is locked, derive new actual pitches
  while preserving the supported functions/octaves. Example: root/minor-third/
  fifth over minor ii maps to root/major-third/fifth over major IV.
- Raw MIDI remains immutable evidence and export/verification data; a separate
  literal-pitch lock is a distinct operation, not the full melody requirement.
- Passing, neighboring, approach, suspension and resolution notes need their
  contextual relations; a fixed root offset or nearest-chord-tone guess is not
  sufficient.
- Unknown or non-tonal harmony remains explicit. Do not discard all melodic
  learning because harmony is unknown; interval/rhythm observations remain usable.
- Incompatible literal-pitch, changed-harmony and fixed-function requests must
  be reported, not silently weakened. No universal precedence choice is invented.

Current literal-pitch/fingering controls are a useful **bounded implementation**,
not fulfillment of the complete relational melody contract.

### Lever endpoints and intermediate behavior

- **0%** means exact identity of the explicitly specified feature.
- **100%** means no direct original target-feature values in its proposal; coincidence
  is allowed. Older forced-difference/maximum-distance wording is superseded.
- Intermediate controls need a named measurable mechanism. Fixed-stage nested
  release behavior is engineering behavior, not calibrated audible distance.
- Broader permissions cannot be inferred from a technique-only edit. Fixed
  dimensions/topology are not freedom controls; unsupported combinations fail.

### Pedal closure is identification-only

Identification and its approved additive continuation are closed and protected.
Deeper analysis, recreation, transfer and creative use remain open alongside the
other techniques. They receive **no special priority**. Existing descriptors
have bounded evidence; they do not close all analysis/recreation requirements.

The next shared-engine experiments consume accepted observations, not a reopened
pedal detector. This is the user's latest explicit scope clarification.

## Current local WIP: separate from shipped main

Eight untracked modules/tests exist: note summaries, aggregate profile summaries,
sequence palm method and tuning-relative proposal. Source-level existence and a
whole-suite result do not make them accepted or delivered.

- Note/aggregate views: focused tests/root arithmetic checks exist; final
  independent component QA is unfinished.
- Sequence experiment (inspected v3 batch):36GPs across old-static/new-static/stateful comparisons;
  code matches its saved batch. Final native/playback acceptance is unfinished;
  the inspected batch contains0WAVs.
- Tuning-relative proposal: actual36GP trial and native evidence exist; candidate
  **not promoted** because bass/harmony relationships regressed. Not a zero-copy
  claim or a claim that every file is invalid.

This gate changes documentation/traceability only. It does not promote a method,
certify musical quality or start additional experiments.

## Evidence and gate completion

Evidence levels are separate: original requirement; dated recorded execution;
current source inspection; current test/reproduction; independent QA; genuine
human acceptance. This register does not upgrade one level into another.

G0 acceptance checklist (current state before publication):

- [x]16unique rows; all original title/criteria/state strings retained verbatim.
- [x] All evidence paths exist; mappings are within roadmap2–8.
- [x] Melody and pedal boundaries explicitly reconciled; no musical success inferred.
- [x] Final ProjectPlanner3000 content review passed after midpoint repairs; publication still pending.
- [x] Independent QABot3000 content QA passed;16original records and all evidence paths reconciled.
- [ ] Source-free register committed/pushed and relevant CI verified.

These unchecked items are requirements, not claims of completion. The following
shared-contract gate may start only after reconciliation passes. Scheduled
automation stays paused.
