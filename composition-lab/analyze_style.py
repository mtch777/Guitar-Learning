"""Standalone GP7 symbolic feature analyzer (no audio or web dependencies).

Exact repeated measures are evidence of repetition, not automatic musical
phrase identification. Section labels are imported from the tab, not inferred.
"""
from __future__ import annotations
import argparse
import collections
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

PITCH_CLASSES = ("C","C#","D","D#","E","F","F#","G","G#","A","A#","B")
TECHNIQUES = {"PalmMuted","Muted","HopoOrigin","HopoDestination","Slide",
              "Bended","HarmonicType","LetRing","Tapped","Trill"}

def ids(element, tag):
    return (element.findtext(tag) or "").split()

def ranked(counter, limit=10):
    return [{"value":str(k), "count":v} for k,v in counter.most_common(limit)]

def profile(path):
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("Content/score.gpif"))
    def index(parent, tag):
        return {element.get("id"):element for element in root.findall(f"./{parent}/{tag}")}
    bars, voices, beats, notes, rhythms = [
        index(a,b) for a,b in (("Bars","Bar"),("Voices","Voice"),
                              ("Beats","Beat"),("Notes","Note"),("Rhythms","Rhythm"))
    ]
    masters = root.findall("./MasterBars/MasterBar")
    tracks = root.findall("./Tracks/Track")
    boundaries = [(i+1, bar.findtext("./Section/Text")) for i,bar in enumerate(masters)
                  if bar.findtext("./Section/Text")]
    sections = [
        {"start_measure":start,
         "end_measure":boundaries[i+1][0]-1 if i+1<len(boundaries) else len(masters),
         "label":label}
        for i,(start,label) in enumerate(boundaries)
    ]
    report = {
        "song":Path(path).stem,
        "measures":len(masters),
        "section_markers":sections,
        "time_signatures":dict(collections.Counter(m.findtext("Time") or "unknown"
                                                   for m in masters)),
        "tracks":[],
        "limitations":[
            "Section boundaries are supplied GP tab annotations, not automatic inference",
            "Motif matching is exact on frets, strings and rhythmic note values",
            "Intervals follow GP note order; simultaneous chord notes may distort them",
            "Harmonic pitch-class counts do not establish a key or chord progression",
            "Counts include tied notes; technique counts are notation occurrences",
            "Percussion without fret/string/MIDI triplets is excluded from pitched-note metrics",
            "No cross-tuning normalization, swing, expressive timing or phrase grouping"
        ]
    }
    for track_index, track in enumerate(tracks):
        name = track.findtext("Name") or "unnamed"
        tuning = [(staff.findtext("./Properties/Property[@name='Tuning']/Pitches") or "")
                  for staff in track.findall("./Staves/Staff")]
        rhythm_counts=collections.Counter()
        techniques=collections.Counter()
        pitches=collections.Counter()
        fret_counts=collections.Counter()
        string_counts=collections.Counter()
        intervals=collections.Counter()
        chords=collections.Counter()
        fingerprints=[]
        previous_pitch=None
        note_count=active_beats=empty_beats=tuplets=0
        for master in masters:
            refs=ids(master,"Bars")
            if track_index>=len(refs):
                raise ValueError("Missing track-to-bar reference")
            measure=[]
            for voice_id in ids(bars[refs[track_index]],"Voices"):
                if voice_id=="-1":continue
                for beat_id in ids(voices[voice_id],"Beats"):
                    beat=beats[beat_id]
                    rhythm_ref=beat.find("Rhythm")
                    rhythm=rhythms.get(rhythm_ref.get("ref")) if rhythm_ref is not None else None
                    value=rhythm.findtext("NoteValue") if rhythm is not None else "Unknown"
                    rhythm_counts[value]+=1
                    if rhythm is not None and rhythm.find("PrimaryTuplet") is not None:
                        tuplets+=1
                    fretted=[]
                    for note_id in ids(beat,"Notes"):
                        note=notes[note_id]
                        properties={p.get("name"):p for p in note.findall("./Properties/Property")}
                        def get(name, child):
                            return properties[name].findtext(child) if name in properties else None
                        fret, string, midi = (get("Fret","Fret"),get("String","String"),
                                              get("Midi","Number"))
                        if None in (fret,string,midi):continue
                        f,s,p=int(fret),int(string),int(midi)
                        note_count+=1
                        fret_counts[f]+=1
                        string_counts[s]+=1
                        pitches[PITCH_CLASSES[p%12]]+=1
                        fretted.append((s,f,p))
                        if previous_pitch is not None:
                            intervals[p-previous_pitch]+=1
                        previous_pitch=p
                        for technique in properties.keys() & TECHNIQUES:
                            techniques[technique]+=1
                        if note.find("Tie") is not None:
                            techniques["Tie"]+=1
                    if len(fretted)>1:
                        chords[tuple(sorted(p%12 for _,_,p in fretted))]+=1
                    if fretted:active_beats+=1
                    else:empty_beats+=1
                    measure.append((value,tuple(sorted((s,f) for s,f,_ in fretted))))
            fingerprints.append(tuple(measure))
        repeats=collections.defaultdict(list)
        for i,fingerprint in enumerate(fingerprints):
            if fingerprint and any(n for _,n in fingerprint):
                repeats[fingerprint].append(i+1)
        repeat_groups=sorted((positions for positions in repeats.values() if len(positions)>1),
                             key=lambda v:(-len(v),v[0]))
        pairs=collections.defaultdict(list)
        for i in range(len(fingerprints)-1):
            two=(fingerprints[i],fingerprints[i+1])
            if all(part and any(n for _,n in part) for part in two):
                pairs[two].append(i+1)
        repeated_pairs=sorted((positions for positions in pairs.values() if len(positions)>1),
                              key=lambda v:(-len(v),v[0]))
        report["tracks"].append({
            "name":name,"tab_track":any(tuning),"tuning":tuning,
            "notes":note_count,"beats_with_notes":active_beats,
            "beats_without_fretted_notes":empty_beats,
            "rhythms":ranked(rhythm_counts),"tuplet_beats":tuplets,
            "pitch_classes":ranked(pitches,12),
            "intervals_semitones_naive":ranked(intervals),
            "frets":ranked(fret_counts),"strings_zero_based":ranked(string_counts),
            "techniques":dict(techniques),
            "repeated_measure_groups":repeat_groups[:12],
            "repeated_two_measure_groups":repeated_pairs[:12],
            "simultaneous_pitch_class_sets":ranked(chords,8)
        })
    return report

def main():
    parser=argparse.ArgumentParser(description="GP7 symbolic style analysis")
    parser.add_argument("files",nargs="+",type=Path)
    parser.add_argument("--output",type=Path,help="Write machine-readable report")
    args=parser.parse_args()
    result=[profile(p) for p in args.files]
    encoded=json.dumps(result,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(encoded,encoding="utf-8")
        print(f"Analyzed {len(result)} files to {args.output}")
    else:
        print(encoded)

if __name__=="__main__":
    main()
