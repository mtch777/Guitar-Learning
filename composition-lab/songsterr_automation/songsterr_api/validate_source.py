#!/usr/bin/env python3
"""Compare live Songsterr notation against exported GP5 independently of the converter."""
import sys,json,glob,os
from pathlib import Path
import guitarpro
sys.path.insert(0,"/tmp/songsterr-dl")
from songsterr_dl.client import SongsterrClient
from tests.comparison import compare_track
out=Path("composition-lab/songsterr_automation/results/source_fidelity_report.json")
out.parent.mkdir(parents=True,exist_ok=True)
report={"song_id":153,"track_index":2,"success":False}
try:
    with SongsterrClient() as client:
        meta=client.meta(153)
        report["revision_id"]=meta["revisionId"]
        raw=client.track(153,meta["revisionId"],meta["image"],2)
    report["source_top_keys"]=sorted(raw.keys())
    report["source_measures"]=len(raw.get("measures",[]))
    report["source_notes"]=sum(len([n for n in b.get("notes",[]) if not n.get("rest")]) for m in raw.get("measures",[]) for v in m.get("voices",[]) for b in v.get("beats",[]) if not b.get("graceNote"))
    candidates=list(Path("songsterr-e2e").glob("*.gp5"))
    if len(candidates)!=1:raise RuntimeError(f"Expected one GP5 file, found {len(candidates)}")
    written=guitarpro.parse(str(candidates[0]))
    problems=compare_track(raw,written.tracks[0],False)
    report["gp5_notes"]=sum(len(b.notes) for m in written.tracks[0].measures for v in m.voices for b in v.beats)
    report["gp5_measures"]=len(written.tracks[0].measures)
    report["difference_count"]=len(problems)
    report["differences"]=problems[:100]
    report["truncated_differences"]=len(problems)>100
    report["success"]=not problems and report["source_measures"]==report["gp5_measures"]
except Exception as error:
    report["error"]=repr(error)
out.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
sys.exit(0 if report["success"] else 1)
