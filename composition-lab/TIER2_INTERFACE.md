# Musical Tier2 — implemented interface

This is a bounded musical-analysis boundary, not the completed song engine.
`musical_tier2.py` consumes only its preceding T1 facts. Its shared pitch
relationship is `pitch = bass_register_anchor + voicing_interval`; analysis solves
for interval, reconstruction solves for pitch, and both validate the same contexts.

| Owner | Stored data | Meaning / limits |
|---|---|---|
| T1 input, nested once | Occurrence ID; part/bar/voice/beat/note; rational base pitch, onset and duration; typed coverage warnings | Exact normalized written fields. No sounding pitch, technique, rests or fingering reconstruction claim. |
| T2 written-start group | Source bar/part/time; lowest written register; member intervals, durations and notation addresses | Coincident written-note starts. Bass is not necessarily chord root; ties/attacks unknown. |
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

Full source/T1 ownership (techniques, rests, tuning/fingering/ties, expression and
source declarations); sounding/sustained harmony; justified key/mode/harmonic-span
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
