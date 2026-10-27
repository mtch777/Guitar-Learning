# Project status against the final musical goal

## Final goal

Analyze source songs into a nested, timed, connected musical representation.
Use the SAME relationships backward: all controls0 recreate the source exactly;
released controls select supported musical changes. Ultimately produce playable
new GP compositions that preserve the source artist's musical character, with
listening evidence. Exact JSON recovery alone does not meet that goal.

Green = accepted within named scope. Yellow = partial. White = not yet delivered
in the current architecture. Historical retired prototypes are not completion.

| Roadmap step | Proven / delivered | Still required to complete |
|---|---|---|
| 1. Source pipeline | 🟢 Captured Songsterr JSON as T0; usable JSON↔GP conversion | Preserve explicit conversion/execution limits; unsupported fields must fail closed |
| 2. Analysis | 🟢 Complete typed/time/source ownership on supported captures; approved technique/pedal identification retained | 🟡 Musical interpretation remains conditional; newly encountered fields can still block T2 coverage |
| ↳ Musical context | 🟡 Chord/tonal/mode candidates, note relationships, nominal overlaps and written motion | Context-supported harmony and roles, ambiguity handling and complete gesture execution; no guessed intent |
| 3. Artist profiles | 🟡 Source corpus and individual observations available | ⚪ Connect choices across songs, local contexts, repetition/variation, sections and tracks; measure independent held-out predictive support |
| 4. Generation methods | 🟡 Shared inverse and source-supported local choice operations | Coherent musical choices across a passage using the same representation; no separate generator or assistant-picked notes |
| 5. Controlled experiments | 🟢 Frozen inputs, failure retention, audited inverses, independent source checks and targeted contrasts | 🟡 Broader positive creative evidence, held-out style tests and listening; a no-choice outcome is not creative acceptance |
| 6. Levers | 🟡 Exact0 and bounded source-supported fingering; local spacing/context work under verification | Every declared lever must prove its musical scope, locks, dependencies, source support, same inverse and audible consequences |
| ↳ T2 levers | 🟡 Foundations for key/mode, progression, chord timing, voicing/inversion, melody, register, rhythm, holds, pulse/meter, dynamics, articulation, techniques and fingering | None is fully accepted across the final intended musical scope; technique execution/placement remains open individually |
| 7. Composition engine | 🟡 Local relationship/inverse machinery | ⚪ T3 motifs/riffs/phrases/call-response; T4 arrangement/sections/transitions; T5 form/returns/development; T6 artist-conditioned support; coherent full-song GP |
| 8. Validation and delivery | 🟢 Automated fidelity/worker/lock infrastructure | 🟡 Three gates on every new boundary and lever; native GP/render checks on actual changes; human source-feel and playability; final complete-song review |

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
