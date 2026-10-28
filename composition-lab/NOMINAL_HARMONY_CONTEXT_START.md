# Common harmony over written spans: bounded START contract

2026-10-28. Bounded implementation and independent END review complete.
No physical-policy expansion, creative activation or source-label inference.

## Existing functions and actual gap

`musical_tier2.written_spans` already derives half-open active occurrence sets
from authoritative pitches, onsets and positive durations. It is source-bar
scoped and stores references, not another pitch stream. `note_context_at` tests
a focal occurrence against the full active population containing that note.
`contextual_passage_roles` already provides degree relations under scored edges
and unscored interval templates. Those interval-wide pitch collections are not
necessarily simultaneous sonorities and must remain a distinct evidence class.

The integration gap is a common, usable temporal evidence contract with
**explicit support populations**. Exact fit to a population containing the
focal note guarantees its chord membership by construction. Report that only
as descriptive whole-sonority compatibility, never independent support for a
note role, accompaniment identity, nonchord tone or musical intention.

## Inputs, scope and independently supported views

Input is the existing complete preceding-tier facts and authoritative musical
owners. Freeze the nine development cases plus Deutschland as ten unique
captures before results; Deutschland is development for this new experiment.
Keep current complete coattack evidence separately identified.

For each existing source-bar-safe written span, expose the complete active
source population and each original occurrence's nominal support interval.
Explicit nonpitched instruments are retained as excluded source refs; unknown
instrument/pitch/execution evidence is never silently treated as pitched truth.

For every active focal occurrence, derive these named support populations:

1. **Full focal-part population**, including the focal occurrence: descriptive
   fit only. Its fit/member result is expressly not independent role evidence.
2. **Focal-part minus focal occurrence**, removing that exact ID only: same-part
   conditional context from other written occurrences. Do not remove all notes
   with the same pitch class. Unison duplicates remain documented witnesses.
3. **Other parts only**, excluding the focal part entirely: cross-part written
   context. No other part is named accompaniment, bass or melody by this scope.
4. **Ensemble minus focal occurrence**: mixed-part complementary context,
   explicitly distinguished from the other-parts-only result.

Equal support-ref sets should reference a single computed population per span,
not be duplicated as independent evidence. Do not vote, average or count these
nested populations as statistically independent support.

Each complementary population supplies every exact observed-PC fit in the
existing pinned vocabulary, subject to the same complete-fit eligibility. No
template completion, invented third/root or carried source-label duration.
Removing the focal note can leave too little evidence or no exact fit: return
that result rather than add the note back to obtain a convenient chord.

Only after fitting the complementary population, evaluate the focal note with
the existing `note_role` relation. It can be a member, nonmember or unknown under
each retained hypothesis. 'Leave-one-out' establishes absence of direct focal
pitch input, not causal independence, actual accompaniment or intended function.
For example, a doubled unison may retain the focal PC after removal; disclose
the other occurrence's original ID instead of overstating independence.

## Timing, ties and uncertainty

- Exact rational half-open cells; original starts/ends only. Held notes are
  references to original occurrences, not newly attacked events.
- Preserve the current source-bar grouping. Inspect measure geometry and refuse
  unsupported cross-bar/invalid-clock population claims; do not quietly merge
  bars or claim full global sounding coverage. Record crossing events explicitly.
- Positive-duration written intervals do not establish acoustic release. Grace
  points, empty/rest intervals and clock quarantines remain counted separately.
- Accepted ties retain exact links and constituent IDs. No additional duration,
  retrigger or chain pitch is invented. Plain membership at a written instant
  does not mean a verified attack or acoustic sound.
- Separate known-written-pitch compatibility from execution certainty. A known
  literal pitch with an expressive declaration may support only that qualified
  nominal view; it cannot certify a sounding harmony or creative-safe context.
  Unknown/dead/fractional pitch and domain eligibility stay explicit. Source
  execution/tie/technique guards remain unchanged for all editing policies.
- Source chord declarations retain exact beat/member provenance and their
  existing admission scope. Never extend them over a span merely because the
  text occurs earlier or the harmonic hypothesis looks plausible.

## Owned outputs and SAME inverse

Store/reference span ID, rational bounds, scope/population IDs, complete included
and excluded source refs/reasons, evidence class, all harmonic hypotheses and
focal coordinates. Existing source/degree/family owners remain the only pitch
authority. No hidden source files, corpus models or cached lower stream.

Reuse the existing exact root/degree/octave equation in both directions for all
coordinates. Full inverse reconstructs the original source through existing
owners, then recomputes the SAME span/population/hypothesis/role function and
rejects stale or forged stored context. Do not describe this as reconstructing
notes from a guessed chord or inversion of inferred musical truth.

Track a held occurrence across adjacent spans using original IDs and the same
specified population/exclusion rule. Report all conditional degree/member
changes and ambiguity; no preferred root progression or resolution is selected.
If linking to existing scored harmonic paths, preserve that DAG's joint
compatibility; never mix interval-model labels with exact-overlap labels as
though they came from one model. Independent span alternatives do not establish
a coherent musical chord sequence by themselves.

## Acceptance checklist and finite done condition

- [x] START review fixes these scopes before inference implementation.
- [x] Complete ten-capture source denominator: all original events; positive,
  grace, nonpitched, unknown, crossing and timing-refused events; all source-bar
  cells including empty/rest/quarantined gaps; all active-note/cell incidences.
  Distinguish source groups, durations, hypotheses, population and role counts.
  Existing `written_spans` omits empty intervals: add accounting via real measure
  frames rather than calling its nonempty list the complete time denominator.
- [x] Independent literal raw interval arithmetic verifies every active set,
  included/excluded ref, population equivalence, boundary and focal role.
- [x] Focal-pitch mutation leaves complementary population fits unchanged when
  identity/time/domain and other source facts are fixed; only focal coordinates
  change. Deleting another same-PC note must change its witness inventory.
- [x] Contrasts: C/E/G background with focal D as nonmember; full-population fit
  tautology marked descriptive; too little/no-fit complementary evidence;
  E-only new start over held C/G; same held C across C-major versus G-major
  complementary contexts; duplicate unisons; same versus other-part scopes;
  ties; unknown/dead/expression/percussion; grace and exact half-open boundaries.
  Sequential nonoverlapping C/E/G must NOT become a simultaneous triad.
- [x] Label masking cannot change observation-derived span fits. Part/string
  renaming cannot introduce an accompaniment or melody preference. Preserve
  source IDs and global transposition equivariance through the degree equation.
- [x] Omitted/extra refs, altered population scope, falsely excluded unknowns,
  invented source-label duration, omitted alternatives, stale degrees and
  duplicated/overlapping temporal cells all fail independent and SAME validation.
- [x] MID review of complete accounting before fresh sampling.
- [x] Actual source-denied zero/full-source and common-relationship workers
  recompute without T0/T1 files, caches or expected answers. Exact zero remains
  unconditional even when no harmonic hypothesis is supported.
- [x] Freeze stable code, then preregister a bounded fresh-source gate; retain
  failures and no-fit populations. END audits actual worker outputs and all
  temporal/role denominators. No creative/audio/artist-quality pass is implied.

Done means a common time-scoped source relationship usable for held-note context
with direct self-support clearly separated from complementary evidence. It is
not another ranking study or permission to loosen the current voicing controls.

## Verified result and limits

Ten development captures:54,383 notes/534,317 facts;20 actual isolated workers.
Fresh preregistered November Rain8452/revision9927032:11,402 notes/145,447 facts;
both workers and independent source/native checks pass. Seed9448772484146180843,
letter i,89 eligible new IDs among first100 public search results,169 exclusions.
This is a bounded reproducible draw, not uniform catalog sampling.

Full suite:1,303 run,1,302 pass,one optional skip. ProjectPlanner3000 independently
audited actual worker outputs, raw source, native coordinates, frozen hashes and
random selection. Private repeatable audit/results are under
`local-artifacts/nominal-harmony-v1/` and `nominal-harmony-fresh-v1/`.

The independent checker shares the previously accepted source clock/rest-duration
primitives. Its interval partitioning, populations, fits, roles, counts, native
theory provenance and new raw rest pointers are independently computed.
Verified meter is a source-pipeline prerequisite: some missing-meter inputs fail
before this module's unavailable-geometry branch. Crossing, unknown-domain and
fractional branches have authored tests but no positive instances in these11
real captures. Population fit counts are exact PC compatibilities; timing-safe
role queries also require clear scope/focal refusals.

`unknown_pitch_occurrences` counts absent normalized pitch values across all
domains; `pitched_unknown_pitch_occurrences` isolates missing pitched values.
Nonpitched, unknown-instrument, unsupported fractional and genuinely missing
focal roles have separate statuses. `written_pitch_qualifications` is deliberately
not a complete execution-safety inventory; existing execution/technique/tie guards
remain authoritative. No source detector, permission or creative policy changed.

This closes the written-context contract, not Tier2, inferred key/mode, chosen
chord function, artist style or audible editing. Existing owners reconstruct
source; conditional hypotheses alone are not claimed sufficient for inversion.
