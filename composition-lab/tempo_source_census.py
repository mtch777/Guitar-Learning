"""Source-only tempo inventory and preregistered opportunity census.

This module does not change a score or implement a tempo owner/selector.
"""
from pathlib import Path
from collections import Counter,defaultdict
from fractions import Fraction as F
import argparse,hashlib,json,re


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
def escape(value):return str(value).replace('~','~0').replace('/','~1')


def raw_fields(documents):
    """Every tempo/BPM-named field, including unknown locations/types/containers."""
    result=[]
    def visit(document,value,path):
        if type(value)is dict:
            for name,child in value.items():
                childpath=path+'/'+escape(name)
                if re.search('tempo|bpm',name,re.I):result.append(dict(source_ref=document+'#'+childpath,field=name,value=child,
                    value_type='null'if child is None else type(child).__name__))
                visit(document,child,childpath)
        elif type(value)is list:
            for i,child in enumerate(value):visit(document,child,path+'/'+str(i))
    for name,value in sorted(documents.items()):visit(name,value,'')
    return result


def global_inventory(capture):
    """Filesystem boundary: retain the independent original declaration oracle."""
    from reversible_temporal import extract,encode,decode
    from check_reversible_temporal import check_observations
    docs={p.name:json.loads(p.read_bytes())for p in capture.glob('*.json')}
    result=global_inventory_documents(docs)
    result['temporal_record_inverse']=check_observations(capture,decode(encode(extract(capture))))
    return result


def global_inventory_documents(docs):
    """Connect existing verified temporal records; never default a source clock."""
    from reversible_temporal import extract_documents as extract_temporal,encode,decode,transform,interpretation_status
    from source_tie_tier1 import extract_documents
    original=extract_temporal(docs);model=encode(original);restored=decode(model)
    if restored!=original:raise ValueError('Existing temporal exact reversal failed')
    exact=dict(status='pass',counts=dict(Counter(r['kind']for r in original['records'])),unsupported=len(original['unsupported']),
        scope='Same-relationship temporal record equality; independent file oracle belongs to the capture wrapper.')
    normalized={r['id']:r for r in transform(original['records'])}
    meanings={r['id']:r for r in interpretation_status(model)}
    try:
        lower=extract_documents(docs);frames=lower['measure_geometry']['frames'];geometry_error=None
    except Exception as exc:lower=None;frames=[];geometry_error=str(exc)
    locations={};parts=[];controls=[]
    for name,part in sorted(docs.items()):
        if not name.startswith('track-'):continue
        sid=docs['metadata.json']['songId'];pid=part['partId'];parts.append(pid)
        for ai,item in enumerate((part.get('automations')or{}).get('tempo',[])):
            locations[f'tempo:part:{sid}:{pid}:{ai}']=dict(source_ref=f'{name}#/automations/tempo/{ai}',part_id=pid,raw=item,
                gradual_tempo={k:part['automations'][k]for k in('gradualTempo',)if k in part['automations']},kind='automation')
        for mi,measure in enumerate(part.get('measures',[])):
            for k,v in measure.items():
                if re.search('repeat|alternate|ending',k,re.I)and v not in(None,False,0):controls.append(dict(source_ref=f'{name}#/measures/{mi}/{escape(k)}',value=v))
            for vi,voice in enumerate(measure.get('voices',[])):
                position=F(0)
                for bi,beat in enumerate(voice.get('beats',[])):
                    if'tempo'in beat:
                        locations[f'tempo:beat:{sid}:{pid}:{mi+1}:{vi}:{bi}']=dict(source_ref=f'{name}#/measures/{mi}/voices/{vi}/beats/{bi}/tempo',part_id=pid,raw=beat['tempo'],kind='beat',bar_index=mi,position_q=str(position)if position is not None else None)
                    d=beat.get('duration')
                    if type(d)is list and len(d)==2 and all(type(x)is int for x in d)and d[0]>=0 and d[1]>0:
                        if position is not None and not beat.get('graceNote'):position+=F(*d)*4
                    else:position=None
    declarations=[]
    for record in original['records']:
        if record['kind']=='meter':continue
        location=locations[record['id']];raw=location['raw'];norm=normalized[record['id']]['fields'];reasons=list(meanings[record['id']]['reasons'])
        index=raw.get('measure')if location['kind']=='automation'else location['bar_index']
        position=norm.get('position_q',{}).get('value')if location['kind']=='automation'else location['position_q']
        if type(index)is not int or not 0<=index<len(frames):reasons.append('MISSING_OR_OUTSIDE_SOURCE_MEASURE')
        if position is None:reasons.append('MISSING_OR_UNKNOWN_SOURCE_POSITION')
        frame=frames[index]if type(index)is int and 0<=index<len(frames)else None
        onset=str(F(frame['start_q'])+F(position))if frame is not None and position is not None else None
        if frame is not None and position is not None and not 0<=F(position)<F(frame['span_q']):reasons.append('POSITION_OUTSIDE_SOURCE_BAR')
        if 'linear'in raw and type(raw['linear'])is not bool:reasons.append('UNKNOWN_LINEAR_STATE')
        gradual=location.get('gradual_tempo',{}).get('gradualTempo')
        if gradual is True:reasons.append('GRADUAL_TEMPO_EXECUTION_UNRESOLVED')
        elif gradual is not None and type(gradual)is not bool:reasons.append('UNKNOWN_GRADUAL_TEMPO_STATE')
        allowed={'bpm','type','measure','position','linear','text','visible'}if location['kind']=='automation'else{'bpm','type','linear','text','visible'}
        if set(raw)-allowed:reasons.append('UNKNOWN_TEMPO_DECLARATION_FIELD')
        declarations.append(dict(id=record['id'],**{k:v for k,v in location.items()if k!='position_q'},onset_q=onset,bar=index+1 if type(index)is int else None,position_q=position,
            quarter_bpm=norm.get('quarter_bpm',{}).get('value'),linear_state={'kind':'explicit','value':raw['linear']}if'linear'in raw else{'kind':'absent'},
            reasons=sorted(set(reasons))))
    grouped=defaultdict(list);unlocated=[]
    for row in declarations:
        if row['onset_q']is None:unlocated.append(row)
        else:grouped[F(row['onset_q'])].append(row)
    points=sorted(grouped);end=F(frames[-1]['start_q'])+F(frames[-1]['span_q'])if frames else None
    global_events=[];firstpart=min(parts)if parts else None
    for i,q in enumerate(points):
        aliases=grouped[q];bpms={a['quarter_bpm']for a in aliases};reasons={r for a in aliases for r in a['reasons']}
        if len(bpms)!=1:reasons.add('CONFLICTING_GLOBAL_BPM_DECLARATIONS')
        if unlocated:reasons.add('UNLOCATED_TEMPO_DECLARATIONS')
        bpm=next(iter(bpms))if len(bpms)==1 and None not in bpms else None
        native=[]
        if reasons:native.append('SOURCE_STEP_NOT_QUALIFIED')
        if not any(a['kind']=='automation'and a['part_id']==firstpart for a in aliases):native.append('NO_FIRST_TRACK_AUTOMATION')
        if any(a['position_q']is None or F(a['position_q'])!=0 for a in aliases):native.append('MID_BAR_NATIVE_SEMANTICS_REQUIRE_PROOF')
        if any(type(a['raw'].get('bpm'))is not int for a in aliases):native.append('NATIVE_INTEGER_BPM_ONLY')
        if points and points[0]!=0:native.append('NATIVE_INITIAL_EVENT_ORDER_RISK')
        nextq=points[i+1]if i+1<len(points)else end
        global_events.append(dict(id='global-tempo:'+str(q),onset_q=str(q),end_q=str(nextq)if nextq is not None else None,
            quarter_bpm=bpm,aliases=aliases,alias_refs=sorted(a['source_ref']for a in aliases),parts=sorted({a['part_id']for a in aliases}),
            missing_track_aliases=sorted(set(parts)-{a['part_id']for a in aliases}),bar=aliases[0]['bar'],position_q=aliases[0]['position_q'],
            meter=frames[aliases[0]['bar']-1]['signature']if aliases[0]['bar']and aliases[0]['bar']<=len(frames)else None,
            reasons=sorted(reasons),native_reasons=sorted(set(native)),incoming_bpm=global_events[-1]['quarter_bpm']if i and not global_events[-1]['reasons']else None,
            source_lifetime_q=str(nextq-q)if nextq is not None else None))
    for e in global_events:e['outgoing_bpm']=next((n['quarter_bpm']for n in global_events if n['onset_q']==e['end_q']and not n['reasons']),None)
    raw=raw_fields(docs);extra=[r for r in raw if not re.fullmatch(r'track-\d+\.json#/automations/tempo(?:/\d+/bpm)?',r['source_ref'])]
    return dict(schema='global-source-tempo-census/1',declarations=declarations,global_events=global_events,unlocated=unlocated,
        geometry_error=geometry_error,score_end_q=str(end)if end is not None else None,
        initial_gap_q=str(points[0])if points and points[0]>0 else None,extra_tempo_fields=extra,source_repeat_controls=controls,
        temporal_record_inverse=exact,unsupported_temporal_records=original['unsupported'],
        counts=dict(declarations=len(declarations),global_events=len(global_events),extra_track_aliases=len(declarations)-len(global_events)-len(unlocated),
            qualified_steps=sum(not e['reasons']for e in global_events),native_bar_start_conditions_met=sum(not e['native_reasons']for e in global_events),
            contradictory_events=sum('CONFLICTING_GLOBAL_BPM_DECLARATIONS'in e['reasons']for e in global_events),unlocated=len(unlocated),repeat_controls=len(controls),
            raw_tempo_fields=len(raw),extra_tempo_fields=len(extra)),
        scope='Written global observations and declared influence; native seconds/repeat execution not proved by this census. Each global event is one observation; all literal track aliases remain.')


def component_inventory(capture,clock):
    docs={p.name:json.loads(p.read_bytes())for p in capture.glob('*.json')}
    return component_inventory_documents(docs,clock)


def component_inventory_documents(docs,clock):
    """Exact event-entry-bar components; these are not inferred phrases."""
    from source_fact_tier1 import extract_documents as extract_facts
    from source_tie_tier1 import extract_documents
    from check_local_dynamics import inventory as dynamics
    from execution_dependencies import build
    from voicing_register import tie_relationships
    from melodic_contour_choices import NOTE_EXPRESSION,BEAT_EXPRESSION
    tier1=extract_facts(docs)
    lower=extract_documents(docs);frames={r['ordinal']:r for r in lower['measure_geometry']['frames']}
    states={r['occurrence_ref']:r for r in dynamics(tier1)['states']}
    dep=build(tier1);links=[set(e['member_refs'])for e in dep['edges']];uncertain={r for u in dep['uncertainty']for r in u['member_refs']}
    ties=tie_relationships(lower);links.extend({r['origin'],r['destination']}for r in ties['links']);uncertain.update(r['destination']for r in ties['unresolved'])
    warnings=lower['source_coverage']['layout_warnings']+lower['source_coverage']['timing_warnings']
    parts=sorted((p for name,p in docs.items()if name.startswith('track-')),key=lambda p:p['partId'])
    layout=[dict(part_id=p['partId'],instrument=p.get('instrumentId'),voices=max((len(m.get('voices',[]))for m in p.get('measures',[])),default=0))for p in parts]
    result=[]
    for ei,event in enumerate(clock['global_events']):
        bar=event['bar'];frame=frames.get(bar);components=[];context_refs=set()
        for part,shape in zip(parts,layout):
            pid=part['partId'];measure=part.get('measures',[])[bar-1]if bar is not None and 0<bar<=len(part.get('measures',[]))else None
            for vi in range(max(1,shape['voices'])):
                reasons=[];pattern=[];position=F(0);attack_count=0;hold_count=0;refs=[]
                voice=measure.get('voices',[])[vi]if measure and vi<len(measure.get('voices',[]))else None
                if frame is None:reasons.append('MISSING_SOURCE_FRAME')
                elif F(frame['span_q'])!=F(frame['signature'][0])*4/F(frame['signature'][1]):reasons.append('NONNOMINAL_SOURCE_BAR')
                if measure is None:reasons.append('MISSING_SOURCE_MEASURE')
                if any(w.get('bar')==bar and(w.get('part_id')is None or w['part_id']==pid)for w in warnings):reasons.append('SOURCE_CLOCK_QUALIFICATION')
                explicit_rest=bool(measure and measure.get('rest')or voice and voice.get('rest'))
                if voice is None and not explicit_rest:reasons.append('MISSING_SOURCE_VOICE')
                if explicit_rest and(not voice or not voice.get('beats'))and frame:
                    pattern=[dict(position_q='0',duration_q=frame['span_q'],kind='rest',grace=False,dynamics_execution=[],beat_execution={})];position=F(frame['span_q'])
                for bi,beat in enumerate(voice.get('beats',[])if voice else[]):
                    ptr=f'track-{pid}.json#/measures/{bar-1}/voices/{vi}/beats/{bi}';refs.append(ptr)
                    duration=beat.get('duration');known=type(duration)is list and len(duration)==2 and all(type(x)is int for x in duration)and duration[0]>=0 and duration[1]>0
                    q=F(*duration)*4 if known else None
                    if q is None:reasons.append('UNKNOWN_WRITTEN_DURATION')
                    notes=[(ni,n)for ni,n in enumerate(beat.get('notes',[]))if not n.get('rest')]
                    rest=explicit_rest or bool(beat.get('rest'))or bool(beat.get('notes'))and not notes
                    attack=bool(notes)and not rest and any(not n.get('tie')for _,n in notes)
                    held=bool(notes)and not rest and any(n.get('tie')for _,n in notes)
                    kind='rest'if rest else'attack_with_hold'if attack and held else'attack'if attack else'hold'if held else'empty_unknown'
                    if kind=='empty_unknown':reasons.append('UNKNOWN_EMPTY_BEAT')
                    attack_count+=attack;hold_count+=held;execution=[]
                    for ni,note in notes:
                        ref=f"event:{part['songId']}:{pid}:{bar}:{vi}:{bi}:{ni}";refs.append(ref);state=states.get(ref)
                        if state is None or not state['known']:reasons.append('UNKNOWN_WRITTEN_DYNAMICS')
                        if ref in uncertain:reasons.append('UNKNOWN_EXECUTION_ENDPOINT_OR_SCOPE')
                        execution.append(dict(dynamic=state['marking']if state else None,fields={k:note[k]for k in(*NOTE_EXPRESSION,'accentuated')if k in note}))
                    execution=[json.loads(x)for x in sorted({json.dumps(x,sort_keys=True)for x in execution})]
                    pattern.append(dict(position_q=str(position)if position is not None else None,duration_q=str(q)if q is not None else None,kind=kind,
                        grace=bool(beat.get('graceNote')),dynamics_execution=execution,beat_execution={k:beat[k]for k in BEAT_EXPRESSION if k in beat}))
                    if q is None:position=None
                    elif position is not None and not beat.get('graceNote'):position+=q
                if frame and position!=F(frame['span_q']):reasons.append('PARTIAL_OR_OVERFLOWING_SOURCE_BAR')
                activity='active_attacks'if attack_count else'held_only'if hold_count else'rest_or_empty_only'
                context=dict(layout=layout,part_id=pid,voice=vi,meter=event['meter'],event_phase_q=event['position_q'],pattern=pattern)
                components.append(dict(part_id=pid,voice=vi,activity=activity,attacks=attack_count,pattern=pattern,reasons=sorted(set(reasons)),
                    context_key=context if not reasons and attack_count else None,source_refs=refs))
                context_refs.update(refs)
        start=F(clock['global_events'][ei-1]['onset_q'])if ei else F(event['onset_q']);end=F(event['end_q'])if event['end_q']is not None else None
        closure=set(context_refs)
        for nearby in clock['global_events'][max(0,ei-1):ei+2]:closure.update(nearby['alias_refs'])
        for e in lower['events']:
            q=F(e['onset_q']);finish=q+F(e['duration_q'])
            if end is not None and(q<end and finish>start or start<=q<end):closure.add(e['id'])
        while True:
            additional=set().union(*(group for group in links if group&closure))if links else set()
            if additional.issubset(closure):break
            closure.update(additional)
        ensemble=dict(layout=layout,meter=event['meter'],event_phase_q=event['position_q'],components=[dict(part_id=c['part_id'],voice=c['voice'],pattern=c['pattern'])for c in components])
        result.append(dict(event_id=event['id'],onset_q=event['onset_q'],end_q=event['end_q'],bpm=event['quarter_bpm'],incoming_bpm=event['incoming_bpm'],outgoing_bpm=event['outgoing_bpm'],
            source_lifetime_q=event['source_lifetime_q'],global_reasons=event['reasons']+event['native_reasons'],components=components,
            ensemble_key=ensemble if not any(c['reasons']for c in components)and any(c['attacks']for c in components)else None,
            closure_start_q=str(start),closure_end_q=str(end)if end is not None else None,closure_refs=sorted(closure),
            full_influence_musical_suitability='NOT_ESTABLISHED_BY_ENTRY_BAR'))
    return dict(schema='tempo-entry-bar-components/1',events=result,scope='Every global tempo-event entry bar. Exact source components; no section/main-part inference.')


def independent(a,b):
    return a['event_id']!=b['event_id']and a['closure_end_q']is not None and b['closure_end_q']is not None and not set(a['closure_refs'])&set(b['closure_refs'])and(F(a['closure_end_q'])<=F(b['closure_start_q'])or F(b['closure_end_q'])<=F(a['closure_start_q']))


def tempo_opportunities(view):
    events=view['events'];reports={}
    def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
    for stratum in('A_passage_speed','B_transition'):
        rows=[];counts=Counter();ensemble_rows=[]
        for target in events:
            def peers(context,get_context):
                if context is None or target['global_reasons']or stratum=='B_transition'and target['incoming_bpm']is None:return[]
                return[d for d in events if not d['global_reasons']and independent(target,d)and get_context(d)==context and(stratum=='A_passage_speed'or d['incoming_bpm']==target['incoming_bpm'])]
            def evidence(donors):
                pair=next(([a['event_id'],b['event_id']]for i,a in enumerate(donors)for b in donors[i+1:]if a['bpm']!=b['bpm']and independent(a,b)),None)
                return dict(donor_event_ids=[d['event_id']for d in donors],observed_bpms=sorted({d['bpm']for d in donors},key=F),independent_contrast=pair,
                    supported_bpms=sorted({d['bpm']for d in donors},key=F)if pair else[])
            component_rows=[]
            for c in target['components']:
                def find(d):
                    return next((q['context_key']for q in d['components']if(q['part_id'],q['voice'])==(c['part_id'],c['voice'])),None)
                ev=evidence(peers(c['context_key'],find));status='UNKNOWN_OR_PARTIAL'if c['reasons']else'NO_RHYTHMIC_ATTACK_EVIDENCE'if not c['attacks']else'GLOBAL_TEMPO_UNQUALIFIED'if target['global_reasons']else'UNKNOWN_INCOMING_BPM'if stratum=='B_transition'and target['incoming_bpm']is None else'SUPPORTED_SOURCE_CONTRAST'if ev['independent_contrast']else'NO_INDEPENDENT_BPM_CONTRAST'
                row=dict(event_id=target['event_id'],part_id=c['part_id'],voice=c['voice'],status=status,activity=c['activity'],**ev);rows.append(row);component_rows.append(row);counts[status]+=1
            en=evidence(peers(target['ensemble_key'],lambda d:d['ensemble_key']));ensemble_rows.append(dict(event_id=target['event_id'],complete_ensemble_available=target['ensemble_key']is not None,**en))
            active=[r for r in component_rows if r['activity']=='active_attacks'];supported=[r for r in active if r['supported_bpms']]
            overlap=set.intersection(*(set(r['supported_bpms'])for r in supported))if supported else set()
            summary='NO_ACTIVE_COMPONENTS'if not active else'NO_SUPPORTED_COMPONENTS'if not supported else'PARTIAL_COMPONENT_SUPPORT'if len(supported)<len(active)else'COMPONENT_DISAGREEMENT'if not overlap else'ALL_ACTIVE_COMPONENTS_HAVE_SHARED_CHOICES'
            counts[summary]+=1
        reports[stratum]=dict(counts=dict(counts),component_denominator=len(rows),global_event_denominator=len(events),components=rows,ensembles=ensemble_rows,
            complete_ensemble_choice_targets=sum(bool(r['independent_contrast'])for r in ensemble_rows),
            scope='Component evidence is not full-ensemble or full-lifetime artistic acceptance. One original global event supplies one source vote.')
    return reports


def field_inventory(protocol,output):
    spec=json.loads(protocol.read_bytes());hashes=spec['source_hashes']
    if any(sha(p)!=expected for p,expected in hashes.items()):raise ValueError('Preregistered source changed')
    output.mkdir(parents=True,exist_ok=False);summary={}
    for name,entry in spec['captures'].items():
        docs={p.name:json.loads(p.read_bytes())for p in Path(entry['path']).glob('*.json')};rows=raw_fields(docs)
        patterns=Counter(re.sub(r'/\d+(?=/|$)','/*',r['source_ref'].split('#',1)[1])for r in rows)
        result=dict(source_scope=entry['scope'],raw_fields=rows,counts=dict(fields=len(rows),paths=dict(patterns)))
        dump(output/(name+'.json'),result);summary[name]=result['counts']
    if any(sha(p)!=expected for p,expected in hashes.items()):raise ValueError('Source changed during inventory')
    result=dict(status='COMPLETE_RAW_TEMPO_FIELD_INVENTORY',summary=summary,source_hashes_unchanged=True,opportunities_not_yet_counted=True)
    dump(output/'result.json',result);return result


def run_census(protocol,output):
    spec=json.loads(protocol.read_bytes());hashes=spec['source_hashes']
    if spec.get('schema')!='source-step-tempo-census-protocol/2':raise ValueError('Preregistered A/B protocol required')
    if any(sha(p)!=expected for p,expected in hashes.items()):raise ValueError('Preregistered source changed')
    own_hash=sha(Path(__file__));output.mkdir(parents=True,exist_ok=False);summary={}
    for name,entry in spec['captures'].items():
        print(name,'start',flush=True);capture=Path(entry['path'])
        clock=global_inventory(capture);components=component_inventory(capture,clock);choices=tempo_opportunities(components)
        dump(output/(name+'.json'),dict(capture_scope=entry['scope'],clock=clock,components=components,opportunities=choices))
        summary[name]=dict(clock=clock['counts'],strata={key:{k:v for k,v in value.items()if k not in('components','ensembles')}for key,value in choices.items()})
        print(name,json.dumps(summary[name]),flush=True)
    if any(sha(p)!=expected for p,expected in hashes.items())or sha(Path(__file__))!=own_hash:raise ValueError('Source or census changed during execution')
    result=dict(status='COMPLETE_PREREGISTERED_TEMPO_CENSUS',summary=summary,source_hashes_unchanged=True,census_sha256=own_hash,protocol_sha256=sha(protocol),
        scope='Observational source support only. No tempo owner, selector, changed output or musical-fit claim.')
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('protocol',type=Path);p.add_argument('output',type=Path);p.add_argument('--opportunities',action='store_true');a=p.parse_args()
    print(json.dumps((run_census if a.opportunities else field_inventory)(a.protocol,a.output),indent=2))
