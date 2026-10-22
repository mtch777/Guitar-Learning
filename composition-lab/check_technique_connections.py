"""Independent source/time connection checks for retained technique meanings.

Uses captured JSON and persisted relations, not detector internals. This is a
written-notation audit, not a listening or physical-execution certification.
"""
from fractions import Fraction as F
import json
from pathlib import Path


def check(documents,upper):
    issues=[];counts=dict(occurrences=0,bends=0,hp_candidates=0,slides=0,known_dynamics=0,unknown_dynamics=0,pedal_cycles=0,excluded_pedal_sections=0);examples={}
    def sample(kind,value):
        if kind not in examples:examples[kind]=value
    core=upper['musical_relationships'];events={}
    for group in core['coattacks']:
        for member in group['members']:
            events[member['id']]=dict(onset_q=group['onset_q'],duration_q=member['duration_q'])
    tracks=upper['derived_views']['techniques']['tracks']
    expected_tracks=[d['partId'] for name,d in documents.items() if name.startswith('track-')]
    actual_tracks=[t['part_id'] for t in tracks]
    if len(actual_tracks)!=len(set(actual_tracks)) or set(actual_tracks)!=set(expected_tracks):issues.append('Technique track inventory/uniqueness differs')
    note_fields={'hp','bend','slide','harmonic','harmonicFret','ghost','staccato','accentuated','tremolo','vibrato','wideVibrato','leftHandVibrato','velocity'}
    beat_fields={'palmMute','tapping','letRing','brushStroke','downStroke','upStroke','pickStroke','fadeIn','tremoloBar','vibrato','wideVibrato','leftHandVibrato','tremolo','harmonic','gradualVelocity','velocity'}
    expected_roots={}
    for name,part in documents.items():
        if not name.startswith('track-'):continue
        for mi,measure in enumerate(part.get('measures',[])):
            for vi,voice in enumerate(measure.get('voices',[])):
                for bi,beat in enumerate(voice.get('beats',[])):
                    base=f'{name}#/measures/{mi}/voices/{vi}/beats/{bi}'
                    for field in beat_fields&beat.keys():expected_roots[base+'/'+field]=beat[field]
                    for ni,note in enumerate(beat.get('notes',[])):
                        for field in note_fields&note.keys():expected_roots[base+f'/notes/{ni}/'+field]=note[field]
    actual_roots=[g['source_fact_ref'] for g in upper['owned_parameters']['technique_declarations']['groups']]
    if len(actual_roots)!=len(set(actual_roots)) or set(actual_roots)!=set(expected_roots):issues.append('Technique declaration root inventory/uniqueness differs')
    declaration_links=[]
    for group in upper['owned_parameters']['technique_declarations']['groups']:
        shape={r['id']:r for r in group['structure']}
        expected_scalars=[]
        def scalar_refs(ref,value):
            if isinstance(value,dict):
                for k,v in value.items():scalar_refs(ref+'/'+k.replace('~','~0').replace('/','~1'),v)
            elif isinstance(value,list):
                for i,v in enumerate(value):scalar_refs(ref+'/'+str(i),v)
            else:expected_scalars.append(ref)
        if group['source_fact_ref'] in expected_roots:scalar_refs(group['source_fact_ref'],expected_roots[group['source_fact_ref']])
        actual_scalars=[p['fact_ref'] for p in group['parameters']]
        if len(actual_scalars)!=len(set(actual_scalars)) or set(actual_scalars)!=set(expected_scalars):issues.append('Technique scalar inventory/uniqueness differs')
        for parameter in group['parameters']:
            row=shape[parameter['fact_ref']];value=documents[row['document']]
            for token in row['pointer'].split('/')[1:]:
                token=token.replace('~1','/').replace('~0','~')
                value=value[int(token)] if isinstance(value,list) else value[token]
            unit={'tone':50,'position':60,'precisePosition':100}.get(row['slot'],1) if group['field'] in ('bend','tremoloBar') else 1
            actual=parameter['parameter']
            if type(value) in (int,float):
                if parameter['unit']!=str(unit) or actual.get('normalized')!=str(F(str(value))/unit):issues.append('Technique normalized scalar differs from source')
            elif parameter['unit']!='1' or json.dumps(actual.get('symbol'))!=json.dumps(value):issues.append('Technique categorical declaration differs from source')
        counts[group['field']+'_persisted_declarations']=counts.get(group['field']+'_persisted_declarations',0)+1
        declaration_links.append(dict(group=group['id'],owner=group['owner_ref'],field=group['field'],source_fact_ref=group['source_fact_ref']))
    for track in upper['derived_views']['techniques']['tracks']:
        pid=track['part_id'];part=documents[f'track-{pid}.json'];raw={};beats={};history={};dynamic_expected={}
        for mi,measure in enumerate(part.get('measures',[]),1):
            for vi,voice in enumerate(measure.get('voices',[])):
                for bi,beat in enumerate(voice.get('beats',[])):
                    location=dict(bar=mi,voice=vi,beat=bi)
                    if beat.get('velocity') is not None:history[vi]=(beat['velocity'],location)
                    for ni,note in enumerate(beat.get('notes',[])):
                        if note.get('rest'):continue
                        ident=f'{pid}:{mi}:{vi}:{bi}:{ni}';raw[ident]=note;beats[ident]=beat
                        if note.get('velocity') is not None:dynamic_expected[ident]=(note['velocity'],dict(location,note=ni),'note_explicit')
                        elif vi in history:dynamic_expected[ident]=(*history[vi],'beat_explicit' if beat.get('velocity') is not None else 'inherited_explicit')
                        else:dynamic_expected[ident]=(None,None,'unspecified')
        references={r['occurrence_ref']:r for r in track['source_occurrences']}
        if len(references)!=len(track['source_occurrences']) or set(references)!=set(raw):
            issues.append(f'{pid}: occurrence inventory differs');continue
        for ident,ref in references.items():
            p,m,v,b,n=map(int,ident.split(':'));pointer=f'track-{p}.json#/measures/{m-1}/voices/{v}/beats/{b}/notes/{n}'
            event=events.get(f"event:{documents['metadata.json']['songId']}:{ident}")
            if ref['source_fact_ref']!=pointer or event is None or event['onset_q']!=ref['onset_q'] or not ref['grace'] and event['duration_q']!=ref['duration_q']:issues.append(f'{ident}: source/time link differs')
            counts['occurrences']+=1
        for ident,note in raw.items():
            for field in ('vibrato','wideVibrato','leftHandVibrato','ghost','dead','staccato','accentuated'):
                if note.get(field):
                    counts[field+'_source_declarations']=counts.get(field+'_source_declarations',0)+1
                    sample(field,dict(source_value=note[field],source=note,time=references[ident],execution='Only the source declaration is known; performed depth/speed/duration not inferred'))
            for field in ('palmMute','tapping','letRing','brushStroke','tremolo'):
                if beats[ident].get(field):sample(field,dict(source_value=beats[ident][field],time=references[ident],scope='beat declaration, not independent performed-note proof'))
        groups=track['coattack_groups']+track['relationship_details'].get('recovered_coattack_groups',[])
        for group in groups:
            ids=group['members'];notes=[raw[i] for i in ids]
            times={references[i]['onset_q'] for i in ids}
            if len(times)!=1 or group['onset_q'] not in times:issues.append('Coattack lacks common source onset')
            labels=set(group['labels']);strings=[n.get('string') for n in notes]
            pitches=[]
            for note in notes:
                string=note.get('string');fret=note.get('fret');tuning=part.get('tuning') or []
                pitches.append(None if note.get('dead') or not isinstance(string,int) or not isinstance(fret,(int,float)) or not 0<=string<len(tuning) else F(str(tuning[string]))+F(str(fret))+F(str(part.get('capo') or 0)))
            if any(p is None for p in pitches) or len(set(strings))!=len(strings):issues.append('Labeled group has unresolved pitch/string');continue
            ordered=sorted(pitches);pcs={p%12 for p in pitches};root=ordered[0];fifth={(root%12),(root+7)%12}
            if 'double_stop' in labels and len(ids)!=2:issues.append('Double stop is not exactly two strings')
            if 'close_interval_texture' in labels and (len(ids)!=2 or ordered[1]-ordered[0]!=1):issues.append('Close texture is not a half step')
            if 'power_chord' in labels and pcs!=fifth:issues.append('Power chord has non-root/fifth tones')
            if 'extended_power_chord' in labels and not (fifth<=pcs and len(pcs-fifth)==1):issues.append('Extended power chord color differs')
            for label in labels:
                counts[label+'_groups']=counts.get(label+'_groups',0)+1
                sample(label,dict(relation=group,source_notes=notes,written_pitches=list(map(str,pitches))))
        for value in track['technique_values']:
            ident=value['occurrence']
            if 'bend' not in value:continue
            source=raw[ident].get('bend');shape=value['bend'];counts['bends']+=1
            if not isinstance(source,dict):issues.append(f'{ident}: bend has no source declaration');continue
            expected=[]
            for point in source.get('points',[]):
                if 'tone' not in point or 'position' not in point and 'precisePosition' not in point:continue
                offset=F(str(point['precisePosition']))/100 if point.get('precisePosition') is not None else F(str(point['position']))/60
                expected.append((str(offset),str(F(str(point['tone']))/50)))
            actual=[(p['offset_fraction'],p['semitones']) for p in shape['points']]
            if actual!=expected:issues.append(f'{ident}: bend pitch/time units differ')
            sample('bend',dict(occurrence=ident,source=source,analysis=shape,time=references[ident]))
        for candidate in track['hopo_transition_candidates']:
            a,b=candidate['origin'],candidate['destination'];counts['hp_candidates']+=1
            if a not in raw or b not in raw:issues.append('HP endpoint absent');continue
            left,right=raw[a],raw[b]
            if not left.get('hp') or left.get('string')!=right.get('string'):issues.append(f'{a}: HP source/string conflict')
            delta=right['fret']-left['fret'];expected='hammer_on' if delta>0 else 'pull_off'
            if candidate['direction']!=expected or candidate['fret_distance']!=abs(delta):issues.append(f'{a}: HP direction/distance conflict')
            if F(references[b]['onset_q'])<=F(references[a]['onset_q']):issues.append(f'{a}: HP destination not later')
            sample('hp_'+candidate['context'],dict(relation=candidate,origin=left,destination=right,origin_time=references[a],destination_time=references[b]))
        for unresolved in track['unresolved_hp']:sample('hp_unresolved',unresolved)
        for slide in track['relationship_details']['slides']['events']:
            ident=slide['occurrence'];counts['slides']+=1
            if ident not in raw or slide['raw_value']!=raw[ident].get('slide') or slide['onset_q']!=references[ident]['onset_q']:issues.append(f'{ident}: slide lacks source/time evidence')
            dest=slide.get('destination')
            if dest is not None and dest not in raw:issues.append(f'{ident}: slide destination absent')
            if slide['status']=='exit_target_unspecified' and dest is not None:issues.append(f'{ident}: unknown slide target was invented')
            if slide['status']=='entry_origin_unspecified' and slide['origin'] is not None:issues.append(f'{ident}: unknown slide origin was invented')
            sample('slide_'+slide['status'],dict(relation=slide,source=raw[ident],time=references[ident]))
        dynamic_ids=[d['occurrence_ref'] for d in track['dynamics']]
        if len(dynamic_ids)!=len(set(dynamic_ids)) or set(dynamic_ids)!=set(raw):issues.append('Dynamic inventory/uniqueness differs')
        for dynamic in track['dynamics']:
            ident=dynamic['occurrence_ref'];provenance=dynamic['provenance']
            counts['known_dynamics' if dynamic['known'] else 'unknown_dynamics']+=1
            if ident not in raw:issues.append('Dynamic source absent');continue
            expected_raw,expected_origin,expected_provenance=dynamic_expected[ident]
            if (dynamic['raw_value'],dynamic['marking_origin'],provenance)!=(expected_raw,expected_origin,expected_provenance):issues.append(f'{ident}: dynamic history/origin differs')
            if provenance=='note_explicit' and dynamic['raw_value']!=raw[ident].get('velocity'):issues.append(f'{ident}: explicit note dynamic differs')
            if provenance=='beat_explicit' and dynamic['raw_value']!=beats[ident].get('velocity'):issues.append(f'{ident}: explicit beat dynamic differs')
            if not dynamic['known'] and dynamic['marking'] is not None:issues.append(f'{ident}: unknown dynamic assigned marking')
            sample('dynamic_'+provenance,dict(relation=dynamic,note=raw[ident],beat_velocity=beats[ident].get('velocity'),time=references[ident]))
        for section in track['approved_pedal_sections']:
            evidence=section.get('evidence',{})
            if evidence.get('accepted') is False:
                counts['excluded_pedal_sections']+=1;sample('pedal_excluded',dict(section_start=section['section_start'],reason=evidence.get('reason')))
        for phrase in track['approved_pedal_phrases']:
            for cycle in phrase['cycles']:
                counts['pedal_cycles']+=1
                if F(cycle['response_start_q'])<=F(cycle['call_start_q']):issues.append('Pedal answer not later than call')
                for key in ('call_members','response_members'):
                    if any(i not in references for i in cycle[key]):issues.append('Pedal member lacks source/time occurrence')
                sample('pedal_call_response',dict(cycle=cycle,call=[dict(note=raw[i],time=references[i]) for i in cycle['call_members']],response=[dict(note=raw[i],time=references[i]) for i in cycle['response_members']]))
    return dict(persisted_declaration_links=declaration_links,status='PASS_SOURCE_BACKED_RELATIONSHIPS' if not issues else 'FAIL',counts=counts,issues=issues,examples=examples,scope='Written source technique distinctions and source/time connections; no acoustic, emotional or generative validation')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('tier2',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    docs={q.name:json.loads(q.read_text(encoding='utf-8-sig')) for q in [a.capture/'metadata.json']+sorted(a.capture.glob('track-*.json'))}
    report=check(docs,json.loads(a.tier2.read_text(encoding='utf-8')));a.output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ('examples','persisted_declaration_links')}));raise SystemExit(0 if report['status']=='PASS_SOURCE_BACKED_RELATIONSHIPS' else 1)
