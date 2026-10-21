"""Independent raw-JSON arithmetic checker for the declared pitch/metric fields.

Does not import the extractor, solver, inverse or legacy score readers.
"""
from collections import Counter
from fractions import Fraction as F
import json


def source_expectation(capture,include_topology=False):
    meta=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"))
    parts=[json.loads(p.read_text(encoding="utf-8-sig")) for p in sorted(capture.glob("track-*.json"),key=lambda p:int(p.stem.split("-")[-1]))]
    def sentinel(m,v):
        beats=v.get("beats",[])
        if len(beats)!=1:return False
        b=beats[0];notes=b.get("notes",[])
        return bool(m.get("rest") and v.get("rest") and b.get("rest") is True and b.get("type")==1 and b.get("duration")==[1,1] and notes and all(n.get("rest") is True for n in notes) and not any(b.get(k) for k in ("graceNote","dots","tuplet","tupletStart","tupletStop")))
    signature=(4,4);start=F(0);layout=[]
    for mi in range(max((len(p.get("measures",[])) for p in parts),default=0)):
        measures=[p["measures"][mi] for p in parts if mi<len(p.get("measures",[]))]
        signatures={tuple(m["signature"]) for m in measures if m.get("signature")}
        if len(signatures)>1:raise ValueError("Independent source checker: conflicting meter")
        if signatures:signature=next(iter(signatures))
        span=F(4*signature[0],signature[1])
        if mi==0 and any(p.get("anacrusis") for p in parts):
            filled=[sum((F(*b["duration"])*4 for b in v.get("beats",[]) if not b.get("graceNote") and b.get("duration")),F(0)) for m in measures for v in m.get("voices",[]) if not sentinel(m,v)]
            pickup=max(filled,default=F(0))
            if 0<pickup<span:span=pickup
        layout.append((start,span));start+=span
    expected={};unknown=Counter();beats=0;topology=dict(measures=[],voices=[],beats=[],notes=[])
    for part in parts:
        tuning=part.get("tuning") or []
        for mi,m in enumerate(part.get("measures",[])):
            mid=f"measure:{meta['songId']}:{part['partId']}:{mi+1}";vids=[]
            topology["measures"].append(dict(id=mid,rest_flag=m.get("rest"),voices=vids))
            for vi,v in enumerate(m.get("voices",[])):
                cursor=F(0);vid=f"voice:{meta['songId']}:{part['partId']}:{mi+1}:{vi}";vids.append(vid);bids=[]
                topology["voices"].append(dict(id=vid,rest_flag=v.get("rest"),beats=bids))
                for bi,b in enumerate(v.get("beats",[])):
                    beats+=1
                    if not b.get("duration"):raise ValueError("Independent checker: missing duration")
                    written=layout[mi][1] if sentinel(m,v) else F(*b["duration"])*4
                    if written<=0:raise ValueError("Independent checker: nonpositive duration")
                    bid=f"beat:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}";bids.append(bid)
                    target=next((f"beat:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{j}" for j in range(bi+1,len(v.get("beats",[]))) if not v["beats"][j].get("graceNote")),None) if b.get("graceNote") else None
                    topology["beats"].append(dict(id=bid,onset_q=str(layout[mi][0]+cursor),duration_q="0" if b.get("graceNote") else str(written),written_duration_q=str(F(*b["duration"])*4),symbols=dict(rest_flag=b.get("rest"),grace_kind=b.get("graceNote"),notation_type=b.get("type"),whole_measure_rest=sentinel(m,v),slots=["rest_placeholder" if n.get("rest") else "note" for n in b.get("notes",[])]),next_regular_beat_ref=target))
                    for ni,n in enumerate(b.get("notes",[])):
                        if n.get("rest"):continue
                        string,fret=n.get("string"),n.get("fret");pitch=None
                        if n.get("dead"):unknown["dead_written_pitch_not_claimed"]+=1
                        elif type(string) is not int or not 0<=string<len(tuning):unknown["no_usable_pitched_string_mapping_including_percussion"]+=1
                        elif type(fret) not in {int,float}:unknown["no_numeric_fret"]+=1
                        else:pitch=str(F(str(tuning[string]))+F(str(fret))+F(str(part.get("capo") or 0)))
                        ident=f"event:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}:{ni}"
                        topology["notes"].append(dict(id=ident,beat_ref=bid,slot=ni,base_pitch=pitch))
                        expected[ident]=dict(id=ident,pitch=pitch,onset_q=str(layout[mi][0]+cursor),duration_q="0" if b.get("graceNote") else str(written))
                    if not b.get("graceNote"):cursor+=written
    if include_topology:return topology
    return expected,dict(beats=beats,unknown_pitch_reasons=dict(unknown))


def check(capture,events):
    expected,coverage=source_expectation(capture);actual={e["id"]:e for e in events}
    if len(actual)!=len(events):raise AssertionError("Duplicate reconstructed identity")
    differences=[dict(id=ident,expected=expected.get(ident),actual=actual.get(ident)) for ident in sorted(set(expected)|set(actual)) if expected.get(ident)!=actual.get(ident)]
    return dict(status="pass_declared_raw_source_fields" if not differences else "fail",expected_occurrences=len(expected),actual_occurrences=len(actual),differences=differences[:20],**coverage)


def check_topology(capture,restored):
    expected=source_expectation(capture,include_topology=True);differences=[];counts={}
    for kind,wanted in expected.items():
        a={r["id"]:r for r in wanted};b={r["id"]:r for r in restored[kind]}
        if len(b)!=len(restored[kind]):raise AssertionError("Duplicate topology identity")
        counts[kind]=len(a)
        differences.extend(dict(kind=kind,id=ident,expected=a.get(ident),actual=b.get(ident)) for ident in sorted(set(a)|set(b)) if a.get(ident)!=b.get(ident))
    return dict(status="pass_declared_topology" if not differences else "fail",counts=counts,differences=differences[:20])
