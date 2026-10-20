"""Small authored catalog for a time-by-tier DATA map; not a GP analysis engine."""
import json,itertools
from pathlib import Path
from fractions import Fraction as F

ROOT=Path(__file__).parent
NAMES=['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B']
MODES={'Ionian':[0,2,4,5,7,9,11],'Dorian':[0,2,3,5,7,9,10],'Phrygian':[0,1,3,5,7,8,10],'Lydian':[0,2,4,6,7,9,11],'Mixolydian':[0,2,4,5,7,9,10],'Aeolian':[0,2,3,5,7,8,10],'Locrian':[0,1,3,5,6,8,10]}
CHORDS={'major':[0,4,7],'minor':[0,3,7],'dim':[0,3,6],'aug':[0,4,8],'sus2':[0,2,7],'sus4':[0,5,7],'7':[0,4,7,10],'maj7':[0,4,7,11],'m7':[0,3,7,10],'add9':[0,4,7,14],'power':[0,7,12],'power+color':[0,7,12,14],'semitone dyad':[0,1]}
TUNING=[64,59,55,50,45,40]
def name(p):return NAMES[p%12]+'_'+str(p//12-1)
def fingering(pitches):
    choices=[]
    for strings in itertools.permutations(range(6),len(pitches)):
        frets=[p-TUNING[s] for p,s in zip(pitches,strings)]
        if all(0<=f<=24 for f in frets):choices.append(((max(frets)-min(frets),max(frets),sum(frets)),list(zip([s+1 for s in strings],frets))))
    if not choices:raise ValueError(pitches)
    return min(choices)[1]
def coords(p,reference,mode=None):
    delta=p-reference;pc=delta%12;scale=MODES.get(mode)
    return dict(reference_midi=reference,signed_semitones=delta,semitones_mod12=pc,relative_octave=delta//12,mode=mode,mode_degree=scale.index(pc)+1 if scale and pc in scale else None,pitch_basis='written_base')
def make(id,group,label,melody=None,chords=None,mode='Aeolian',technique=None,form='AB',rest=False):
    melody=melody or [64,67,69,71,64,67,66,64]
    chords=chords or [(52,'minor','Aeolian'),(48,'major','Lydian'),(55,'major','Ionian'),(50,'major','Mixolydian')]
    R={}
    def add(id,tier,kind,value,inputs=(),start=None,duration=None,channel='main',**kw):
        assert id not in R
        R[id]=dict(tier=tier,kind=kind,value=value,inputs=list(inputs),time=None if start is None else dict(start_q=str(start),duration_q=str(duration)),channel=channel,**kw)
        return id
    add('setup0',0,'tuning','standard tuning',tracks={'melody':TUNING,'harmony':TUNING})
    add('setup1',1,'track_context','melody / harmony',['setup0'],tuning_midi=TUNING)
    add('key0',0,'key_instruction','E · '+mode,root_midi=64,mode=mode,scale_semitones=MODES[mode],status='declared_fixture')
    add('key1',1,'key_context','E · '+mode,['key0'],root_midi=64,mode=mode,scale_semitones=MODES[mode])
    add('key2',2,'scale','E '+mode,['key1'],scale_semitones=MODES[mode])
    note_ids=[];relation_ids=[];chord_rel=[]
    for i,(root,quality,localmode) in enumerate(chords):
        pitches=[root+x for x in CHORDS[quality]];fingers=fingering(pitches);members=[]
        for j,(pitch,(string,fret)) in enumerate(zip(pitches,fingers)):
            raw=f'c{i}_{j}_0';n=f'c{i}_{j}_1';add(raw,0,'encoded_note',name(pitch),start=i*2,duration=2,channel='harmony',track='harmony',string=string,fret=fret,rhythm=dict(denominator=2),techniques={});add(n,1,'note',name(pitch),[raw,'setup0'],start=i*2,duration=2,channel='harmony',track='harmony',pitch_midi=pitch,letter_octave=name(pitch),string=string,fret=fret,techniques={});members.append(n)
        add('mode'+str(i)+'_0',0,'mode_instruction',localmode or '?',mode=localmode,scale_semitones=MODES.get(localmode),scope_q=[str(i*2),str(i*2+2)],status='declared_fixture' if localmode else 'unknown')
        add('mode'+str(i)+'_1',1,'mode_context',localmode or '?',['mode'+str(i)+'_0'],mode=localmode,scale_semitones=MODES.get(localmode),scope_q=[str(i*2),str(i*2+2)])
        cid='ch'+str(i);chord_rel.append(cid)
        add(cid,2,'chord',NAMES[root%12]+' '+quality,members+['mode'+str(i)+'_1'],start=i*2,duration=2,channel='harmony',root_midi=root,pitch_members=pitches,quality=quality,mode=localmode,mode_status='declared_fixture' if localmode else 'unknown',members=members)
    for i,pitch in enumerate(melody):
        start=F(i);duration=F(1);raw=f'n{i}_0';nid=f'n{i}_1';rid=f'n{i}_2';effects={}
        if technique:
            kind=technique['kind'];at=technique.get('at',2)
            if i==at:effects={kind:{k:v for k,v in technique.items() if k not in ('kind','at')}}
        if rest and i==3:
            add(raw,0,'encoded_rest','rest',start=start,duration=duration,channel='melody',rhythm=dict(denominator=4));add(nid,1,'rest','rest',[raw],start=start,duration=duration,channel='melody',track='melody');add(rid,2,'rest_relation','silence',[nid],start=start,duration=duration,channel='melody');relation_ids.append(rid);continue
        string,fret=fingering([pitch])[0]
        # Fretted technique examples explicitly keep the same string.
        if technique and technique['kind'] in ('hammer','pull','slide') and i in (0,1):string,fret=1,pitch-64
        add(raw,0,'encoded_note',name(pitch),start=start,duration=duration,channel='melody',track='melody',string=string,fret=fret,rhythm=dict(denominator=4),techniques=effects)
        add(nid,1,'note',name(pitch),[raw,'setup0'],start=start,duration=duration,channel='melody',track='melody',letter_octave=name(pitch),pitch_midi=pitch,string=string,fret=fret,techniques=effects,attack=not(kind=='tie' and i==at) if technique else True)
        chord=R[chord_rel[i//2]];key=coords(pitch,64,mode);ch=coords(pitch,chord['root_midi'],chord['mode'])
        degree=key['mode_degree'];cdegree=ch['mode_degree'];value='K'+(str(degree) if degree else '∉')+' / C'+(str(cdegree) if cdegree else '?' if ch['mode'] is None else '∉')
        add(rid,2,'note_relations',value,[nid,'key1','mode'+str(i//2)+'_1']+chord['members'],start=start,duration=duration,channel='melody',note_ref=nid,chord_ref=chord_rel[i//2],interval_of_note_base_key=key,interval_of_note_current_chord_mode=ch,chord_tone=pitch%12 in {p%12 for p in chord['pitch_members']},previous_ref=note_ids[-1] if note_ids else None,technique=effects)
        note_ids.append(nid);relation_ids.append(rid)
    for k,(start,ids) in enumerate([(0,relation_ids[:4]),(4,relation_ids[4:])]):
        pitches=[R[R[x]['note_ref']]['pitch_midi'] if R[x].get('note_ref') else None for x in ids];base=next(p for p in pitches if p is not None);relative=[p-base if p is not None else None for p in pitches]
        defid='def'+str(k);add(defid,3,'pattern_definition',('A' if k==0 else 'B')+' · '+','.join(str(x) if x is not None else 'rest' for x in relative),ids,relative_pitches=relative,relative_onsets_q=['0','1','2','3'],status='authored_fixture')
        add('p'+str(k),3,'phrase',('A' if k==0 else 'A′' if form=='AA′' else 'B'),ids,start=start,duration=4,definition_ref=defid,first_pitch_midi=base,members=ids)
    add('harmonic_series',3,'progression',' → '.join(R[x]['value'] for x in chord_rel),chord_rel,chords=chord_rel)
    add('song',4,'form',form,['p0','p1','harmonic_series'],start=0,duration=8,members=['p0','p1'],progression_ref='harmonic_series')
    return dict(id=id,group=group,label=label,fixture=True,key=dict(root='E',mode=mode),duration_q='8',meter=[4,4],records=R)
def build():
    cases=[make('ab','A/B','E minor · i–VI–III–VII · A/B',technique=dict(kind='bend',at=2,points=[['0','0'],['1/2','2'],['1','0']],pitch_unit='semitones',time_unit='fraction_of_note'))]
    techniques=[dict(kind='bend',at=2,points=[['0','0'],['1/2','2'],['1','0']],pitch_unit='semitones',time_unit='fraction_of_note'),dict(kind='hammer',at=0,destination_index=1),dict(kind='pull',at=0,destination_index=1),dict(kind='slide',at=0,destination_index=1,type='legato'),dict(kind='vibrato',at=2,rate_hz=None,depth_semitones=None),dict(kind='palm_mute',at=2,enabled=True),dict(kind='dead',at=2,sounding_pitch=None),dict(kind='ghost',at=2,enabled=True),dict(kind='tie',at=1,origin_index=0),dict(kind='let_ring',at=2,release_time=None)]
    for t in techniques:
        melody=[64,66,67,69,64,66,67,64] if t['kind']=='hammer' else [66,64,67,69,66,64,67,64] if t['kind']=='pull' else [66,69,67,69,66,69,67,64] if t['kind']=='slide' else [64,64,67,69,64,64,67,64] if t['kind']=='tie' else None
        cases.append(make('tech_'+t['kind'],'Techniques',t['kind'].replace('_',' '),melody=melody,technique=t))
    for quality in CHORDS:cases.append(make('chord_'+quality,'Chords','E '+quality,chords=[(52,quality,None)]*4))
    for mode,scale in MODES.items():
        quality='dim' if scale[4]==6 else 'minor' if scale[2]==3 else 'major';cases.append(make('mode_'+mode,'Modes','E '+mode,melody=[64+x for x in scale]+[76],chords=[(52,quality,mode)]*4,mode=mode))
    progressions=[('minor descending',[(52,'minor','Aeolian'),(50,'major','Mixolydian'),(48,'major','Lydian'),(47,'minor','Phrygian')]),('major I–V–vi–IV',[(52,'major','Ionian'),(59,'major','Mixolydian'),(49,'minor','Aeolian'),(57,'major','Lydian')]),('power roots',[(40,'power',None),(43,'power',None),(50,'power',None),(40,'power',None)])]
    for i,(label,chords) in enumerate(progressions):cases.append(make('progression_'+str(i),'Progressions',label,chords=chords,melody=[64,68,69,71,64,68,66,64] if i==1 else None,mode='Ionian' if i==1 else 'Aeolian'))
    for label,melody in [('stepwise',[64,66,67,69,71,69,67,64]),('leaps',[64,71,67,76,64,74,71,64]),('chromatic',[64,65,66,67,69,68,67,64])]:cases.append(make('melody_'+label,'Melodies',label,melody=melody))
    cases.append(make('aa','A/B','A → A′',melody=[64,67,69,71,64,67,69,74],form='AA′'))
    cases.append(make('rest','A/B','A · pause → B',rest=True))
    return dict(schema='time-tier-map/1',fixture=True,units=dict(time='exact rational quarter notes',string='1=highest',mode='declared fixture context, not inferred'),cases=cases)
if __name__=='__main__':
    data=build();(ROOT/'tier-map.examples.json').write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'));print(len(data['cases']),'cases')
