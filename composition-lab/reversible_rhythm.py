"""Higher rhythm tier: chronological relationships replace the onset channel.

Only ordered beat duration parameters and the preceding written-clock model enter.
No observed onset stream, copied onset-definition hashes, source paths or guesses.
"""
from copy import deepcopy
import reversible_written_clock as clock
from reversible_numeric_view import project
from reversible_relationships import ConstraintError,realize_numeric,factor_numeric,solve
from reversible_topology import BEAT_CHANNELS

DURATION_CHANNELS={k:v for k,v in BEAT_CHANNELS.items() if k!="onset_q"}


def encode(parent):
    clock.decode(parent)
    lower=deepcopy(parent)
    patterns=clock.topology(lower["lower"])["beat_patterns"]
    clock.topology(lower["lower"])["beat_patterns"]=project(patterns,list(DURATION_CHANNELS))
    model=dict(schema="rhythm-driven-clock/1",lower=lower)
    if decode(model)!=parent:raise ConstraintError("Rhythm relationships do not recover the exact canonical parent")
    return model


def decode(model):
    if not isinstance(model,dict) or set(model)!={"schema","lower"} or model["schema"]!="rhythm-driven-clock/1":raise ConstraintError("Invalid rhythm representation")
    parent=deepcopy(model["lower"])
    if not isinstance(parent,dict) or set(parent)!={"schema","lower"} or parent["schema"]!="shared-written-clock/1":raise ConstraintError("Rhythm requires the preceding clock tier")
    envelope=parent["lower"];top=clock.topology(envelope);patterns=top["beat_patterns"]
    if patterns["channels"]!=DURATION_CHANNELS:raise ConstraintError("Rhythm tier must contain duration channels only")
    frames,owners=clock.context(envelope)
    values={r["id"]:r for r in realize_numeric(patterns)};regions=[]
    for occurrence in patterns["occurrences"]:
        cursor=frames[owners[occurrence["region_id"]]]["start_q"];rows=[]
        for ident in occurrence["members"]:
            row=values[ident]
            rows.append(dict(id=ident,values=dict(row["values"],onset_q=str(cursor)),symbols=row["symbols"]))
            cursor=solve(clock.advance(),dict(start=cursor,span=row["values"]["duration_q"]),["next"])["next"]
        regions.append(dict(id=occurrence["region_id"],unit=occurrence["unit"],rows=rows))
    restored=factor_numeric(regions,BEAT_CHANNELS)
    for occurrence in restored["occurrences"]:del occurrence["anchors"]["onset_q"]
    top["beat_patterns"]=restored
    clock.decode(parent)
    return parent
