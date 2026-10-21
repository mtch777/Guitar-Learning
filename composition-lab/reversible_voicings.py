"""Exact written attack co-onsets, jointly reconstructed with tie relations.

Lowest nominal-position anchor is NOT a chord root. No acoustic harmony claim.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import hashlib,json
from reversible_relationships import ConstraintError
import reversible_annotations as annotations
import reversible_ties as ties

REASONS={"explicit_tie_destination","zero_metric_duration","unknown_written_position","dead_note","invalid_written_position","incomplete_candidate","ambiguous_string_at_onset","no_other_eligible_co_onset"}


def select(facts,tie_destinations):
    ctx=ties.context(annotations.encode(facts)["physical"]);groups=defaultdict(list);excluded=[];order={ident:i for i,ident in enumerate(ctx)}
    for ident,r in ctx.items():
        if ident in tie_destinations:excluded.append(dict(id=ident,reason="explicit_tie_destination"))
        elif r["duration"]<=0:excluded.append(dict(id=ident,reason="zero_metric_duration"))
        else:groups[r["track"],r["onset"]].append(r)
    accepted=[]
    for rows in groups.values():
        invalid={}
        for r in rows:
            reason=("dead_note" if r["dead"] else "unknown_written_position" if r["position"] is None or r["kind"]!="pitched_position" or r["lane"] is None else "invalid_written_position" if not r["valid_position"] else None)
            if reason:invalid[r["id"]]=reason
        if invalid:
            excluded.extend(dict(id=r["id"],reason=invalid.get(r["id"],"incomplete_candidate")) for r in rows);continue
        if len({r["lane"][2] for r in rows})!=len(rows):
            excluded.extend(dict(id=r["id"],reason="ambiguous_string_at_onset") for r in rows);continue
        if len(rows)<2:
            excluded.extend(dict(id=r["id"],reason="no_other_eligible_co_onset") for r in rows);continue
        rows=sorted(rows,key=lambda r:(F(r["position"]),order[r["id"]]))
        anchor=F(rows[0]["position"])
        accepted.append(dict(members=[r["id"] for r in rows],intervals=[str(F(r["position"])-anchor) for r in rows]))
    return accepted,sorted(excluded,key=lambda r:r["id"])


def factor(groups):
    definitions={};occurrences=[]
    for group in groups:
        definition=dict(intervals=group["intervals"])
        key=hashlib.sha256(json.dumps(definition,sort_keys=True,separators=(",",":")).encode()).hexdigest();definitions.setdefault(key,definition)
        occurrences.append(dict(definition=key,members=group["members"]))
    return definitions,occurrences


def equations(model):
    result=[];known={};holes=[];used=set();seen=set()
    for occurrence in model["occurrences"]:
        if set(occurrence)!={"definition","members"} or occurrence["definition"] not in model["definitions"]:raise ConstraintError("Invalid voicing occurrence")
        key=occurrence["definition"];used.add(key);definition=model["definitions"][key]
        if set(definition)!={"intervals"}:raise ConstraintError("Unexpected voicing payload")
        members=occurrence["members"];intervals=definition["intervals"]
        if len(members)<2 or len(members)!=len(intervals) or any(not isinstance(i,str) for i in intervals):raise ConstraintError("Invalid voicing cardinality")
        values=list(map(F,intervals))
        if values[0]!=0 or values!=sorted(values):raise ConstraintError("Lowest nominal-position anchor required")
        if any(ident in seen for ident in members) or len(set(members))!=len(members):raise ConstraintError("Duplicate voicing ownership")
        seen.update(members)
        for i,ident in enumerate(members[1:],1):
            parameter=f"interval:{key}:{i}";known[parameter]=intervals[i];holes.append(ident)
            result.append({f"position:{ident}":F(1),f"position:{members[0]}":F(-1),parameter:F(-1)})
    if used!=set(model["definitions"]):raise ConstraintError("Unused voicing definition/cache")
    return result,known,holes


def encode(prior):
    facts=ties.decode(prior);tie_destinations={r["destination"] for r in prior["links"]+prior["unresolved"]}
    groups,excluded=select(facts,tie_destinations);definitions,occurrences=factor(groups)
    model=dict(schema="voicing-constrained-song/1",lower=deepcopy(prior),definitions=definitions,occurrences=occurrences,excluded=excluded)
    eq,known,holes=equations(model)
    physical=model["lower"]["lower"]["physical"]
    physical["position_patterns"]=ties.strip_coordinates(physical["position_patterns"],holes)
    # No staged voicing decoder: ALL holes solve jointly with tie equations.
    ties.decode(model["lower"],eq,known,holes)
    return model


def decode(model):
    if set(model)!={"schema","lower","definitions","occurrences","excluded"} or model["schema"]!="voicing-constrained-song/1":raise ConstraintError("Unexpected voicing upper fields")
    eq,known,holes=equations(model)
    facts=ties.decode(model["lower"],eq,known,holes)
    tie_destinations={r["destination"] for r in model["lower"]["links"]+model["lower"]["unresolved"]}
    groups,excluded=select(facts,tie_destinations);definitions,occurrences=factor(groups)
    if definitions!=model["definitions"] or occurrences!=model["occurrences"] or excluded!=model["excluded"]:raise ConstraintError("Voicing membership/exclusions differ from reconstructed facts")
    return facts


def hypotheses(model):
    """Derived existing labels, never reconstruction inputs or chord function."""
    from technique_analysis import classify_group
    return [dict(members=o["members"],labels=classify_group([dict(midi=F(v),string=i) for i,v in enumerate(model["definitions"][o["definition"]]["intervals"])])) for o in model["occurrences"]]
