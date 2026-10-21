"""Continuous fresh-capture/stripped-reverse gates for the bounded shared operator."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from reversible_relationships import encode
from check_reversible_source import check


def read(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def extract(capture):
    # Stage1: only captured Tier0 documents, through existing pure source parsers.
    api=Path(__file__).parent/"songsterr_automation/songsterr_api"
    sys.path.insert(0,str(api))
    from source_semantics import layout
    from analyze_relationships import occurrences
    meta=read(capture/"metadata.json")
    files=sorted(capture.glob("track-*.json"),key=lambda p:int(p.stem.split("-")[-1]))
    parts=[read(p) for p in files];headers,layout_warnings=layout(parts)
    if len(parts)!=len(meta["tracks"]):raise ValueError("Missing captured tracks")
    result=[];warnings=[];expected=0
    for file,part in zip(files,parts):
        pid=int(file.stem.split("-")[-1])
        if part.get("partId")!=pid:raise ValueError("Part identity differs")
        for field,value in (("songId",meta["songId"]),("revisionId",meta["revisionId"])):
            if field in part and part[field]!=value:raise ValueError("Source revision identity differs")
        rows,graces,_,issues=occurrences(part,headers);warnings.extend(dict(part_id=pid,**w) for w in issues)
        expected+=sum(not n.get("rest") for m in part.get("measures",[]) for v in m.get("voices",[]) for b in v.get("beats",[]) for n in b.get("notes",[]))
        grace_ids={r["occurrence"] for r in graces}
        for row in rows+graces:
            result.append(dict(id=f"event:{meta['songId']}:{row['occurrence']}",part_id=pid,bar=row["bar"],voice=row["voice"],beat=row["beat"],note=row["note"],pitch=str(F(str(row["midi"]))) if row["midi"] is not None else None,onset_q=row["onset_q"],duration_q="0" if row["occurrence"] in grace_ids else row["duration_q"]))
    if len(result)!=expected:raise ValueError(f"Incomplete source extraction: {len(result)}/{expected}")
    if len({e["id"] for e in result})!=len(result):raise ValueError("Duplicate event identity")
    return dict(tier=1,schema="normalized-written-fields/1",events=result,source_coverage=dict(expected=expected,actual=len(result),tracks=len(parts),layout_warnings=layout_warnings,timing_warnings=warnings),scope="base_pitch_and_metric_onset_duration_only")


def _run(capture,output,topology=False,positions=False,annotations=False,ties=False):
    if output.exists():raise ValueError("Fresh private QA output required")
    output.mkdir(parents=True)
    facts=extract(capture)
    (output/"tier1-checker-only.json").write_text(json.dumps(facts,indent=2),encoding="utf-8")
    if ties:
        annotations=True;positions=True
        from reversible_annotations import extract as extract_annotations
        from reversible_ties import encode as encode_ties
        annotation_facts=extract_annotations(capture)
        (output/"annotations-checker-only.json").write_text(json.dumps(annotation_facts,indent=2),encoding="utf-8")
        upper=encode_ties(annotation_facts)
    elif annotations:
        positions=True
        from reversible_annotations import extract as extract_annotations,encode as encode_annotations
        annotation_facts=extract_annotations(capture)
        (output/"annotations-checker-only.json").write_text(json.dumps(annotation_facts,indent=2),encoding="utf-8")
        upper=encode_annotations(annotation_facts)
    elif positions:
        from reversible_positions import extract as extract_positions,encode as encode_positions
        position_facts=extract_positions(capture)
        (output/"positions-checker-only.json").write_text(json.dumps(position_facts,indent=2),encoding="utf-8")
        upper=encode_positions(position_facts)
    elif topology:
        from reversible_topology import extract as extract_topology,encode as encode_topology
        topology_facts=extract_topology(capture)
        (output/"topology-checker-only.json").write_text(json.dumps(topology_facts,indent=2),encoding="utf-8")
        upper=encode_topology(topology_facts)
    else:upper=encode(facts)
    isolated=output/"isolated";isolated.mkdir()
    for filename in ("reversible_relationships.py","reverse_tier_worker.py","reversible_topology.py","reversible_positions.py","reversible_annotations.py","reversible_ties.py"):shutil.copyfile(Path(__file__).parent/filename,isolated/filename)
    (isolated/"tier2-only.json").write_text(json.dumps(upper,indent=2),encoding="utf-8")
    # These copied files are the only task inputs available to the audited worker.
    command=[sys.executable,"-I","-S",str((isolated/"reverse_tier_worker.py").resolve()),str((isolated/"tier2-only.json").resolve()),str((isolated/"reconstructed.json").resolve()),str((isolated/"read-audit.json").resolve())]
    completed=subprocess.run(command,cwd=isolated,capture_output=True,text=True)
    (output/"reverse-process.json").write_text(json.dumps(dict(command=command,returncode=completed.returncode,stdout=completed.stdout,stderr=completed.stderr),indent=2),encoding="utf-8")
    if completed.returncode:raise RuntimeError("Isolated reverse failed: "+completed.stderr[-1000:])
    restored=read(isolated/"reconstructed.json")["events"]
    expected=sorted([{k:e[k] for k in ("id","pitch","onset_q","duration_q")} for e in facts["events"]],key=lambda e:e["id"])
    mismatches=[dict(expected=a,actual=b) for a,b in zip(expected,restored) if a!=b]
    if len(restored)!=len(expected):mismatches.append(dict(counts=[len(expected),len(restored)]))
    annotation_upper=upper["lower"] if ties else upper
    physical_upper=annotation_upper["physical"] if annotations else upper
    if positions:abstraction=dict(beat_patterns=physical_upper["topology"]["beat_patterns"]["sharing"],position_patterns=physical_upper["position_patterns"]["sharing"],physical_coverage=physical_upper["coverage"])
    elif topology:abstraction={k:upper[k]["sharing"] for k in ("beat_patterns","pitch_patterns")}
    else:abstraction=upper["abstraction"]
    if annotations:abstraction.update({k:annotation_upper[k]["sharing"] for k in ("markers","curve_headers","curve_points")})
    if ties:abstraction["tie_relations"]=dict(resolved=len(upper["links"]),removed_numeric_coordinates=len(upper["links"]),unresolved=len(upper["unresolved"]),unresolved_reasons=dict(Counter(r["reason"] for r in upper["unresolved"])))
    report=dict(status="pass_declared_scope" if not mismatches else "fail",scope=upper.get("scope","tie_constrained_normalized_source_song" if ties else "normalized_topology_positions_and_source_annotations" if annotations else "normalized_topology_and_written_position_settings" if positions else "normalized_beat_voice_rest_grace_topology_and_base_pitch"),source_coverage=facts["source_coverage"],events=len(expected),known_pitch_events=sum(e["pitch"] is not None for e in expected),unknown_pitch_events=sum(e["pitch"] is None for e in expected),mismatches=mismatches[:20],abstraction=abstraction,source_files=[dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(capture.glob("*.json"))],whole_song_GP_inverse="NOT_IMPLEMENTED",unsupported=["complete_source_fields","resolved_technique_execution","full_GP_inverse","musical_style_controls"]+([] if positions else ["physical_fingering"]))
    if topology or positions:
        from check_reversible_source import check_topology
        result=read(isolated/"reconstructed.json")["topology"]
        report["independent_topology_check"]=check_topology(capture,result)
        if report["independent_topology_check"]["status"]=="fail":report["status"]="fail"
    if positions:
        from check_reversible_source import check_positions
        report["independent_position_check"]=check_positions(capture,read(isolated/"reconstructed.json")["physical"])
        if report["independent_position_check"]["status"]=="fail":report["status"]="fail"
    if annotations:
        from check_reversible_source import check_annotations
        report["independent_annotation_check"]=check_annotations(capture,read(isolated/"reconstructed.json")["annotations"])
        if report["independent_annotation_check"]["status"]=="fail":report["status"]="fail"
    if ties:
        from check_reversible_source import check_tie_relations
        report["independent_tie_check"]=check_tie_relations(capture,upper["links"],upper["unresolved"])
        if report["independent_tie_check"]["status"]=="fail":report["status"]="fail"
    report["independent_raw_source_check"]=check(capture,restored)
    if report["independent_raw_source_check"]["status"]=="fail":report["status"]="fail"
    (output/"qa.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report


def run(capture,output,topology=False,positions=False,annotations=False,ties=False):
    if output.exists():raise ValueError("Fresh private QA output required")
    try:return _run(capture,output,topology,positions,annotations,ties)
    except Exception as error:
        if output.exists():
            (output/"failure.json").write_text(json.dumps(dict(status="failed_preserved_selection",error_type=type(error).__name__,message=str(error),capture=str(capture),mode="ties" if ties else "annotations" if annotations else "positions" if positions else "topology" if topology else "pitch_time"),indent=2),encoding="utf-8")
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("capture",type=Path);p.add_argument("output",type=Path);p.add_argument("--topology",action="store_true");p.add_argument("--positions",action="store_true");p.add_argument("--annotations",action="store_true");p.add_argument("--ties",action="store_true");a=p.parse_args()
    if "local-artifacts" not in a.output.resolve().parts:p.error("Private output required")
    result=run(a.capture.resolve(),a.output.resolve(),a.topology,a.positions,a.annotations,a.ties);print(json.dumps(result))
    if result["status"]!="pass_declared_scope":raise SystemExit(1)


if __name__=="__main__":main()
