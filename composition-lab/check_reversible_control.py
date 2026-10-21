"""Direct raw source oracle; producer decode only, no extract/plan/encode."""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib
from reversible_control import decode

def typed(x):
 return {"type":type(x).__name__,"value":str(F(str(x))) if type(x) in (int,float) else x}
def check(capture,upper):
 meta=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"));m=json.loads(upper.read_text());f=decode(m)
 parts=[];records=[];endings=[];unsupported=[];regions=[];reasons=[];where={}
 for path in sorted(capture.glob("track-*.json")):
  t=json.loads(path.read_text(encoding="utf-8-sig"));pid=f"part:{meta['songId']}:{t['partId']}";refs=[];pending=[];pickup={"kind":"absent"}
  if "anacrusis" in t:
   x=t["anacrusis"]
   if type(x) in (int,float,bool,str,type(None)):pickup={"kind":"scalar","value":typed(x)}
   else:pickup={"kind":"unsupported"};unsupported.append(dict(owner=pid,field="anacrusis",source_type=type(x).__name__))
  for i,b in enumerate(t.get("measures",[])):
   ident=f"measure:{meta['songId']}:{t['partId']}:{i+1}";refs.append(ident);where[ident]=(pid,i);fields={}
   for key in ("repeatStart","repeat"):
    if key not in b:continue
    x=b[key]
    if type(x) in (int,float,bool,str,type(None)):fields[key]=typed(x)
    else:
     unsupported.append(dict(owner=ident,field=key,source_type=type(x).__name__));reasons.append(dict(owner=ident,field=key,reason="unsupported_source_shape"))
   if fields:records.append(dict(id=ident,fields=fields))
   if "repeatStart" in fields:
    x=b["repeatStart"]
    if x is True:pending.append((i,ident))
    elif x is not False:reasons.append(dict(owner=ident,field="repeatStart",reason="non_boolean_start"))
   if "repeat" in fields:
    x=b["repeat"];v=F(str(x)) if type(x) in (int,float) else None
    if v==0:pass
    elif v is None or v<0 or v.denominator!=1:reasons.append(dict(owner=ident,field="repeat",reason="invalid_repeat_count"))
    elif not pending:reasons.append(dict(owner=ident,field="repeat",reason="no_explicit_start"))
    else:
     start,sid=pending.pop();regions.append(dict(part_ref=pid,start_ref=sid,span=str(i-start+1),count=str(v),count_type=type(x).__name__))
   if "alternateEnding" in b:
    x=b["alternateEnding"]
    if type(x) is list and all(type(y) in (int,float,bool,str,type(None)) for y in x):endings.append(dict(owner=ident,kind="array",items=[typed(y) for y in x]))
    elif type(x) in (int,float,bool,str,type(None)):endings.append(dict(owner=ident,kind="scalar",items=[typed(x)]))
    else:unsupported.append(dict(owner=ident,field="alternateEnding",source_type=type(x).__name__))
  reasons.extend(dict(owner=ident,field="repeatStart",reason="unmatched_start") for _,ident in pending)
  parts.append(dict(id=pid,measure_refs=refs,anacrusis=pickup))
 expected=dict(schema="control-source-observations/1",parts=parts,records=sorted(records,key=lambda x:x["id"]),endings=sorted(endings,key=lambda x:x["owner"]),unsupported=sorted(unsupported,key=lambda x:(x["owner"],x["field"])))
 if expected!=f:raise ValueError("Raw declaration/presence/ownership mismatch")
 if sorted(reasons,key=lambda x:(x["owner"],x["field"],x["reason"]))!=m["unresolved"]:raise ValueError("Independent unresolved reasons mismatch")
 # Region parameters are read directly from their one-row generic numeric occurrences.
 defs=m["regions"]["definitions"];occ=m["regions"]["occurrences"];actual=[]
 bybinding={r["id"]:r for r in m["bindings"]}
 for o in occ:
  d=defs[o["definition"]];b=bybinding[o["members"][0]]
  if len(o["members"])!=1 or o["anchors"] or o["unit"]!="1":raise ValueError("Unexpected region generic ownership")
  actual.append(dict(part_ref=b["part_ref"],start_ref=b["start_ref"],span=d["parameters"]["measure_span"][0],count=d["parameters"]["source_repeat_count"][0],count_type=b["count_type"]))
 if actual!=regions:raise ValueError("Independent eligible-region set mismatch")
 return dict(status="pass",records=len(records),endings=len(endings),regions=len(regions),expected_regions=regions,unsupported=len(unsupported),upper_sha256=hashlib.sha256(upper.read_bytes()).hexdigest())


if __name__=="__main__":
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("capture",type=Path);p.add_argument("upper",type=Path);a=p.parse_args()
 print(json.dumps(check(a.capture,a.upper)))
