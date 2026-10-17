#!/usr/bin/env python3
"""Verify converted Guitar Pro notes/measures and emit a machine-readable report."""
import json,glob,sys
from pathlib import Path
import guitarpro
files=list(Path(sys.argv[1]).rglob("*.gp5"))
out={"gp5_files":[],"success":False}
for f in files:
    s=guitarpro.parse(str(f))
    tracks=[]
    for t in s.tracks:
        measure_count=len(t.measures)
        notes=sum(len(b.notes) for m in t.measures for v in m.voices for b in v.beats)
        beats=sum(len(v.beats) for m in t.measures for v in m.voices)
        tracks.append({"name":t.name,"measures":measure_count,"beats":beats,"notes":notes,"strings":len(t.strings)})
    out["gp5_files"].append({"path":str(f),"bytes":f.stat().st_size,"tracks":tracks})
out["success"]=bool(files) and any(t["notes"]>0 and t["measures"]>0 for x in out["gp5_files"] for t in x["tracks"])
p=Path("composition-lab/songsterr_automation/results/e2e_conversion_report.json")
p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
if not out["success"]:sys.exit(1)
