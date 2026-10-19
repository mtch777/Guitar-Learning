# What aligned patterns preserve—and what they do not

**Existing alignment preserves when parts play. It does not preserve or directly
control how their written pitches move together.** This is a scope finding,
not a musical accuracy score or an instruction to copy every source trajectory.

This audit uses the **existing** 12 aligned cores and their matched 100% role-pitch
outputs. It does not rebuild aligned generation or repeat its earlier marginal
technique-rate study. No new score, model or default is created.

## Matched evidence

Verify all 24 GP hashes against their archived batches, and each complete plain
canonical score against the actual GP archive. Composer and role-model hashes
match. Original generator and role-consumer Git blobs are recovered exactly;
the recorded `gp_author.py` hash is unresolved. This limits historical serializer
identity, not the separately verified current artifact comparisons.

The 222 newly generated recurrence cells share their source song/bar across
harmony, melody and bass. Source rhythm/rest membership matches both stages;
raw aligned note cardinality also matches. Existing earlier studies already
established these bounded scaffold properties.

Accepted source checks cover 504 selected role-bars, 4,514 written-pitch groups
and 6,906 note/string/fret/tuning relationships; no tie-destination rows occur
in those checked attacks. These remain written attack minima, not a complete
sounding-voice reconstruction or functional-role ground truth.

## New relationship measured

At the union of harmony/melody attack clocks, when both written events are
active, measure `melody minimum − harmony minimum`. Compare its change to the
next clock only when joint activity continues; do not bridge a rest gap.
Constant transposition of either whole part leaves these **changes** unchanged.

| Descriptive count | Raw aligned core | Later role-pitch stage |
|---|---:|---:|
| Exact changes among 1,002 changing source transitions | 36 | 23 |
| Same direction among those 1,002 | 435 | 381 |
| Same magnitude among those 1,002 | 59 | 42 |
| Exact zero changes among 702 unchanged source transitions | 260 | 299 |
| Complete equal trajectories, among 203 measurable cells | 1 | 1 |
| Complete equal trajectories, among 166 varying-source cells | 0 | 0 |

There are 2,068 jointly active points and 1,704 measurable transitions. Nineteen
cells have no measurable transition and are excluded from the 203-cell
denominator; counting their empty trajectories as successful preservation would
inflate the result. The one equal nonempty trajectory is constant.

Cells are clustered within 12 cores and reused source material: 160 distinct
source song-bars across 23 songs/23 families. These are **not** 1,704 independent
observations. Per-core/family counts, original stage records and examples remain
private. Independent delta rescoring and public CLI replay agree exactly.

## Implication for requirements

The raw aligned stage already resynthesizes root motion; later role-pitch
generation changes the resulting relationship again. This pinpoints where
shared rhythm ceases to imply shared pitch movement. It does not isolate an
audible cause, demonstrate that exact source copying is desirable, or invalidate
allowed unlocked variation. Earlier failed studies remain failed.

The missing capability here is **explicit representation and intentional control
of this signed inter-part interval-change trajectory**, with support and permissions—not another alignment toggle or
an unconditional hard lock to source pitches. Any next implementation must
declare which relationship is preserved, which variations are allowed and how
other locked dimensions survive.

Public tools: `aligned_relationship_audit.py` (exact relationship primitive) and
`audit_aligned_stages.py` (read-only archived-stage CLI). Private evidence:
`local-artifacts/source-transition-context-v1/actual-context-support-v1/aligned-stage-audit-v1/`.
