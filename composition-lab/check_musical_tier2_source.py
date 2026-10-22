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


def check_declared_keys(capture, lower):
    """Raw declaration values/absence + independently computed written clocks."""
    import json
    parts=[json.loads(p.read_text(encoding="utf-8-sig")) for p in sorted(capture.glob("track-*.json"),key=lambda p:int(p.stem.split("-")[-1]))]
    # Reuse independent raw arithmetic oracle, NOT extraction/layout/core code.
    topology=source_expectation(capture,include_topology=True)
    raw_layout=source_expectation(capture,include_layout=True)
    starts={}
    for beat in topology["beats"]:
        _,_,part,bar,*_=beat["id"].split(":")
        key=(int(part),int(bar)); value=F(beat["onset_q"])
        starts[key]=min(starts.get(key,value),value)
    expected=[];issues=[]
    expected_inventory=[dict(part_id=p["partId"],measure_count=len(p.get("measures",[])),end_q=str(sum(raw_layout[len(p["measures"])-1])) if p.get("measures") else "0") for p in parts]
    if json.dumps(expected_inventory,sort_keys=True,allow_nan=False)!=json.dumps(lower["source_key_inventory"],sort_keys=True,allow_nan=False): issues.append("Typed inventory population/multiplicity differs")
    inventory={r["part_id"]:r for r in lower["source_key_inventory"]}
    if len(inventory)!=len(parts) or set(inventory)!={p["partId"] for p in parts}:issues.append("Source inventory parts differ")
    for part in parts:
        pid=part["partId"];measures=part.get("measures",[])
        expected_end=str(sum(raw_layout[len(measures)-1])) if measures else "0"
        if pid not in inventory or inventory[pid]["measure_count"]!=len(measures) or inventory[pid]["end_q"]!=expected_end:issues.append("Raw measure inventory/end clock differs")
        for index,measure in enumerate(measures):
            if "keySignature" not in measure:continue
            onset=raw_layout[index][0]
            if (pid,index+1) in starts and starts[(pid,index+1)]!=onset: issues.append("First beat conflicts with raw declaration bar start")
            expected.append(dict(id=f"key:{pid}:{index+1}",part_id=pid,bar=index+1,onset_q=str(onset),source_pointer=f"track-{pid}.json#/measures/{index}/keySignature",value=measure["keySignature"]))
    # Typed JSON comparison protects int/bool, absent/null and every occurrence.
    canonical=lambda x:json.dumps(x,sort_keys=True,allow_nan=False)
    if canonical(expected)!=canonical(lower["source_key_declarations"]):issues.append("Raw present/null/absent declaration population/value/time differs")
    return dict(status="PASS" if not issues else "FAIL",declarations=len(expected),parts=len(parts),issues=issues,
                scope="Every present/null declaration and absence inventory; onset from independent raw meter/pickup layout, including empty measures",
                end_q_scope="Independently recomputed raw meter/pickup layout end")
