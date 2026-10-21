"""Transient channel projection through the existing numeric equations.

A view is NOT validation of its parent and must never replace complete parent
validation after an owning operator restores intentional holes. No new solver.
"""
from copy import deepcopy
from reversible_relationships import ConstraintError,validate_channels,realize_numeric,factor_numeric


def project(model,channels):
    if isinstance(channels,str):raise ConstraintError("Channel collection required, not a string")
    fields=list(channels)
    if not fields or any(not isinstance(k,str) for k in fields) or len(set(fields))!=len(fields):raise ConstraintError("Nonempty unique channel selection required")
    validate_channels(model["channels"])
    if not set(fields)<=set(model["channels"]):raise ConstraintError("Unknown projected channel")
    fields=sorted(fields);view=deepcopy(model)
    view["channels"]={k:view["channels"][k] for k in fields}
    for definition in view["definitions"].values():
        definition["masks"]={k:definition["masks"][k] for k in fields}
        definition["parameters"]={k:definition["parameters"][k] for k in fields}
    for occurrence in view["occurrences"]:
        occurrence["anchors"]={k:v for k,v in occurrence["anchors"].items() if k in fields}
    # Inherited definition keys are opaque registry references for this temporary
    # view. Re-factor solved rows through the SAME canonical factoring machinery;
    # never publish/store this cropped registry as an authoritative second cache.
    selected={r["id"]:r for r in realize_numeric(view)}
    regions=[dict(id=o["region_id"],unit=o["unit"],rows=[selected[ident] for ident in o["members"]]) for o in view["occurrences"]]
    return factor_numeric(regions,view["channels"])
