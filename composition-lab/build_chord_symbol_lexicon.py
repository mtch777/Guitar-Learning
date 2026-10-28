"""Compile bounded chord spelling/quality syntax from pinned music21, no songs."""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path


def numeric_qualities(harmony,pitch,aliases):
    """Compile only native numeric syntax with one transposition-stable formula.

    Slash bass is deliberately absent: a native parser can ADD that bass to its
    pitch collection, which must never invent the base chord's identity.
    """
    domain=sorted({int(re.fullmatch(r'[#-]*(\d+)',token)[1])
        for formula,_ in harmony.CHORD_TYPES.values() for token in formula.split(',')})
    roots=[pitch.Pitch(midi=60+i).name for i in range(12)]
    audit=[];accepted={}
    for number in domain:
        suffix=str(number);rows=[]
        for root in roots:
            try:
                symbol=harmony.ChordSymbol(root+suffix)
                pc=pitch.Pitch(root).pitchClass
                intervals=sorted({(p.pitchClass-pc)%12 for p in symbol.pitches})
                matches=[]
                for kind in harmony.CHORD_TYPES:
                    formal=harmony.ChordSymbol(root=root,kind=kind)
                    if sorted({(p.pitchClass-pc)%12 for p in formal.pitches})==intervals:matches.append(kind)
                rows.append(dict(root=root,native_kind=symbol.chordKind,intervals=intervals,matches=sorted(matches)))
            except (ValueError,TypeError) as error:rows.append(dict(root=root,error=type(error).__name__+': '+str(error),matches=[]))
        signatures={(tuple(r.get('intervals',[])),tuple(r['matches'])) for r in rows}
        status='NO_UNIQUE_FORMULA'
        if len(signatures)==1 and all(len(r['matches'])==1 for r in rows):
            kind=rows[0]['matches'][0]
            if suffix in aliases and aliases[suffix]!=[kind]:status='EXISTING_ALIAS_CONFLICT'
            else:accepted[suffix]=[kind];status='ACCEPTED_EXISTING_ALIAS' if suffix in aliases else 'ACCEPTED_NATIVE_NUMERIC_SYNTAX'
        elif len(signatures)>1:status='TRANSPOSITION_DISAGREEMENT'
        audit.append(dict(suffix=suffix,status=status,roots=rows))
    if any(r['status']=='EXISTING_ALIAS_CONFLICT' for r in audit):raise ValueError(dict(numeric_quality_audit=audit))
    return accepted,audit


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
    numeric,audit=numeric_qualities(harmony,pitch,aliases)
    aliases.update(numeric)
    roots=dict(sorted(roots.items()));aliases={k:sorted(v) for k,v in sorted(aliases.items())}
    provenance=dict(source='music21.pitch.Accidental, harmony.CHORD_TYPES and native numeric-degree syntax',version=music21.__version__,
        sha256=hashlib.sha256(json.dumps([roots,aliases,audit],sort_keys=True,ensure_ascii=True).encode()).hexdigest(),
        scope='Finite aliases plus unique native numeric formula matches across all12 roots; integer ASCII accidentals and established standard Unicode glyphs; no arbitrary alterations or inferred harmony')
    return roots,aliases,provenance,audit


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');a=p.parse_args()
    path=Path(__file__).with_name('chord_symbol_lexicon.py');values=dict(zip(('ROOT_SPELLINGS','QUALITY_ALIASES','PROVENANCE','NUMERIC_QUALITY_AUDIT'),definitions()))
    text=path.read_text(encoding='utf-8')
    if a.write:
        lines=text.splitlines()
        for name,value in values.items():lines=[name+' = '+repr(value) if line.startswith(name+' = ') else line for line in lines]
        path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    else:
        actual={n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(text).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values}
        if actual!=values:raise ValueError('Lexicon differs from pinned library')
    print(json.dumps(dict(root_spellings=len(values['ROOT_SPELLINGS']),quality_aliases=len(values['QUALITY_ALIASES']),verified=True)))
