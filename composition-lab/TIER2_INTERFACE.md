# Musical Tier2 — implemented interface

This is a bounded musical-analysis boundary, not the completed song engine.
`musical_tier2.py` consumes only its preceding T1 facts. Its shared pitch
relationship is `pitch = bass_register_anchor + voicing_interval`; analysis solves
for interval, reconstruction solves for pitch, and both validate the same contexts.

| Owner | Stored data | Meaning / limits |
|---|---|---|
| T1 input, nested once | Occurrence ID; part/bar/voice/beat/note; rational base pitch/time; typed warnings; schema-specific geometry, key and physical/tie declarations | Exact owned fields only. Schema4 includes physical/tie facts; it does not own full technique execution, rests or sounding pitch. |
| T2 written-start group | Source bar/part/time; lowest written register; member intervals, durations and notation addresses | Coincident written-note starts. Bass is not necessarily chord root; explicit ties are handled separately, acoustic attacks remain unknown. |
| T2 interpretation | Literal pitch classes; all exact compatible published chord forms/roots; bass/root interval; known/unknown counts | Fixed music21 9.9.2 theory vocabulary, 50 definitions. Not trained artist rules; not a selected true chord. Incomplete sets stay unresolved. |
| T2 nominal spans | Half-open start/end; references to active, newly starting and continuing occurrences; separate part/ensemble contexts | Uses written duration only. No acoustic sustain, tie-chain, let-ring or pedal-sustain inference. Zero-duration notes have no nominal span. |
| Note query | Candidate-relative unwrapped interval, octave, pitch-class interval, membership and context reference | Conditional on that candidate. Exact-set membership is arithmetic, not non-chord-note/function recognition. |
| T2 tonal evidence | Whole-song pooled and per-part duration exposure; all 48 major/minor candidates across two published profile families; explicit used/excluded occurrence references | Pearson correlations, not probabilities. Order-invariant, part-doubling sensitive. Invalid timing excluded. No automatic tonic/key selected. |
| Tonal note/chord query | Explicit candidate ID, note interval/octave/reference-scale membership; chord-root interval; exact local harmonic-context reference | Major/natural-minor reference membership is conditional, not note function or general mode identification. |
| Explicit unknown | Base key; chord-relative mode; functional note role | No unsupported key/mode/emotion is fabricated. |

A register anchor and relative intervals are necessary realization choices: chord
labels cannot recover voicing, octaves or occurrence timing. Single-note groups
retain one register and contribute no chord abstraction by themselves. Musical
meaning is tested separately from exact reconstruction; not every note is understood
because every note reconstructs.

`analyze` returns T2 with its sole T1 input nested in `input`. `strip_lower` removes
that entire input. The audited inverse receives only T2, explicit variation=0 and
shared relationship code. It reconstructs exact declared T1 fields. It cannot read
raw scores, caches or expected output. Python audit is used, not an OS sandbox;
resource quotas and hostile native-code isolation are not claimed.

Derived interpretations/spans are checked against those SAME pitch/time relations.
Stale contexts, arbitrary split groups, conflicting nested inputs, unknown payloads,
hidden metadata streams, bad identities and coverage inconsistencies are rejected.
Transposition is a deterministic QA intervention, not an artist-style percentage
lever or learned musical choice.

## Actual three-gate evidence

| Gate | Evidence | Verdict |
|---|---|---|
| 1. Fresh song | Frozen random Chala Head Cha La: 6386 occurrences/12 tracks. Then new frozen random Poison: 6101 occurrences/8 tracks. Direct independent raw-source pitch/time/ID comparison. No replacement of failed runs. | PASS declared source scope; tonal interpretation accuracy untested. |
| 2. Remove and reverse | Entire T1 input removed; fresh `-I -S` worker executes actual same core. Typed exact comparison plus independent raw-source comparison; real file/network/process/import denial attempts. | PASS declared T1 boundary; not full GP reconstruction. |
| 3. Musical abstraction | Raw-source witnesses; C/E/G compatibility; D/A part distinguished from D/F#/A ensemble; inversion and symmetric alternatives. Nominal overlap distinguishes new E from continuing C/E/G, with candidate-relative third. Held-note/context-change and stale-context tests. | Planner approved written-start slice; nominal-overlap completion review recorded in progress log. Not complete key/mode/function analysis. |

Private captures and complete nested/stripped JSON live under ignored
`local-artifacts/`. Public source has only code, tests and aggregate results.
Initial runner failure and import-challenge setup failure are retained privately;
subsequent fixes rerun the SAME frozen song. No audio/style quality claim.

## Still open

Full source/T1 ownership (all techniques, rests, expression and source declarations
beyond the explicitly owned schema4 physical/tie facts); sounding harmony beyond
nominal/tie continuity; justified key/mode/harmonic-span
inference; melodic/non-chord-note functions; higher phrase/song/artist context;
learned nonzero levers; composed all-tier/GP inverse. Existing accepted technique
identification and conversion work remain preserved, not replaced by this boundary.

## Tonal-candidate addition

Published profile families: music21 9.9.2 KrumhanslSchmuckler and
TemperleyKostkaPayne. Reproduced source weights/version/hash, no fitted artist
preferences or manually chosen ranking weights. Every tonic/major-minor score is
retained. Undefined correlations stay null. Whole-song and part views are not
independent votes. Nominal duration is not a performed accent or attack weight.

`tonal_note_context` links a real occurrence and its current chord-compatible
context to an explicit tonal candidate. Root coordinates are separate from harmonic
function; minor reference membership means natural-minor reference ONLY, not that
raised sixth/seventh notes are wrong. The tonic register reference is a coordinate
convention, not an observed tonic note. Source declarations cannot be reread by
Tier2; schema1 lacks them and expanded schema2 carries them faithfully.

Fresh Last Nite: 6152 exact occurrences, 4395 used for distributional exposure,
1757 unknown-pitch occurrences retained/excluded. Independent raw-source music21
oracle matched288 scores. Beatles regression matched384 more. These verify method
arithmetic and context links, NOT tonal-center accuracy. Full suite:816 tests,
815 passed/1optional skip. Planner approval and delivered commit recorded in log.

## Source-declared signatures (expanded preceding input)

T1 schema2 adds exact measure-level keySignature present/null occurrences with
part/bar/rational onset/source pointer and complete track measure/end inventory.
Missing is distinct from null. Opaque track.key strings are NOT musical signatures.
The core consumes this T1 only; it never reopens captures.

T2 stores signature definitions via signed fifths, explicit major/minor and minimal
source spelling gauges (raw count sign; zero-accidental direction). It does not
carry the raw source object. SAME equations reconstruct every raw declaration;
tonic PC alone cannot recover enharmonic spelling. Repeated formatting variants
share a semantic signature context; original declaration occurrences are retained.
Missing inherits; null cancels the active declaration; neither defaults to C major.
Unknown encodings fail closed with retained input/failure rather than guessed mode.

Primary Songsterr client semantics are frozen by source hashes. Instrument/display
transposition has not been verified; decoded source notation tonic is not declared
concert tonic. Candidate scores can be shown conditionally if frames align, with
no claim of agreement/conflict or established key. Repeated signatures do not count
as independent votes or changes.

Actual positive source: Chop Suey, 8719 note occurrences and1221 declarations on
11tracks/111bars -> one signature definition/11semanticcontexts. Actual negative
sources: recent random captures and495 Invent Animate track files have no measure
key declarations. Null/change/sign/zero cases are primary-client-backed synthetic
tests, not claimed actual corpus occurrences. Expanded blind inverse and raw
presence/value/clock/absence checks are recorded in the progress log.

## Actual measure frames and temporal evidence

Current upper schema: `musical-context-relations/2`. Preceding schema3,
`normalized-written-context-facts/3`, owns one canonical `measure_geometry`:
source format/identity, frame ordinal/source label, rational start/span, actual
meter and explicit/inherited witness, source part membership. Source pickup
declaration and observed first notated extent remain distinct. No guessed4/4 or
note-envelope-as-measure. Key inventory summaries must match this geometry;
upper signature contexts reference it rather than retaining another inventory.

The SAME meter-unit and start/advance equations reverse this geometry. Source
key declarations `None` mean outside owned input scope; `[]` mean owned/verified
absence. MusicXML references do not receive fabricated Songsterr objects.

`temporal_tonal_evidence` stores all24 AardenEssen major/minor hypotheses per
real measure and source part/pooled view, with used/excluded occurrence refs,
duration histogram, raw correlation, immutable window4 inverse-distance sum,
and exact contributing frame/weight references. Empty measures retain24 null
candidates. Whole written duration is assigned to its onset measure; cross-frame
notes are flagged. This is not acoustic sustain. Neighboring future measures
contribute: offline evidence, not causal prediction or calibrated probability.

Installed music21 floatingKey mutates cached neighbor vectors. This implementation
explicitly fixes that mutation, retaining published profile/weight definitions;
it does not claim full native temporal parity. Native raw correlations and an
independent stateless sum are checked separately. No artist weights are fitted.

`temporal_note_context` and `tonal_note_context` call ONE shared candidate
coordinate helper: actual note/chord intervals against an explicit tonic
hypothesis, with current context/time/part refs. This is conditional scale
membership, not established key, mode or melodic function.

### Verified scope and unresolved musical gap

- New frozen random25201/rev7475088:10tracks/105frames; exact isolated inverse,
  independent raw geometry and55440 temporal score comparisons, all5 actual
  source-access denial challenges pass. Failed freeze-overlap run retained;
  unchanged-code rerun uses SAME selected song.
- Positive signature regression:8719events/1221declarations,111frames,
  63936independent temporal comparisons; exact inverse/source checks pass.
- Three privately frozen annotated Bach references:186/183/237source occurrences,
  independent literal XML clocks/pitches/meter/part inventory and isolated inverse.
  10320raw/temporal score comparisons pass. Annotations are evaluator-only.
- Source/reference audit found one trailing annotation beat and a transposed
  edition. Original failures retained; Planner-approved common-support/fixed
  transposition assumptions frozen before rescoring; contradictions not removed.
- Strict duration agreement with aligned analyst labels, raw/smoothed:
  00457.5/52.5%;01042.3/69.2%;01480.4/94.6%. Smoothing helps AND hurts.
  This is NOT general key accuracy, artist fidelity, or a musical-quality score.
- Eleven of sixteen annotated changes occur inside physical measures. One
  hypothesis per measure cannot represent those boundaries; sub-measure harmonic
  context, tonicization vs key change, note function and modes remain unresolved.

Full suite825tests:824pass/1optional skip; Vite build passes. Actual commands,
private artifacts and independent Planner review are in the progress log.

## Bounded chord-span refinement

`harmonic_span_evidence(T2, start_q, end_q, part_id, max_edges)` consumes only
the existing T2 relationships. It is an on-demand deterministic refinement,
not a separate generator or a new pitch-owning tier.

| Output | What it establishes |
|---|---|
| Nominal note-on/off boundaries | Possible harmonic boundaries; no forced bar cuts. Already-held notes are clipped to the request without inventing attacks. |
| Segment scores | Published Pardo–Birmingham six-family/72-root baseline. Positive note-cell evidence minus negative evidence minus missing chord PCs. Cell counts, not duration weights. No stylistic tie breakers. |
| Optimal predecessor DAG | Every equally optimal boundary path, stored compactly. Canonical path is serialization only, not preferred music. |
| Mandatory boundaries | Boundaries present on every globally optimal path. Counts refer to boundary paths, not full chord-label assignments. |
| Cell label consensus | Union of winning labels across every globally optimal covering edge, including no-evidence alternatives. `unanimous_under_this_objective` is not a confirmed chord. |
| Unknown overlays | Exact unknown/noninteger-pitch intervals retained separately. They cannot multiply pitched evidence by splitting the scoring grid. Partial evidence is explicit. |
| Conditional note context | Explicit optimal-edge selection; shared note/root/register equation. A held note can change chord-relative role without changing pitch. Stale analysis is rejected. |
| Operational refusal | Invalid timing or excessive requested DAG edges produce explicit NOT_RUN status. No silent truncation or easier replacement. |

The method combines sequential chord tones into spans: the controlled C–E–G
arpeggio gains a C-major hypothesis despite no simultaneous triad. Repeated
triads retain optional boundaries without forcing chord changes. Incomplete
sonorities remain ambiguous; this vocabulary does not cover all guitar harmony.

Three frozen annotated-reference diagnostics: canonical-path strict duration
agreement87.5/86.5/74.1%, versus instantaneous exact sets76.9/84.6/71.9%.
All-optimal-path consensus strict agreement86.3/81.7/72.3%. Out-of-vocabulary
labels remain in denominators. These are qualified analyst-label comparisons,
not general accuracy or musical quality. Exact boundary agreement is recorded
separately; chord changes are not key changes.

New random Static X54387/rev9800793:4181source occurrences reconstruct exactly;
frozen first8source-frame requests cover part0 and ensemble. Independent raw
source arithmetic verifies the DAG optimum, all optimal predecessors and
canonical-edge labels/weights; actual isolated worker recomputes analysis AND
inverse from strippedT2. Code/source hashes and frozen local code snapshots are
retained privately. Planner approved this bounded method after fixing the
unknown-grid leak and strengthening the freeze. Existing detectors are untouched.

Still missing: justified local key/harmony-function inference, general modes,
non-chord-note functions, sounding/tie-aware context, artist context, nonzero
style-preserving choices, and full all-field/all-tier GP reconstruction.

## Conditional note motion and chord membership

| Relationship | Owned evidence and limit |
|---|---|
| Three-note motion | Exact signed semitone changes, register return, durations and gaps. Uses preserved source bar/beat/note addresses, never storage order. |
| Melodic-line eligibility | Refuses grace, unknown pitches, simultaneity, overlapping same-voice notes, skipped occurrences and noncontiguous intervals. Raw rests, ties and attacks are outside this T1 scope. |
| Joint chord membership | Up to three explicit note/time queries on ONE globally optimal harmonic path. One chord label per edge applies to every query it covers; incompatible alternatives cannot be mixed. |
| Held-note context | The same occurrence can be queried at different half-open interior times without inventing another note attack. |
| Uncertainty | All feasible membership vectors; one valid whole-path witness per vector. Unknown and unsupported fractional pitches stay unknown. Query-clock and supporting-edge incomplete evidence are separate. |
| Musical function | Chord membership and measured motion are evidence, not proof of passing/neighbor intent, diatonic steps, established key, mode or emotional meaning. Those labels remain unresolved. |

`note_motion_evidence` and `harmonic_membership_evidence` consume T2 only.
The stripped isolated worker uses the SAME functions and the existing shared
inverse; no source/expected lower data is staged. Exact scope remains the owned
written T1 fields, not complete GP or technique execution reconstruction.

Frozen random Songsterr91316/rev5925322:655/655 source occurrences match;
the first fixed triple contains a grace occurrence and correctly refuses a
unique melodic interpretation. Its two positive-duration members still receive
conditional membership checks; the grace is retained as unqueryable, not replaced.
Independent raw arithmetic checks source motion/refusals and returned witnesses;
exhaustive small-case tests establish joint-vector completeness separately.
The initial failed source-order test is retained. No claim of annotated note-role
accuracy follows from these results.

## Written tie continuity

Optional T1 `normalized-written-tie-context/4` extends the existing geometry/key
facts with only the source declarations consumed by accepted tie eligibility:

| Owner | Exact data / relationship |
|---|---|
| T1 part | Instrument domain, tuning and capo; original field presence/type/value. |
| T1 occurrence | Existing note ID plus string, fret, dead and tie declarations; original presence/type/value. No duplicate pitch/time stream. |
| T2 physical choices | Those source choices once; explicit true tie flags removed and represented by links or unresolved destinations. Missing/null/false/other scalars remain distinct. |
| T2 written tie link | Existing origin/destination IDs; same part/voice/string lane, exact adjacency, valid equal nominal position, explicit tie and compatible dead state. |
| T2 unresolved tie | Original destination plus reason; never repaired by guessing another note. |
| Written chain | Original occurrence references and derived nominal endpoints/extent. Unresolved incoming origins stay explicit. Timing-uncertain chains are quarantined. |

The pure `written_tie_edges` predicate is shared with the retained tie detector;
its legacy caller keeps the existing numeric constraint validation. Forward
analysis and stripped inverse rederive the SAME predicates and restore exact
declarations. Existing note coordinates are not removed or duplicated.

A tied three-segment notation and three untied repetitions therefore differ
in declared continuity while retaining all three original occurrences. Neither
an absent tie flag nor a resolved link proves a physical attack or acoustic
sustain. Existing written-occurrence harmonic evidence is unchanged; tie-aware
harmonic weighting and preparation/resolution identification remain open.

### Chain-to-harmony query

`tied_harmonic_context(T2, harmonic_evidence, origin_ref, clocks)` connects
declared continuity to the existing joint harmonic-membership relationships.

| Input / result | Exact meaning |
|---|---|
| Origin + one to three clocks | Explicit original chain origin; clocks inside its half-open nominal interval. Requested order is preserved. |
| Constituent mapping | Each clock resolves to exactly one original written occurrence. No fabricated long note or additional attack replaces those occurrences. |
| Harmonic scope | Current evidence must cover the whole chain and the compatible part/ensemble. Stale or incompatible evidence is rejected. |
| Joint membership | The SAME existing helper supplies path-consistent alternatives. Continuity can remain the same while chord membership changes. |
| Quarantine | Whole-chain timing uncertainty, dead/unknown pitch or unresolved incoming continuity prevents harmonic-role interpretation. |
| No resolved chain | Absent continuity and an unresolved explicit declaration are distinct outcomes. Neither proves an acoustic attack. |
| Resource outcome | Original NOT_RUN is retained; no shorter or easier chain is substituted. |

The controlled tied C4 across C-major then G-major changes from member to
nonmember. Writing the same pitches as untied repetitions preserves those same
harmonic memberships; only the continuity relationship differs. This does not
identify a suspension, preparation, resolution, local key or emotional function.

## Conditional reference-collection degrees

An explicit existing tonal-candidate ID supplies the tonic and reference
collection. This is a reference for the query, not a chosen true key or mode.

| Relationship | Meaning / limit |
|---|---|
| Optional degree | Exact integer1–7 for a note inside that reference collection. Chromatic and unknown notes remain unmapped; no nearest-degree guess. |
| Register | Existing tonic-PC/MIDI-zero reference convention. It is not authored letter spelling or a newly added tonic note. |
| Shared equation | `pitch = tonic_pc + 12 × relative_octaves + reference_intervals[degree − 1]`. Solved and checked in both directions for mapped members. |
| Signed diatonic movement | `7 × octave_difference + degree_difference`. Adjacent movement has magnitude1, including7→1 across an octave. |
| Chromatic distance | Exact semitone distance retained separately. A14-semitone leap can span eight scale degrees; it is not an adjacent step. |
| Source eligibility | Diatonic melodic movement is withheld for ambiguous/nonconsecutive/grace/unknown/gapped sequences. Individual note coordinates remain separately visible. |
| Shared contexts | Global and temporal note contexts use the SAME degree calculation and existing source/candidate/time references. No bulk note×candidate products. |

Exact inverse scope is explicit: mapped reference coordinates solve their pitch;
outside-collection notes still reconstruct through their existing exact written
realization. This does not identify passing tones, authored spelling, chord modes,
harmonic function or style-preserving variation.

Fresh frozen Songsterr14355/rev9766773:9,254source occurrences match and reconstruct
exactly from stripped T2. All six first-owned-voice triples remain, including three
melodic refusals. Twelve parallel-reference contexts contain36note evaluations:
25mapped degree inversions plus explicit unmapped/unknown cases. Independent
native major/natural-minor checks cover3,072tonic/MIDI combinations;336published
profile-score comparisons pass. The winning KS score chooses only a query reference;
tied/undefined maxima remain inconclusive. No source key-accuracy claim follows.

## Joint reference-collection and harmonic context

`joint_reference_harmonic_context(T2, harmonic_evidence, queries, candidate_id)`
joins existing relationships without introducing another score or chord vocabulary.

| Stored relationship | Exact meaning |
|---|---|
| Explicit reference | Existing global, part or temporal candidate ID; never silently promoted to the true key. Temporal candidates apply only inside their actual frame. |
| Note → reference | The SAME scale-degree/register equation; chromatic and unknown cases remain explicit. |
| Note → chord | Every covering optimal chord label and its note membership. These are marginal possibilities, not independent choices that can be freely combined. |
| Joint alternatives | Existing path-consistent membership vectors, with one whole-path witness per vector. A witness proves existence, not uniqueness or every possible label interpretation. |
| Complete evidence | Full harmonic DAG/scoring package stored once, referenced by canonical SHA256 and exact request. The hash alone cannot replace that package. |
| Unresolved meaning | Established key, mode, chord mode and harmonic function remain unset. No emotional intent is inferred. |

A controlled A# against an explicit B-natural-minor reference is outside that
collection while remaining a member of a supported F#-major chord. This does
not prove B minor, harmonic minor, tonicization or a particular artistic intent.

Fresh frozen Songsterr6701/rev9071983:3,842source occurrences match; the entire
owned Tier1 and the same joint query output reconstruct from stripped Tier2 in
the isolated worker. All three first-owned-voice triples remain; percussion
queries retain unknown pitch. Independent checks verify192profile scores,
the complete bounded harmonic DAG and feasible membership vectors, all marginal
labels, native reference degrees, source clocks and stored evidence hashes.
The source's312resolved and11unresolved explicit tie declarations are preserved.
The selected pitched source notes happen to belong to both reference and chords;
the outside-reference contrast is controlled-test evidence, not a source finding.
