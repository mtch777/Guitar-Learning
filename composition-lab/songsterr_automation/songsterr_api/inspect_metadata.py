#!/usr/bin/env python3
"""Inspect real Songsterr search and metadata JSON without assuming a schema."""
import json, urllib.request, urllib.error, time
from pathlib import Path
BASE = "https://www.songsterr.com"
OUT = Path("songsterr-diagnostics/metadata_inventory.json")
HEADERS = {"User-Agent":"CompositionLab-Songsterr-Endpoint-SmokeTest/1.0","Accept":"application/json"}
def get(path):
    t=time.monotonic()
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE+path,headers=HEADERS),timeout=20) as r:
            raw=r.read(4_000_000)
            return {"url":BASE+path,"status":r.status,"content_type":r.headers.get("Content-Type"),"elapsed_ms":round((time.monotonic()-t)*1000),"data":json.loads(raw)}
    except Exception as e: return {"url":BASE+path,"error":str(e),"elapsed_ms":round((time.monotonic()-t)*1000)}
def schema(x,depth=0):
    if depth>=4:return type(x).__name__
    if isinstance(x,dict):return {k:schema(v,depth+1) for k,v in x.items()}
    if isinstance(x,list):return {"type":"array","length":len(x),"element":schema(x[0],depth+1) if x else None}
    return type(x).__name__
out={}
for size in (5,25,100):
    r=get(f"/api/songs?pattern=Pink+Floyd&size={size}")
    data=r.pop("data",None)
    r["count"]=len(data) if isinstance(data,list) else None
    r["schema"]=schema(data[0]) if isinstance(data,list) and data else schema(data)
    r["sample"]=data[:2] if isinstance(data,list) else data
    r["song_ids"]=[s.get("songId") for s in data if isinstance(s,dict)] if isinstance(data,list) else []
    out[f"search_size_{size}"]=r
    time.sleep(1)
for sid in (153,79):
    r=get(f"/api/meta/{sid}")
    data=r.pop("data",None)
    r["schema"]=schema(data)
    r["sample"]=data
    out[f"meta_{sid}"]=r
    time.sleep(1)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
for key,r in out.items():
    print("INSPECT",key,"HTTP",r.get("status"),"count",r.get("count"),"error",r.get("error"))
    print("SCHEMA",json.dumps(r.get("schema"),ensure_ascii=False)[:5000])
    print("SAMPLE",json.dumps(r.get("sample"),ensure_ascii=False)[:6000])
print("Saved:",OUT)
