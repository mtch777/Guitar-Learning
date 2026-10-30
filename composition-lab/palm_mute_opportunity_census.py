"""Strict source opportunity count only; no palm-muting intervention."""
from collections import Counter,defaultdict
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import argparse,hashlib,json


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def declaration(beat):
    if 'palmMute'not in beat:return dict(kind='absent')
    if type(beat['palmMute'])is bool:return dict(kind='explicit',value=beat['palmMute'])
    return dict(kind='unknown',value=deepcopy(beat['palmMute']))


def inventory(tier1):
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    from check_local_accents import inventory as raw_note_context
    from execution_dependencies import build
    from voicing_register import tie_relationships
    from melodic_contour_choices import NOTE_EXPRESSION,BEAT_EXPRESSION,SAFE_BEAT,SAFE_NOTE
    docs=project_documents(tier1);lower=extract_documents(docs)
    events={r['id']:r for r in lower['events']};states={r['occurrence_ref']:r for r in raw_note_context(tier1)['occurrences']}
    pinned=set(build(tier1)['pinned_members']);ties=tie_relationships(lower)
    for link in ties['links']:pinned.update((link['origin'],link['destination']))
    pinned.update(r['destination']for r in ties['unresolved'])
    raw={};streams=defaultdict(list);bybeat=defaultdict(list)
    for name,part in sorted(docs.items()):
        if not name.startswith('track-'):continue
        for bar,measure in enumerate(part.get('measures',[]),1):
            for voice,v in enumerate(measure.get('voices',[])):
                for bi,beat in enumerate(v.get('beats',[])):
                    path=f'{name}#/measures/{bar-1}/voices/{voice}/beats/{bi}'
                    index=len(streams[part['partId'],voice]);streams[part['partId'],voice].append(path)
                    for ni,note in enumerate(beat.get('notes',[])):
                        if note.get('rest'):continue
                        ref=f"event:{part['songId']}:{part['partId']}:{bar}:{voice}:{bi}:{ni}"
                        raw[ref]=dict(part=part,beat=beat,note=note,path=path,stream_index=index,voice=voice,rest=bool(measure.get('rest')or v.get('rest')or beat.get('rest')))
                        bybeat[path].append(ref)
    groups=defaultdict(list)
    for e in events.values():groups[e['part_id'],F(e['onset_q'])].append(e)
    rows=[]
    for (pid,onset),members in sorted(groups.items()):
        members.sort(key=lambda e:(e['voice'],e['beat'],e['note'],e['id']))
        refs=[e['id']for e in members];reasons=set();part=raw[refs[0]]['part'];closure=set(refs);beats={};shape=[]
        flags=(docs['metadata.json'].get('tracks')or[])
        if type(part.get('instrumentId'))is not int or not 24<=part['instrumentId']<=39 or pid<len(flags)and flags[pid].get('isVocalTrack'):
            reasons.add('OUTSIDE_GUITAR_BASS_SCOPE')
        for e in members:
            ref=e['id'];r=raw[ref];note=r['note'];state=states.get(ref);beats[r['path']]=r['beat']
            if r['rest']:reasons.add('SOURCE_REST_CONTAINER')
            if set(note)-SAFE_NOTE or set(r['beat'])-SAFE_BEAT:reasons.add('UNKNOWN_SOURCE_DECLARATION')
            if any(k in note and note[k]is not None and note[k]is not False for k in NOTE_EXPRESSION)or any(
                k!='palmMute'and k in r['beat']and r['beat'][k]is not None and r['beat'][k]is not False for k in BEAT_EXPRESSION):
                reasons.add('OTHER_EXECUTION_DECLARATION')
            if e['pitch']is None or F(e['pitch']).denominator!=1:reasons.add('UNKNOWN_WRITTEN_PITCH')
            if F(e['duration_q'])<=0:reasons.add('NONPOSITIVE_WRITTEN_DURATION')
            if type(note.get('string'))is not int or type(note.get('fret'))is not int or note['fret']<0:reasons.add('UNKNOWN_PHYSICAL_SHAPE')
            if state is None:reasons.add('MISSING_SOURCE_CONTEXT')
            else:reasons.update(state['reasons'])
            if ref in pinned:reasons.add('INCIDENT_EXECUTION_DEPENDENCY')
            lane=streams[pid,e['voice']];i=r['stream_index']
            for path in lane[max(0,i-1):i+2]:closure.add(path);closure.update(bybeat[path])
            shape.append(dict(voice=e['voice'],pitch=e['pitch'],duration_q=e['duration_q'],string=note.get('string'),fret=note.get('fret'),
                meter=None if state is None else state['source_meter'],position_q=None if state is None else state['position_q'],
                dynamic=None if state is None else state['dynamic_marking'],note_notation=deepcopy(note)))
        if set(refs)&{r for path in beats for r in bybeat[path]}!={r for path in beats for r in bybeat[path]}:
            reasons.add('INCOMPLETE_SOURCE_BEAT')
        if closure&pinned:reasons.add('NEIGHBOR_EXECUTION_DEPENDENCY')
        declarations=[dict(beat_ref=path,state=declaration(beat))for path,beat in sorted(beats.items())]
        states_pm=[r['state']for r in declarations]
        if any(s['kind']=='unknown'for s in states_pm):reasons.add('UNKNOWN_PALM_MUTE_DECLARATION');mode='unknown'
        else:
            on=[s['kind']=='explicit'and s['value']is True for s in states_pm]
            mode='on'if all(on)else'off'if not any(on)else'mixed'
            if mode=='mixed':reasons.add('MIXED_MUTED_AND_UNMUTED_COATTACK')
        context=dict(part_id=pid,notes=shape,beat_notation=[dict(voice=next(events[r]['voice']for r in refs if raw[r]['path']==path),
            fields={k:deepcopy(v)for k,v in beat.items()if k not in('notes','palmMute')})for path,beat in sorted(beats.items())])
        rows.append(dict(coattack_ref=f'coattack:{pid}:{onset}',part_id=pid,onset_q=str(onset),
            end_q=str(max(F(e['onset_q'])+F(e['duration_q'])for e in members)),member_refs=refs,beat_refs=sorted(beats),
            closure_refs=sorted(closure),declarations=declarations,mute_mode=mode,reasons=sorted(reasons),
            context_key=None if reasons else context))
    return dict(schema='source-palm-mute-opportunity-census/1',raw_note_occurrences=len(raw),located_note_occurrences=len(events),
        unlocated_note_refs=sorted(set(raw)-set(events)),coattacks=rows,
        scope='Written declaration opportunities only; absence is not verified unmuted execution')


def independent(a,b):
    return set(a['closure_refs']).isdisjoint(b['closure_refs'])and not(F(a['onset_q'])<F(b['end_q'])and F(b['onset_q'])<F(a['end_q']))


def opportunities(view):
    contexts=defaultdict(list)
    for row in view['coattacks']:
        if row['context_key']is not None:contexts[encoded(row['context_key'])].append(row)
    pairs=[];targets=[]
    for group in contexts.values():
        on=[r for r in group if r['mute_mode']=='on'];off=[r for r in group if r['mute_mode']=='off']
        pairs.extend([a['coattack_ref'],b['coattack_ref']]for a in on for b in off if independent(a,b))
        for target in group:
            donors=[r for r in group if independent(target,r)]
            witness=next(([a['coattack_ref'],b['coattack_ref']]for a in donors if a['mute_mode']=='on'for b in donors if b['mute_mode']=='off'and independent(a,b)),None)
            if witness:targets.append(dict(target_ref=target['coattack_ref'],witness_pair=witness,
                donor_refs=[r['coattack_ref']for r in donors],source_modes=sorted({r['mute_mode']for r in donors})))
    rows=view['coattacks'];literals=Counter()
    for r in rows:
        for d in r['declarations']:
            s=d['state'];literals['absent'if s['kind']=='absent'else'explicit_true'if s==dict(kind='explicit',value=True)else'explicit_false'if s==dict(kind='explicit',value=False)else'unknown']+=1
    return dict(counts=dict(raw_note_occurrences=view['raw_note_occurrences'],unlocated_notes=len(view['unlocated_note_refs']),coattacks=len(rows),
        eligible=sum(not r['reasons']for r in rows),all_modes=dict(Counter(r['mute_mode']for r in rows)),
        eligible_modes=dict(Counter(r['mute_mode']for r in rows if not r['reasons'])),declaration_states=dict(literals),
        independent_on_off_pairs=len(pairs),leave_target_out_opportunities=len(targets),refusals=dict(Counter(q for r in rows for q in r['reasons']))),
        independent_pairs=pairs,targets=targets)


def run(protocol,output):
    from source_fact_tier1 import extract
    specification=json.loads(protocol.read_bytes());hashes=specification['hashes']
    if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Preregistered source/code changed')
    output.mkdir(parents=True,exist_ok=False);summary={}
    for name,entry in specification['captures'].items():
        print(name,'start',flush=True);view=inventory(extract(Path(entry['path'])));result=opportunities(view)
        dump(output/(name+'.json'),dict(capture_scope=entry['scope'],inventory=view,opportunities=result));summary[name]=dict(scope=entry['scope'],**result['counts'])
        print(name,json.dumps(result['counts']),flush=True)
    if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Source/code changed during census')
    result=dict(status='COMPLETE_PREREGISTERED_DEVELOPMENT_CENSUS',summary=summary,
        no_intervention_implemented=True,no_audible_or_style_claim=True)
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('protocol',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.protocol,a.output)
