#!/usr/bin/env python3
"""Configurable Songsterr song selection, track selection and GP5 download."""
import argparse,json,re,subprocess,sys
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0,"/tmp/songsterr-dl")
from songsterr_dl.client import SongsterrClient
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--artist",default="")
 p.add_argument("--song",default="")
 p.add_argument("--song-id",default="")
 p.add_argument("--tracks",default="all")
 p.add_argument("--output",default="composition-lab/songsterr_automation/downloads")
 p.add_argument("--existing",choices=["skip","overwrite"],default="skip")
 p.add_argument("--max-songs",type=int,default=10)
 p.add_argument("--report",default="songsterr-run/selection.json")
 a=p.parse_args()
 if a.max_songs<1 or a.max_songs>100: p.error("max-songs must be 1..100")
 root=Path(a.output)
 allowed=Path("composition-lab/songsterr_automation/downloads")
 if root!=allowed and allowed not in root.parents:p.error("output must be within composition-lab/songsterr_automation/downloads")
 if ".." in root.parts or root.is_absolute():p.error("invalid output")
 report={"args":vars(a),"songs":[],"errors":[]}
 with SongsterrClient() as client:
  if a.song_id:
   match=re.search(r"(?:-s|^)(\d+)(?:t\d+)?(?:$|[/?#])",a.song_id)
   sid=int(match.group(1)) if match else int(a.song_id)
   metas=[client.meta(sid)]
  else:
   if not a.artist and not a.song:p.error("provide artist, song or song-id")
   query=" ".join(x for x in (a.artist,a.song) if x and x.lower()!="all")
   found=client.search(query,size=100)
   ids=[]
   for item in found:
    if a.artist and a.artist.lower() not in str(item.get("artist","")).lower():continue
    if a.song and a.song.lower()!="all" and a.song.lower() not in str(item.get("title","")).lower():continue
    sid=item.get("songId")
    if sid and sid not in ids:ids.append(sid)
   metas=[client.meta(sid) for sid in ids[:a.max_songs]]
  if not metas:report["errors"].append("No matching songs")
  for meta in metas:
   sid=meta["songId"]
   available=meta.get("tracks",[])
   selector=a.tracks.strip().lower()
   if selector=="all":indices=list(range(len(available)))
   elif selector in ("guitar","bass","drums","vocals"):
    tokens={"guitar":("guitar",),"bass":("bass",),"drums":("drum",),"vocals":("vocal",)}[selector]
    indices=[i for i,t in enumerate(available) if any(v in (str(t.get("instrument",""))+" "+str(t.get("name",""))+" "+str(t.get("hash",""))).lower() for v in tokens)]
   else:
    try:indices=[int(v.strip()) for v in selector.split(",")]
    except ValueError:p.error("tracks must be all/guitar/bass/drums/vocals or comma-separated indices")
   indices=list(dict.fromkeys(indices))
   if not indices or any(i<0 or i>=len(available) for i in indices):
    report["errors"].append(f"Song {sid}: no valid tracks selected");continue
   folder=root/str(sid)
   folder.mkdir(parents=True,exist_ok=True)
   item={"song_id":sid,"artist":meta.get("artist"),"title":meta.get("title"),"revision_id":meta.get("revisionId"),"selected_tracks":indices,"folder":str(folder)}
   gpfiles=list(folder.glob("*.gp5"))
   if gpfiles and a.existing=="skip":
    item.update(status="skipped",gp5=[str(x) for x in gpfiles])
   else:
    cmd=["songsterr-dl",str(sid),"--revision",str(meta["revisionId"]),"--tracks",",".join(map(str,indices)),"-f","gp5","-o",str(folder)]
    if a.existing=="overwrite":cmd.append("--overwrite")
    res=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
    item.update(status="ok" if res.returncode==0 else "error",returncode=res.returncode,output=(res.stdout+res.stderr)[-5000:],gp5=[str(x) for x in folder.glob("*.gp5")])
    if res.returncode:report["errors"].append(f"Song {sid}: converter returned {res.returncode}")
   report["songs"].append(item)
 destination=Path(a.report);destination.parent.mkdir(parents=True,exist_ok=True)
 destination.write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2))
 return 1 if report["errors"] else 0
if __name__=="__main__":raise SystemExit(main())
