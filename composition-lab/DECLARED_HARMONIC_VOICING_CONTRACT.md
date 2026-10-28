# Source-declared harmonic voicing owner: START contract

Design for the next bounded implementation, 2026-10-27. This replaces selected
pitch ownership; it is not another report, predictor or independent generation
engine. No nonzero permission is activated by this contract alone.

## Purpose and existing pieces

Current bass-relative families distinguish spacing but not a stated chord root,
formula-degree multiplicity and inversion. The new scope uses literal source
chord declarations as conditional context. A declared Em/G is not the same claim
as a G-root chord merely because G is lowest. A declaration is source evidence,
not adjudicated harmony, key, artist intent or sounding-pitch truth.

| Existing component | Reuse; do not duplicate |
|---|---|
| Complete T1 / connected source choices | Sole exact source declaration text, topology, notation, tuning/capo and metadata |
| `chord_degree_definitions.py` | Generated music21 9.9.2 formula tokens, alteration and unwrapped semitones |
| `chord_degree_relations.note_role` / `pitch_from_degree` | SAME root + theoretical semitones + 12 × octave relation in both directions |
| `voicing_semantics.py` | Conditional hypothesis/support/membership/doubling/inversion lock checks; not an alternate pitch authority |
| `musical_tier2.py` | Canonical normalized group structure and all existing recomputed contexts |
| `voicing_families.py` | Existing owner for fallback groups; no retained interval backup for newly degree-owned groups |
| Source annotation / glyph diagnostics | Prior parser evidence and independently verified lexical normalization; not a runtime answer cache |
| Connected inverse / physical relation | Recover ordinary normalized pitches, then derive frets from actual owned string/tuning/capo choices |

## Initial admissible binding

Enumerate EVERY literal beat-level `chord.text` declaration from complete T1,
including null/wrong-type/unparsed/conflicting/unsupported occurrences. Keep an
explicit outcome and source fact reference for every declaration. Do not count
only successful examples.

A degree-owned group initially requires:

1. One unambiguous source declaration binding: exact declaring part, voice,
   measure, beat and nominal rational onset. Its written note occurrences must
   identify the complete coattack group; do not bind an arbitrary overlapping
   part or ensemble sonority. Multiple concurrent declarations or mixed source
   bindings fall back unless their unique binding is independently established.
2. At least two known integer base pitches; no grace/zero-duration member or
   uncertain clock. The group's observed PC SET equals the declaration's pinned
   formula PC set exactly, with no unknown/nonpitched members. Multiplicity may
   differ from the formula. Initial eligibility is stricter than the earlier
   annotation/overlap concordance diagnostic: do not promise the same counts.
3. A uniquely supported static parser interpretation in the pinned 50-form
   vocabulary. Custom alterations/additions outside it, ambiguous syntax and
   unmatched/contradictory formula sets fall back. Never choose a parse because
   it happens to fit the notes.
4. Unique degree-slot mapping for each member under that formula. Enharmonic or
   compound-degree aliases cannot be silently selected to manufacture a role;
   initially ambiguous mappings fall back with a specific reason.
5. Label pitch frame established for this scope. Initially accept absent/null/
   zero capo without inventing a shift; nonzero/unverified convention falls back.
   Never estimate a transposition offset by maximizing note agreement.
6. Explicit slash-bass, if present, agrees with the actual lowest written PC and
   is a supported formula member. A bare `C` DOES NOT assert C-bass: E/G bass can
   still be an observed inversion under that conditional C hypothesis.

No inherited label duration is inferred. A declaration binds only its exact
source onset/group. Arpeggiation or a held harmony across later groups needs a
separate temporal relationship; it is not enabled by this owner.

## Parser provenance and scope

Generate alias/formula, natural-letter and accidental tables reproducibly from
pinned music21 9.9.2 source. Runtime must remain pure stdlib and source-denied.
Use a mechanical finite lexical parser, not hand-written musical chord rules,
per-song lookup tables, staged source predictions or nearest-symbol guessing.
Compare its complete supported domain against the native library independently.

Resolve exact quality aliases BEFORE considering an optional FINAL slash followed
by a note token. `6/9` is a quality alias, not automatically a slash bass. Preserve
literal Unicode/ASCII spelling through the EXISTING source choice, including
case/alias spelling. Only generated root/bass accidental semantics may normalize;
quality suffixes are not rewritten (`F#m3` remains unsupported unless the pinned
vocabulary actually defines it). If two semantic parses remain, fall back.

Do not use the library's default `ChordSymbol.bass()` as an explicit bass promise.
Its default root-bass for an ordinary symbol is a parser realization, not a source
claim. Explicit slash-bass detection must follow literal syntax and generated
aliases, with targeted `C`, `C/E`, `C/G`, `C6/9`, `C6/9/E` and malformed tests.

## Sole ownership and minimum integration point

Add an explicit opt-in `declared_chords` mode at `connected_tier2.analyze`.
Legacy/default analysis stays unchanged. The mixed musical representation has
exactly ONE pitch owner for each group: supported declared-degree owner OR its
existing coattack/family owner. Fallback is a declared source-support outcome,
not an error that discards notes or breaks exact0 reconstruction.

The declaration literal stays owned ONCE by the current named source choice.
The degree group stores its source `label_ref`, source occurrence metadata and
unique degree-slot/register choices. Root/kind/formula are derived from the
referenced literal and pinned definitions, not stored as free editable duplicates.
Do not embed the raw label a second time, the old member pitches, old intervals,
old bass anchor or a backup spacing vector in the selected group.

Minimal inverse order:

1. Validate/decode existing non-fret source choices with the SAME scalar relation;
   at minimum make referenced declaration text available. This is access to the
   preceding owned parameters, not a source-file read. Keep existing known-fret
   ownership/coverage checks after normalized pitches become available.
2. Strictly parse each referenced label, verify its exact source binding and
   realize members with existing `pitch_from_degree`. Decode fallback groups
   through their existing owner. Build the prior normalized musical core once;
   recompute its bass/interval/context views from realized pitches using existing
   functions. Those derived fields are not stored as another pitch authority.
3. Continue the EXISTING connected physical inverse and source restoration. All
   source choices, technique owners, ordered source skeleton, coverage uniqueness
   and raw pitch/time consistency checks remain mandatory.
4. Recompute forward ownership from the reconstructed T1 and compare canonical
   representation, so stale label refs, wrong binding, inconsistent formula
   support or hidden fields cannot survive by silently switching owners.

Changing a structurally valid degree/register or source label can be a genuine
musical edit, not intrinsically detectable corruption without original evidence.
Current edit controls do NOT authorize it. Distinguish invalid representation
from a valid changed parameter; complete source/lock comparison must catch an
unauthorized edit rather than requiring the inverse to memorize source answers.

## Meaning and parameter gauge

For each selected member:

    pitch = parsed_root_pc + pinned_degree.theoretical_semitones
            + 12 * relative_octaves

Use the generated unwrapped slot (`9`, diminished `--7`, suspended `4`, etc.),
not merely modulo-12 semitone labels. Relative octaves are exact integers with
negative registers permitted where the equation requires them. The source chord
supplies theoretical degree spelling; it does NOT prove authored note spelling.
SPN/courtesy declarations remain exact separate facts; existing nonzero SPN
refusal remains until those note-spelling relationships are explicitly coupled.

Doubling is the observed degree multiplicity. Inversion is derived from actual
lowest note under the declared hypothesis. Bass register is derived, not a second
stored anchor. Preserve occurrence identities and metadata; no fabricated third,
new note, removed nonchord tone or forced acoustic attack. Other compatible
harmonic hypotheses remain available as conditional views, not silently erased.

## Independent checker and finite acceptance

Proposed `check_declared_chord_ownership.check(documents, upper,
restored_tier1=None)` returns status, issues and complete counts/reasons.
It must NOT import the producer lift/parser/eligibility decisions as its oracle.
Use direct raw declaration/source-address traversal and rational clock arithmetic;
use pinned native music21 ONLY in the parent checker for independent symbol
interpretation. Verify all selected AND fallback group/annotation inventories,
part/voice/onset binding, observed PCs, explicit slash bass, source frame, unique
slot matches, per-occurrence equation, cardinality and sole-owner coverage.
Original raw text remains external evaluator evidence, never worker input.

Required tests: all supported table aliases/roots vs native parser; ordinary C
with E-bass; explicit C/E success and C/G contradiction; quality slash syntax;
ambiguous/unknown label; false/null/float formula fields; bool/float register;
duplicate/missing/foreign occurrence or label refs; hidden old interval/cache;
wrong source binding; incomplete/missing/extra/unknown tone; fractional/grace/
timing/capo cases; stale owner and fallback injection. Malformed selected-owner
inputs refuse; valid unsupported original declarations remain legacy-owned.

Execute exact pairwise owner→prior-core and composed T1 stripped inverses in the
actual audited worker, with lower/source/cache unavailable. Independently compare
ALL existing frozen annotation cases, not favorable excerpts; retain parser and
coverage failures and report changed eligibility counts. Then exactly one frozen
new random portability slot after code/test freeze, without replacement. QA3 is
source-declared conditional chord/role ownership and its contrasts, not established
harmony, style or creative preference. Keep all prior detector/technique and GP
conversion limitations explicit.

Done for this endeavor means source-supported musical ownership actually drives
selected pitch reconstruction, with all three scoped QA gates and complete
fallback accounting. It does not grant inversion/doubling release, audible-edit,
artist-style or full-Tier2 acceptance. Any later such control requires its own
explicit harmonic/degree/melody/physical lock contract and source-supported choice.

