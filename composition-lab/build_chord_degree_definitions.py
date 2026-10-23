"""Reproduce chord-definition degree slots from pinned music21; no song inputs."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

PINNED_VERSION='9.9.2'


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()


def definitions():
    import music21
    from music21 import harmony,pitch,scale
    if music21.__version__!=PINNED_VERSION:raise ValueError('Pinned music21 9.9.2 required for theory reproduction')
    major=scale.MajorScale('C4');records=[];formulas=[]
    for kind,value in harmony.CHORD_TYPES.items():
        formula=value[0];slots=[]
        for token in formula.split(','):
            match=re.fullmatch(r'([#-]*)([1-9][0-9]*)',token)
            if match is None:raise ValueError('Unrecognized source degree token')
            accidental,number=match.groups();degree=int(number)
            alteration=0 if not accidental else pitch.Accidental(accidental).alter
            if int(alteration)!=alteration:raise ValueError('Noninteger source alteration requires explicit review')
            # Compound degree octaves follow the source degree number, not
            # whatever voicing register ChordSymbol happens to emit.
            source_pitch=major.pitchFromDegree((degree-1)%7+1)
            source_pitch.octave=4+(degree-1)//7
            source_pitch.accidental=None if not accidental else pitch.Accidental(accidental)
            semitones=source_pitch.ps-pitch.Pitch('C4').ps
            if int(semitones)!=semitones:raise ValueError('Noninteger source degree interval')
            slots.append((token,degree,int(alteration),int(semitones),int(semitones)%12))
        pcs=tuple(sorted({p.pitchClass for p in harmony.ChordSymbol(root='C',kind=kind).pitches}))
        if tuple(sorted({s[4] for s in slots}))!=pcs:raise ValueError('Source degree expansion differs from library chord')
        records.append((kind,formula,tuple(slots)));formulas.append((kind,pcs))
    # Literal AST read avoids importing or altering the active musical core.
    core=Path(__file__).with_name('musical_tier2.py')
    node=next(n for n in ast.parse(core.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='THEORY_FORMS' for t in n.targets))
    if tuple(formulas)!=ast.literal_eval(node.value):raise ValueError('Existing pinned THEORY_FORMS differs')
    records=tuple(records)
    provenance=dict(source='music21.harmony.CHORD_TYPES[kind][0]',version=music21.__version__,
        degree_semantics='Source chord-definition degree slots relative to major/perfect scale degrees; alterations use music21 Accidental',
        register_semantics='Compound degree semitones retained; actual voicing register is a separate realization choice',
        spelling_scope='Theoretical template spelling only; not authored note spelling, inferred function or emotion',
        definitions_sha256=digest(records),pitch_class_forms_sha256=digest(tuple(formulas)),
        native_harmony_source_sha256=hashlib.sha256(Path(harmony.__file__).read_bytes()).hexdigest(),
        native_scale_source_sha256=hashlib.sha256(Path(scale.__file__).read_bytes()).hexdigest())
    return records,provenance


def render(records,provenance):
    return '''"""Generated pinned theory definitions, not song analysis or artist rules.

Reproduce with build_chord_degree_definitions.py --write. Runtime is stdlib-only.
Definition degrees do not assert a source note's authored enharmonic spelling.
"""
'''+ 'CHORD_DEGREE_DEFINITIONS = '+repr(records)+'\n\nCHORD_DEGREE_PROVENANCE = '+repr(provenance)+'''\n\n
def degree_definitions(kind):
    """Fresh records retain every source token, alteration and compound degree."""
    matches=[slots for name,formula,slots in CHORD_DEGREE_DEFINITIONS if name==kind]
    if type(kind) is not str or len(matches)!=1:raise ValueError('Known pinned chord kind required')
    return tuple(dict(token=token,degree=degree,alteration=alteration,theoretical_semitones=semitones,pitch_class=pc)
                 for token,degree,alteration,semitones,pc in matches[0])
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args()
    records,provenance=definitions();text=render(records,provenance);target=Path(__file__).with_name('chord_degree_definitions.py')
    if args.write:target.write_text(text,encoding='utf-8')
    elif target.read_text(encoding='utf-8')!=text:raise ValueError('Generated degree definitions/provenance differ')
    print(json.dumps(dict(chord_kinds=len(records),degree_slots=sum(len(x[2])for x in records),source_version=provenance['version'],verified=True)))


if __name__=='__main__':main()
