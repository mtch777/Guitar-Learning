"""Learn 16-bar phrase-recurrence structure, not guitar notes or finished .gp scores."""
from __future__ import annotations
import argparse,json,random
from collections import Counter,defaultdict
from pathlib import Path
from phrase_development import analyze

ACTIONS=("introduce","repeat","vary","transpose","return")

def select_track(song):
    tracks=song["guitar_tracks"]
    if not tracks:return None
    return min(tracks,key=lambda t:(0 if "rhythm" in t["track"].lower()
        else 1 if "guitar" in t["track"].lower() else 2,-len(t["phrases"]),t["track"]))

def events_for_track(track):
    seq=[];last={}
    for p in track["phrases"]:
        family=p["motif_family"]
        if family is None or p["note_count"]<4:continue
        r=p["relationship"]
        if family not in last: action="introduce"
        elif r=="identical":action="repeat" if last[family]==len(seq)-1 else "return"
        elif r=="transposed_exact":action="transpose"
        elif r=="varied":action="vary"
        else:action="return"
        seq.append({"action":action,"family":family,"bars":p["bars"],
                    "source_measure":p["start_measure"],"section":p["section"]})
        last[family]=len(seq)-1
    return seq

def train(songs):
    starts=Counter();transition=defaultdict(Counter);durations=defaultdict(Counter);examples=[]
    for song in songs:
        t=select_track(song)
        if not t:continue
        seq=events_for_track(t)
        if not seq:continue
        starts[seq[0]["action"]]+=1
        for i,p in enumerate(seq):
            durations[p["action"]][p["bars"]]+=1
            if i:transition[seq[i-1]["action"]][p["action"]]+=1
        examples.append({"song":song["song"],"track":t["track"],"phrases":len(seq)})
    if not examples:raise ValueError("No guitar phrases")
    return {"sources":examples,"initial_actions":dict(starts),
        "transitions":{k:dict(v) for k,v in transition.items()},
        "durations":{k:{str(b):n for b,n in v.items()} for k,v in durations.items()},
        "limitations":["Tiny corpus; no note composition",
                       "Phrase boundaries are provisional",
                       "One representative rhythm guitar per song"]}

def pick(rng,counts):
    pairs=[(k,float(v)) for k,v in sorted(counts.items()) if v>0]
    if not pairs:raise ValueError("Empty distribution")
    roll=rng.random()*sum(v for _,v in pairs)
    for k,v in pairs:
        roll-=v
        if roll<=0:return k
    return pairs[-1][0]

def plan(model,bars=16,seed=17):
    if bars<2:raise ValueError("At least two bars required")
    rng=random.Random(seed);results=[];families=[];used=0
    while used<bars:
        left=bars-used
        if not results:action="introduce"
        else:
            weights={action:model["transitions"].get(results[-1]["action"],{}).get(action,0)+1
                     for action in ACTIONS}
            if len(families)>=5:weights["introduce"]=0
            action=pick(rng,weights)
            # Minimum coherence constraint: a contrasting B then reprise of A.
            if used>=bars//2 and len(families)==1:action="introduce"
            elif left<=4 and len(families)>1:action="return"
        if action=="introduce":
            family=chr(65+len(families)) if len(families)<26 else "F"+str(len(families)+1)
            families.append(family);source=None
        else:
            recent=results[-1]["family"]
            older=families[:-1] if action=="return" else []
            family=(families[0] if left<=4 else rng.choice(older)) if older else recent
            earlier=[p for p in results if p["family"]==family]
            if not earlier:family=recent;earlier=[p for p in results if p["family"]==family]
            source=earlier[-1]["phrase"]
            if action=="return" and family==recent:action="repeat"
        durations={int(k):v for k,v in model["durations"].get(action,{}).items()
                   if 0<int(k)<=left}
        length=pick(rng,durations) if durations else min(left,4)
        results.append({"phrase":len(results)+1,"start_measure":used+1,
                        "end_measure":used+length,"bars":length,"family":family,
                        "action":action,"develops_phrase":source})
        used+=length
    return {"bars":bars,"seed":seed,"phrase_plan":results,
            "sequence":" → ".join(x["family"]+":"+x["action"] for x in results),
            "output_type":"structure_only_no_note_generation"}

def evaluate(songs):
    reports=[]
    for i,test in enumerate(songs):
        training=train([s for j,s in enumerate(songs) if j!=i])
        t=select_track(test);seq=events_for_track(t) if t else []
        pairs=list(zip(seq,seq[1:]))
        hits=sum(b["action"] in training["transitions"].get(a["action"],{})
                 for a,b in pairs)
        reports.append({"held_out_song":test["song"],"test_track":t["track"] if t else None,
            "transitions_tested":len(pairs),"observed_in_training":hits,
            "coverage":round(hits/len(pairs),3) if pairs else None})
    return reports

def main():
    p=argparse.ArgumentParser()
    p.add_argument("files",nargs="+",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--bars",type=int,default=16)
    p.add_argument("--seed",type=int,default=17)
    args=p.parse_args()
    songs=[analyze(x) for x in args.files]
    model=train(songs)
    data={"model":model,"proposed_composition":plan(model,args.bars,args.seed),
          "leave_one_song_out_evaluation":evaluate(songs) if len(songs)>1 else []}
    result=json.dumps(data,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(result,encoding="utf-8")
        print("Wrote",args.output)
    else:print(result)
if __name__=="__main__":main()
