# Tempo: source and native execution investigation

No tempo owner, choice policy, converter repair or connected-model change is being implemented in this task. Musical-context review owns the source census. This review owns existing converter/native behavior and the performed clock.

## Acceptance checklist

- [x] Identify raw tempo fields, aliases, defaults, precedence, unknown types and ramps.
- [x] Compare explicit source positions/BPM against neutral model, GP5 bridge, actual GP7 and full MIDI tempo events.
- [x] Verify quarter-note positions stay fixed while seconds follow the integral of `60 / BPM` over quarter-note time.
- [x] Verify every part uses the same performed tempo map; inspect repeat traversal and explicit re-entry tempo changes separately from written bar locations.
- [x] Measure interactions with millisecond-based execution rather than assuming all note releases scale uniformly.
- [x] Report observed blockers and the smallest defensible scope; no repair or intervention implemented.

Evidence is private under `local-artifacts/tempo-native-semantics-v1`. Synthetic diagnostics are explicitly labelled as authored codec tests, never source-derived music.

## What the seven existing captures support

Reused ProjectPlanner3000's actual native-map audit; did not regenerate those seven scores. The source census found **438 aliases for 47 distinct global declarations**, all `track.automations.tempo[]`, positive integer BPM, `type: 4`, `position: 0`. No metadata tempo, beat-local tempo or ramp flag was observed. Absence remains absence, not an invented `false`.

| Evidence | Result |
|---|---|
| Every distinct source declaration exists at the same native bar/value, including redundant values | Pass on all seven |
| Export's copied source documents equal the current capture; native file hashes match | Pass on all seven |
| Active and performed step-tempo schedules | Pass on all seven |
| Native export level | Six GP7 scores; **AllSmallThings is GP5 only**, because its existing GP7 dead-tie failure remains open |

Native GP5 import labels later tempo automations `isLinear=true` even for these source steps. The pinned MIDI generator still emits steps. That native flag is not evidence of a source ramp. External Guitar Pro application ramp execution has not been established.

## Exact clock and converter checks

| Check | Observed result |
|---|---|
| Plain two-track diagnostic, one step changed 60→90 BPM | Every non-tempo MIDI event stays exact; both parts share the same clock |
| Total time from the actual performed MIDI map | `19/3` seconds → `17/3` seconds |
| Change interval ends at quarter 8 | Later absolute times remain **2/3 second earlier**, including after the next tempo declaration |
| Non-4/4 source position | `offset_q = 4 × position`: `.5` in 3/4 becomes 2 quarters; `.25` in 3/8 becomes 1 quarter |
| Redundant 120 BPM declaration at a bar start, through JSON→GP5→GP7 | Preserved; it resets tempo on repeat re-entry |
| Converted declaration followed by an authored native loop | `34/3` seconds with explicit reset; `12` seconds without |

The repeat loop was authored in the native diagnostic **after** converting the source tempo declarations. This proves converter preservation of the reset plus native repeat execution; it does not prove Songsterr repeat-notation conversion. The result agrees with the earlier `REVERSIBLE_TEMPORAL_CONTEXT.md` probe and closes its converter-bypass gap.

For step intervals, use exact rational `seconds = Σ 60 × quarter_span / BPM`. A sustained note's elapsed duration uses both endpoint times, splitting at every intervening tempo change. Written positions, performed repeat occurrences and seconds remain separate coordinates. Renderer millisecond/sample rounding is not exact rational time.

## Measured outside-scope problems

These do **not** occur in the seven observed bar-start tempo forms, but must not silently become eligible:

| Source/native case | Actual behavior |
|---|---|
| Metadata-only or non-first-track-only automation | Converter falls back to 120 or ignores the other track's map |
| First automation starts later than the song | Its BPM is applied from the beginning; position is lost |
| Fractional BPM | `120.75→120`, `60.75→60` before GP export |
| Automation between first-track beat boundaries | Position snaps forward to a beat; exact intended time is lost |
| Same-bar beat markings `120→60→120` | GP5 import drops the final 120 declaration |
| Contradictory track declarations at one time | Both native events appear; event order determines the effective tempo |
| Unverified note unit or declared ramp | Existing converter ignores it and emits ordinary step values; this is not a valid interpretation |
| A mid-bar tempo change with an earlier palm-muted note | Changing the later step 60→90 changes that earlier release **80→120 ticks**, although its actual tempo is still 120. Native note generation uses the upcoming bar tempo too early |

All initial 13 authored codec diagnostics nevertheless passed the existing GP checked-model roundtrip and regular source-note checks. Those checks do not establish tempo fidelity; an independent tempo ledger is required.

## Recommended boundary before implementation

Start with explicitly present, agreeing global aliases for positive integer `type: 4` **bar-start steps**, with an explicit initial tempo. Preserve every declaration and its presence; reject conflicting aliases, unknown units, ramps, missing starts and unsupported placement. This is an execution boundary, not a musical selection rule.

Keep all pitches, written clocks, dynamics and other markings locked. Verify the whole performed ledger, including every repeat visit and all later absolute seconds. Time-based note caps, bends, fades, grace and legato behavior need an exact consequence check or an explicit exclusion; they cannot be assumed to scale uniformly. No owner or source-conditioned choice policy has been approved by this investigation alone.

Private results: `source-model-tempo.json`, `native-tempo-report.json`, `non44-and-converted-reset-report.json`, `measured-clock-check.json`. The last report binds the reused Planner audit and verifies exact equations, whole MIDI equality in the plain diagnostic, source/native document identity and each GP hash.

Commands: `prepare_and_export.py`; retained `export_csv_gp7.mjs`; `probe_native.mjs`; `prepare_non44_and_reset.py`; `probe_non44_and_reset.mjs`; `check_measured_clock.py`. Final result: **PASS_EXACT_CLOCK_EQUATIONS_AND_MEASURED_SCOPE_CHECKS**, with the outside-scope failures above retained. No production source or test file changed.
