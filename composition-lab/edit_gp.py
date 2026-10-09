"""Minimal GP7 score editor. Independent of web app and audio classifier.

Edits one plain fretted note (+/- 1 semitone) and verifies the modified
score survives re-import. It is NOT yet a general GPIF composition writer.
"""
from __future__ import annotations
import argparse
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

PITCHES = {"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}
NAMES = ("C","C#","D","D#","E","F","F#","G","G#","A","A#","B")

def prop(note, name, child):
    return note.find(f"./Properties/Property[@name='{name}']/{child}")

def pitch_number(p):
    accidental = p.findtext("Accidental") or ""
    return (int(p.findtext("Octave"))+1)*12 + PITCHES[p.findtext("Step")] + {"":0,"#":1,"b":-1,"x":2,"bb":-2}[accidental]

def set_pitch(p, number):
    name = NAMES[number % 12]
    p.find("Step").text = name[0]
    p.find("Accidental").text = name[1:] or None
    p.find("Octave").text = str(number // 12 - 1)

def edit_note(source, destination, *, note_id=None, semitones=1):
    """Shift exactly one plain guitar note; reject unsafe/unsupported edits."""
    if type(semitones) is not int or semitones not in (-1,1):
        raise ValueError("Only one-semitone shifts supported")
    src, dst = Path(source), Path(destination)
    if src.resolve() == dst.resolve():
        raise ValueError("Input and output paths must differ")
    with zipfile.ZipFile(src) as archive:
        infos = archive.infolist()
        contents = {i.filename:archive.read(i.filename) for i in infos}
    if not contents.get("VERSION",b"").startswith(b"7."):
        raise ValueError("Expected GP7 archive container")
    score = ET.fromstring(contents["Content/score.gpif"])
    change = None
    for note in score.findall("./Notes/Note"):
        if note_id is not None and note.get("id") != str(note_id):
            continue
        fret, midi, string = (prop(note,n,c) for n,c in
            (("Fret","Fret"),("Midi","Number"),("String","String")))
        pitches = [prop(note,n,"Pitch") for n in ("ConcertPitch","TransposedPitch")]
        if any(x is None for x in (fret,midi,string,*pitches)):
            continue
        if note.find("Tie") is not None:
            continue
        forbidden = {"Bend","Slide","HopoOrigin","HopoDestination","Harmonic","Vibrato"}
        if any(p.get("name") in forbidden for p in note.findall("./Properties/Property")):
            continue
        if any(x.tag in forbidden for x in note):
            continue
        old_fret = int(fret.text)
        new_fret = old_fret + semitones
        if not (1 <= old_fret <= 22 and 0 <= new_fret <= 24):
            continue
        old_midi = int(midi.text)
        pitch_values = [pitch_number(p) for p in pitches]
        fret.text, midi.text = str(new_fret), str(old_midi+semitones)
        for p, number in zip(pitches,pitch_values):
            set_pitch(p, number+semitones)
        change = {"note_id":note.get("id"),"string":int(string.text),
                  "old_fret":old_fret,"new_fret":new_fret,
                  "old_midi":old_midi,"new_midi":old_midi+semitones}
        break
    if change is None:
        raise ValueError("No safely editable fretted note found")
    contents["Content/score.gpif"] = ET.tostring(score,encoding="utf-8",xml_declaration=True)
    dst.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(dst,"w") as archive:
        for info in infos:
            archive.writestr(info,contents[info.filename])
    with zipfile.ZipFile(src) as original, zipfile.ZipFile(dst) as edited:
        parsed = ET.fromstring(edited.read("Content/score.gpif"))
        target = next(n for n in parsed.findall("./Notes/Note") if n.get("id")==change["note_id"])
        assert int(prop(target,"Fret","Fret").text)==change["new_fret"]
        assert int(prop(target,"Midi","Number").text)==change["new_midi"]
        changed = [name for name in original.namelist() if original.read(name)!=edited.read(name)]
        if changed != ["Content/score.gpif"]:
            raise AssertionError(f"Unexpected archive changes: {changed}")
    return {"source":src.name,"output":str(dst),"change":change,
            "changed_members":changed,"reimport_verified":True}

def main():
    parser = argparse.ArgumentParser(description="Single-note GP7 editing proof")
    parser.add_argument("source",type=Path)
    parser.add_argument("destination",type=Path)
    parser.add_argument("--note-id")
    parser.add_argument("--semitones",type=int,default=1)
    args = parser.parse_args()
    print(json.dumps(edit_note(args.source,args.destination,
        note_id=args.note_id,semitones=args.semitones),indent=2))

if __name__ == "__main__":
    main()
