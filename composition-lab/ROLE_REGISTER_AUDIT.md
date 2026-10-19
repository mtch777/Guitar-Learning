# Role/register comparison: source versus generated harmony

**The large harmony-register gap survives the measured tuning-offset and
alternative-anchor checks.** This is a bounded written-register finding, not
functional harmony, artist intent or proof of a musical remedy.

Use the original 1,311 known development melody boundaries (35 work families,
42 songs), unchanged family → song → boundary weights. All 953 unknown harmony
boundaries remain unknown. Recover the exact original lowest-part-ID selection;
do not choose whichever source track matches the generated result best.

Per row, verify:

- `H = harmony minimum − melody lowest open`
- `H = harmony own register + (harmony lowest open − melody lowest open)`
- `melody own register − vertical distance = H`

All rows and weighted means reconcile. Accepted source records independently
match 2,622 written-pitch groups and 4,553 note/string/fret/tuning relationships.
No selected harmony/melody pair shares the same track. Full source part/tuning
identities and exact clocks remain in private evidence.

| Weighted mean, semitones | Source | Original output | Rejected masked output |
|---|---:|---:|---:|
| Harmony above its own lowest open | 9.086 | 28.916 | 24.019 |
| Harmony-to-melody lowest-open offset | −0.229 | 0 | 0 |
| Melody above its own lowest open | 28.754 | 30.355 | 30.355 |
| Melody minus harmony minimum | 19.897 | 1.439 | 6.336 |

Both outputs use the exact same 107 eligible clocks; 8 lack active harmony.
Their means are not the four-core pooled means from the earlier G6 audit.
A closer vertical-distance **mean** does not cancel the rejected candidate's
worse vertical-distance **distribution** or its other failed frozen gates.

629/1,311 boundaries have multiple active eligible harmony parts. Enumerating
all such choices on the **same** cohort gives weighted-mean bounds:

| Measure | Minimum | Maximum |
|---|---:|---:|
| Harmony above its own lowest open | 8.744 | 10.517 |
| Harmony minimum above melody lowest open | 8.516 | 10.289 |

These are per-boundary extrema; they need not describe a consistent whole-track
assignment. The generated means exceed even those maxima. The enumeration is
limited to existing selected/accepted role candidates; unselected tracks,
misclassified roles, functional interpretation and artist fidelity remain open.

`role_register_audit.py` reproduces the source joins, accepted-note checks,
weighted identities, per-family coverage and alternative bounds. CLI outputs
must remain in private `local-artifacts`; no source annotations are published.
No detector, source role, generator default, failed gate or approved pedal changed.
