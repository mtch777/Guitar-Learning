"""Author a source-free, relational architecture fixture; not a GP decoder/inverse."""
from fractions import Fraction as F
from collections import defaultdict,Counter
from pathlib import Path
import json
from copy import deepcopy

ROOT=Path(__file__).parent

def build():
    records={}; notes=[]; rests=[]
    def add(id,tier,kind,label,inputs=(),**kw):
        assert id not in records
        records[id]=dict(tier=tier,kind=kind,label=label,inputs=list(inputs),**kw)
        return id
    bars=[];q=F(0)
    for i,n in enumerate([4,4,4,4,4,4,3,4],1):
        bars.append(dict(bar=i,start_q=str(q),duration_q=str(n),meter=[n,4]));q+=n
    tracks={'lead':dict(name='Lead guitar',tuning=[64,59,55,50,45,40]),'rhythm':dict(name='Rhythm guitar',tuning=[64,59,55,50,45,38]),'bass':dict(name='Bass',tuning=[43,38,33,26])}
    add('notation',0,'score_settings','Score settings',setting_refs=['score_meter','score_tempos','score_repeats','source_extension']+['tuning_'+t for t in tracks],status='authored normalized notation fixture; not literal GPIF')
    add('score_meter',0,'meter_settings','Bar lengths and meter',bars=bars)
    add('score_tempos',0,'tempo_settings','Tempo instructions',tempos=[dict(at_q='0',bpm=100),dict(at_q='16',bpm=80)])
    add('score_repeats',0,'repeat_settings','Repeat instructions',repeat=dict(first_bar=1,last_bar=2,additional_passes=1))
    for track,t in tracks.items():add('tuning_'+track,0,'tuning_settings',t['name']+' tuning',track=track,**t)
    add('source_extension',0,'opaque_source_field','Uninterpreted source field',property_name='fixture_extension',raw_value='uninterpreted',meaning=None,preservation='retain unchanged; do not assign musical meaning')
    def rhythm(duration):
        choices={F(4):dict(denominator=1,dots=0),F(3):dict(denominator=2,dots=1),F(2):dict(denominator=2,dots=0),F(3,2):dict(denominator=4,dots=1),F(1):dict(denominator=4,dots=0),F(3,4):dict(denominator=8,dots=1),F(1,2):dict(denominator=8,dots=0),F(1,3):dict(denominator=8,dots=0,tuplet=[3,2])}
        return choices[F(duration)]
    def note(id,track,start,duration,string,fret,voice=0,**technique):
        start,duration=F(start),F(duration);bar=next(b for b in bars if F(b['start_q'])<=start<F(b['start_q'])+F(b['duration_q']))
        raw=add('raw_'+id,0,'encoded_note',letter_octave(tracks[track]['tuning'][string-1]+fret)+' note · source fields',track=track,bar=bar['bar'],offset_q=str(start-F(bar['start_q'])),voice=voice,string_highest_is_1=string,fret=fret,rhythm=rhythm(duration),technique=deepcopy(technique))
        pitch=tracks[track]['tuning'][string-1]+fret
        add(id,1,'note',letter_octave(pitch)+' note · '+track,[raw,'score_meter','tuning_'+track],track=track,track_ref='track_'+track,voice=voice,time=dict(clock='written_q',start=str(start),duration=str(duration)),pitch_midi=pitch,letter_octave=letter_octave(pitch),pitch_spelling='display convention; source enharmonic spelling not specified',string_highest_is_1=string,fret=fret,technique=technique,bar=bar['bar'],attack=not technique.get('tie_from'),pitch_status='written pitch; sounding pitch of dead note unresolved' if technique.get('dead') else 'written base pitch')
        notes.append(id);return id
    curve=dict(time_unit='fraction_of_written_note',pitch_unit='semitones',points=[['0','0'],['1/3','2'],['2/3','2'],['1','0']])
    # One central call/answer idea and a clearly varied return.
    for label,base,returning in [('a',F(0),False),('b',F(16),True)]:
        note(label+'1','lead',base, '1/2',1,0)
        note(label+'2','lead',base+F(1,2),'1/2',1,0)
        note(label+'3','lead',base+1,'1/2',1,3)
        note(label+'4','lead',base+F(3,2),'3/2',1,7 if returning else 5,**({'vibrato':dict(kind='finger',rate_hz=None,depth_semitones=None)} if returning else {'bend':curve}))
        note(label+'5','lead',base+4,'1/2',1,0)
        note(label+'6','lead',base+F(9,2),'1/2',1,0)
        for j,fret in enumerate([3,5,7]):note(label+'t'+str(j),'lead',base+5+F(j,3),'1/3',1,fret)
        note(label+'_ending','lead',base+6,1,1,10,accent=True)
    note('hold1','lead',8,2,1,12,let_ring=True)
    note('hold2','lead',10,2,1,12,tie_from='hold1')
    note('hold3','lead',12,1,1,12,tie_from='hold2')
    note('under1','lead',8,4,4,2,voice=1,let_ring=True)
    note('under2','lead',12,4,4,2,voice=1,tie_from='under1')
    note('open1','lead','27/2','1/2',1,0,hammer_to='fretted')
    note('fretted','lead',14,'1/2',1,2,pull_to='open2')
    note('open2','lead','29/2','1/2',1,0)
    note('texture1','lead',24,'1/2',1,1)
    note('texture2','lead',24,'1/2',2,7)
    note('slide1','lead',25,'1/2',1,8,slide_to='slide2',slide_kind='legato')
    note('slide2','lead','51/2','1/2',1,10)
    note('ending','lead',27,4,1,0,let_ring=True)
    for b in bars:
        start=F(b['start_q']);length=F(b['duration_q']);bi=b['bar'];fret=5 if bi==6 else 0 if bi==7 else 2
        positions=[(start,length)] if bi in (3,4,8) else [(start,F(1)),(start+1,F(1))]
        for j,(pos,dur) in enumerate(positions):
            for string in [6,5,4]:note(f'ch{bi}_{j}_{string}','rhythm',pos,dur,string,fret,palm_mute=bi in (1,2,5,6,7))
        note('bass'+str(bi),'bass',start,length,4,fret)
    # Explicit rests complete written voice coverage; second voice exists only in bars 3-4.
    for track,voice,scope in [('lead',0,range(1,9)),('lead',1,[3,4]),('rhythm',0,range(1,9)),('bass',0,range(1,9))]:
        for bi in scope:
            bar=bars[bi-1];start=F(bar['start_q']);end=start+F(bar['duration_q']);spans=sorted(set((F(records[id]['time']['start']),F(records[id]['time']['start'])+F(records[id]['time']['duration'])) for id in notes if records[id]['track']==track and records[id]['voice']==voice and records[id]['bar']==bi));cursor=start
            for a,b in spans+[(end,end)]:
                if a>cursor:
                    id=f'rest_{track}_{voice}_{bi}_{len(rests)}';raw=add('raw_'+id,0,'written_rest',f'Written rest · bar {bi}',track=track,voice=voice,bar=bi,offset_q=str(cursor-start),rhythm=rhythm(a-cursor));add(id,1,'rest',f'{track} rest · bar {bi}',[raw,'score_meter'],track=track,track_ref='track_'+track,voice=voice,bar=bi,time=dict(clock='written_q',start=str(cursor),duration=str(a-cursor)));rests.append(id)
                cursor=max(cursor,b)
    for track in tracks:add('track_'+track,1,'track',tracks[track]['name'],['tuning_'+track],track=track,**tracks[track])
    visits=[];elapsed=F(0);playq=F(0)
    for i,bi in enumerate([1,2,1,2,3,4,5,6,7,8]):
        bar=bars[bi-1];duration=F(bar['duration_q']);bpm=100 if F(bar['start_q'])<16 else 80;seconds=duration*60/bpm
        visits.append(dict(visit=i+1,bar=bi,written_start_q=bar['start_q'],playback_start_q=str(playq),duration_q=str(duration),start_seconds=str(elapsed),duration_seconds=str(seconds),bpm=bpm));playq+=duration;elapsed+=seconds
    add('playback',1,'playback_map','Written bars ≠ playback visits',['score_meter','score_tempos','score_repeats'],visits=visits,total_written_q=str(q),total_playback_q=str(playq),total_seconds=str(elapsed))
    for at,bpm in [(0,100),(16,80)]:add('tempo'+str(at),1,'tempo_change',f'{bpm} BPM',['score_tempos'],time=dict(clock='written_q',point=str(at)),bpm=bpm)
    # Adjacent-tier relationships, each with explicit member identity.
    def rel(id,kind,label,members,**kw):
        spans=[records[n]['time'] for n in members];start=min(F(t['start']) for t in spans);end=max(F(t['start'])+F(t['duration']) for t in spans)
        return add(id,2,kind,label,members,members=members,time=dict(clock='written_q',start=str(start),duration=str(end-start)),**kw)
    rel('bend','bend','A bends up, holds, releases',['a4'],base_midi=69,peak_midi=71,curve=curve)
    rel('vibrato','vibrato','Return sustains B with vibrato',['b4'],execution='finger vibrato marking only; rate/depth unknown')
    rel('tie_high','tie_chain','E5 held across the bar line',['hold1','hold2','hold3'],note_segments=3,attacks=1,written_duration_q='5')
    rel('tie_low','tie_chain','Lower E3 held in voice 2',['under1','under2'],note_segments=2,attacks=1,written_duration_q='8')
    rel('overlap','overlap','Two voices overlap',['hold1','hold2','hold3','under1','under2'],meaning='Written spans overlap; let-ring physical release not inferred')
    rel('hammer','hammer_on','Open E → fretted F♯',['open1','fretted'],origin='open1',destination='fretted',fret_change=2)
    rel('pull','pull_off','Fretted F♯ → open E',['fretted','open2'],origin='fretted',destination='open2',fret_change=-2)
    rel('slide','slide','C5 slides to D5',['slide1','slide2'],origin='slide1',destination='slide2',kind_detail='legato')
    rel('close','coattack','Two strings, one semitone apart',['texture1','texture2'],labels=['double_stop','close_interval_texture'],pitch_distance_semitones=1)
    groups=defaultdict(list)
    for id in notes:
        n=records[id]
        if n['track']=='rhythm':groups[n['time']['start']].append(id)
    chords=[]
    for i,(start,members) in enumerate(groups.items()):chords.append(rel('power'+str(i),'coattack','Root / fifth / octave',members,labels=['power_chord'],root_midi=min(records[x]['pitch_midi'] for x in members),tonal_quality='unknown: no third encoded'))
    lead0=sorted((n for n in notes if records[n]['track']=='lead' and records[n]['voice']==0),key=lambda id:(F(records[id]['time']['start']),records[id]['pitch_midi']))
    for i,(a,b) in enumerate(zip(lead0,lead0[1:])):
        if records[a]['time']['start']!=records[b]['time']['start']:rel('step'+str(i),'interval','Neighboring written pitch steps',[a,b],semitones=records[b]['pitch_midi']-records[a]['pitch_midi'],gap_q=str(F(records[b]['time']['start'])-F(records[a]['time']['start'])-F(records[a]['time']['duration'])))
    calls=[]
    for label in ['a','b']:
        calls.append(rel('call_'+label,'call_response','Repeated E call → higher answer',[label+'1',label+'2',label+'3',label+'4'],call=[label+'1',label+'2'],answer=[label+'3',label+'4'],status='fixture-declared grouping; not detector validation'))
        rel('run_'+label,'tuplet_group','Three eighth-note triplets',[label+'t0',label+'t1',label+'t2'],ratio=[3,2])
    for label,base in [('a',F(0)),('b',F(16))]:
        members=[id for id in notes+rests if records[id]['track']=='lead' and records[id]['voice']==0 and base<=F(records[id]['time']['start'])<base+8]
        rel('phrase_'+label,'phrase_membership','Complete 2-bar occurrence: notes AND rests',members,status='fixture-declared scope; no phrase detector')
        rel('aligned_'+label,'cross_track_alignment','Lead call, rhythm and bass attack together',[label+'1','ch1_0_6' if label=='a' else 'ch5_0_6','bass1' if label=='a' else 'bass5'],relationship='same onset across three tracks; no emotional/instrument-role inference')
    for label in ['a','b']:
        calls.append(rel('call_'+label+'_second','call_response','Second E call -> triplet answer',[label+'5',label+'6',label+'t0',label+'t1',label+'t2',label+'_ending'],call=[label+'5',label+'6'],answer=[label+'t0',label+'t1',label+'t2',label+'_ending'],status='fixture-declared grouping; not detector validation'))
    # Encapsulate all T2 evidence in T3 so T4 does not bypass tiers.
    t2=list(k for k,v in records.items() if v['tier']==2)
    add('idea',3,'pattern_definition','Same call / rhythm; answer varies',calls,relative_onsets_q=['0','1/2','1','3/2','4','9/2','5','16/3','17/3','6'],durations_q=['1/2','1/2','1/2','3/2','1/2','1/2','1/3','1/3','1/3','1'],baseline_relative_pitches=[0,0,3,5,0,0,3,5,7,10],rest_pattern=[dict(start_q='3',duration_q='1'),dict(start_q='7',duration_q='1')],status='fixture-declared common shape; answer pitch/performance variation explicit',time=None)
    for label in ['a','b']:
        add('occ_'+label,3,'pattern_occurrence','A · bend response' if label=='a' else 'B · higher response + vibrato',['phrase_'+label,'call_'+label,'call_'+label+'_second','run_'+label,'bend' if label=='a' else 'vibrato'],definition='idea',members=['phrase_'+label,'call_'+label,'run_'+label],time=dict(clock='written_q',start='0' if label=='a' else '16',duration='8'),choices=dict(first_midi=64,pitch_delta_by_member_index={} if label=='a' else {'3':2}),difference='A4 bends to B4 and releases' if label=='a' else 'Written B4 with vibrato; no bend curve',status='authored occurrence')
    add('support',3,'supporting_relationships','Accompaniment, sustain and transitions',t2,members=t2,status='All lower relationship evidence retained, not an inferred instrument role')
    for id,label,start,duration in [('region_space','Sustain and transitions in bars 3-4',F(8),F(8)),('region_ending','Texture and ending in bars 7-8',F(24),F(7))]:
        selected=[key for key in t2 if start<=F(records[key]['time']['start']) and F(records[key]['time']['start'])+F(records[key]['time']['duration'])<=start+duration]
        add(id,3,'relationship_region',label,selected,members=selected,time=dict(clock='written_q',start=str(start),duration=str(duration)),status='fixture-declared region; references only contained relationships')
    for id,label,start,duration,members in [('opening','Opening / call and answer','0','8',['occ_a','idea']),('space','Held voices / open-string answer','8','8',['region_space']),('return','Varied return','16','8',['occ_b','idea']),('ending_section','Texture / ending','24','7',['region_ending'])]:
        add(id,4,'section',label,members,members=[x for x in members if x!='idea'],time=dict(clock='written_q',start=start,duration=duration),status='author-declared section, not inferred boundary')
    add('development',4,'development','Same call, different response',['idea','occ_a','occ_b'],members=['occ_a','occ_b'],time=None,retained=['call pitch','call rhythm','answer onset/durations'],changed=['answer written pitch','bend versus vibrato'],interpretation='Observed fixture contrast, not learned artist style')
    lead_attacks=[id for id in notes if records[id]['track']=='lead' and records[id]['attack']];bend_attacks=[id for id in lead_attacks if records[id]['technique'].get('bend')]
    add('bend_share',4,'scoped_statistic','Bend share · lead attacks',['support','occ_a','occ_b'],time=None,population=dict(track='lead',unit='written note attacks',exclude='tie destinations; repeat visits not counted'),numerator=len(bend_attacks),denominator=len(lead_attacks),percent=100*len(bend_attacks)/len(lead_attacks),status='Descriptive only; one synthetic passage is not an artist profile')
    add('ambiguity',4,'uncertain_interpretation','Power chords do not establish major/minor',['support'],time=None,known='Root/fifth/octave pitch content',unknown='Tonal quality / function without enough context',status='unknown, not guessed')
    cases=[dict(id='idea',title='🔁 Follow the idea',root='development',select=['development','idea','occ_a','occ_b','call_a','call_b','a1','a2','a3','a4','b1','b2','b3','b4'],explains='The same E call returns. The answer changes from a bent A to a written B with vibrato.',preserve='Exact note members, timing, initial pitch, curve and per-occurrence differences. A shared pattern does not erase exceptions.'),dict(id='performance',title='🎸 Techniques / overlapping voices',root='space',select=['space','region_space','region_ending','tie_high','tie_low','overlap','hammer','pull','slide','close','bend','vibrato','hold1','hold2','hold3','under1','under2','open1','fretted','open2','texture1','texture2','slide1','slide2','a4','b4'],explains='Notation connects actual events: tie destinations are not new attacks; two voices can overlap; techniques have physical endpoints.',preserve='Individual written segments, voice identity, string/fret, technique curves and unknown vibrato depth/rate.'),dict(id='timing',title='⏱️ Tuplets / repeats / tempo',root='playback',select=['opening','return','ending_section','occ_a','occ_b','run_a','run_b','playback','tempo0','tempo16','at0','at1','at2','bt0','bt1','bt2','notation'],explains='8 written bars produce 10 playback visits. Bar 7 is 3/4; the return slows from 100 to 80 BPM.',preserve='Exact 1/3-quarter durations, meter, repeat instructions and a separate playback-visit map.'),dict(id='evidence',title='📊 Counts / uncertainty',root='bend_share',select=['bend_share','ambiguity','support','occ_a','occ_b','bend','close']+chords[:3],explains='Statistics name their population. Repeated playback and tied segments must not inflate written attack counts.',preserve='Evidence links, denominator policy and unknown interpretations. No guessed artist or emotional meaning.')]
    data=dict(schema='illustrative-tiered-passage/3',purpose='Synthetic architecture example; not GPIF extraction, implemented inverse, detected phrases or validated music.',units=dict(written_q='exact rational quarter notes',span='[start, start+duration)',string='1 is highest',playback='separate repeat-expanded visits; exact seconds'),rules=dict(pitch='written_midi = tuning[string-1] + fret',rhythm='duration_q = 4/denominator * dot_multiplier * tuplet_denominator/tuplet_numerator',pattern='onset = occurrence.start + relative_onset; duration = pattern.duration; pitch = first_pitch + relative_pitch + occurrence_delta',bend='sounding pitch = written base + curve displacement; mark unknown physical details explicitly',tier_access='inputs references preceding tier only; every output carries prior typed records, not source blobs',limits='Same-tier descriptive links are not extra forward inputs. No inverse or variation is executed.'),cases=cases,records=records,final=dict(roots=['opening','space','return','ending_section','development','bend_share','ambiguity'],all_tiers_retained=True))
    enrich(data)
    return data

def letter_octave(p):return ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'][p%12]+'_'+str(p//12-1)

def pitch_name(p):return ['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'][p%12]+str(p//12-1)


def enrich(data):
    """Explicit illustrative lower contexts -> relationships -> enriched note views.

    No harmonic detector or inference model: key and one mode hint are declared
    fixture annotations. Chord support is actual, finite written note overlap.
    """
    R=data['records'];notes={id:r for id,r in R.items() if r['kind']=='note'}
    def add(id,tier,kind,label,inputs=(),**kw):
        assert id not in R
        R[id]=dict(tier=tier,kind=kind,label=label,inputs=list(inputs),**kw);return id
    def extent(ids):
        a=min(F(R[id]['time']['start']) for id in ids);b=max(F(R[id]['time']['start'])+F(R[id]['time']['duration']) for id in ids)
        return dict(clock='written_q',start=str(a),duration=str(b-a))
    def relation(id,kind,label,members,family,**kw):
        return add(id,2,kind,label,members,members=members,family=family,time=extent(members),**kw)
    # Lower-tier context is declared data, not an inferred answer.
    scale=[0,2,3,5,7,8,10]
    add('source_key',0,'key_annotation','Declared base key: E natural minor',tonic_pitch_class=4,reference_tonic_midi=64,mode='natural_minor',scale_semitones=scale,status='composer-declared fixture annotation; not detected from notes')
    add('source_chord_mode',0,'chord_mode_annotation','Declared E Aeolian chord-scale: first 2 beats',root_pitch_class=4,mode='aeolian',scale_semitones=scale,start_q='0',end_q='2',status='explicit fixture annotation; NOT inferred from a power chord')
    R['notation']['setting_refs']+=['source_key','source_chord_mode']
    add('layout',1,'score_layout','Resolved meter / bar layout',['score_meter'],bars=R['score_meter']['bars'])
    add('key_instruction',1,'key_instruction','E natural minor · source declaration',['source_key'],**{k:R['source_key'][k] for k in ['tonic_pitch_class','reference_tonic_midi','mode','scale_semitones','status']})
    add('mode_instruction',1,'chord_mode_instruction','E Aeolian · source-declared span',['source_chord_mode'],root_pitch_class=4,mode='aeolian',scale_semitones=scale,time=dict(clock='written_q',start='0',duration='2'),status=R['source_chord_mode']['status'])
    for id,n in notes.items():
        technique=n['technique'];normalized={}
        for key,value in technique.items():
            if value is False:continue
            normalized[key]=deepcopy(value)
        if 'bend' in technique:
            normalized['bend']={**technique['bend'],'base_midi':n['pitch_midi'],'written_duration_q':n['time']['duration'],'points_in_score':[dict(at_q=str(F(n['time']['start'])+F(p[0])*F(n['time']['duration'])),displacement_semitones=p[1],sounding_midi=str(n['pitch_midi']+F(p[1]))) for p in technique['bend']['points']]}
        n['performance_parameters']=normalized
    add('key_context',2,'key_context','Base-key context · E natural minor',['key_instruction'],family='harmony',tonic_pitch_class=4,reference_tonic_midi=64,mode='natural_minor',scale_semitones=scale,time=dict(clock='written_q',start='0',duration=R['playback']['total_written_q']),status='known as declared fixture key; identification not implemented')
    # Metric location is a useful relationship, not a carrier solely for annotations.
    for id,n in notes.items():
        bar=R['layout']['bars'][n['bar']-1];offset=F(n['time']['start'])-F(bar['start_q'])
        add('metric_'+id,2,'metrical_position',n['letter_octave']+' · position in bar',[id,'layout'],members=[id],family='rhythm',time=n['time'],bar=n['bar'],bar_offset_q=str(offset),quarter_beat_number=offset.numerator//offset.denominator+1,position='bar_start' if offset==0 else 'quarter_beat' if offset.denominator==1 else 'subdivision',accent_inference=None)
    # Chord identity comes from each simultaneous rhythm-group's actual pitches.
    groups=defaultdict(list)
    for id,n in notes.items():
        if n['track']=='rhythm':groups[n['time']['start']].append(id)
    chord_ids=[]
    for i,(start,ids) in enumerate(groups.items()):
        root=min(notes[id]['pitch_midi'] for id in ids);pcs=sorted({notes[id]['pitch_midi']%12 for id in ids});time=extent(ids)
        mode_known=F(time['start'])>=0 and F(time['start'])+F(time['duration'])<=2 and root%12==R['mode_instruction']['root_pitch_class']
        cid='chord_context_'+str(i);chord_ids.append(cid)
        add(cid,2,'chord_context',letter_octave(root)+' root · power chord',ids+(['mode_instruction'] if mode_known else []),members=ids,family='harmony',time=time,root_midi=root,root_pitch_class=root%12,pitch_classes=pcs,chord_quality='power_chord',mode=R['mode_instruction']['mode'] if mode_known else None,mode_scale_semitones=scale if mode_known else None,mode_status='source-declared chord-scale annotation' if mode_known else 'unknown: root/fifth/octave alone does not determine mode',physical_sustain_after_written_end='unknown; not extended')
    # Relations within and across voices/tracks use explicit endpoints and clocks.
    by_voice=defaultdict(lambda:defaultdict(list))
    for id,n in notes.items():by_voice[n['track'],n['voice']][n['time']['start']].append(id)
    for (track,voice),groups in by_voice.items():
        ordered=sorted(groups,key=F)
        for i,(a,b) in enumerate(zip(ordered,ordered[1:])):
            src,dst=groups[a],groups[b];gap=F(b)-max(F(notes[id]['time']['start'])+F(notes[id]['time']['duration']) for id in src)
            relation(f'next_{track}_{voice}_{i}','same_voice_successor','Next written group · '+track,src+dst,'temporal',origin_group=src,destination_group=dst,track=track,voice=voice,onset_gap_q=str(F(b)-F(a)),gap_after_previous_written_end_q=str(gap),interpretation='chronological neighbor groups, not inferred call/response')
            if len(src)==len(dst)==1 and notes[src[0]]['string_highest_is_1']==notes[dst[0]]['string_highest_is_1']:
                relation(f'fret_{track}_{voice}_{i}','same_string_transition','Same-string fret movement',src+dst,'physical',origin=src[0],destination=dst[0],fret_delta=notes[dst[0]]['fret']-notes[src[0]]['fret'],articulation='only explicit source techniques establish slide/hammer/pull')
    onset_groups=defaultdict(list)
    for id,n in notes.items():onset_groups[n['time']['start']].append(id)
    for i,(start,ids) in enumerate(sorted(onset_groups.items(),key=lambda item:F(item[0]))):
        if len(ids)>1:relation('simultaneous_'+str(i),'simultaneous_onset','Notes attacked/notated at the same onset',ids,'temporal',track_count=len({notes[id]['track'] for id in ids}),voice_count=len({(notes[id]['track'],notes[id]['voice']) for id in ids}),answer_status='simultaneous onset is not an answer to that onset')
    bass=[id for id,n in notes.items() if n['track']=='bass']
    lower_voice=[id for id,n in notes.items() if n['track']=='lead' and n['voice']==1]
    for id,n in notes.items():
        if n['track']!='lead' or n['voice']!=0:continue
        for other in bass+lower_voice:
            o=notes[other];a=max(F(n['time']['start']),F(o['time']['start']));b=min(F(n['time']['start'])+F(n['time']['duration']),F(o['time']['start'])+F(o['time']['duration']))
            if a<b:
                relation('over_'+id+'_'+other,'cross_track_overlap' if o['track']!=n['track'] else 'cross_voice_overlap','Written overlap · '+n['letter_octave']+' / '+o['letter_octave'],[id,other],'cross_track' if o['track']!=n['track'] else 'cross_voice',intersection=dict(start_q=str(a),duration_q=str(b-a)),pitch_distance_semitones=n['pitch_midi']-o['pitch_midi'],sounding_overlap='not independently validated')
    # Structured pitch coordinates distinguish tonic, chord root and mode slot.
    labels=['1','b2','2','b3','3','4','b5','5','b6','6','b7','7']
    interval_names=['unison/octave','minor second','major second','minor third','major third','perfect fourth','tritone','perfect fifth','minor sixth','major sixth','minor seventh','major seventh']
    def coordinates(pitch,root,mode=None,steps=None):
        signed=pitch-root;pc=signed%12;slot=steps.index(pc)+1 if steps and pc in steps else None
        return dict(pitch_basis='written_base',reference_midi=root,chromatic_semitones=signed,semitones_mod_12=pc,relative_octave=signed//12,chromatic_degree_label=labels[pc],interval_class_name=interval_names[pc],mode=mode,mode_degree=slot,scale_membership=None if steps is None else pc in steps,mode_status='unknown' if steps is None else 'known from explicit fixture annotation')
    for id,n in notes.items():
        start=F(n['time']['start']);end=start+F(n['time']['duration']);contexts=[cid for cid in chord_ids if F(R[cid]['time']['start'])<end and F(R[cid]['time']['start'])+F(R[cid]['time']['duration'])>start]
        boundaries=sorted({start,end}|{max(start,F(R[c]['time']['start'])) for c in contexts}|{min(end,F(R[c]['time']['start'])+F(R[c]['time']['duration'])) for c in contexts});segments=[]
        for a,b in zip(boundaries,boundaries[1:]):
            active=[c for c in contexts if F(R[c]['time']['start'])<=a and a<F(R[c]['time']['start'])+F(R[c]['time']['duration'])]
            item=dict(start_q=str(a),duration_q=str(b-a),context_ids=active)
            if not active:item.update(status='unknown: no simultaneous rhythm chord written here',alternatives=[])
            else:
                item.update(status='known written chord support; mode may remain unknown',alternatives=[dict(chord_context=c,**coordinates(n['pitch_midi'],R[c]['root_midi'],R[c]['mode'],R[c]['mode_scale_semitones']),chord_tone=n['pitch_midi']%12 in R[c]['pitch_classes']) for c in active])
            segments.append(item)
        add('harmonic_'+id,3,'note_harmonic_view',n['letter_octave']+' · key / current chord',['metric_'+id,'key_context']+contexts,note_ref=id,family='harmony',time=n['time'],interval_of_note_base_key=dict(context_id='key_context',**coordinates(n['pitch_midi'],R['key_context']['reference_tonic_midi'],R['key_context']['mode'],R['key_context']['scale_semitones'])),interval_of_note_current_chord_mode=segments,scope_note='Later-tier annotation of the same note; Tier 1 pitch/fingering are not overwritten. Bend sounding trajectory is stored separately from written-base coordinates.')
    # Computed occurrence comparison, not just a prose label saying "different".
    a=sorted((id for id in R['phrase_a']['members'] if R[id]['kind']=='note'),key=lambda id:F(R[id]['time']['start']));b=sorted((id for id in R['phrase_b']['members'] if R[id]['kind']=='note'),key=lambda id:F(R[id]['time']['start']))
    diffs=[]
    for x,y in zip(a,b):
        left,right=notes[x],notes[y];diffs.append(dict(reference_note=x,variant_note=y,written_pitch_delta=right['pitch_midi']-left['pitch_midi'],duration_ratio=str(F(right['time']['duration'])/F(left['time']['duration'])),relative_onset_delta_q=str(F(right['time']['start'])-16-F(left['time']['start'])),technique_keys_removed=sorted(set(left['performance_parameters'])-set(right['performance_parameters'])),technique_keys_added=sorted(set(right['performance_parameters'])-set(left['performance_parameters']))))
    add('variation_detail',3,'pattern_variation','Exact return differences',['phrase_a','phrase_b'],family='pattern',time=None,comparisons=diffs,status='computed fixture comparison; no generation')
    R['development']['inputs'].append('variation_detail')
    # Extend all-evidence summary and keep section evidence spatially local.
    t2=[id for id,r in R.items() if r['tier']==2];R['support']['inputs']=t2;R['support']['members']=t2
    for region in ['region_space','region_ending']:
        r=R[region];a=F(r['time']['start']);b=a+F(r['time']['duration']);ids=[id for id in t2 if R[id].get('time') and 'start' in R[id]['time'] and a<=F(R[id]['time']['start']) and F(R[id]['time']['start'])+F(R[id]['time']['duration'])<=b];r['inputs']=ids;r['members']=ids
    family_by_kind={'bend':'technique','vibrato':'technique','tie_chain':'sustain','overlap':'cross_voice','hammer_on':'technique','pull_off':'technique','slide':'technique','coattack':'pitch','interval':'pitch','call_response':'pattern','tuplet_group':'rhythm','phrase_membership':'membership','cross_track_alignment':'cross_track'}
    for r in R.values():
        if r['tier']==2:r.setdefault('family',family_by_kind.get(r['kind'],'other'))
    data['relationship_families']={family:dict(record_count=sum(r.get('family')==family and r['tier']>=2 for r in R.values()),kinds=sorted({r['kind'] for r in R.values() if r.get('family')==family and r['tier']>=2})) for family in sorted({r['family'] for r in R.values() if 'family' in r})}
    data['cases'].insert(0,dict(id='note_detail',title='🎵 Note / techniques / intervals',root='a4',select=['key_context','chord_context_1','metric_a4','harmonic_a4','a4','raw_a4','bend','source_key','source_chord_mode','score_meter','score_tempos','score_repeats','source_extension'],explains='A_4 note: encoded technique, resolved curve, base-key coordinates and current chord context. Key/mode annotations are declared for this fixture, not detected.',preserve='Written pitch and fingering, exact bend points, timing, context identity, register and unknown harmony during accompaniment rests.'))
    data['cases'].append(dict(id='relationships',title='🔗 More relationships',root='harmonic_b5',select=['harmonic_b5','key_context','metric_b5','b5','raw_b5','chord_context_8','variation_detail','development','source_extension'],explains='E_4 over a G power chord: key-relative interval differs from chord-root interval. The chord mode remains unknown. Browse relationship families below.',preserve='Endpoints, direction, track/voice, temporal overlap, context, source evidence and uncertainty—not just untyped links.'))
    data['display_label_policy']='letter_octave aliases use a documented chromatic spelling convention; a source-fret record does not claim the GP explicitly spelled that letter.'

if __name__=='__main__':
    data=build();path=ROOT/'tiered-passage.example.json';path.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'));print(json.dumps(dict(records=len(data['records']),counts=dict(Counter(r['kind'] for r in data['records'].values())),output=str(path))))
