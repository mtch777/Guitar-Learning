# Procedural riff design

Active contract: [PROCEDURAL_RIFF_PROGRESS.md](PROCEDURAL_RIFF_PROGRESS.md).
Artist and Mode are the only generation inputs. The reference material supplies
phrase lengths, organization, returns, articulation and entry/ending relationships.
The existing Drop E player and fretboard remain the output.

## Alternatives considered

Four independent team drafts were compared. Their overlapping suggestions reduce
to these distinct mechanisms; combining their draft counts would inflate the list.

| Mechanism | Useful contribution | Why it is insufficient alone |
| --- | --- | --- |
| Adapt one complete reference program | Coherent whole-riff organization | Can become cosmetic transposition |
| Variable-order phrase transitions | Recombination from observed neighbors | Does not remember a distant return |
| Duration-aware musical states | Phrase roles with observed duration distributions | Broad labels erase specific gestures |
| Hierarchical phrase grammar | Parent ideas, dependent accents, varied returns | Can impose a stock A/B formula |
| Joint constraint search | Reconcile modal, physical and relational choices | Needs meaningful musical constraints |
| Compress music into repeat/vary instructions | Reusable identity and development | Compression is not musical importance |
| Generate an energy/register trajectory | Overall breathing and direction | A trajectory does not supply good notes |
| Co-plan rhythmic skeletons and pitch responses | Preserve groove and call/response | Separate streams can lose their coupling |
| Transfer compatible phrase-family contours | New material from observed vocabulary | Arbitrary swaps can break anchors and endings |
| Search connected entry/exit states | Make seams and endings actionable | Local compatibility does not create themes |
| Rank many structured candidates | Prefer stronger coherent realizations | Cannot create alternatives missing from the generator |
| Iteratively rewrite a relational program | Develop ideas through explicit operations | Requires bounds and conservation of useful relationships |

## Selected path

Use a complete source-derived relational program, transfer a genuinely different
compatible contour into its motif families, and realize the connected program
jointly. This combines whole-riff organization, hierarchy, contour transfer and
constraint search. Candidate ranking helps choose physical placements; it is not
a substitute for representing the relationships.

In this version, phrase order and form are inherited from a selected analyzed
reference program. The engine generates new pitches and contours within that
connected structure. Selecting and realizing an existing form is not a claim of
composing a new whole-riff ordering or learning a universal songwriting grammar.

This choice was tested on two differently organized complete programs, including
long phrases, dependent accents and technique links. Removing a return edge or
changing one mapped variation slot changes its intended destination while unrelated
material and local random seeds remain fixed. Literal semitone accents influence
the actual selected notes. These are causal checks, not label-count checks.

The first wider review found missing relationships despite successful generation:
an unchanged chord could change at a child boundary, a low answer could end up
above its high call, and independently chosen positions could create excessive
travel. Those findings require stronger joint decisions; they do not justify
calling every technically valid output musically successful.

## Intended execution

```text
PRIVATE ANALYSIS / COMPILATION
    retain original notes, clocks, ties, techniques and source identity
    identify witnessed phrases, nested gestures, accents and parent relationships
    preserve uncertain boundaries and rejected interpretations
    distinguish a reviewed riff from an inferred supporting passage
    identify complete returns and directed changes by occurrence correspondence
    establish opening and ending intent: deliberate loop, release, or unresolved
    extract source-supported shared tones, register roles and movement context
    create compatible NEW contour/equality programs for complete motif families
    prove privately that each new program cannot reproduce its source/transposition
    export only the new programs, safe relationships and pooled shape vocabulary

GENERATE(artists, E_mode, internal_seed)
    filter programs and shapes to the selected artists
    choose a supported complete program; retain failed candidate evidence
    establish its parent/child structure and source-derived phrase durations
    choose modal pitches for motif families
        share corresponding variables at exact returns
        share verified musical return slots while retaining each instance's marks
        preserve declared invariant slots in developed returns
        retain common tones and high/low relationships across phrase boundaries
        preserve source-supported articulation and salient interval functions
    choose string/fret placements across the WHOLE program
        retain holds, occupied strings and linked technique endpoints
        exact returns reuse the same execution
        open strings do not locate the fretting hand
        tapping is separate from ordinary fretting-hand reach
        rank travel using the observed source move and available time
        allow large shifts between phrases when the transition time supports them
        keep each phrase's ordinary hand position cohesive; open strings and taps
            have separate execution responsibilities
        reconsider earlier choices when a later relationship cannot be met
    verify the resulting events, not just the attempted choices
    verify opening/ending relationships and complete phrase ownership
    verify mode, novelty, relations, exact clocks and physical connections
    return one playable event stream + phrase/shape relationships + reproducible seed

DISPLAY
    play the entire riff, or start playback by clicking any phrase
    show exact generated contacts and active shapes on the full Drop E fretboard
    provide playback speeds and a timestamped JSON export
```

An exact parent may cross differently divided children. Its correspondence must
remain operative across those cuts; matching only identical flat child durations
does not integrate the newly learned hierarchy. An ending is not established just
because a capture stops there. A repeated internal cycle does not prove that a
later changed ending can be trimmed or looped back to the opening.

Music-equivalent returns have narrower authority than identical source execution.
Different engraving can coexist with equal observed notes, clocks and technique
connections. Text annotations stay private and explicitly uncertain; they do not
authorize copying execution or declaring a complete loop. The compiler independently
checks the actual occurrences before admitting a musical-parent relationship.

## Evidence and limits

The source collection, failed attempts and detailed annotations remain private.
A first public-pack candidate exposed an original-pitch hash that allowed source
reconstruction; it was rejected. The replacement exports newly compiled ordinal
programs and keeps original-pitch fingerprints and transformation witnesses private.

Artist selection currently filters available evidence. It does not claim a complete
learned model of an artist. Rhythms and articulation are reused deliberately from
references; new pitch/contour realization is not a claim of inventing every rhythm.
Muted browser/native checks establish playback wiring and event fidelity, not
listening acceptance. Completion remains governed by the progress checklist and
independent counterexample review.
