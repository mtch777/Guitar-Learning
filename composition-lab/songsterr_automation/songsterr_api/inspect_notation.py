#!/usr/bin/env python3
"""Read-only inspection of Songsterr revisions and track notation structure."""
import json, urllib.request, urllib.error, time, collections
from pathlib import Path
OUT=Path("songsterr-diagnostics/notation_inventory.json")
HEADERS={"User-Agent":"CompositionLab-Songsterr-Endpoint-SmokeTest/1.0","Accept":"application/json"}
def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=25) as r:
            raw=r.read(8_000_000)
            return {"status":r.status,"content_type":r.headers.get("Content-Type"),"data":json.loads(raw)}
    except urllib.error.HTTPError as e:
        return {"status":e.code,"error":str(e),"sample":e.read(200).decode("utf-8","replace")}
    except Exception as e: return {"error":repr(e)}
def structure(x,depth=0):
    if depth>5:return type(x).__name__
    if isinstance(x,dict):return {k:structure(v,depth+1) for k,v in x.items()}
    if isinstance(x,list):return {"length":len(x),"first":structure(x[0],depth+1) if x else None}
    return type(x).__name__
def summarize(name,url):
    r=fetch(url)
    data=r.pop("data",None)
    record={"url":url,**r,"schema":structure(data)}
    if name=="revisions" and isinstance(data,list):
        record["count"]=len(data)
        record["first_revision"]=data[0] if data else None
    if name=="meta" and isinstance(data,dict):
        record["meta_fields"]=list(data)
        record["current"]=data.get("current")
        record["revisionId"]=data.get("revisionId")
        record["image"]=data.get("image")
    if name=="notation" and data is not None:
        record["top_keys"]=list(data) if isinstance(data,dict) else None
        record["payload_bytes_estimate"]=len(json.dumps(data))
    print(name,record.get("status"),"schema:",json.dumps(record.get("schema"),ensure_ascii=False)[:7000],flush=True)
    return record
out={}
song=153
out["meta"]=summarize("meta",f"https://www.songsterr.com/api/meta/{song}")
time.sleep(1)
out["revisions"]=summarize("revisions",f"https://www.songsterr.com/api/meta/{song}/revisions")
# Do not assume nested fields or CDN root without verifying actual metadata.
current=out["meta"].get("current")
if isinstance(current,dict):
    revision=current.get("revisionId")
    img=current.get("image")
    out["identified"]={"songId":song,"revisionId":revision,"image":img,"track_count":len(current.get("tracks",[]))}
    if revision is not None and img and isinstance(img,str):
        # Songsterr-dl documented CDN path is tested only if actual URL base is known.
        out["notation_status"]="Metadata supports a notation path; require confirmed CDN origin before requesting."
else:out["notation_status"]="Cannot identify current revision from metadata."
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
print("Saved",OUT,flush=True)
