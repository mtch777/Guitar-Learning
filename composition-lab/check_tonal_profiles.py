"""Independent tonal-profile oracle against primary music21 implementation.

Private source is read by parent QA only, never the shared musical core/inverse.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
from check_reversible_source import source_expectation


def inventory_issues(raw, given):
    expected={"song-pooled"}|{f"part:{i.split(':')[2]}" for i in raw}
    issues=[]
    if len(given)!=len(expected) or {s["id"] for s in given}!=expected:
        issues.append("Complete raw scope population missing/duplicated")
    wanted={(family,quality,tonic) for family in ("KrumhanslSchmuckler","TemperleyKostkaPayne") for quality in ("major","minor") for tonic in range(12)}
    for scope in given:
        candidates=scope["candidates"]
        keys=[(c["family"],c["quality"],c["tonic_pc"]) for c in candidates]
        if len(keys)!=48 or set(keys)!=wanted or any(type(c["tonic_pc"]) is not int or c["id"]!=f"{scope['id']}/{c['family']}/{c['tonic_pc']}/{c['quality']}" or (c["score"] is not None and (type(c["score"]) not in (float,int) or not math.isfinite(c["score"]))) for c in candidates):
            issues.append("Complete typed candidate population missing/duplicated")
    return issues


def exposure_issues(used, excluded, scope):
    if sorted(used)!=sorted(scope["used_member_refs"]) or any(sorted(excluded[k])!=sorted(scope["excluded_member_refs"][k]) for k in excluded):
        return ["Exposure ownership/exclusion multiplicity differs"]
    return []


def check(capture, upper):
    import music21
    from music21 import note, stream
    from music21.analysis import discrete
    raw,_=source_expectation(capture)
    warnings=upper["source_quality"]
    blocked={w["bar"] for category in ("layout_warnings","timing_warnings") for w in warnings[category]}
    issues=inventory_issues(raw,upper["tonal_evidence"]["scopes"]); comparisons=0; scopes=[]
    expected_scopes={"song-pooled"}|{f"part:{i.split(':')[2]}" for i in raw}
    given=upper["tonal_evidence"]["scopes"]
    if len(given)!=len(expected_scopes) or {s["id"] for s in given}!=expected_scopes:
        issues.append("Complete raw scope population missing/duplicated")
    expected_candidates={(family,quality,tonic) for family in ("KrumhanslSchmuckler","TemperleyKostkaPayne") for quality in ("major","minor") for tonic in range(12)}
    for scope in upper["tonal_evidence"]["scopes"]:
        candidate_keys=[(c["family"],c["quality"],c["tonic_pc"]) for c in scope["candidates"]]
        if len(candidate_keys)!=48 or set(candidate_keys)!=expected_candidates or any(type(c["tonic_pc"]) is not int or c["id"]!=f"{scope['id']}/{c['family']}/{c['tonic_pc']}/{c['quality']}" or (c["score"] is not None and (type(c["score"]) not in (float,int) or not math.isfinite(c["score"]))) for c in scope["candidates"]):
            issues.append("Complete typed candidate population missing/duplicated")
            continue
        part=None if scope["id"]=="song-pooled" else int(scope["id"].split(":")[1])
        eligible={i:r for i,r in raw.items() if part is None or int(i.split(":")[2])==part}
        hist=[F(0) for _ in range(12)]; used=[]; excluded={k:[] for k in ("unknown_pitch","noninteger_pitch","zero_duration","source_timing_uncertain")}
        score=stream.Stream()
        for ident,row in eligible.items():
            p=row["pitch"]; duration=F(row["duration_q"]); reason=None
            if p is None: reason="unknown_pitch"
            elif F(p).denominator!=1: reason="noninteger_pitch"
            elif duration==0: reason="zero_duration"
            elif int(ident.split(":")[3]) in blocked: reason="source_timing_uncertain"
            if reason: excluded[reason].append(ident); continue
            used.append(ident); hist[int(F(p)%12)]+=duration
            n=note.Note(int(F(p))); n.quarterLength=duration; score.append(n)
        if list(map(str,hist))!=scope["pitch_class_duration_q"]: issues.append("Raw duration exposure differs")
        issues.extend(exposure_issues(used,excluded,scope))
        counts={"unknown_pitch_members":len(excluded["unknown_pitch"]),"noninteger_pitch_members":len(excluded["noninteger_pitch"]),"zero_duration_known_members":len(excluded["zero_duration"]),"timing_excluded_members":len(excluded["source_timing_uncertain"]),"known_positive_duration_members":len(used)}
        if any(type(scope[k]) is not int or scope[k]!=v for k,v in counts.items()) or scope["total_known_duration_q"]!=str(sum(hist)):
            issues.append("Exposure count/duration denominator differs")
        for family in ("KrumhanslSchmuckler","TemperleyKostkaPayne"):
            method=getattr(discrete,family)(); distribution=method._getPitchClassDistribution(score)
            if distribution is None: distribution=[0]*12
            if any(abs(float(a)-float(b))>1e-9 for a,b in zip(hist,distribution)): issues.append("music21 distribution differs")
            for quality in ("major","minor"):
                expected=method._getDifference([0]*12,distribution,quality)
                for tonic in range(12):
                    actual=next(c["score"] for c in scope["candidates"] if c["family"]==family and c["quality"]==quality and c["tonic_pc"]==tonic)
                    undefined=len(set(hist))==1
                    if (undefined and actual is not None) or (not undefined and (actual is None or abs(actual-expected[tonic])>1e-12)): issues.append("Published profile score differs")
                    comparisons+=1
        scopes.append(dict(id=scope["id"],used=len(used),excluded={k:len(v) for k,v in excluded.items()}))
    return dict(status="PASS" if not issues else "FAIL", music21_version=music21.__version__, music21_source_sha256=hashlib.sha256(Path(discrete.__file__).read_bytes()).hexdigest(), compared_scores=comparisons,
                issues=issues[:20],scopes=scopes,degenerate_policy="Pearson undefined => None; music21 zero fallback intentionally not treated as evidence",
                timing_quarantine_provenance="Uses accepted source_quality warnings; this oracle does not independently validate warning generation", claim="Agreement with published distributional method, NOT key accuracy")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("capture",type=Path);p.add_argument("upper",type=Path);p.add_argument("output",type=Path);a=p.parse_args()
    if a.output.exists():p.error("Retain prior result; choose fresh path")
    result=check(a.capture,json.loads(a.upper.read_text()))
    result["upper_sha256"]=hashlib.sha256(a.upper.read_bytes()).hexdigest()
    result["oracle_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result["status"]=="PASS" else 1)
