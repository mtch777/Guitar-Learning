# Local step-tempo source census

Scope: raw source inventory and a preregistered opportunity test only. No tempo
owner, selector, shared-clock edit or new source acquisition is authorized here.

## Acceptance checklist

- [x] Freeze the same five development captures plus already-seen B.Y.O.B. and
  Innuendo, with source hashes and the comparison rule before counting choices.
- [x] Inventory every tempo/BPM-related raw field and original source location.
- [x] Derive exact rational locations where explicitly supported; retain missing
  units/locations, malformed values, contradictions and ramp declarations.
- [x] Group coincident equivalent track copies into one global observation while
  retaining all literal aliases and their distinct source metadata.
- [x] Record each declaration's inherited lifetime and complete surrounding
  evidence; distinguish redundant redeclarations from actual BPM changes.
- [x] Compare metadata/start declarations without inventing missing clock values.
- [x] Count the preregistered rhythm-conditioned transition opportunities with
  complete denominators, refusals and independent source witnesses.
- [x] Cross-check native converter placement/unit/ramp semantics with the native
  reviewer; report source-level and native-supported scope separately.
- [ ] Review with Planner and stop before implementing a tempo owner or selector.

Proposed comparison, approved for census: same song/layout, source meter and
phase, known incoming step BPM, matching entry-bar per-part/voice attack/rest and
written-duration pattern with relevant dynamics/execution qualification. Pitches
need not match. Two distinct next-BPM witnesses must be independent of the target
and each other; all original aliases of one global event count once. Donor
lifetime is a dependency/independence fact, not an equal-length condition. The
target lifetime remains fixed. Suitability later in that lifetime is unproven.

Raw notation is not acoustic tempo truth. Missing values are not defaulted to
120 BPM or 4/4; explicit ramps will not be approximated as steps. No section,
emotion, intended groove or artist-level interpretation is inferred.

## Frozen questions and existing logic reused

Private `local-artifacts/tempo-census-v1/protocol.json` preceded raw field counts.
`protocol-v2.json` preceded opportunity counts and records Planner's refinement:

- **A, passage speed:** same source-defined entry-bar rhythm, meter and event
  phase; incoming BPM is risk metadata, not an equality requirement.
- **B, transition:** same A conditions, plus known identical incoming BPM.
- Every part/voice component and exact full-ensemble equality are separate
  strata. Entirely resting/inactive components do not supply positive rhythmic
  evidence. No main part is selected and no similarity threshold is used.
- Two distinct next-BPM witnesses must be independent of target and each other.
  One original global event counts once. Full antecedent/influence time ranges,
  tempo aliases, entry context and transitive note-execution dependencies are
  retained. Donor lifetimes need not equal the target lifetime.

`reversible_temporal.py` supplies the existing verified type-4 and position
equations; its decode and independent `check_reversible_temporal.py` source check
pass on all seven inputs. Accepted source clocks, inherited-dynamic observations
and execution links are reused. New code only connects those observations to
global aliases, lifetimes and exact rhythmic source comparisons.

## Actual source inventory

| Capture | Raw BPM declarations | Global events | Duplicate track aliases | A supported components | B supported components | Full-ensemble choices A / B |
|---|---:|---:|---:|---:|---:|---:|
| Sweet Child | 144 | 16 | 128 | 0 | 0 | 0 / 0 |
| All the Small Things | 12 | 1 | 11 | 0 | 0 | 0 / 0 |
| Earlier Queen capture | 8 | 1 | 7 | 0 | 0 | 0 / 0 |
| Knockin' | 18 | 2 | 16 | 0 | 0 | 0 / 0 |
| Leper Messiah | 32 | 4 | 28 | 0 | 0 | 0 / 0 |
| B.Y.O.B., already seen | 112 | 16 | 96 | 2 | 0 | 0 / 0 |
| Innuendo, already seen | 112 | 7 | 105 | 0 | 0 | 0 / 0 |
| **Total** | **438** | **47** | **391** | **2** | **0** | **0 / 0** |

All 438 declarations are positive integer BPM, explicit type 4, position zero,
stored in track automation lists. No metadata tempo, beat-local tempo, ramp flag,
conflicting tempo or unlocated declaration was present. Metadata/start tempo
agreement therefore cannot be measured: these captures contain no metadata tempo
to compare. All literal source aliases remain in the private output; the 391
duplicate copies do not become independent evidence.

There are **454 event-entry-bar components** in each A/B denominator. In A:
239 have no rhythmic attacks, 44 are unknown/partial, 169 are qualified but lack
independent contrasting BPMs, and 2 have a source contrast. No source was replaced.
The 44 unknown/partial rows comprise 20 nonnominal entry-bar spans and 24 rows
with unresolved execution endpoints/scopes. There are no missing-dynamics rows
in this actual sample. These are retained qualifications, not an instruction to
repair source notation or relax the comparison.

## What the two observations mean

Only B.Y.O.B.'s guitar part 3 / voice 0 supplies a contrast, at **bars 95 and
144**. Its exact entry-bar rhythm also appears at bar 1. The independently
separated original global events carry **153 and 162 BPM**.

| Original event | BPM | Incoming BPM | Declared lifetime, quarter notes | Antecedent + influence range |
|---|---:|---:|---:|---|
| Bar 1 | 162 | None before the source starts | 24 | 0–24 |
| Bar 95 | 153 | 162 | 16 | 316–392 |
| Bar 144 | 153 | 162 | 36 | 528–608 |

Both target bars have **five active components**. Only this guitar supplies
contrasting tempo evidence; the other four do not. This is **partial component
support**, not complete-band agreement. B fails because the 162-BPM witness is
the initial event, with no incoming tempo; the comparable incoming-162 witnesses
only lead to 153 BPM. A therefore does not prove that omitting the later slowdown
is an appropriate transition.

Recommendation for review: this is a narrowly identified passage-speed
hypothesis worth preserving. It does **not yet justify promoting a global tempo
choice as supported by the whole band or by the entire target lifetime**. No
owner/selector is built by this census, and no replacement condition or broader
BPM palette was substituted to force a result.

## Native findings and verification

The independent native reviewer verified all **47 actual source marks** using
the six existing GP7 outputs and All the Small Things' GP5 output. Original
document identity, GP hashes, bar-start tempo maps and performed schedule were
checked; source track aliases agree. Evidence:
`planner-actual-tempo-map.json` and the native reviewer's separate
`local-artifacts/tempo-native-semantics-v1/measured-clock-check.json`.

The current sources avoid measured converter failures: metadata/other-track-only
tempo maps can be ignored; fractional BPM can truncate; non-quarter units and
ramps are not faithfully executed; off-beat changes can move; same-bar return
changes can be lost. Mid-bar changes can also alter earlier palm-mute release
caps. These findings restrict a future owner/operation; they are not waived by
the clean current source sample. Absent ramp flags remain absent declarations,
not claims about the recording's physical tempo.

Commands and actual results:

- `python -m unittest test_tempo_source_census -v`: **6 passed**, covering raw
  inventory, duplicate aliases, A/B witnesses, inactive components, missing
  dynamics, conflicting BPMs, unknown units and explicit ramps.
- `python tempo_source_census.py .../protocol.json .../fields`: complete raw
  inventory, source hashes unchanged.
- `python tempo_source_census.py .../protocol-v2.json .../census --opportunities`:
  complete A/B census, source and census-code hashes unchanged. Every row,
  refusal, alias and source witness remains private in the per-song JSON.

Current state: census complete and delivered to Planner/root for interpretation.
No connected-tier, shared timing, detector, tempo owner or selector was edited.
