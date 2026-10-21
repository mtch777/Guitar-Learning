"""One rational constraint system for forward/reverse pitch and metric time.

No song-specific constants, musical generator, source lookup or reverse rulebook.
Scope excludes fingering, performance, notation reconstruction and style claims.
"""
from collections import defaultdict,deque,Counter
from fractions import Fraction as F
import hashlib
import json


class ConstraintError(ValueError):pass


def solve(equations,known,required):
    """Resolve singly unknown affine equations; refuse unresolved/free variables.

    This is intentionally a conservative solver. It does not guess a free value
    or claim a general linear-system uniqueness theorem when propagation stalls.
    """
    values={k:F(v) for k,v in known.items()};users=defaultdict(list)
    for i,e in enumerate(equations):
        for variable in e:users[variable].append(i)
    queue=deque(range(len(equations)));pending=set(queue)
    while queue:
        i=queue.popleft();pending.discard(i);e=equations[i]
        unknown=[v for v,c in e.items() if F(c) and v not in values]
        subtotal=sum((F(c)*values[v] for v,c in e.items() if v in values),F(0))
        if not unknown:
            if subtotal:raise ConstraintError(f"Conflicting equation {i}")
        elif len(unknown)==1:
            v=unknown[0];values[v]=-subtotal/F(e[v])
            for j in users[v]:
                if j not in pending:pending.add(j);queue.append(j)
    missing=set(required)-values.keys()
    if missing:raise ConstraintError("Unresolved constraints: "+", ".join(sorted(missing)[:8]))
    return values


def equations(pitch_known,unit):
    """Same declarations are used with either observations or parameters known."""
    unit=F(unit)
    if unit<=0:raise ConstraintError("Positive time-unit gauge required")
    result=[]
    for i,known in enumerate(pitch_known):
        if known:result.append({f"pitch:{i}":1,"pitch_anchor":-1,f"interval:{i}":-1})
        result.extend([{f"onset:{i}":1,"time_anchor":-1,f"offset:{i}":-unit},{f"duration:{i}":1,f"ratio:{i}":-unit}])
    return result


def encode(facts):
    grouped=defaultdict(list);seen=set()
    for event in facts["events"]:
        if event["id"] in seen:raise ConstraintError("Duplicate occurrence identity")
        seen.add(event["id"])
        if F(event["duration_q"])<0:raise ConstraintError("Negative metric duration")
        grouped[event["part_id"],event["bar"],event["voice"]].append(event)
    definitions={};occurrences=[]
    for region,events in sorted(grouped.items()):
        events=sorted(events,key=lambda e:(F(e["onset_q"]),e["beat"],e["note"]))
        mask=[e["pitch"] is not None for e in events]
        anchor=next((F(e["pitch"]) for e in events if e["pitch"] is not None),None)
        start=F(events[0]["onset_q"])
        positive=[F(e["duration_q"]) for e in events if F(e["duration_q"])>0]
        unit=min(positive) if positive else F(1) # Explicit gauge, not performed ornament timing.
        known={"time_anchor":start}
        if anchor is not None:known["pitch_anchor"]=anchor
        required=[]
        for i,event in enumerate(events):
            known[f"onset:{i}"]=event["onset_q"];known[f"duration:{i}"]=event["duration_q"]
            required.extend([f"offset:{i}",f"ratio:{i}"])
            if mask[i]:known[f"pitch:{i}"]=event["pitch"];required.append(f"interval:{i}")
        solved=solve(equations(mask,unit),known,required)
        pattern=dict(pitch_known=mask,relative_intervals=[str(solved[f"interval:{i}"]) if mask[i] else None for i in range(len(events))],relative_onsets=[str(solved[f"offset:{i}"]) for i in range(len(events))],duration_ratios=[str(solved[f"ratio:{i}"]) for i in range(len(events))])
        key=hashlib.sha256(json.dumps(pattern,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        definitions.setdefault(key,pattern)
        occurrences.append(dict(region=list(region),definition=key,members=[e["id"] for e in events],pitch_anchor=str(anchor) if anchor is not None else None,time_anchor_q=str(start),time_unit_q=str(unit),unit_basis="smallest_positive_metric_duration" if positive else "all_zero_duration_gauge_no_performed_timing_claim"))
    reuse=Counter(o["definition"] for o in occurrences)
    return dict(schema="reversible-pitch-time/1",tier=2,scope="base_pitch_and_metric_onset_duration_only",definitions=definitions,occurrences=occurrences,
        abstraction=dict(definitions=len(definitions),occurrences=len(occurrences),shared_definitions=sum(n>1 for n in reuse.values()),unique_definitions=sum(n==1 for n in reuse.values()),occurrences_using_shared_definitions=sum(n for n in reuse.values() if n>1),normalized_pattern_numeric_parameters=sum(sum(p["pitch_known"])+2*len(p["pitch_known"]) for p in definitions.values()),occurrence_numeric_parameters=sum(2+(o["pitch_anchor"] is not None) for o in occurrences)),
        unsupported=["fingering/tuning/capo","techniques/performance","ties/rests/notation","complete GP/source inverse","stylistically validated nonzero controls"])


def decode(representation):
    if representation.get("schema")!="reversible-pitch-time/1":raise ConstraintError("Unsupported relationship schema")
    # Lower facts/caches are not legal inputs to this operation.
    if set(representation)-{"schema","tier","scope","definitions","occurrences","abstraction","unsupported"}:raise ConstraintError("Unexpected input/lower-tier payload")
    result=[];seen=set()
    for occurrence in representation["occurrences"]:
        if set(occurrence)!={"region","definition","members","pitch_anchor","time_anchor_q","time_unit_q","unit_basis"}:raise ConstraintError("Unexpected occurrence fields")
        if occurrence["definition"] not in representation["definitions"]:raise ConstraintError("Missing pattern definition")
        p=representation["definitions"][occurrence["definition"]]
        if set(p)!={"pitch_known","relative_intervals","relative_onsets","duration_ratios"}:raise ConstraintError("Unexpected pattern/source fields")
        mask=p["pitch_known"]
        if not isinstance(mask,list) or any(type(v) is not bool for v in mask):raise ConstraintError("Boolean pitch mask required")
        if len(occurrence["members"])!=len(mask) or any(len(p[k])!=len(mask) for k in ("relative_intervals","relative_onsets","duration_ratios")):raise ConstraintError("Pattern membership/cardinality differs")
        if any((v is None)!= (not present) for v,present in zip(p["relative_intervals"],mask)):raise ConstraintError("Pitch mask/interval availability differs")
        known={"time_anchor":occurrence["time_anchor_q"]}
        if occurrence["pitch_anchor"] is not None:known["pitch_anchor"]=occurrence["pitch_anchor"]
        required=[]
        for i,pitch_known in enumerate(mask):
            known[f"offset:{i}"]=p["relative_onsets"][i];known[f"ratio:{i}"]=p["duration_ratios"][i]
            required.extend([f"onset:{i}",f"duration:{i}"])
            if pitch_known:known[f"interval:{i}"]=p["relative_intervals"][i];required.append(f"pitch:{i}")
        solved=solve(equations(mask,occurrence["time_unit_q"]),known,required)
        for i,ident in enumerate(occurrence["members"]):
            if ident in seen:raise ConstraintError("Duplicate occurrence identity")
            seen.add(ident)
            if solved[f"duration:{i}"]<0:raise ConstraintError("Negative metric duration")
            result.append(dict(id=ident,pitch=str(solved[f"pitch:{i}"]) if mask[i] else None,onset_q=str(solved[f"onset:{i}"]),duration_q=str(solved[f"duration:{i}"])))
    return sorted(result,key=lambda e:e["id"])
