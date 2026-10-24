# Composition Lab — tier and creative-lever acceptance plan

Updated 2026-10-23 with ProjectPlanner3000, against main `14f5d42`.
This is the active completion plan under the musical-analysis reset, not a
promotion of historical generation/profile/control prototypes.

## Goal

Source songs become nested, timed, source-linked musical relationships. The
SAME relationships run backward: exact source recovery at all-zero controls;
supported musical variation when specified choices are released; playable GP
output. Musical meaning, fidelity and source/artist feel require separate evidence.

Retain source conversion and approved technique detectors. Preserve private
scores, models, annotations and old baselines. No separate recreation/generation
engine, manually chosen pitch offsets or invented artist preferences.

## Mandatory tier gateway

**Every declared lever is part of its owning tier's acceptance.** A tier is not
complete until all its declared levers pass, or the user explicitly approves a
scope change. Unknown, unimplemented, unsupported and no eligible alternative
are separate recorded outcomes, never automatic passes. Independent levers within
the current tier can advance while another is blocked. Do not start dependent
next-tier work or promote the next tier until this gateway passes, unless the
user explicitly approves a scope change.

For EACH lever, record and verify:

- [ ] Musical meaning, scope, source/time witnesses and source-supported choices.
- [ ] Exact unlocked parameters, separately locked dimensions and dependency map.
- [ ] Sole preceding-tier input; single parameter ownership; SAME forward and
  backward relations; no lower-note stream/cached-answer fallback.
- [ ] QA 1: a frozen new random song through unchanged logic; failures retained.
- [ ] QA 2: lower/source/cache payloads removed; exact 0% reconstruction in the
  audited worker; independent comparison of the complete declared boundary.
- [ ] QA 3: source-backed musical relationships, positive/negative/ambiguous
  examples, unknowns and relevant independent interpretation checks.
- [ ] Supported nonzero proposals realized through those same relations, with
  other locks unchanged and incompatible requests explicitly refused.
- [ ] Current reference-release semantics: 0/50/100% controls, reproducible seeds, release opportunities and realized
  changes measured separately. 0 is exact; 50 is release probability, not an
  audible distance; 100 removes direct original target-value preference and
  allows coincidence. Validate the release mechanism across seeds/opportunities.
- [ ] Relevant downstream tiers/coordinates re-evaluated; no stale labels,
  impossible fingerings or contradictory timing introduced silently.
- [ ] GP conversion/import checks and actual rendered audible consequences where
  applicable. Human source-feel/playability judgments remain separate acceptance.
- [ ] Planner start/middle/end review, regressions, reproducible artifacts and
  commands/results. Mark exactly which scope passed and which did not.

Do not wait until Tier 6 to test edits: run a small supported change after each
new relationship's zero-control inverse is proven. Do not call one slice a pass
for the entire tier or for another lever.

## Tier ownership and required lever register

| Tier | Responsibility | Levers that must pass here | Current state |
|---|---|---|---|
| T0 | Immutable captured Songsterr JSON | None; source provenance/fidelity gate | Verified captured-source scope |
| T1 | Complete typed score facts | None; complete extraction, time/source ownership and reconstruction gate | Verified complete captured-JSON scope; not all acoustic execution |
| T2 | Local musical context and gestures | Every T2 row below, including each named technique separately | OPEN: exact source inverse and bounded conditional analyses; no active nonzero creative lever |
| T3 | Ideas and phrases | Idea/riff/motif development; call/response; phrase endings/resolution; phrase density; recurring rhythmic, pause/hold and accent patterns | Pending replacement architecture |
| T4 | Sections and arrangement | Part roles/interactions; texture/layering; instrumentation; section lengths; transitions; section density; section tempo/meter organization | Pending replacement architecture |
| T5 | Whole-song development | Section order/form; returns/transformations; whole-song tonal, tempo and intensity routes | Pending replacement architecture |
| T6 | Artist/style across songs | Context-conditioned support for the choices of earlier-tier levers, variation, exceptions, missingness and held-out predictive value | Pending replacement architecture; one song is not artist evidence |

T4/T5 are separate only if T5 adds relationships among sections. A name or larger
scope does not earn a new tier. Higher-tier controls propagate through lower-tier
relations without creating duplicate owners. T6 conditions choices; it does not
rewrite observed source facts or supply invented intent/emotional labels.

## Tier 2: readiness and missing pieces

No row below is a completed nonzero lever. Current `connected_tier2.reconstruct`
accepts ONLY explicit `variation=0`. Historical eleven-control prototypes,
conditional analysis reports and deterministic transposition tests do not change
that fact.

| ID / lever | Existing testable foundation | Missing before creative acceptance | Status |
|---|---|---|---|
| T2-01 Key / tonal center / mode | Source signatures; provisional global/local candidates; candidate-relative intervals and collection degrees | Independently supported center/collection selection and alternatives; coordinated pitch/harmony changes; missing/ambiguous contexts; mode changes beyond a forced major/minor choice | OPEN |
| T2-02 Chord progression | Candidate roots/qualities, harmonic paths, chord degrees and voice motion | Context-supported sequence proposals, joint path/role consistency and reconciliation of melody/bass/other locked parts; no automatic functional labels from template fits | OPEN |
| T2-03 Chord timing | Rational harmonic-span alternatives and active-note/overlap evidence | Supported changed harmonic rhythm; coupled held-note, rest, voice and tie updates; exact unaffected timing | OPEN |
| T2-04 Chord voicing / inversion | Actual sonorities, compatible chord PCs, bass versus root, interval/register relationships | Source-supported alternative selection, active edit interface, re-evaluation of context, physical/lock checks and GP/audio proof | FIRST IMPLEMENTATION CANDIDATE |
| T2-05 Melody function / contour | Conditional chord/collection degrees; directed motion; bounded passing/neighbor evidence | Coherent passage-level proposals; contextual non-chord roles; independent function, contour and octave locks; optional internal literal-pitch constraints; same-relation remapping and verification | OPEN |
| T2-06 Register | Exact pitch/octave/position relationships | Supported register choices, scoped propagation and conflicts with melodic octave, voicing and physical locks; active edit interface and GP/audio proof | FIRST IMPLEMENTATION CANDIDATE with T2-04 |
| T2-07 Local rhythm | Rational onsets/durations and source event/voice topology | Context-supported rhythmic alternatives; pulse/subdivision/accent relationships; coupled placement, meter/voice totals, rests and ties; no arbitrary time perturbation | OPEN |
| T2-08 Pauses / holds | Source rests, nominal durations, tie and sustain observations | Meaningful silence/hold alternatives; clear sounding versus notated duration; surrounding timing and technique dependencies | OPEN |
| T2-09 Local tempo / pulse / meter | Source tempo/meter declarations and measure geometry | Explicit local pulse/grouping/regrouping relations, tempo-map dependencies, re-metering and notation/time reconciliation; large-scale tempo routes remain T4/T5 | OPEN |
| T2-10 Dynamics / accents | Source velocity/markings and retained dynamic analysis | Context-supported expressive alternatives; inherited versus explicit values; acoustic/rendering consequences and locked surrounding expression | OPEN |
| T2-11 Articulation | Preserved staccato/ringing/connected markings and technique links | Separate execution/edit contract for each articulation; attack/end/sustain dependencies and actual rendering checks | OPEN |
| T2-12 Individual techniques | Source declarations, retained identification and bounded inverses | Per-technique musical placement/trajectory/destination relationships, supported proposals, dependencies, same-relation edit and playback evidence; see individual rows below | OPEN per technique |
| T2-13 Physical realization | Shared pitch = tuning + capo + fret relationship; source string/position choices | Supported alternative fingering/position/tuning/capo proposals, coordinated dependent changes and explicit machine/human playability limits | OPEN |

Melody function and octave are distinct locks. Revoicing/register changes cannot
claim to preserve a locked melodic octave. Changing harmony while locking
function may require pitch changes; optional internal literal-pitch constraints
and function locks can conflict. This does not introduce an additional user-facing
absolute-pitch similarity lever. There is no silent universal precedence rule.

### Individual technique acceptance rows

Each row needs the entire lever gateway above, not just an unchanged detector.

| Technique | Identification/declaration foundation | Creative-lever gate |
|---|---|---|
| Bends | Existing curves and approved identification retained | OPEN: contextual choice/trajectory, dependencies, shared realization and playback |
| String vibrato | Source flags and approved identification retained; unwritten speed/depth remain unknown | OPEN: supported execution parameters and independently checked rendering |
| Slides | Existing endpoint analysis and unknown/refusal cases retained | OPEN: supported endpoints/arrival timing and physical/tie/playback dependencies |
| Hammer-ons from open strings | Existing identification retained | OPEN: contextual transition choice, linked-note/string constraints and playback |
| Pull-offs to open strings | Existing identification retained | OPEN: contextual transition choice, linked-note/string constraints and playback |
| Palm muting | Existing flags/identification retained | OPEN: supported coattack/phrase choices and audible execution |
| Tapping | Existing source markings/analysis retained with limits | OPEN: supported physical/gesture relationships and playback |
| Harmonics | Source markings/values retained with sounding-pitch limits | OPEN: type/node/sounding-pitch/physical relationship and playback |
| Dead / ghost notes | Source distinctions and existing analysis retained | OPEN: supported placement/physical/expression choices and playback |

Fretted hammer/pull listening experiments stay retired. Tremolo picking is not
the user's string-vibrato request. Pedal identification and approved continuation
remain closed/protected; creative pedal behavior belongs to T3 pitch/rhythm
organization, with no special priority. Double stops, power/extended-power chords
and close-interval textures belong to harmony/voicing, not extra effect sliders.

## Current immediate experiment — not yet a delivered lever

- [x] Planner START reviewed constraints and proposed source-supported revoicing.
- [x] New random song selected/captured before analysis: Rolling Stones,
  Satisfaction, Songsterr 16453 / revision 7421771, six tracks;
  seed 9084737611129534236, query c. Prior corpus/captures excluded before draw.
- [ ] Freeze generic candidate eligibility and selection before seeing outcomes.
- [ ] Complete one bounded T2 passage and run all three source/inverse/meaning gates.
- [ ] Find an actual supported alternative realization in this song, or retain
  explicit no-eligible-candidate outcome. No replacement song or manual offset.
- [ ] Unlock only declared voicing/register scope; solve pitches/frets using the
  existing relations, refusing conflicting melody/technique/physical locks.
- [ ] Compare source-to-GP and reconstructed-to-GP baseline fidelity separately.
- [ ] Produce changed GP and audio, verify exact unaffected locks and audible
  difference; no human quality judgment invented.
- [ ] Planner MID/END, actual review QA and delivery. This is not Tier2 closure.

## Final completion gate

All implemented tier boundaries pass all three QA gates, individually and
composed. All declared levers meet their registered scopes and lock semantics.
Fresh held-out songs and independent artist families test portability, coherence,
style support and copying/diversity. Native GP fidelity, conversion limitations,
actual playback, physical execution and human musical/source-feel acceptance
remain distinct checks. No artifact count or test total substitutes for them.

## Plan-change verification

This update changes requirements and acceptance documentation only. No detector,
inverse, source, model, GP, audio or website changes. Prior source/math/CI results
remain dated evidence, not a new creative-lever pass. Planner confirms current
nonzero readiness from `connected_tier2.py`: none implemented end-to-end.
