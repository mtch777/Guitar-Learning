"""Independent raw-source witnesses for written-start scope, not harmonic truth."""
from collections import defaultdict
from fractions import Fraction as F
from check_reversible_source import source_expectation


def check(capture, upper):
    raw, _ = source_expectation(capture)
    expected = defaultdict(dict)
    for ident, note in raw.items():
        _, song, part, bar, voice, beat, slot = ident.split(":")
        expected[(int(part), int(bar), note["onset_q"])][ident] = note["pitch"]
    issues = []; actual_keys = set(); witnesses = []
    for group in upper["coattacks"]:
        key = (group["part_id"], group["bar"], group["onset_q"])
        actual_keys.add(key)
        members = expected.get(key, {})
        if set(members) != {m["id"] for m in group["members"]}: issues.append("Source membership mismatch")
        known = [F(p) for p in members.values() if p is not None]
        pcs = sorted({p % 12 for p in known})
        ctx = group["interpretation"]
        if ctx["distinct_pitch_classes"] != list(map(str, pcs)): issues.append("Literal pitch classes differ from raw source")
        if ctx["unknown_members"] != sum(p is None for p in members.values()): issues.append("Unknown count differs from raw source")
        if known and F(group["bass_register_anchor"]) != min(known): issues.append("Bass register differs from raw source")
        for m in group["members"]:
            original = members.get(m["id"])
            if original is not None and F(m["voicing_interval"]) != F(original)-min(known): issues.append("Voicing interval differs from raw source")
        for candidate in ctx["chord_candidates"]:
            if sorted({F((candidate["root_pc"]+d)%12) for d in candidate["formula"]}) != pcs: issues.append("Candidate fails raw-source pitch-class witness")
        if ctx["chord_candidates"] and len(witnesses)<12:
            witnesses.append(dict(part=key[0], bar=key[1], onset_q=key[2], source_occurrences=list(members), raw_pitches=list(members.values()), alternatives=ctx["chord_candidates"]))
    if actual_keys != set(expected): issues.append("Source written-start populations missing")
    return dict(status="PASS" if not issues else "FAIL", source_groups=len(expected), issues=issues, witnesses=witnesses, scope="Independent raw written-start membership, bass/voicing intervals and candidate exact-PCS witness; NOT tonal or chord-function adjudication")


def check_overlaps(capture, upper):
    """Brute-force independent interval witness directly from raw JSON arithmetic."""
    raw, _ = source_expectation(capture)
    by_bar = defaultdict(list)
    for ident, row in raw.items():
        _, _, part, bar, *_ = ident.split(":")
        start = F(row["onset_q"]); end = start + F(row["duration_q"])
        if end > start: by_bar[int(bar)].append((int(part),ident,start,end,row["pitch"]))
    expected = {}
    for bar, rows in by_bar.items():
        times = sorted({t for _,_,a,b,_ in rows for t in (a,b)})
        for start,end in zip(times,times[1:]):
            active = [r for r in rows if r[2] <= start < r[3]]
            if active: expected[(bar,str(start),str(end))] = active
    actual = {(s["bar"],s["start_q"],s["end_q"]):s for s in upper["nominal_written_spans"]}
    issues=[]
    if set(actual) != set(expected) or len(actual) != len(upper["nominal_written_spans"]): issues.append("Nominal interval population differs from raw source")
    for key, rows in expected.items():
        if key not in actual: continue
        span = actual[key]; start = F(key[1])
        populations = [(span["ensemble_context"],rows)]
        if {p["part_id"] for p in span["part_contexts"]} != {r[0] for r in rows}: issues.append("Part context population differs")
        populations += [(p,[r for r in rows if r[0] == p["part_id"]]) for p in span["part_contexts"]]
        for evidence,population in populations:
            if set(evidence["occurrence_refs"]) != {r[1] for r in population}: issues.append("Overlap occurrence set differs")
            if set(evidence["starting_refs"]) != {r[1] for r in population if r[2] == start}: issues.append("Starting refs differ")
            if set(evidence["continuing_refs"]) != {r[1] for r in population if r[2] < start}: issues.append("Continuing refs differ")
            pcs=sorted({F(r[4])%12 for r in population if r[4] is not None})
            if evidence["interpretation"]["distinct_pitch_classes"] != list(map(str,pcs)): issues.append("Overlap pitch classes differ")
            for candidate in evidence["interpretation"]["chord_candidates"]:
                if sorted({F((candidate["root_pc"]+d)%12) for d in candidate["formula"]}) != pcs: issues.append("Overlap candidate fails raw pitch-set witness")
    return dict(status="PASS" if not issues else "FAIL", nominal_spans=len(expected), issues=issues[:20], scope="Raw source half-open written-duration overlaps, not acoustic sustain")
