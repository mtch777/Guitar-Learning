"""Compile bounded chord spelling/quality syntax from pinned music21, no songs."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def definitions():
    import music21
    from music21 import harmony,pitch
    if music21.__version__!='9.9.2':raise ValueError('Pinned music21 9.9.2 required')
    roots={}
    def put(spelling,pc):
        if spelling in roots and roots[spelling]!=pc:raise ValueError('Conflicting library accidental glyph: '+ascii(spelling))
        roots[spelling]=pc
    for letter in 'ABCDEFG':
        for name,modifier in pitch.accidentalNameToModifier.items():
            accidental=pitch.Accidental(name)
            if not float(accidental.alter).is_integer():continue
            pc=pitch.Pitch(letter+modifier).pitchClass
            put(letter+modifier,pc)
        # Reuse the already-tested lexical adapter's bounded standard glyphs.
        # Native music21 renders triple-flat with the ordinary-flat glyph;
        # arbitrary accidental.unicode is therefore NOT an invertible spelling.
        from experiment_chord_glyph_adapter import glyph_map
        for glyph,modifier in glyph_map().items():put(letter+glyph,pitch.Pitch(letter+modifier).pitchClass)
    aliases={}
    for kind,(_,names) in harmony.CHORD_TYPES.items():
        for name in names:aliases.setdefault(name,[]).append(kind)
    roots=dict(sorted(roots.items()));aliases={k:sorted(v) for k,v in sorted(aliases.items())}
    provenance=dict(source='music21.pitch.Accidental and harmony.CHORD_TYPES aliases',version=music21.__version__,
        sha256=hashlib.sha256(json.dumps([roots,aliases],sort_keys=True,ensure_ascii=True).encode()).hexdigest(),
        scope='Exact finite quality aliases and integer ASCII accidental spellings; established natural/single/double Unicode glyph adapter only; no arbitrary alterations or inferred harmony')
    return roots,aliases,provenance


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');a=p.parse_args()
    path=Path(__file__).with_name('chord_symbol_lexicon.py');values=dict(zip(('ROOT_SPELLINGS','QUALITY_ALIASES','PROVENANCE'),definitions()))
    text=path.read_text(encoding='utf-8')
    if a.write:
        lines=text.splitlines()
        for name,value in values.items():lines=[name+' = '+repr(value) if line.startswith(name+' = ') else line for line in lines]
        path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    else:
        actual={n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(text).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values}
        if actual!=values:raise ValueError('Lexicon differs from pinned library')
    print(json.dumps(dict(root_spellings=len(values['ROOT_SPELLINGS']),quality_aliases=len(values['QUALITY_ALIASES']),verified=True)))
