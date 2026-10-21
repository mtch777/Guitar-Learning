"""Inspect real tiered-song records, exact time or source links without a new UI."""
import argparse
from collections import defaultdict,deque
from fractions import Fraction as F
import json
from pathlib import Path
from build_tiered_song import layers,read,pointer


class SongWalk:
    def __init__(self,package):
        self.package=package;self.states=layers(package)
        self.nodes={r["id"]:r for state in self.states.values() for r in state["records"]}
        self.forward=defaultdict(list);self.reverse=defaultdict(list);self.source=[]
        for state in self.states.values():
            for edge in state.get("links",[]):
                self.forward[edge["from_id"]].append(edge)
                if "to_id" in edge:self.reverse[edge["to_id"]].append(edge)
                else:self.source.append(edge)

    def at_time(self,q,clock="written_quarter_notes",part_id=None):
        q=F(q);result=[]
        for record in self.nodes.values():
            if part_id is not None and record["scope"].get("part_id")!=part_id:continue
            time=record["time"]
            if not time or time["basis"]!=clock:continue
            if any(F(s["start"])<=q<F(s["end"]) or F(s["start"])==F(s["end"])==q for s in time["spans"]):result.append(record["id"])
        return result

    def source_users(self,document,path):
        # A parent preservation link is NOT proof every child field is interpreted.
        result=[]
        for edge in self.source:
            ref=edge["to_source"]
            exact=ref["pointer"]==path
            ancestor=path.startswith(ref["pointer"]+"/")
            descendant=path=="" or ref["pointer"].startswith(path+"/")
            if ref["document"]==document and (exact or ancestor or descendant):
                relation="exact_field" if exact else "parent_preservation" if ancestor else "user_of_contained_field"
                result.append(dict(record=edge["from_id"],type=edge["type"],matched_source_pointer=ref["pointer"],exact_field=exact,query_relation=relation))
        return result

    def walk(self,start,direction="down",depth=2):
        if start not in self.nodes:raise ValueError("Unknown record ID")
        seen={start};queue=deque([(start,0)]);edges=[]
        while queue:
            ident,level=queue.popleft()
            if level>=depth:continue
            for edge in self.forward[ident] if direction=="down" else self.reverse[ident]:
                edges.append(edge)
                target=edge.get("to_id") if direction=="down" else edge["from_id"]
                if target is not None and target not in seen:seen.add(target);queue.append((target,level+1))
        # This is a traversal result, not another authoritative song representation.
        return dict(start=start,direction=direction,depth=depth,records=[self.nodes[i] for i in sorted(seen)],links=edges)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("package",type=Path)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument("--record");group.add_argument("--time");group.add_argument("--source")
    p.add_argument("--direction",choices=("up","down"),default="down");p.add_argument("--depth",type=int,default=2)
    p.add_argument("--clock",choices=("written_quarter_notes","playback_quarter_notes"),default="written_quarter_notes");p.add_argument("--part",type=int);p.add_argument("--output",type=Path)
    a=p.parse_args();walk=SongWalk(read(a.package))
    if a.record:result=walk.walk(a.record,a.direction,a.depth)
    elif a.time is not None:result=dict(clock=a.clock,position=str(F(a.time)),records=walk.at_time(a.time,a.clock,a.part))
    else:
        document,path=a.source.split("#",1);result=dict(source=a.source,users=walk.source_users(document,path),meaning="Exact-field and parent-preservation links distinguished; not a claim every child field is understood")
    encoded=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:
        if "local-artifacts" not in a.output.resolve().parts or a.output.exists():p.error("Fresh private output path required")
        a.output.write_text(encoded,encoding="utf-8")
    else:print(encoded)

if __name__=="__main__":main()
