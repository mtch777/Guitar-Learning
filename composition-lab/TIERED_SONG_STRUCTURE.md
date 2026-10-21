# Captured Songsterr song → nested, timed analysis JSON

## Authority and scope
Tier0 is captured Songsterr metadata and track JSON, preserved semantically unchanged. Capture file byte hashes and canonical-payload hashes are separate. Converted GP is a separate playback/export artifact, not raw authority. No original copyrighted payload is published in Git.

The pilot is the ENTIRE Cloud Cascade capture, Songsterr460099 revision9588298: six tracks,5350 note occurrences,3738 written beats. These are observed pilot counts, not universal format guarantees. The package is scoped to one song/revision. Artist-labelled summaries describe this one captured song; cross-song generalization is unavailable.

## Physical hierarchy

```
representation: tier5 artist-level descriptive findings
  lower_tier: tier4 song structure/summaries
    lower_tier: tier3 patterns and candidate pattern hypotheses
      lower_tier: tier2 relationships and shared observation witnesses
        lower_tier: tier1 resolved events, source beats, playback visits
          lower_tier: tier0 captured metadata and track payloads
```

Each layer owns its records and links. It contains the complete lower state once. Musical structures do not own source notes: overlapping chords/patterns share stable event references. Source unknown fields are not discarded because no current analysis understands them.

A layer is an abstraction level, not a musical datatype or a detected phrase. A mode hypothesis can cover an entire song while still being a relationship hypothesis. A section label is a source annotation, not proven verse/chorus function. Empty/unknown outputs remain explicit, never filled with invented musical labels.

## Record and time contract
- source_id identifies the captured Songsterr song/revision. A separate analysis_revision hashes normalized outputs, implementation inventory and source hashes; package_id includes both source identity and analysis revision. IDs are local to that immutable analysis snapshot. Cross-package references require package_id AND record_id. Canonical note IDs depend on original part/bar/voice/beat/note occurrence, not on detected patterns.
- Tier0 documents retain payload, filename, byte_sha256 and payload_sha256. Source pointers address literal values; negative/invalid array pointers are rejected.
- A record retains kind, tier, scope, values, output origin and interpretation status. Exact legacy output remains reconstructible from record references. Raw-note/beat payload views resolve back to Tier0 rather than duplicate those objects.
- Exact written time uses rational quarter-note strings and half-open spans. Grace attachments have zero metrical duration, with written ornament duration retained separately.
- Playback visits use a SEPARATE playback_quarter_notes clock and point back to written events. Repeated playback never duplicates the canonical written source.
- A measure scope is labelled as scope, not precise attack evidence. Artist aggregates have no invented continuous time interval; their evidence is disjoint lower-level observations.
- Some legacy phrase/harmonic functions use a declared rounded pitch-center projection. Their numerical outputs and limitations are retained; they do not overwrite exact source clocks.

## Connections, counts and exact materialization
Canonical links distinguish source resolution, event-in-beat, mere event mentions, scope membership, metric denominator observations, graph endpoints and complete counted units. Sharing a bar is not evidence that an event was used by a particular calculation.

Existing conditional tables cap examples at two. An OPTIONAL observation sink now records every Counts.add contribution without changing any existing table, weight or probability. Shared observation witnesses are stored once; each conditional cell links to every contribution, including negatives. The ordered contribution stream references witnesses and count cells. It can reconstruct the original complete log exactly; duplicate source groups are not expanded into one parameter-object record per statistic.

Individual-note summaries retain three distinct units: written regular segments, fresh note attacks, and summed written duration mass. Their exact denominator observations include source marker-state/unknown reasons. These are not attack-group percentages, occupied time, acoustic duration or emotional judgments.

output_roots and record origins allow exact materialization of EVERY invoked JSON-normalized legacy output after explicitly declared resource validation. The legacy evidence helper constructs a GP filename even in an API-only temporary directory: that nonexistent resource is marked unavailable, never presented as a real GP. This non-musical adapter correction is recorded separately. A top-level legacy_output_projections map reconstructs mixed old report fields without putting higher-tier references inside canonical lower events. Individual-note composite views and ordered count logs live at their highest required tier; their lower observations remain below. Every canonical embedded reference/link must target its own or a lower tier, so each retained lower state is structurally self-contained. Field mapping is derived from those origins, not a second manually maintained copy. Reverse indexes are derived from the SAME canonical links, not duplicated backlinks. The written and playback indexes are separate. Individual-note denominator observations retain the exact three statistical units and marker-state reasons. Statistical result cells reference shared witnesses rather than copies of the same source group; the original ordered contribution log can still be recovered exactly.

## Existing logic and limits
The implementation registry records actual module hashes, docstrings, functions and dispositions. Current capture core includes repaired rest semantics, dynamics, typed slides, local timing regions, coattacks, HOPO and sustain. Approved pedal identification/expansion is unchanged, separate from older candidate windows and dialogue measurements. Reused model-free graph, harmony, phrase, motif, content-identity and opportunity logic retains its own selection caps, approximations and hypothesis status.

Composer-dependent, external-trained-model, generation/control and GP-format-specific functions are not falsely described as executed source analysis. Applicable pure algorithms receive explicit API-derived views rather than fabricated GP fields.

This is a complete-data MAPPING pilot, not proof of musical interpretation, GP inversion or isolated tier execution. Existing composite analyzers still calculate several abstraction levels together. The adapter maps their results truthfully; it does not yet enforce previous-tier-only process isolation. That architectural execution gate remains open.

## QA and review
Run build_tiered_song.py with a captured song directory and a fresh private local-artifacts output directory; run verify_tiered_song.py against that bundle and original capture. Private existing-outputs.json is the independent mapping reference. QA checks full raw-note/beat coverage, source equality, exact legacy-output materialization, dangling links, clock validity, complete conditional numerators/denominators and upward/downward evidence paths. Mutation tests deliberately corrupt source, clocks, identities and links.

ProjectPlanner3000 has reviewed and challenged the implementation at start and midpoint. Final independent artifact approval remains required before presenting the full data as ready. Do not substitute tests, serialization success or a commit for that review.

## Calculation inputs are not counted units (semantic review corrections)
Neutral count witnesses remain in Tier2 and contain ONLY exact counted occurrence IDs. Shared calculation descriptors live in Tier3 (Tier5 for song-selection/weighting metadata); each ordered count contribution and result cell references its context. Descriptors distinguish origin/next groups, source curves, classifier lookup results, whole-track register populations, earlier-bar pattern searches, accepted role/cycle records, supplied programs, and explicit absence predicates. Empty lookup results remain empty and retain their search scope. Track eligibility has its own input links.

The verifier independently compares actual graph link targets with these descriptors and selected formulas: exact origin/next IDs, bend/beat-scoped whammy units, prior-only eligible pattern populations/last matches, classifier/pair/cycle/program inputs, and adjacent-bar attack membership. An absent eligible attack does not claim acoustic silence. Missing pitch is not a missing attack. Cycle return boundaries do not imply a played return note.

Graph note/beat clocks use canonical occurrence clocks, including silent beats and grace points. Graph groups use their existing memberships; no whole-bar population is attached to a single graph note. Inferred sounding lanes link to existing sustain records with disjoint written spans, without a physical sustain claim.

Existing phrase-development results link to the exact earlier candidate phrase, distinguish full primary-voice comparison populations from selected lowest-pitch outline witnesses, and retain adjacent candidate pairs underlying transition counts. Source phrase boundaries and heuristic candidate boundaries remain different concepts.

Actual exact/rounded/ensemble algorithm inputs are retained under extended/analysis_inputs. Method-input links are explicitly NOT count membership. Reexecution tests reproduce original graph/harmony outputs from materialized inputs; they do not demonstrate isolated previous-tier execution or an inverse.
