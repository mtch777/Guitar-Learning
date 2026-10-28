# Typed written events inside voicing context

## Scope

Explicit dead notes have a nominally unpitched role. They must not disappear
from rhythmic/context evidence, and a missing pitch must not be guessed.
This is an opt-in contextual relationship, not a new pitch owner or generator.
Existing degree, tuning and fret equations still reconstruct every occurrence.

## Relationships

- Exact `dead:true`, absent/false, and invalid types remain distinct.
- Known written pitch, nominal unpitched notation, and unresolved pitch/execution
  are separate. Unknown clock/lane, conflicting spelling and expressive execution
  remain refused. Only the two pitch-obstruction reasons attributable to explicit
  dead notation are removed; no slide, tie, HP or roll dependency is waived.
- Keep every event ID, order, string, onset, duration, declaration and rest/gap.
  Dead-fret presence, type and value stay physical notation, never a pitch claim.
- Mixed windows retain their typed slot sequence and signed intervals between
  known pitched members. A relation across a dead note is bracketing evidence,
  not consecutive picked-note motion or an identified melodic voice.
- Add a full span for every maximal dead-note run, including both neighbors or
  boundaries. Multiple dead notes cannot hide a changed bracketing octave.
- Independent source witnesses must exclude the entire changed neighborhood.
- Old policies and fully pitched path signatures remain unchanged. New control
  policy is `declared_degree_nominal_slots`; other control dimensions stay locked.

## Acceptance checklist

- [x] Planner START contract, including arbitrary-length dead runs.
- [x] MID: 30 producer/checker tests pass; independent raw checker accepts the
  authored same-inverse changed case with 21 witnessed paths and zero issues.
- [x] Actual isolated zero and changed reconstruction retain every dead field.
- [x] Missing witnesses, altered brackets, unknown/slide neighbors, wrong dead
  types, and dead-fret variants tested; default behavior unchanged.
- [x] Full regression: 1,220 passes, one optional skip (86.044 seconds).
  Freeze: 499 project / 266 native Python files. Seed 1204003730266738499,
  162 excluded song IDs; new capture: The Smiths, Heaven Knows I'm Miserable Now,
  song 17400, revision 9332590, ten tracks.
- [x] Same Queen 48 source proposals rerun without outcome-driven changes.
  Ten distinct changed layouts, none admitted. Four retain unresolved slides;
  all ten lack some independently observed neighboring pattern.
- [x] Actual source-free whole and degree-pair inverse plus independent raw
  checks pass on Queen, fresh Smiths, Police and Killswitch: 30,684 note
  occurrences / 294,008 typed source facts. All failures remain retained.
- [x] Planner END: all project/native/capture hashes, eight actual whole/pair
  workers and complete proposal ledgers verified. Independent raw inventory
  agrees on all 6,511 mixed paths / 1,466 dead occurrences / 2,801 known-pitch
  pair intervals, including 1,860 refused paths and every maximal dead span.
- [ ] Source-only commit/push and CI.
- [x] No real changed layout admitted; changed export/render is not applicable.
  Authored positive tests prove capability, not a successful real-song lever.

## Separate unresolved question

Physical string adjacency is contextual evidence, not established melody/voice
identity. This experiment keeps the existing independent-witness requirement.
It does not silently replace it with permission, infer artist intent, or claim
an absent pattern is inherently unmusical. Artistic listening acceptance remains
separate from exact reconstruction and bounded relationship checks.

All ten proposed Queen layouts preserve the lowest pitch but change the highest
pitch C5 <-> A4. That is an observed envelope change, not proof of melody identity.
The part is source-named Lead Guitar. There is no permission to silently treat it
as accompaniment. Fresh Smiths has 62 declared chord groups, 17 eligible targets
and 205 same-layout donor links, but no different observed layout. Neither outcome
proves that new voicings are musically impossible.
