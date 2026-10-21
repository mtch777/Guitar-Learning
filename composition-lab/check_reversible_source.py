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


def check_positions(capture,restored):
    """Direct source field checker; imports no position extractor or solver."""
    meta=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"))
    def numeric(obj,key):
        value=obj.get(key)
        return dict(present=key in obj,value=str(F(str(value))) if value is not None else None,number_type=type(value).__name__ if value is not None else None)
    settings=[];positions=[];regions={}
    for path in sorted(capture.glob("track-*.json"),key=lambda p:int(p.stem.split("-")[-1])):
        part=json.loads(path.read_text(encoding="utf-8-sig"));sid=f"settings:{meta['songId']}:{part['partId']}"
        settings.append(dict(id=sid,instrument_id=numeric(part,"instrumentId"),capo=numeric(part,"capo"),tuning=dict(present="tuning" in part,value=[str(F(str(x))) for x in part["tuning"]] if part.get("tuning") is not None else None)))
        for mi,m in enumerate(part.get("measures",[])):
            for vi,v in enumerate(m.get("voices",[])):
                regions[f"voice:{meta['songId']}:{part['partId']}:{mi+1}:{vi}"]=sid
                for bi,b in enumerate(v.get("beats",[])):
                    for ni,n in enumerate(b.get("notes",[])):
                        if n.get("rest"):continue
                        positions.append(dict(id=f"event:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}:{ni}",string=numeric(n,"string"),fret=numeric(n,"fret"),dead=dict(present="dead" in n,value=n.get("dead"))))
    differences=[]
    for kind,wanted in (("settings",settings),("positions",positions)):
        a={r["id"]:r for r in wanted};b={r["id"]:r for r in restored[kind]}
        if len(b)!=len(restored[kind]):raise AssertionError("Duplicate physical identity")
        differences.extend(dict(kind=kind,id=ident,expected=a.get(ident),actual=b.get(ident)) for ident in sorted(set(a)|set(b)) if a.get(ident)!=b.get(ident))
    if regions!=restored["region_settings"]:differences.append(dict(kind="region_settings_mismatch"))
    return dict(status="pass_declared_physical_fields" if not differences else "fail",settings=len(settings),positions=len(positions),differences=differences[:20])


def check_annotations(capture,restored):
    """Independent direct raw comparison of supported source observations."""
    meta=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"));markers=[];curves=[];unsupported=[]
    def value(v):return dict(type=type(v).__name__,value=str(F(str(v))) if type(v) in (int,float) else v)
    def visit(owner,kind,obj):
        fields={};excluded={"fret","string","dead","rest"} if kind=="note" else {"rest"} if kind=="rest_slot" else {"notes","duration","type","rest","graceNote"}
        curve_field="bend" if kind=="note" else "tremoloBar" if kind=="beat" else None
        for field,v in obj.items():
            if field in excluded:continue
            if field==curve_field and isinstance(v,dict) and isinstance(v.get("points"),list) and all(isinstance(p,dict) and all(type(x) in (int,float,bool,str,type(None)) for x in p.values()) for p in v["points"]) and all(type(x) in (int,float,bool,str,type(None)) for k,x in v.items() if k!="points"):
                ident=f"curve:{owner}:{field}"
                curves.append(dict(id=ident,owner=owner,kind=kind,field=field,header={k:value(x) for k,x in v.items() if k!="points"},points_present=True,points=[dict(id=f"{ident}:point:{i}",fields={k:value(x) for k,x in p.items()}) for i,p in enumerate(v["points"])]))
            elif type(v) in (int,float,bool,str,type(None)):fields[field]=value(v)
            else:unsupported.append(dict(owner=owner,kind=kind,field=field,source_type=type(v).__name__))
        if fields:markers.append(dict(id=owner,fields=fields))
    for path in sorted(capture.glob("track-*.json"),key=lambda p:int(p.stem.split("-")[-1])):
        part=json.loads(path.read_text(encoding="utf-8-sig"))
        for mi,m in enumerate(part.get("measures",[])):
            for vi,v in enumerate(m.get("voices",[])):
                for bi,b in enumerate(v.get("beats",[])):
                    visit(f"beat:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}","beat",b)
                    for ni,n in enumerate(b.get("notes",[])):
                        if n.get("rest"):visit(f"rest-slot:beat:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}:{ni}","rest_slot",n)
                        else:visit(f"event:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}:{ni}","note",n)
    differences=[]
    for kind,wanted in (("markers",markers),("curves",curves)):
        a={r["id"]:r for r in wanted};b={r["id"]:r for r in restored[kind]}
        if len(b)!=len(restored[kind]):raise AssertionError("Duplicate annotation identity")
        differences.extend(dict(kind=kind,id=ident,expected=a.get(ident),actual=b.get(ident)) for ident in sorted(set(a)|set(b)) if a.get(ident)!=b.get(ident))
    if Counter(json.dumps(x,sort_keys=True) for x in unsupported)!=Counter(json.dumps(x,sort_keys=True) for x in restored["unsupported"]):differences.append(dict(kind="unsupported_inventory_mismatch"))
    return dict(status="pass_declared_annotation_fields" if not differences else "fail",marker_owners=len(markers),scalar_fields=sum(len(r["fields"]) for r in markers),curves=len(curves),points=sum(len(c["points"]) for c in curves),unsupported_fields=len(unsupported),unsupported_by_field=dict(Counter(x["kind"]+"."+x["field"] for x in unsupported)),differences=differences[:20])


def raw_relation_context(capture):
    """Direct raw arithmetic and source membership; no producer imports."""
    events,_=source_expectation(capture);meta=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"));rows={};lanes={};true=set()
    for path in capture.glob("track-*.json"):
        part=json.loads(path.read_text(encoding="utf-8-sig"));tuning=part.get("tuning") or []
        for mi,m in enumerate(part.get("measures",[])):
            for vi,v in enumerate(m.get("voices",[])):
                for bi,b in enumerate(v.get("beats",[])):
                    for ni,n in enumerate(b.get("notes",[])):
                        if n.get("rest"):continue
                        ident=f"event:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}:{ni}"
                        string,fret=n.get("string"),n.get("fret");lane=(part["partId"],vi,string) if type(string) is int and string>=0 else None
                        nominal=F(str(tuning[string]))+F(str(part.get("capo") or 0))+F(str(fret)) if lane is not None and string<len(tuning) and type(fret) in (int,float) and part.get("instrumentId")!=1024 else None
                        row=dict(track=part["partId"],source_measure=mi,order=len(rows),id=ident,lane=lane,onset=F(events[ident]["onset_q"]),duration=F(events[ident]["duration_q"]),nominal=nominal,fret_valid=type(fret) in (int,float) and fret>=0,dead=n.get("dead") is True);rows[ident]=row
                        if n.get("tie") is True:true.add(ident)
                        if lane is not None and row["duration"]>0:lanes.setdefault(lane,{}).setdefault(row["onset"],[]).append(ident)
    return rows,lanes,true


def check_tie_relations(capture,links,unresolved):
    """Independent raw eligibility, position/time and unresolved-reason checks."""
    rows,lanes,true=raw_relation_context(capture)
    errors=[];accounted=[]
    for link in links:
        a=rows.get(link["origin"]);b=rows.get(link["destination"]);accounted.append(link["destination"])
        valid=bool(a and b and b["id"] in true and a["lane"] is not None and a["lane"]==b["lane"] and a["duration"]>0 and b["duration"]>0 and a["onset"]+a["duration"]==b["onset"] and a["nominal"] is not None and a["nominal"]==b["nominal"] and a["fret_valid"] and b["fret_valid"] and a["dead"]==b["dead"])
        if valid:
            groups=lanes[b["lane"]];earlier=[q for q in groups if q<b["onset"]]
            prior=groups[max(earlier)] if earlier else []
            valid=len(groups[b["onset"]])==1 and prior==[a["id"]] and link["kind"]==("written_dead_tie" if b["dead"] else "written_pitched_tie")
        if not valid:errors.append(dict(kind="invalid_link",link=link))
    # Independent per-destination eligibility query, including unresolved reasons.
    expected_links={};expected_unresolved={}
    for ident in true:
        b=rows[ident];reason=None;a=None
        if b["duration"]<=0:reason="zero_metric_duration"
        elif b["lane"] is None:reason="invalid_string_lane"
        else:
            groups=lanes[b["lane"]];prior_clocks=[q for q in groups if q<b["onset"]]
            candidates=groups[max(prior_clocks)] if prior_clocks else []
            if len(groups[b["onset"]])!=1:reason="ambiguous_lane_onset"
            elif len(candidates)!=1:reason="no_predecessor"
            else:
                a=rows[candidates[0]]
                if a["onset"]+a["duration"]!=b["onset"]:reason="noncontiguous"
                elif a["nominal"] is None or b["nominal"] is None:reason="unmapped_position"
                elif not a["fret_valid"] or not b["fret_valid"]:reason="invalid_written_position"
                elif a["dead"]!=b["dead"]:reason="dead_transition"
                elif a["nominal"]!=b["nominal"]:reason="different_written_position"
        if reason:expected_unresolved[ident]=reason
        else:expected_links[ident]=dict(origin=a["id"],destination=ident,kind="written_dead_tie" if b["dead"] else "written_pitched_tie")
    if {r["destination"]:r for r in links}!=expected_links:errors.append(dict(kind="eligible_link_set_mismatch"))
    if {r["destination"]:r["reason"] for r in unresolved}!=expected_unresolved:errors.append(dict(kind="unresolved_reason_mismatch"))
    accounted.extend(r["destination"] for r in unresolved)
    if len(accounted)!=len(set(accounted)) or set(accounted)!=true:errors.append(dict(kind="true_flag_ownership_mismatch"))
    return dict(status="pass_declared_written_tie_relations" if not errors else "fail",true_flags=len(true),resolved=len(links),unresolved=len(unresolved),differences=errors[:20])


def check_voicing_relations(capture,model):
    rows,_,true=raw_relation_context(capture);populations={};expected_excluded={};expected_groups={}
    for ident,r in rows.items():
        if ident in true:expected_excluded[ident]="explicit_tie_destination"
        elif r["duration"]<=0:expected_excluded[ident]="zero_metric_duration"
        else:populations.setdefault((r["track"],r["source_measure"],r["onset"]),[]).append(r)
    for population in populations.values():
        invalid={r["id"]:("dead_note" if r["dead"] else "unknown_written_position" if r["nominal"] is None or r["lane"] is None else "invalid_written_position" if not r["fret_valid"] else None) for r in population}
        if any(invalid.values()):
            expected_excluded.update({r["id"]:invalid[r["id"]] or "incomplete_candidate" for r in population});continue
        if len({r["lane"][2] for r in population})!=len(population):
            expected_excluded.update({r["id"]:"ambiguous_string_at_onset" for r in population});continue
        if len(population)<2:
            expected_excluded.update({r["id"]:"no_other_eligible_co_onset" for r in population});continue
        ordered=sorted(population,key=lambda r:(r["nominal"],r["order"]))
        expected_groups[tuple(r["id"] for r in ordered)]=[r["nominal"]-ordered[0]["nominal"] for r in ordered]
    actual_groups={tuple(o["members"]):list(map(F,model["definitions"][o["definition"]]["intervals"])) for o in model["occurrences"]}
    errors=[]
    if len(actual_groups)!=len(model["occurrences"]) or actual_groups!=expected_groups:errors.append(dict(kind="voicing_population_or_interval_mismatch"))
    actual_excluded={r["id"]:r["reason"] for r in model["excluded"]}
    if len(actual_excluded)!=len(model["excluded"]) or actual_excluded!=expected_excluded:errors.append(dict(kind="voicing_exclusion_mismatch"))
    return dict(status="pass_declared_written_coonsets" if not errors else "fail",source_note_population=len(rows),candidate_populations=len(populations),groups=len(expected_groups),removed_numeric_coordinates=sum(len(m)-1 for m in expected_groups),excluded=len(expected_excluded),differences=errors)
