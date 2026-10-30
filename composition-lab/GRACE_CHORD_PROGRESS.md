# Simultaneous grace chords at GP export

## Objective
Restore a source-declared simultaneous grace chord when the GP5 bridge has
split its existing notes into successive native grace beats. This is an opt-in
export repair, not a new musical choice or a change to technique detection.

## Acceptance checklist
- [x] Read current source and retained Green Day failure; identify importer cause.
- [x] Planner START/MID/END challenge and independent review.
- [x] Authenticate the complete source/native voice, exact note membership and
      ordered source occurrences before joining any fragment.
- [x] Reject unknown/missing/duplicate/remapped notes, incompatible fragment
      metadata, ambiguous hosts, cross-source joins and partial changes.
- [x] Preserve all existing note effects and their host relationships.
- [x] Export/reimport actual GP7; independent source grace checker passes.
- [x] Whole-score before/after comparison identifies every changed field.
- [x] Same frozen Green Day capture in a new development output; original failure
      and captures remain untouched. This is not a new random-song pass.
- [x] Recheck existing one-to-one grace positives and negative guards.
- [x] Actual accent GP/MIDI/audio output from the existing isolated inverse,
      or retain the specific remaining blocker without claiming success.

## Diagnosis
The backend hangs one grace on each host note. alphaTab 1.8.4's GP5 importer
`readGrace` creates a new Beat for each attached grace. Thus a two-note source
grace chord can become two one-note native grace beats. The measured example is
Green Day / Boulevard of Broken Dreams, track 3, bar 9, source beat 3. The
source/native regular onset grid already agrees; simultaneity does not.

The source supplies the intended grouping. No grouping may be inferred from
similar pitches, durations or musical taste. Ordinary source boundaries and each
grace chord's complete string/fret member set must authenticate correspondence.

## Boundaries
No change to approved detectors, standalone bend repair, dead-note/tie conversion,
percussion, source captures, original failures or unrelated WIP. Native playback
of grace timing remains renderer behavior, not proven recorded performance.

## Results and next action
Implemented `join_source_grace_chords.mjs`, called only by the existing opt-in
pitched-grace exporter. Its pure plan matches complete source voices; contiguous
native fragments must have disjoint string/fret sets exactly equal to ONE source
grace chord. Every serialized beat property must agree except ID, note membership
and performed start/duration. Conflicting automation, text, dynamics, mode, glyph
duration or nominal position refuses. Source member order is retained.

The candidate uses the native serializer, preserving note IDs, effects and explicit
target-note links. Duplicate IDs or unresolved note links refuse. Planning and
candidate construction never mutate the original native score. The existing
complete one-to-one grace validator runs on the candidate before export; the
independent source oracle runs after real GP7 reimport. Default export is unchanged.

### Green Day development result
Six source grace chords are restored from twelve importer-created one-note beats.
The independent GP7 checker passes all 92 pitched grace beats / 98 grace notes in
73 voices. The two percussion graces remain explicitly unchecked.

Whole-score native comparison: 10,157 notes and 346,130 serialized note fields
match, including slide/hammer/tie target IDs. Every regular beat field and clock
matches. The only retained-beat differences are the six joined grace glyphs
(sixteenth to eighth) and their renderer-selected lengths (60 to 120 ticks).
This restores simultaneous attacks; it does not claim recorded grace performance.
After actual GP7 reimport, all 792 serialized slide/hammer/tie link endpoints among
8,944 pitched notes still point to the same track/bar/voice/beat/string/fret
occurrences. This additional check excludes percussion-specific export repair;
the before/after-join field comparison above still includes all native notes.

The original actual source-denied accent inverse outputs were copied, not rerun
or edited. Source, zero and changed GP outputs now pass native roundtrip and direct
source checks. One accent changes 0 to 1; its paired MIDI events change velocity
95 to 111. Source/zero audio samples match exactly. The change has measured audio
delta RMS 0.0009207866 focused / 0.0009207886 ensemble. No listening judgment.

Evidence: `local-artifacts/grace-chord-v1/development-greenday-qa/` and
`whole-native-join-audit.json`. The original failed Green Day output is untouched.
This is a same-song DEVELOPMENT repair; a new-random-song gate is still required
after the combined implementation is frozen by the parent task.

### Verification
`node --test` on `test_join_source_grace_chords.mjs`,
`test_restore_source_graces.mjs` and `test_check_source_graces.mjs`:
27 passed, no skips. Native tests cover before/on-beat chords, preserved slide and
hammer-pull destinations, note parent/index, source note order and idempotence.
Adversarial cases include conflicting automation, wrong membership, ordinary
boundary corruption, late-voice failure, duplicate IDs and unresolved links.

Five separate fixed-source regression copies reproduce prior results exactly:
Leper and Queen pass; Sweet Child and Knockin retain existing bend differences;
All Small Things retains its dead-note/tie identity refusal. All four completed
exports report zero new grace joins and unchanged prior grace/source checks.

Final ID-guard changes were verified with a separate new three-output export.
All GPIF contents match the audio-audited outputs after normalizing ONLY generated
chord UUIDs and their references; all other archive contents and bound bend curves
are exact. Raw GP bytes differ because chord UUIDs are generated at import.
`postguard-output-equality.json` records this distinction and current module hashes.

Planner independently approved this bounded repair after reviewing the code,
27-test result, full-note/clock/link comparisons and native/audio evidence. Approval
does not relabel the development repair as a fresh-song pass or human listening.

## Coordinated fresh-source regression

The parent selected B.Y.O.B. (6699) with one preregistered random draw shared by
rhythm and melody. Original and actual zero-worker exports independently pass
the existing source-to-model, GP5 effect and checked GP7 comparisons: seven
parts, 152 bars and 8,767 native notes each. Direct source checks report zero
differences over 5,315 pitched notes and 7,318 beats. Full normalized GP archives
and all 47,099 MIDI events match; 298-curve companion payloads match and remain
bound to their corresponding scores.

This source contains no pitched grace chords, so it is an unchanged-source
regression, not a second positive demonstration of this repair. Four percussion
grace notes remain outside the pitched-grace oracle. No changed audio or human
musical approval is inferred. Private evidence is
`local-artifacts/parallel-levers-v1/native-zero-review/review-summary.json`.

Next: parent publication and CI. No additional converter scope was introduced.
