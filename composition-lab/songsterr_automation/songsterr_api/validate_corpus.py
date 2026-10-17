#!/usr/bin/env python3
"""Network corpus audit: Songsterr source -> GP5 independent comparison."""
import json,sys,subprocess,time
from pathlib import Path
import guitarpro
sys.path.insert(0,"/tmp/songsterr-dl")
from songsterr_dl.client import SongsterrClient
from tests.comparison import compare_track
CASES=[(153,[2,7,10],"acoustic+bass+drums"),(271,[3,6],"bends+slides+lead"),(378962,[0],"technical guitar"),(10770,[0],"additional repertoire"),(63101,[0],"additional repertoire")]
root=Path("songsterr-corpus");root.mkdir(exist_ok=True)
results=[]
with SongsterrClient() as client:
 for sid,indices,label in CASES:
  entry={"song_id":sid,"category":label,"tracks":[]}
  try:
   meta=client.meta(sid);entry.update(title=meta.get("title"),artist=meta.get("artist"),revision_id=meta["revisionId"])
   indices=[i for i in indices if i<len(meta.get("tracks",[]))]
   if not indices:raise ValueError("No selected tracks in metadata")
   for idx in indices:
    part={"track_index":idx,"name":meta["tracks"][idx].get("name")}
    try:
     raw=client.track(sid,meta["revisionId"],meta["image"],idx)
     dest=root/f"{sid}_{idx}";dest.mkdir(exist_ok=True)
     cmd=["songsterr-dl",str(sid),"--revision",str(meta["revisionId"]),"--tracks",str(idx),"-f","gp5","-o",str(dest),"--overwrite"]
     run=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
     files=list(dest.glob("*.gp5"))
     part["converter_exit"]=run.returncode
     part["converter_log_tail"]=(run.stdout+run.stderr)[-1200:]
     if run.returncode or len(files)!=1:raise RuntimeError(f"Conversion failed: {run.returncode}, GP5 files={len(files)}")
     gp=guitarpro.parse(str(files[0]));issues=compare_track(raw,gp.tracks[0],raw.get("instrumentId")==1024)
     part.update(source_measures=len(raw.get("measures",[])),gp5_measures=len(gp.tracks[0].measures),source_notes=sum(len([n for n in b.get("notes",[]) if not n.get("rest")]) for m in raw.get("measures",[]) for v in m.get("voices",[]) for b in v.get("beats",[]) if not b.get("graceNote")),gp5_notes=sum(len(b.notes) for m in gp.tracks[0].measures for v in m.voices for b in v.beats),differences=len(issues),first_differences=issues[:20],gp5_path=str(files[0]))
     part["passed"]=not issues and part["source_measures"]==part["gp5_measures"]
    except Exception as exc:part.update(passed=False,error=repr(exc))
    entry["tracks"].append(part);print("TRACK",sid,idx,part["passed"],part.get("differences"),part.get("error"),flush=True)
    time.sleep(1)
  except Exception as exc:entry["error"]=repr(exc)
  results.append(entry)
out={"cases":results,"tracks_tested":sum(len(x["tracks"]) for x in results),"tracks_passed":sum(t["passed"] for x in results for t in x["tracks"]),"success":all(x["tracks"] and all(t["passed"] for t in x["tracks"]) for x in results)}
p=Path("composition-lab/songsterr_automation/results/source_corpus_report.json");p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+"\n")
print("SUMMARY",json.dumps({k:v for k,v in out.items() if k!="cases"}))
sys.exit(0 if out["success"] else 1)
