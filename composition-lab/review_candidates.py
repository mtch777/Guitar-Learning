"""Generate human-auditable examples; do NOT label guesses as ground truth.

Input: JSON reports made by phrase_analysis.py and validate_structure.py.
Output: CSV rows with example locations, numeric evidence, and blank human labels.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

FIELDS=["song","kind","track","measure_a","measure_b","length_bars","candidate",
        "algorithm_evidence","review_label","reviewer_notes"]
ALLOWED={"confirmed","rejected","uncertain"}

def audit_rows(motif_reports, structure_reports, motifs_per_track=3, chords_per_song=8):
    rows=[]
    for song in motif_reports:
        for track in song["tracks"]:
            matches=track.get("candidate_variant_motifs",[])
            selected=[];used=set()
            for match in sorted(matches,key=lambda m:(m["edit_distance"],-m["length_bars"])):
                a,b=match["bars"]
                if any(abs(a-x)<match["length_bars"] and abs(b-y)<match["length_bars"]
                       for x,y in used):continue
                selected.append(match);used.add((a,b))
                if len(selected)>=motifs_per_track:break
            for m in selected:
                a,b=m["bars"]
                rows.append({"song":song["file"],"kind":"motif","track":track["track"],
                    "measure_a":a,"measure_b":b,"length_bars":m["length_bars"],
                    "candidate":"edited or transposed riff",
                    "algorithm_evidence":json.dumps({"distance":m["edit_distance"],
                        "notes":m["notes"],"pitch_shift":m["first_pitch_shift"]})})
    for song in structure_reports:
        for item in song["blind_boundary_candidates"]:
            rows.append({"song":song["file"],"kind":"section_boundary","track":"",
                "measure_a":item["measure"],"measure_b":"","length_bars":"",
                "candidate":"structural boundary",
                "algorithm_evidence":json.dumps({"novelty":item["score"],
                    "harmonic_change":item["harmonic_change"],
                    "density_change":item["density_change"]})})
        # Choose varied measures (not simply the highest model-confidence chords).
        harmonic=song["harmonic_context"]
        if harmonic:
            samples=sorted(set(min(len(harmonic)-1,round(i*(len(harmonic)-1)/max(chords_per_song-1,1)))
                               for i in range(min(chords_per_song,len(harmonic)))))
            for i in samples:
                entry=harmonic[i];chords=entry["chord_candidates"]
                if not chords:continue
                top=chords[0];runner=chords[1]["score"] if len(chords)>1 else 0
                rows.append({"song":song["file"],"kind":"chord","track":"",
                    "measure_a":entry["measure"],"measure_b":"","length_bars":1,
                    "candidate":top["name"],
                    "algorithm_evidence":json.dumps({
                        "score":top["score"],"margin":round(top["score"]-runner,3),
                        "bass_root_hypothesis":entry["bass_root_hypothesis"],
                        "alternatives":chords[:3],
                        "pitch_class_weights":entry["pitch_class_weights"]})})
    return [{field:row.get(field,"") for field in FIELDS} for row in rows]

def write_audit(rows,path):
    with open(path,"w",newline="",encoding="utf-8") as f:
        out=csv.DictWriter(f,fieldnames=FIELDS)
        out.writeheader();out.writerows(rows)

def score_reviews(path):
    with open(path,newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    summary={}
    for kind in sorted(set(r["kind"] for r in rows)):
        grouped=[r for r in rows if r["kind"]==kind]
        statuses={v:sum(r["review_label"]==v for r in grouped) for v in ALLOWED}
        unreviewed=sum(not r["review_label"].strip() for r in grouped)
        invalid=[r["review_label"] for r in grouped if r["review_label"].strip()
                 and r["review_label"] not in ALLOWED]
        summary[kind]={"total":len(grouped),"confirmed":statuses["confirmed"],
            "rejected":statuses["rejected"],"uncertain":statuses["uncertain"],
            "unreviewed":unreviewed,"invalid_labels":invalid,
            "confirmed_share_of_reviewed":round(statuses["confirmed"]/
             (statuses["confirmed"]+statuses["rejected"]),3)
             if statuses["confirmed"]+statuses["rejected"] else None}
    return summary

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    gen=sub.add_parser("create")
    gen.add_argument("--motifs",type=Path,required=True)
    gen.add_argument("--structure",type=Path,required=True)
    gen.add_argument("--output",type=Path,required=True)
    check=sub.add_parser("score")
    check.add_argument("audit",type=Path)
    args=p.parse_args()
    if args.command=="create":
        motifs=json.loads(args.motifs.read_text(encoding="utf-8"))
        structure=json.loads(args.structure.read_text(encoding="utf-8"))
        rows=audit_rows(motifs,structure)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        write_audit(rows,args.output)
        print(json.dumps({"audit":str(args.output),"examples":len(rows),
                          "status":"UNREVIEWED"},indent=2))
    else:print(json.dumps(score_reviews(args.audit),indent=2))

if __name__=="__main__":
    main()
