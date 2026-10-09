"""Independent GP7 motif/harmony research. No audio or web dependencies.

Match pitch-transposed riffs, note contours and rhythmic patterns per track.
These are symbolic signatures, NOT inferred phrases or chord progressions.
"""
from __future__ import annotations
import argparse
import json
import zipfile
from pathlib import Path
from collections import Counter, defaultdict
from xml.etree import ElementTree as ET

NAMES = ("C","C#","D","D#","E","F","F#","G","G#","A","A#","B")
DURATION = {"Whole":4,"Half":2,"Quarter":1,"Eighth":.5,"16th":.25,"32nd":.125,"64th":.0625}

def ids(el, key):
    return (el.findtext(key) or "").split()

def read_score(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("Content/score.gpif"))
    def idx(parent, tag):
        return {n.get("id"):n for n in root.findall(f"./{parent}/{tag}")}
    bars,voices,beats,notes,rhythms = [
        idx(a,b) for a,b in (("Bars","Bar"),("Voices","Voice"),("Beats","Beat"),
                            ("Notes","Note"),("Rhythms","Rhythm"))]
    masters = root.findall("./MasterBars/MasterBar")
    tracks = []
    for ti,tr in enumerate(root.findall("./Tracks/Track")):
        measures=[]
        for master in masters:
            barrefs=ids(master,"Bars")
            if ti >= len(barrefs):
                raise ValueError("Missing bar reference for track")
            events=[]
            for voice_i,voice_ref in enumerate(ids(bars[barrefs[ti]],"Voices")):
                if voice_ref == "-1":continue
                onset=0
                for beat_ref in ids(voices[voice_ref],"Beats"):
                    beat=beats[beat_ref]
                    rref=beat.find("Rhythm")
                    rhythm=rhythms.get(rref.get("ref")) if rref is not None else None
                    value=rhythm.findtext("NoteValue") if rhythm is not None else None
                    if value not in DURATION:
                        raise ValueError(f"Unsupported duration {value!r}")
                    duration=DURATION[value]
                    if rhythm.find("AugmentationDot") is not None:duration*=1.5
                    t=rhythm.find("PrimaryTuplet")
                    if t is not None:
                        numerator,denominator=t.findtext("Num"),t.findtext("Den")
                        if numerator and denominator:duration*=int(denominator)/int(numerator)
                    pitches=[]
                    for note_ref in ids(beat,"Notes"):
                        n=notes[note_ref]
                        midi=n.findtext("./Properties/Property[@name='Midi']/Number")
                        string=n.findtext("./Properties/Property[@name='String']/String")
                        fret=n.findtext("./Properties/Property[@name='Fret']/Fret")
                        if all(v is not None for v in (midi,string,fret)):
                            pitches.append(int(midi))
                    events.append((voice_i,round(onset,6),round(duration,6),tuple(sorted(pitches))))
                    onset+=duration
            measures.append(events)
        tracks.append({"name":tr.findtext("Name") or "", "measures":measures})
    return {"file":Path(path).name,"measure_count":len(masters),
            "sections":[{"measure":i+1,"label":b.findtext("./Section/Text")} for i,b in enumerate(masters)
                        if b.findtext("./Section/Text")],
            "meters":dict(Counter(b.findtext("Time") or "unknown" for b in masters)),
            "tracks":tracks}

def motif_signature(events, flexible=False):
    voices=sorted({v for v,t,d,p in events if p})
    if not voices:return None
    seq=[(t,d,p) for v,t,d,ps in events if v == voices[0] for p in ps]
    if len(seq)<4:return None
    baseline=seq[0][2]
    if flexible:return tuple(p-baseline for t,d,p in seq)
    return tuple((t,d,p-baseline) for t,d,p in seq)

def repeat_groups(signatures, limit=12):
    grouped=defaultdict(list)
    for measure,s in enumerate(signatures,1):
        if s is not None:grouped[s].append(measure)
    return sorted((g for g in grouped.values() if len(g)>1),
                  key=lambda g:(-len(g),g[0]))[:limit]

def profile(path):
    music=read_score(path)
    output={"file":music["file"],"measure_count":music["measure_count"],
            "sections":music["sections"],"meters":music["meters"],"tracks":[],
            "limitations":[
                "Section boundaries come from tab labels, not automatic detection",
                "Motifs require four pitched events in a single voice within a measure",
                "Matches ignore absolute pitch; flexible matches also ignore rhythm",
                "No insertions/deletions, phrase segmentation, or rhythmic swing modeled",
                "Chord pitch-class sets are observations, not chord progressions",
                "Only notes with MIDI/string/fret properties contribute to pitched analysis",
                "Multi-note beats are excluded from melodic interval transitions"]}
    for track in music["tracks"]:
        pitches=Counter(); intervals=Counter(); chords=Counter()
        last=None
        for bar in track["measures"]:
            for voice,onset,duration,ps in sorted(bar,key=lambda x:(x[1],x[0])):
                pitches.update(NAMES[p%12] for p in ps)
                if len(ps)>1:
                    chords[tuple(sorted(set(NAMES[p%12] for p in ps)))]+=1
                    last=None
                elif len(ps)==1:
                    if last is not None:intervals[ps[0]-last]+=1
                    last=ps[0]
        timed=[motif_signature(bar) for bar in track["measures"]]
        flex=[motif_signature(bar,True) for bar in track["measures"]]
        pair=[(a,b) if a is not None and b is not None else None
              for a,b in zip(timed,timed[1:])]
        output["tracks"].append({
            "name":track["name"],"pitch_classes":pitches.most_common(12),
            "melodic_intervals_semitones":intervals.most_common(12),
            "simultaneous_pitch_class_sets":[{"notes":list(k),"count":v}
                                            for k,v in chords.most_common(10)],
            "transposition_invariant_measures":repeat_groups(timed),
            "rhythm_flexible_motifs":repeat_groups(flex),
            "transposition_invariant_two_bar_motifs":repeat_groups(pair)})
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("files",nargs="+",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    output=json.dumps([profile(p) for p in args.files],indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(output,encoding="utf-8")
        print(f"Wrote {args.output}")
    else:print(output)

if __name__=="__main__":main()
