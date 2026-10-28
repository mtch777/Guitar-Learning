# Project status against the final musical goal

## Final goal

Analyze source songs into a nested, timed, connected musical representation.
Use the SAME relationships backward: all controls0 recreate the source exactly;
released controls select supported musical changes. Ultimately produce playable
new GP compositions that preserve the source artist's musical character, with
listening evidence. Exact JSON recovery alone does not meet that goal.

Green = accepted within named scope. Yellow = partial. White = not yet delivered
in the current architecture. Historical retired prototypes are not completion.

| Roadmap step | Status | What is done | What remains |
|---|---|---|---|
| **1. Source pipeline** | Usable; export limitations remain | Songsterr JSON retained as T0; 98 tested GP files reopen; paired playback restores 866 pre-export bend curves. | Standalone GP still changes bend curves in 23 tested files and one track's instrument sound in another. The converter omits fine bend timing/point vibrato, pick scrapes, crescendo/diminuendo marks, sustain-pedal marks, dead-slap marks, lyrics and specified notation details. See the exact limits below; these are not all active blockers. |
| **2. Analysis** | Partial | Connected source facts, musical relationships and retained technique analysis share source/time references. | Turn conditional evidence into supported musical interpretations and complete execution relationships. |
| ↳ Source coverage | Verified for supported captures | Complete typed T1 facts; isolated exact reconstruction of supported captured JSON. The 30 pick-scrape declarations that blocked Zero now have exact typed T2 ownership; that capture passes complete reversal. | Unknown future source fields may still need T2 owners. Pick-scrape acoustic execution and GP export remain unsupported; preserved declarations are not a sounding model. |
| ↳ Technique identification | Protected within approved scope | Existing approved technique and pedal identification integrated; source declarations and accepted tie/HP/slide dependencies checked. | Identification is not full recreation: contextual placement, execution, sounding behavior and edit dependencies remain open per technique. |
| ↳ Musical understanding | Conditional / partial | Chord/key/mode hypotheses, note roles, overlaps, spacing, doubling/inversion distinctions and written lane-motion checks. Source-declared chord degrees now replace old pitch coordinates in58 supported real groups;245 notes reconstruct from root/degree/octave equations. | Reliable contextual choice, harmonic/voice-role evidence and ambiguity handling. Source labels do not establish sounding harmony or key. Numeric power-chord labels ending in5 currently fall back rather than use degree ownership. |
| **3. Artist profiles** | Not delivered | Source corpus and individual observations are available as foundations. | Multi-song, context-dependent patterns and exceptions; independent held-out evidence of artist-specific choices. |
| **4. Creation methods** | Partial | Same relationships reconstruct source and realize bounded source-supported local choices; simultaneous multi-chord choices now use one atomic inverse. Controlled tests pass where each isolated chord change fails. | All four real-song sequence trials still returned only existing voicings. Coherent musical decisions and an approved audible change remain undelivered. |
| **5. Controlled experiments** | Working infrastructure; musical acceptance partial | Frozen inputs, retained failures, stripped inverse workers, independent source/lock checks and positive/negative contrast tests. All 16 physically valid voicing proposals were independently checked and refused for insufficient context evidence. | Positive real musical changes, generalization and listening evidence. Refusal correctness and no-choice outcomes do not prove creativity. |
| **6. Levers** | Partial; none fully accepted at intended scope | Exact0 and measurable bounded controls; source-supported fingering changes verified through GP. | Each lever's supported alternatives, independent locks/dependencies, same inverse and relevant audible/playability evidence. No admitted real audible voicing change in the latest work. |
| ↳ T2 lever coverage | Foundations available | Relationships for key/mode, chords/timing, voicing, melody/register, rhythm/holds, pulse/meter, dynamics/articulation, techniques and fingering. | Finish each declared lever separately; doubling/inversion freedom and complete technique creation are not implied by existing coordinate or fingering proofs. |
| **7. Composition engine** | Local core only | Connected local relationships and inverse machinery exist. | Accepted higher tiers and coherent new whole-song GP output, using the same relationship chain. |
| ↳ T3: ideas and phrases | Not delivered | No accepted implementation in the current architecture. | Motifs/riffs, phrases, call-response, recurrence and development, with reversible ownership and controls. |
| ↳ T4: arrangement and sections | Not delivered | No accepted implementation in the current architecture. | Part roles, texture/instrumentation, sections, transitions and their musical dependencies. |
| ↳ T5: whole-song development | Not delivered | No accepted implementation in the current architecture. | Form, returns, transformations and whole-song tonal, tempo and intensity routes. T6 artist evidence must condition these choices. |
| **8. Validation and delivery** | Partial | Automated fidelity/lock infrastructure, native GP/render checks on tested changes; current checkpoint tested and delivered. | All three QA gates per boundary/lever, artist/style validation, human source-feel/playability and final complete-song listening/release review. |

## Specific source-pipeline limits

- **Bends in a GP file by itself:** 23 of the 98 tested files have changed bend curves after export/reopen. Our paired JSON companion restores 866 pre-export model curves for our playback path. Making the GP file alone equally faithful remains parked.
- **Bend detail lost before export:** the converter rounds bend time/height and does not use the source's finer `precisePosition` or point-specific vibrato flags. The companion cannot restore information that never entered the converted model. Raw Songsterr JSON still retains it.
- **Unconverted performance markings:** the converter explicitly does not export pick scrapes, crescendo/diminuendo markings, sustain-pedal markings or dead-slap markings. These are capability gaps when the fields occur, not a claim that every song contains them. Zero has 30 pick-scrape declarations. Their separate Tier2 ownership gap is now repaired; the exporter remains unchanged.
- **Unconverted notation/text:** lyrics, track title lines, written key signatures, original clef, grand-staff grouping, flat spelling of tuning and short/drone-string markings. These affect notation and player instructions; they do not by themselves prove changed note pitches.
- **Instrument sound:** one tested track reopens with program 27 instead of 30. Its playback sound selection changes. The other 23 native failures in this corpus are bend-curve differences; these 24 reports contain no separate whammy/tie/slide/duration difference category.
- **Playback verification:** automated reopen/render tests use alphaTab. Playback in the Guitar Pro desktop application has not been verified; this is missing verification, not a demonstrated additional defect.

Whole-bar-rest and dead/tied-flag conversion fixes are already delivered. Remaining
overlong source bars, ambiguous slide endpoints and mixed dead-to-pitched ties are
separate source-interpretation issues, not evidence those repairs are unfinished.

## Dependency order from here

1. Close the current local-voicing experiment honestly, including failures and any
   missing source declaration ownership. An authored positive is not a real-song win.
2. Complete musically meaningful T2 relationships and EACH lever's acceptance;
   test supported changes incrementally instead of waiting for a whole song.
3. Build T3 musical ideas and phrase development with the same exact inverse.
4. Build T4 sections/arrangement, then T5 relationships among sections and returns.
5. Connect multi-song artist evidence to the choices in those relationships (T6).
   Gather evidence progressively; do not call one-song patterns an artist profile.
6. Run complete source-to-new-song-to-GP experiments, independent source/style
   comparisons and actual listening/playability review. Correct demonstrated gaps.

Every step uses the three QA gates: genuinely new input, stripped exact inverse,
and meaningful musical abstraction. These are continuing acceptance conditions,
not a final testing phase. A reliable overall completion percentage is unavailable.

Current experiment details and final commands/results:
`AUDIBLE_VOICING_PROGRESS.md` and `CONTEXT_PREDICTION_PROGRESS.md`.

Previous delivered source checkpoint: `0097f34`, CI40476531318 SUCCESS. Current
local iteration: 1,161 Python passes /one optional skip, 43 JS passes, production
build passes. Four actual isolated reconstructions recovered 28,020 occurrences
and 247,802 typed source facts exactly, including the repaired pick-scrape capture
and one newly selected song. All 901 admitted sequence realizations matched the
original; no real audible voicing change was admitted. Controlled nonzero tests
pass, but real-song musical/lever acceptance is still open. Details and source
freeze: `MUSICAL_ITERATION_PROGRESS.md`.

Subsequent declared-chord ownership slice: 1,177 Python passes /one optional skip.
Four captures (including newly selected Jump) recover23,801 notes and240,745 typed
facts exactly in actual stripped workers. Planner independently approved the
bounded musical ownership result:58 selected groups /245 degree coordinates,
no duplicate pitch authority. This adds chord-degree meaning to exact reversal;
it does not deliver a nonzero creative voicing policy or audible change.
