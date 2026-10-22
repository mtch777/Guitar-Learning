# Musical Tier2 — implemented interface

This is a bounded musical-analysis boundary, not the completed song engine.
`musical_tier2.py` consumes only retained T1 written-note facts. Its shared pitch
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
Tier2; they are unavailable until faithfully added to its preceding input.

Fresh Last Nite: 6152 exact occurrences, 4395 used for distributional exposure,
1757 unknown-pitch occurrences retained/excluded. Independent raw-source music21
oracle matched288 scores. Beatles regression matched384 more. These verify method
arithmetic and context links, NOT tonal-center accuracy. Full suite:816 tests,
815 passed/1optional skip. Planner approval and delivered commit recorded in log.
