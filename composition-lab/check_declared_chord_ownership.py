"""Independent native-library/raw-source audit of conditional degree ownership.

No producer parser, selection, lift, or inverse is imported. Native music21 is
an evaluation dependency only; this is not the isolated reconstruction worker.
"""
from collections import Counter
from fractions import Fraction as F
import json
import re
from functools import lru_cache

@lru_cache(maxsize=1)
def native_numeric_aliases():
    """Independent text-parser probe; explicit slash bass is never in this probe."""
    from music21 import harmony,__version__
    if __version__!='9.9.2':raise ValueError('Pinned native theory oracle 9.9.2 required')
    numbers=sorted({int(re.search(r"\d+",token).group()) for formula,_ in harmony.CHORD_TYPES.values() for token in formula.split(",")})
    roots=("C","C#","D","E-","E","F","F#","G","A-","A","B-","B")
    accepted={}
    for number in numbers:
        choices=[]
        for root in roots:
            try:
                native=harmony.ChordSymbol(root+str(number));actual={p.pitchClass for p in native.pitches}
                matches=[kind for kind in harmony.CHORD_TYPES if {p.pitchClass for p in harmony.ChordSymbol(root=root,kind=kind).pitches}==actual]
            except (ValueError,TypeError):matches=[]
            choices.append(matches)
        if any(len(c)!=1 for c in choices) or len({c[0] for c in choices})!=1:continue
        kind=choices[0][0];old={k for k,(_,aliases) in harmony.CHORD_TYPES.items() if str(number) in aliases}
        if old and old!={kind}:continue
        accepted[str(number)]=kind
    return accepted

class _File:
    def __init__(self,name,value):self.name=name;self.stem=name.rsplit('.',1)[0];self.value=value
    def read_text(self,**kwargs):return json.dumps(self.value)
class _Capture:
    def __init__(self,documents):self.documents=documents
    def __truediv__(self,name):return _File(name,self.documents[name])
    def glob(self,pattern):return [_File(k,v) for k,v in self.documents.items() if k.startswith('track-') and k.endswith('.json')]

LEGACY_PROFILE='music21-9.9.2-aliases'
CURRENT_PROFILE='music21-9.9.2-aliases+numeric-degrees'

def native_interpretations(text,profile=CURRENT_PROFILE):
    from music21 import harmony,pitch,__version__
    if __version__!='9.9.2':raise ValueError('Pinned native theory oracle 9.9.2 required')
    if type(profile) is not str or profile not in (LEGACY_PROFILE,CURRENT_PROFILE):raise ValueError('Unknown native admission profile')
    if type(text) is not str:return []
    roots={}
    for letter in 'ABCDEFG':
        for name,modifier in pitch.accidentalNameToModifier.items():
            a=pitch.Accidental(name)
            if float(a.alter).is_integer():roots[letter+modifier]=(pitch.Pitch(letter+modifier).pitchClass,letter+modifier)
        for name in ('natural','sharp','flat','double-sharp','double-flat'):
            a=pitch.Accidental(name);roots[letter+a.unicode]=(pitch.Pitch(letter+a.modifier).pitchClass,letter+a.modifier)
    found={}
    for spelling,(root,ascii_root) in roots.items():
        if not text.startswith(spelling):continue
        tail=text[len(spelling):];variants=[(tail,None)]
        if '/' in tail:
            quality,bass=tail.rsplit('/',1)
            if bass in roots:variants.append((quality,roots[bass][0]))
        for quality,bass in variants:
            for kind,(formula,aliases) in harmony.CHORD_TYPES.items():
                if quality not in aliases and (profile!=CURRENT_PROFILE or native_numeric_aliases().get(quality)!=kind):continue
                chord=harmony.ChordSymbol(root=ascii_root,kind=kind)
                pcs=sorted({p.pitchClass for p in chord.pitches})
                degrees=[]
                for token in formula.split(','):
                    match=re.fullmatch(r'([#-]*)(\d+)',token);acc,degree=match.groups();degree=int(degree)
                    # Native interval machinery supplies compound degree distance.
                    from music21 import scale
                    semitone=scale.MajorScale('C').pitchFromDegree(degree).midi-60
                    semitone+=pitch.Accidental(acc).alter if acc else 0
                    degrees.append((token,int(semitone)))
                found[root,kind,bass]=dict(root_pc=root,kind=kind,slash_bass_pc=bass,pcs=pcs,degrees=degrees)
    return list(found.values())

def check(documents,upper,restored_tier1=None):
    from check_reversible_source import source_expectation
    issues=[];counts=Counter();capture=_Capture(documents)
    try:
        expected,_=source_expectation(capture)
        wrapper=upper['musical_relationships']
        if set(wrapper) not in ({'schema','core'},{'schema','core','admission_profile'}) or wrapper['schema']!='source-declared-chord-degrees/1':raise ValueError('Wrong owner envelope')
        profile=wrapper.get('admission_profile',LEGACY_PROFILE)
        if type(profile) is not str or profile not in (LEGACY_PROFILE,CURRENT_PROFILE):raise ValueError('Unknown owner admission profile')
        if 'admission_profile' in wrapper and profile==LEGACY_PROFILE:raise ValueError('Explicit legacy profile is noncanonical')
        core=wrapper['core'];groups=core['coattacks'];seen=[];group_seen=set()
        topology=source_expectation(capture,include_topology=True);layout=source_expectation(capture,include_layout=True)
        invalid_bars=set()
        sums={}
        for beat in topology['beats']:
            _,_,part,bar,voice,index=beat['id'].split(':');key=(int(part),int(bar),int(voice))
            sums[key]=sums.get(key,F(0))+F(beat['duration_q'])
        for (part,bar,voice),duration in sums.items():
            if duration>layout[bar-1][1]:invalid_bars.add((part,bar))
        labels={};parts={}
        for name,p in documents.items():
            if not name.startswith('track-'):continue
            parts[p['partId']]=p
            for mi,m in enumerate(p.get('measures',[])):
                for vi,v in enumerate(m.get('voices',[])):
                    for bi,b in enumerate(v.get('beats',[])):
                        if isinstance(b.get('chord'),dict) and 'text' in b['chord']:
                            labels[p['partId'],mi+1,vi,bi]=(name+f'#/measures/{mi}/voices/{vi}/beats/{bi}/chord/text',b['chord']['text'])
        literal_owners=[c for c in upper['owned_parameters']['source_choices'] if '/chord/text' in c['fact_ref']]
        expected_labels={ref:value for ref,value in labels.values()}
        if Counter(c['fact_ref'] for c in literal_owners)!=Counter(expected_labels.keys()):issues.append('Incomplete/duplicate literal declaration owners')
        for c in literal_owners:
            if c.get('owner')!='source_chord_annotation' or c.get('parameter')!={'symbol':expected_labels.get(c['fact_ref'])}:issues.append('Source chord literal mismatch')
        raw_groups={}
        for ref,row in expected.items():
            fields=ref.split(':');key=(int(fields[2]),int(fields[3]),F(row['onset_q']))
            raw_groups.setdefault(key,set()).add(ref)
        ordered_keys=sorted(raw_groups,key=lambda k:(k[2],k[1],k[0]))
        if len(groups)!=len(ordered_keys):issues.append('Complete source group denominator mismatch')
        for gi,g in enumerate(groups):
            if g['id']!='coattack:'+str(gi) or g['scope_type']!='coincident_written_note_starts':issues.append('Group identity/scope mismatch')
            if gi>=len(ordered_keys) or (g['part_id'],g['bar'],F(g['onset_q']))!=ordered_keys[gi]:issues.append('Group ordering/source partition mismatch')
            counts['groups']+=1
            members=g['members'];refs=[m['id'] for m in members];seen.extend(refs)
            if g['id'] in group_seen:issues.append('Duplicate group')
            group_seen.add(g['id'])
            addresses={(int(r.split(':')[2]),int(r.split(':')[3]),int(r.split(':')[4]),int(r.split(':')[5])) for r in refs}
            attached=[labels[a] for a in addresses if a in labels]
            raw=[expected[r] for r in refs]
            if set(refs)!=raw_groups.get((g['part_id'],g['bar'],F(g['onset_q']))):issues.append('Raw coattack membership mismatch')
            for member,row in zip(members,raw):
                fields=member['id'].split(':')
                if [member[k] for k in ('bar','voice','beat','note')]!=list(map(int,fields[3:])) or F(member['duration_q'])!=F(row['duration_q']):issues.append('Occurrence source address/duration mismatch')
            if any(F(r['onset_q'])!=F(g['onset_q']) for r in raw):issues.append('Source clock mismatch')
            candidates=native_interpretations(attached[0][1],profile=profile) if len(attached)==1 else []
            capo=parts[g['part_id']].get('capo');valid_capo=capo is None or (type(capo) in (int,float) and capo==0)
            known=all(r['pitch'] is not None and F(r['pitch']).denominator==1 for r in raw)
            pitches=[F(r['pitch']) for r in raw] if known else []
            eligible=len(addresses)==1 and len(candidates)==1 and valid_capo and known and all(F(r['duration_q'])>0 for r in raw) and (g['part_id'],g['bar']) not in invalid_bars
            h=candidates[0] if len(candidates)==1 else None
            if eligible:
                eligible=len({p%12 for p in pitches})>=2 and {p%12 for p in pitches}==set(h['pcs']) and (h['slash_bass_pc'] is None or min(pitches)%12==h['slash_bass_pc'])
                eligible=eligible and all(sum((p-h['root_pc']-s)%12==0 for _,s in h['degrees'])==1 for p in pitches)
            if type(g['timing_uncertain']) is not bool or g['timing_uncertain']!=((g['part_id'],g['bar']) in invalid_bars):issues.append('Source timing flag mismatch')
            selected='declared_chord_ref' in g
            counts['selected' if selected else 'fallback']+=1
            if selected!=bool(eligible):issues.append('Raw/native eligibility mismatch: '+g['id'])
            if selected:
                allowed={'id','part_id','bar','timing_uncertain','onset_q','scope_type','members','declared_chord_ref'}
                if set(g)!=allowed:issues.append('Unexpected selected group owner fields')
                if 'bass_register_anchor' in g or g['declared_chord_ref']!=attached[0][0]:issues.append('Wrong declaration/duplicate bass owner')
                for member,p in zip(members,pitches):
                    if 'voicing_interval' in member:issues.append('Duplicate interval owner')
                    if set(member)!={'id','bar','voice','beat','note','duration_q','degree_token','relative_octaves'}:issues.append('Unexpected selected member owner fields')
                    token=member.get('degree_token');octave=member.get('relative_octaves')
                    matches=[s for t,s in h['degrees'] if t==token]
                    if type(token) is not str or type(octave) is not int or len(matches)!=1 or h['root_pc']+matches[0]+12*octave!=p:issues.append('Degree equation mismatch: '+member['id'])
                    counts['degree_coordinates']+=1
            else:
                for member,r in zip(members,raw):
                    interval=member.get('voicing_interval');anchor=g.get('bass_register_anchor')
                    actual=None if interval is None or anchor is None else F(anchor)+F(interval)
                    wanted=None if r['pitch'] is None else F(r['pitch'])
                    if actual!=wanted:issues.append('Fallback pitch mismatch: '+member['id'])
        if Counter(seen)!=Counter(expected.keys()):issues.append('Incomplete/duplicate source occurrence inventory')
        if restored_tier1 is not None:
            from check_complete_source_facts import check as facts_check
            report=facts_check(capture,restored_tier1)
            if report.get('issues') or not str(report.get('status','')).startswith('PASS'):issues.append('Complete source reconstruction failed')
    except (KeyError,TypeError,ValueError,IndexError) as exc:issues.append(type(exc).__name__+': '+str(exc))
    return dict(status='PASS_INDEPENDENT_DECLARED_CHORD_OWNERSHIP' if not issues else 'FAIL',issues=issues,counts=dict(counts),scope='Conditional written chord degrees; no acoustic/root/key truth or creative permission')

