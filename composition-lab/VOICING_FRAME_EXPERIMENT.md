# Root-relative voicing frames â€” bounded experiment

Question: are we missing reusable source voicings because the same chord degrees
occur under different roots or in different octave blocks?

Planner approved this experiment on 2026-10-28. The current creative policy stays
unchanged until evidence and the three QA gates justify an explicit integration.

## Relationship

For a whole source chord group, use exact rational arithmetic:

`frame = floor((lowest written pitch - declared root pitch class) / 12)`

`degree register = frame + octave offset`

The degree token retains its original theoretical meaning, including compound
degrees. An offset may be negative. This is a coordinate system around the
declared root, not an inferred key, bass role, inversion label or preferred
register. Existing degree-to-pitch relationships remain authoritative.

## Fixed experiment

Development cohort: all six already-frozen inner-voicing cases (Queen, Smiths,
Texas Flood, Linkin Park, Nirvana and Slayer). No claim that these are new tests.

| Arm | Donor family | Register coordinates |
| --- | --- | --- |
| A | Same song, part, root and chord kind | Existing absolute degree register |
| B | Same song, part, root and chord kind | Source pattern in target root frame |
| C | Same song, part and chord kind | Source pattern in target root frame |

All arms share eligibility, neighborhood exclusions and physical checks. Enumerate
every qualifying donor. Target root, chord label, explicit slash declaration,
literal outer notes, timing, strings and other source facts stay fixed. Each
donor has exactly one alignment; do not search octave shifts to obtain a pass.
Report donor links and unique actual layouts separately, including duplicate
layouts across arms. Keep every refusal and exact stage reached.

The old verifier requires literal donor pitches. A root-frame policy would need
an explicit degree/register relationship check in that position. Do not change
donor records to impersonate the old policy. Offline geometric preflight is not
admission; later execution/context/technique/pedal checks must still run.

## Acceptance checklist

- [x] Planner START approves the exact frame and comparison arms.
- [x] Exact frame-to-degree recovery, including compound degrees and inversions.
- [x] Source/candidate enumeration frozen before looking at outcomes.
- [x] Complete A/B/C denominator and refusal report; A matches existing results.
- [x] Planner MID challenges semantics, oracle independence and selection bias.
- [x] If useful, implement an explicit opt-in relationship using the existing
  inverse and unchanged remaining protections; otherwise retain the rejection.
- [x] New random capture chosen after code freeze; retain unsupported cases.
- [x] Actual isolated reconstruction after removing covered lower payloads;
  independently compare the exact declared scope against source.
- [x] QA3 separates demonstrated degree/register abstraction from unproved
  chord interpretation, inferred voice roles, artist fit and listening quality.
- [x] Planner END audits evidence and remaining gaps.

## END — rejected for creative activation

All nine existing isolated frame outputs were independently checked (216 groups).
Same-root normalization adds no changed layouts. Across-root normalization adds
twelve: eleven protected-envelope and one formula refusal. No policy activated.
The first RHCP random-source failure is retained; slapping ownership repairs and
same-source replays are development, not fresh evidence. QOTSA and Avicii have
zero covered declared-degree groups and remain explicit noncoverage outcomes.
Planner closure: local-artifacts/voicing-frame-v3/planner-independent-closure.json.
