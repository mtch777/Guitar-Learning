"""Private source explorer: stratified examples, not a musical confidence classifier."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import shutil
from source_semantics import seconds_between
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pedal_dialogue import note_roles

CATEGORIES={
 'regular':('One low note, the same answer each time','Neighboring calls and replies repeat their pitches and rhythm.'),
 'varied':('Same pedal, changing answers','The anchor burst repeats while the following answer changes.'),
 'interval':('Two notes acting as the pedal','The returning anchor contains two pitches rather than one.'),
 'long_answer':('Short pedal bursts, long replies','The response spans at least twice as long as the call.'),
 'short_answer':('Long pedal bursts, short replies','The response spans at most half as long as the call.'),
 'rhythm':('Same reply notes, different rhythm','Response pitches repeat but their timing changes.'),
 'polyphony':('Chords or double stops answering the pedal','The response contains simultaneous notes; no single melody is invented.'),
 'close':('Half-step pairs answering the pedal','A response includes a two-pitch semitone collection, using written pitches.'),
 'overlap':('Pedal keeps ringing under the reply','The anchor’s written sustain overlaps the response.'),
 'subdivision':('Triplets and other uneven rhythms','The excerpt includes exact thirds or other non-binary note durations.'),
 'mixed':('Pedal and reply played together','At least one attack combines anchor and other notes, outside the pure call/response labels.'),
 'minimal':('Barely enough repeats to establish a pedal','The region contains only two operational exchanges: sparse evidence, not a confidence claim.'),
 'censored':('Unclear where the pedal pattern ends','No anchor-only return closes this exchange. A mixed/unknown attack or the analysis boundary can interrupt it; this is not a claimed phrase ending.'),
}


def demonstrates_return(pair):
    """A selected example must actually show a call, reply and returning call."""
    return (len(pair)==2 and pair[0].get('closed_by_anchor_return',False)
            and F(pair[0]['call']['start_q']) < F(pair[1]['call']['start_q']))


def kinds(region,pair):
    a=pair[0];out=[];response=a['response'];call=a['call']
    if len(pair)>1:
        b=pair[1]
        same_call=all(call[k]==b['call'][k] for k in ('pitch_signature','rhythm_signature'))
        same_pitch=response['pitch_signature']==b['response']['pitch_signature']
        same_rhythm=response['rhythm_signature']==b['response']['rhythm_signature']
        if same_call and same_pitch and same_rhythm:out.append('regular')
        if same_call and not(same_pitch and same_rhythm):out.append('varied')
        if same_pitch and not same_rhythm:out.append('rhythm')
    if len(region['anchor_pitches'])==2:out.append('interval')
    ratio=F(a['response_to_call_span_ratio'])
    if ratio>=2:out.append('long_answer')
    if ratio<=F(1,2):out.append('short_answer')
    if any(c['response']['note_texture']!='monophonic' for c in pair):out.append('polyphony')
    if any(c['response']['semitone_dyad_attacks'] for c in pair):out.append('close')
    if any(F(c['call_sustain_into_response_q'])>0 for c in pair):out.append('overlap')
    if any(F(d).denominator & (F(d).denominator-1) for c in pair for role in ('call','response') for d in c[role]['notated_duration_histogram']):out.append('subdivision')
    start=F(a['call']['start_q']);end=F(pair[-1]['response']['end_q'])
    if any(e['kind']=='mixed' and start<=F(e['onset_q'])<end for e in region['events']):out.append('mixed')
    if len(region['cycles'])==2 and not region.get('related_anchor_continues'):out.append('minimal')
    if any(c['right_censored'] for c in pair):out.append('censored')
    return out


def build(report,dialogues,corpus,out):
    out.mkdir(exist_ok=False);songs={s['song_id']:s for s in report['songs']};candidates=defaultdict(list)
    eligible={}
    for item in dialogues:
        sid=item['song_id'];song=songs[sid];folder=corpus/str(sid)
        quality=json.loads((folder/'gp7-validation.json').read_text(encoding='utf-8-sig'))
        if song['ai_generated'] is not False or song['is_junk'] is not False or not quality.get('roundtripPass'):continue
        track=next(t for t in song['tracks'] if t['part_id']==item['part_id']);byid={n['occurrence']:n for n in track['rows']}
        eligible[sid,item['part_id']]=(song,track)
        for region in item['dialogues']:
            region=dict(region)
            region['related_anchor_continues']=any(F(other['scope_start_q'])==F(region['scope_end_q']) and
                (set(other['anchor_pitches'])<=set(region['anchor_pitches']) or set(region['anchor_pitches'])<=set(other['anchor_pitches']))
                for other in item['dialogues'] if other is not region)
            for i,cycle in enumerate(region['cycles']):
                pair=region['cycles'][i:i+2]
                if not demonstrates_return(pair):continue
                members=[byid[n] for c in pair for n in c['call_members']+c['response_members']]
                if not members:continue
                first=min(n['bar'] for n in members);last=max(n['bar'] for n in members)
                if last-first>5:continue
                start=max(1,first-1);end=min(len(song['shared_layout']),last+1)
                base=F(song['shared_layout'][start-1]['start_q']);limit=F(song['shared_layout'][end-1]['start_q'])+F(song['shared_layout'][end-1]['span_q'])
                seconds=seconds_between(base,limit,song['timeline'])
                if seconds is None or not 4<=seconds<=25:continue
                if any(sum(v['bar']==b for v in song['playback']['order'])!=1 for b in range(start,end+1)):continue
                entry=dict(song_id=sid,part_id=item['part_id'],start_bar=start,end_bar=end,base_q=str(base),end_q=str(limit),
                           anchor=region['anchor_pitches'],cycles=pair,events=region['events'],section_start=region['section_start'])
                for category in kinds(region,pair):candidates[category].append(entry)
    selected=[];used=Counter();windows=[];missing=[]
    # Rare families first so abundant regular examples cannot consume their songs.
    for category in sorted(CATEGORIES,key=lambda k:len(candidates[k])):
        choices=sorted(candidates[category],key=lambda c:(used[songs[c['song_id']]['candidate_work_family']],c['end_bar']-c['start_bar'],c['song_id'],c['start_bar']))
        chosen=None
        for c in choices:
            family=songs[c['song_id']]['candidate_work_family']
            if used[family]>=2:continue
            if any(sid==c['song_id'] and not(c['end_bar']<a or c['start_bar']>b) for sid,a,b in windows):continue
            chosen=c;break
        if chosen is None:missing.append(category);continue
        selected.append(dict(chosen,category=category));used[songs[chosen['song_id']]['candidate_work_family']]+=1
        windows.append((chosen['song_id'],chosen['start_bar'],chosen['end_bar']))
    selected.sort(key=lambda c:list(CATEGORIES).index(c['category']))
    cases=[];jobs=[]
    for selection in selected:
        song,track=eligible[selection['song_id'],selection['part_id']]
        ident=f'example-{len(cases)+1:02d}';base=F(selection['base_q']);limit=F(selection['end_q'])
        note_roles={n:role for c in selection['cycles'] for role in ('call','response') for n in c[role+'_members']}
        # A simultaneous attack can contain both pedal and answer. Preserve the
        # group-level observation, but color individual notes by membership.
        event_roles={ident:role for e in selection['events']
                     for ident,role in note_roles(e['notes'],selection['anchor']).items()}
        notes=[]
        for n in track['rows']:
            start=F(n['onset_q']);end=start+F(n['duration_q'])
            if n['midi'] is None or not(start<limit and end>base):continue
            role=event_roles.get(n['occurrence'],note_roles.get(n['occurrence'],'context'))
            if role=='unknown':role='context'
            if n['tie_destination'] and n['midi'] in selection['anchor']:role='call_sustain'
            notes.append(dict(id=n['occurrence'],pitch=n['midi'],bar=n['bar'],string=n['string'],fret=n['fret'],
                              start=seconds_between(base,max(start,base),song['timeline']),end=seconds_between(base,min(end,limit),song['timeline']),
                              duration_q=n['duration_q'],onset_q=n['onset_q'],role=role))
        points=sorted({base,limit}|{F(t['onset_q']) for t in song['timeline']['tempo'] if base<F(t['onset_q'])<limit})
        time_map=[dict(seconds=seconds_between(base,q,song['timeline']),x=float((q-base)/(limit-base)*960)) for q in points]
        gp=out/(ident+'.gp');shutil.copyfile(corpus/str(song['song_id'])/'score.gp',gp)
        cases.append(dict(id=ident,category=selection['category'],heading=CATEGORIES[selection['category']][0],explanation=CATEGORIES[selection['category']][1],
                          song=song['title'],track=track['name'] or f"Track {track['part_id']+1}",start_bar=selection['start_bar'],end_bar=selection['end_bar'],
                          song_id=song['song_id'],source_sha256=hashlib.sha256(gp.read_bytes()).hexdigest(),anchor=selection['anchor'],
                          base_q=selection['base_q'],end_q=selection['end_q'],
                          notes=notes,time_map=time_map,cycles=selection['cycles'],seconds=seconds_between(base,limit,song['timeline']),
                          caveat='Listen for whether the highlighted pedal and replies match what you hear. The excerpt may include surrounding material.'))
        ti=next(i for i,t in enumerate(song['tracks']) if t['part_id']==selection['part_id'])
        for mode in ('context','focused'):
            jobs.append(dict(case_id=ident,method='unchanged_source',mode=mode,file=str(gp.resolve()),track=ti,
                             start_bar=selection['start_bar'],end_bar=selection['end_bar'],target_bar=selection['start_bar'],target_offset_q='0',out=str((out/(ident+'.'+mode+'.wav')).resolve())))
    old_root=corpus.parent.parent
    outside=[('pedal-revision-v1','case-09','outside_arpeggio','An arpeggio, not a pedal','Previously reviewed as an arpeggio-like chord cycle rather than a pedal. The current rule abstains.'),
             ('pedal-revision-v1','case-05','outside_chords','Changing chords, not a pedal','Previously reviewed as chord playing without an alternating pedal/response relationship.'),
             ('pedal-fresh-v2','case-01','outside_single_departure','Repeated low notes, but only one reply','Previously accepted as not enough recurring departures and returns to form a pedaling section.')]
    for directory,old_id,category,heading,explanation in outside:
        root=old_root/directory
        if not (root/'cases.json').exists():continue
        old=next(c for c in json.loads((root/'cases.json').read_text(encoding='utf-8')) if c['id']==old_id)
        song=songs[old['song_id']];base=F(old['base_q']);limit=F(old['end_q']);ident=f'example-{len(cases)+1:02d}'
        gp=out/(ident+'.gp');shutil.copyfile(root/(old_id+'.gp'),gp)
        for mode in ('context','focused'):shutil.copyfile(root/(old_id+'.'+mode+'.wav'),out/(ident+'.'+mode+'.wav'))
        notes=[dict(id=n['occurrence'],pitch=n['midi'],bar=n['bar'],string=n['string'],fret=n['fret'],
                    start=seconds_between(base,max(base,F(n['onset_q'])),song['timeline']),end=seconds_between(base,min(limit,F(n['onset_q'])+F(n['duration_q'])),song['timeline']),
                    onset_q=n['onset_q'],duration_q=n['duration_q'],role='context') for n in old['notes']]
        points=sorted({base,limit}|{F(t['onset_q']) for t in song['timeline']['tempo'] if base<F(t['onset_q'])<limit})
        cases.append(dict(id=ident,category=category,heading=heading,explanation=explanation,song=old['title'],track=old['track'],
                          start_bar=old['start_bar'],end_bar=old['end_bar'],song_id=old['song_id'],source_sha256=hashlib.sha256(gp.read_bytes()).hexdigest(),
                          base_q=str(base),end_q=str(limit),anchor=[],notes=notes,cycles=[],time_map=[dict(seconds=seconds_between(base,q,song['timeline']),x=float((q-base)/(limit-base)*960)) for q in points],
                          caveat='Prior human-reviewed contrast example, not a universal rule about arpeggios or chord playing.'))
    (out/'cases.json').write_text(json.dumps(cases,separators=(',',':')),encoding='utf-8')
    (out/'render-jobs.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    manifest=dict(cases=len(cases),categories=[c['category'] for c in cases],unavailable_categories=missing,source_families=len({songs[c['song_id']]['candidate_work_family'] for c in cases}),
                  sampling='Selective breadth examples from non-AI/non-junk detailed-roundtrip-pass sources; not population estimates.')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for name in ('dialogue-explorer.html','dialogue-explorer.js'):
        shutil.copyfile(Path(__file__).parents[2]/name,out/('index.html' if name.endswith('.html') else name))
    print(json.dumps(manifest))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);p.add_argument('dialogues',type=Path);p.add_argument('corpus',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Source excerpts stay private')
    build(json.loads(a.report.read_text(encoding='utf-8')),json.loads(a.dialogues.read_text(encoding='utf-8')),a.corpus,a.out)
