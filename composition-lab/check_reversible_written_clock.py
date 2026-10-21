"""Independent raw written-frame/address oracle for the bounded clock lift."""
from fractions import Fraction as F
import json
from pathlib import Path
from reversible_written_clock import timing_view


def expected(capture):
    meta=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"))
    parts=[json.loads(p.read_text(encoding="utf-8-sig")) for p in sorted(capture.glob("track-*.json"))]
    if any("anacrusis" in p and type(p["anacrusis"]) not in (bool,type(None)) for p in parts):raise ValueError("Unverified raw pickup flag")
    total=max((len(p.get("measures",[])) for p in parts),default=0)
    result=[];start=F(0);signature=None
    for i in range(total):
        declarations=[];signatures=set();fills=[]
        for p in parts:
            if i>=len(p.get("measures",[])):continue
            m=p["measures"][i];mid=f"measure:{meta['songId']}:{p['partId']}:{i+1}"
            if "signature" in m:
                raw=m["signature"]
                if not isinstance(raw,list) or len(raw)!=2 or any(type(x) not in (int,float) or x<=0 for x in raw):raise ValueError("Unusable raw meter")
                signatures.add(tuple(F(str(x)) for x in raw));declarations.append("meter:"+mid)
            for v in m.get("voices",[]):
                beats=v.get("beats",[])
                sentinel=False
                if m.get("rest") and v.get("rest") and len(beats)==1:
                    b=beats[0];notes=b.get("notes",[])
                    sentinel=(b.get("rest") is True and b.get("type")==1 and b.get("duration")==[1,1] and bool(notes) and all(n.get("rest") is True for n in notes) and not any(b.get(k) for k in ("graceNote","dots","tuplet","tupletStart","tupletStop")))
                if not sentinel:fills.append(sum((4*F(*b["duration"]) for b in beats if not b.get("graceNote")),F(0)))
        if len(signatures)>1:raise ValueError("Conflicting raw meters")
        if signatures:signature=next(iter(signatures))
        if signature is None:raise ValueError("Missing raw initial meter")
        nominal=4*signature[0]/signature[1];span=nominal;status="nominal"
        if i==0 and any(p.get("anacrusis") is True for p in parts):
            occupied=max(fills,default=F(0))
            if 0<occupied<nominal:span=occupied;status="observed_short_pickup"
            elif occupied==0:status="pickup_flag_without_independent_occupancy"
            else:status="pickup_flag_without_short_occupancy"
        result.append(dict(index=i,start_q=str(start),span_q=str(span),nominal_span_q=str(nominal),meter_evidence=declarations,status=status));start+=span
    addresses=[]
    for p in parts:
        pid=f"part:{meta['songId']}:{p['partId']}"
        for i,m in enumerate(p.get("measures",[])):
            for vi,v in enumerate(m.get("voices",[])):
                cursor=F(result[i]["start_q"])
                for bi,b in enumerate(v.get("beats",[])):
                    if isinstance(b.get("tempo"),dict):
                        owner=f"beat:{meta['songId']}:{p['partId']}:{i+1}:{vi}:{bi}"
                        addresses.append(dict(id="tempo:"+owner,owner=owner,kind="beat_tempo",status="linked",event_q=str(cursor)))
                    # Source's single whole-measure-rest duration cannot affect
                    # another beat in that voice (sentinel has exactly one beat).
                    if not b.get("graceNote"):cursor+=4*F(*b["duration"])
        for i,a in enumerate((p.get("automations") or {}).get("tempo",[])):
            if not isinstance(a,dict):continue
            address=dict(id=f"tempo:{pid}:{i}",owner=pid,kind="automation_tempo")
            if "measure" not in a or "position" not in a:address["status"]="missing_source_address"
            elif type(a["measure"]) not in (int,float) or type(a["position"]) not in (int,float):address["status"]="unsupported_source_address"
            else:
                index=F(str(a["measure"]))
                if index.denominator!=1 or not 0<=index<len(p.get("measures",[])):address["status"]="source_measure_out_of_range"
                else:address.update(status="linked",measure_ref=f"measure:{meta['songId']}:{p['partId']}:{int(index)+1}",event_q=str(F(result[int(index)]["start_q"])+4*F(str(a["position"]))))
            addresses.append(address)
    return result,addresses


def check(capture,model):
    frames,addresses=expected(capture);actual=timing_view(model)
    projection=[{k:f[k] for k in frames[0]} for f in actual["frames"]] if frames else []
    if frames!=projection:raise ValueError("Independent raw written frame mismatch")
    if addresses!=actual["tempo_addresses"]:raise ValueError("Independent raw tempo-address mismatch")
    return dict(status="pass",frames=len(frames),tempo_addresses=len(addresses),linked=sum(a["status"]=="linked" for a in addresses))
