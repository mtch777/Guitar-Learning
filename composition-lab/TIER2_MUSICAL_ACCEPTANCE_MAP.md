# Tier2 musical acceptance map

2026-10-22. Requirements consolidation, NOT an implemented tier, selected model,
new benchmark or engine authorization. Applies THREE_QA_GATES.md and the design in
TIER2_MUSICAL_CONTEXT_DESIGN.md. The new information must be musical relationships;
a schema, codec or test fixture alone does not supply them.

## Evidence and assertion boundaries

| Relationship/question | Actually verifiable now | Interpretation still requiring evidence | Exact reversal obligation |
|---|---|---|---|
| Written/sounding pitch and time | Source occurrence, part/voice, rational clock, declared tuning/technique fields; known coordinate arithmetic | Harmonic sounding pitch, sustain/interpolation or execution when decoder/technique semantics are unresolved | Preserve every declared pitch/time/technique coordinate, including unknown and missing fields; a pitch-class label cannot replace octave/spelling/fingering |
| Key declaration versus inferred key | A genuinely present source declaration has exact source address/value; absence must stay absent | Tonic, local/global key, changing/unsupported center; declaration is evidence, not validated answer | Declared notation remains recoverable independently of inferred candidates; retain owned realization choices without a copied event stream |
| Literal sonority versus chord | Exact pitched members, attacks/continuations and scope can be checked; part-only and ensemble sets differ | Root/quality/omissions/inversion/harmonic span; dyad does not prove a complete triad, bass does not prove root | Anchored unwrapped member intervals, octave/voicing, exact temporal realization and unresolved events must recover previous facts via shared relations |
| Mode/collection | Given an explicit candidate center/collection, interval and degree arithmetic is checkable | Which center/mode is supported; chord-scale mode and song/local mode are separate; chord identity does not determine mode | Preserve distinguishing notes and contradictory/out-of-collection events; missing modal evidence must not be replaced by guessed notes |
| Each note relative to key/chord | Under each candidate context, exact interval, octave, membership and time intersection can be verified | Passing/suspension/extension/resolution and other functions; one note can have different conditional roles during its duration | Same source occurrence and full trajectory recoverable, not merely a degree or chord-tone flag; changing context cannot silently retune a locked note |
| Harmonic transitions and span boundaries | Exact source declaration times where available; complete model coverage and signed boundary offsets | Whether a change is harmonic, ornamental or alternative segmentation; temporal context may help AND hurt | Preserve onset/release, ties and continuation through context changes, plus uncertainty; boundaries cannot silently quantize/drop events |
| Repeated voicing in different contexts | Exact source repetitions and independent memberships, not pooled duplicate counts | Same notes do not establish same chord/function; repeated cases are dependent | Shared definitions plus meaningful per-occurrence choices must return each distinct occurrence; sharing cannot erase variation |
| Artist/emotional account | Only declared provenance, measured relations and review status | Artist understanding, emotional intent and audible effect require additional cross-song/audio/human evidence | Neither a lossless inverse nor confident labels prove artistic meaning; no automated emotional PASS |

`interval_of_note_base_key` and `interval_of_note_current_chord_mode` must identify
their context candidate and exact time segment. Store chord-root distance separately
from optional chord-relative mode/degree; UNKNOWN mode must not suppress the known
root interval. Preserve octave as well as pitch class. Written base and sounding
trajectory views must be named separately. These are required semantics, not a
mandated JSON layout or permission to invent a mode detector.

## Observed cases that future QA must retain

| Existing evidence | Required assertion | Prohibited shortcut |
|---|---|---|
| Beatles source C sonorities, later repeated contexts and original-method local/global disagreement | Preserve exact declaring-part and ensemble evidence; compare local candidate support separately from global decoded context | Model agreement as truth; force C whenever that pitch set appears |
| Beatles incomplete A-only/Dm or rootless/track-conflicting source declarations | Mark source declaration, literal evidence and interpretation ambiguity separately | Treat every chord symbol as complete ensemble ground truth or invent missing members |
| Reference003306b: local winner missed globally; local loser recovered globally | Include BOTH error and recovery classes, exact source spans and unchanged original model provenance | Change weights/boundaries to make local winners always win |
| Reference005708b: same paired outcome, with different denominators | Preserve per-score counts and limits; do not pool into a claimed general accuracy | More reference runs presented as progress toward a reversible musical tier |
| RoughBoy metadata.hasChords plus separate supplemental chord resource | Keep independent resources/revisions and explicit unresolved timing; frozen notation unchanged | Availability flag or untimed token used as beat-aligned harmonic truth |
| Sum41 no captured timed chord labels | Retain source-portability evidence and interpretation UNTESTED/INCONCLUSIVE | Easier-song reroll, discarded song or fabricated labels |

Source-free reports: TIER2_SOURCE_DISAGREEMENTS.md,
TIER2_REFERENCE_BOUNDARY_RESULTS.md and CHORD_SOURCE_AVAILABILITY.md.
Existing references describe observed limitations; they are not ready-made training
labels, a new adjudicated dataset or permission to hardcode their answers.

## Smallest next checks, without implementing a musical engine

1. **Evidence-envelope validation.** Against an actually declared preceding-input
   schema, require occurrence IDs, rational half-open spans/point events, part/voice,
   written-versus-sounding coordinate domain and source/hypothesis type. Independently
   recompute event/context intersections. Reject wrong occurrence, shifted boundary,
   track-versus-ensemble scope swaps and a known claim built on unavailable pitch.
   The current flat evidence adapter cannot be called nested-tier validation.
2. **Conditional coordinate checking.** Only when a real candidate record interface
   exists, check interval/degree arithmetic, octave, membership and context changes
   against the supplied candidate. Keep alternative contexts distinct. Explicit
   unknown mode or key must survive. Tests must include same note/different context
   and same context/contradictory note; structural correctness is not label accuracy.
3. **Observed-resource integrity.** Validate source-address equality and resource
   revision/availability distinctions with the existing source checkers. No untimed
   supplement may satisfy a timed-label field. This is feasible now and needs no
   model run, renamed tier or rewritten conversion pipeline.

Only item3 is immediately executable on the retained actual source interfaces.
Items1–2 require a declared candidate/input adapter before code, not a fabricated
musical tier. The existing worker harness can test synthetic guard behavior only;
it cannot confer musical meaning or authorize a production adapter by itself.

## Gates requiring an actual future musical-tier implementation

| Gate | Completion evidence | Present state |
|---|---|---|
| Musical contract | New musical question, previous-input-only dependency, candidate/unknown semantics, exact ownership/realization and no-copy proof | Design exists; actual Tier2 implementation absent |
| Fresh portability | Frozen new source run with independent raw/relationship checks and complete unknowns | Extraction scope has evidence; interpretation accuracy not established |
| Shared inverse | Actual Tier2 output with lower payload removed; approved callable solves same relations at explicit0; independent field diff and consumed-code/I/O audit | Active operator absent; NOT RUN |
| Musical meaning | Walk real note through supported context/alternative to exact reconstruction; source-backed contrasts, context interventions, independent adjudication | FAIL/PENDING; reference results do not close it |
| Nonzero controls | Actual conditional proposals, coherent opportunity/lock semantics, measured intervention behavior;0regression retained | Not implemented; manual parameter edits are not percentage controls |

A useful next engineering endeavor must name one approved real interface and its
musical/reconstruction contract before coding. If none exists, finish that design
and ownership decision first. Do not add another report router, standalone inverse,
notation codec or model benchmark merely to make the dashboard greener. No step
here revives the retired architecture or alters accepted technique/pedal detection.
