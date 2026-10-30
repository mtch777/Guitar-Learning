"""Independent raw scope, written GP, performed clock and renderer-reference QA.

No tempo selection or musical generation occurs here. The native counterfactual
shares the pinned renderer; mathematical clocks, caps and complete field locks
are additional independent checks, not a claim of artistic or physical truth.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import hashlib,json,math,re,sys,zipfile
import xml.etree.ElementTree as ET

from source_fact_tier1 import extract,extract_documents,project_documents
from source_tie_tier1 import extract_documents as located_documents
from check_accent_artifacts import _fidelity
from check_dynamic_artifacts import read,sha
from check_voicing_artifacts import canonical_ids,differences,audio


def tempo_inventory(before):
    docs=project_documents(before)
    located=located_documents(docs);frames=located['measure_geometry']['frames']
    groups={};tracks=[n for n in docs if re.fullmatch(r'track-\d+\.json',n)]
    for name in tracks:
        for i,event in enumerate(docs[name].get('automations',{}).get('tempo',[])):
            if set(event)!={'measure','position','bpm','type'} or type(event['measure'])is not int or event['measure']<0 or event['measure']>=len(frames) or type(event['position'])not in(int,float) or event['position']!=0 or type(event['type'])is not int or event['type']!=4 or type(event['bpm'])is not int or event['bpm']<=0:
                raise ValueError('Initial native scope requires explicit integer quarter-BPM bar-start steps; unknown fields remain unsupported')
            key=event['measure'];groups.setdefault(key,[]).append((name,i,event))
    if 0 not in groups:raise ValueError('Explicit initial tempo required; no invented default')
    marks=[]
    for measure,rows in sorted(groups.items()):
        if len(rows)!=len(tracks) or len({n for n,_,_ in rows})!=len(tracks) or len({e['bpm']for _,_,e in rows})!=1:
            raise ValueError('Every track must agree on every global tempo alias')
        refs=[f'{n}#/automations/tempo/{i}'for n,i,_ in rows]
        frame=frames[measure]
        marks.append(dict(bar=measure+1,onset_q=frame['start_q'],bpm=rows[0][2]['bpm'],alias_refs=refs))
    return docs,marks,frames


def source_scope(before,after,demo):
    docs,marks,frames=tempo_inventory(before);expected=deepcopy(docs);target=demo['target'];chosen=demo['chosen']
    selected=[m for m in marks if F(m['onset_q'])==F(target['onset_q'])]
    if len(selected)!=1:raise ValueError('Unique original global tempo target required')
    mark=selected[0];refs=target['alias_refs']
    if len(refs)!=len(set(refs)) or set(refs)!=set(mark['alias_refs']) or target['bpm_refs']!=[r+'/bpm'for r in refs]:raise ValueError('Incomplete target tempo alias scope')
    if target['bar']!=mark['bar'] or F(target['position_q'])!=0 or F(target['quarter_bpm'])!=mark['bpm']:raise ValueError('Declared target tempo or source time differs')
    index=marks.index(mark);end=marks[index+1]['onset_q']if index+1<len(marks)else F(frames[-1]['start_q'])+F(frames[-1]['span_q'])
    if F(target['end_q'])!=F(end):raise ValueError('Target lifetime must end at next explicit source declaration')
    bpm=F(chosen['quarter_bpm'])
    if bpm.denominator!=1 or bpm<=0:raise ValueError('Integer positive native quarter-BPM required')
    for ref in refs:
        match=re.fullmatch(r'(track-\d+\.json)#/automations/tempo/(\d+)',ref)
        if not match:raise ValueError('Original tempo declaration pointer required')
        name,i=match.groups();expected[name]['automations']['tempo'][int(i)]['bpm']=int(bpm)
    if extract_documents(expected)!=after:raise ValueError('Inverse changed a field outside the complete global BPM aliases')
    component=re.fullmatch(r'part:(\d+):voice:(\d+)',target['component_ref'])
    if not component or target['evidence_label']!='PARTIAL':raise ValueError('Explicit partial component evidence required')
    return dict(docs=docs,changed_docs=expected,marks=marks,frames=frames,bar=mark['bar'],onset_q=mark['onset_q'],end_q=str(F(end)),
        before_bpm=mark['bpm'],after_bpm=int(bpm),part=int(component[1]),position_q='0',literal_changed=before!=after)


def check_source(before,after,demo):
    try:
        s=source_scope(before,after,demo)
        return dict(status='PASS_INDEPENDENT_STEP_TEMPO_SOURCE_SCOPE',issues=[],bar=s['bar'],before_bpm=s['before_bpm'],after_bpm=s['after_bpm'],artist_fit_validated=False)
    except Exception as e:return dict(status='FAIL',issues=[str(e)],artist_fit_validated=False)


def performed_ledger(marks,visits,quarter_ticks):
    """Replay explicit marks on every visit; absent marks carry performed tempo."""
    bybar={m['bar']:m['bpm']for m in marks};tempo=None;end=F(0);seconds=F(0);rows=[];events=[]
    for v in visits:
        start,stop=F(v['start']),F(v['end'])
        if start!=end or stop<=start:raise ValueError('Performed bar clocks are not a contiguous positive sequence')
        if v['bar']in bybar:
            tempo=F(bybar[v['bar']]);events.append(dict(tick=str(start),bpm=str(tempo)))
        if tempo is None:raise ValueError('No performed initial tempo')
        finish=seconds+(stop-start)/quarter_ticks*60/tempo
        rows.append(dict(bar=v['bar'],start=str(start),end=str(stop),bpm=str(tempo),start_seconds=str(seconds),end_seconds=str(finish)))
        seconds=finish;end=stop
    return dict(bars=rows,events=events,total_seconds=str(seconds))


def seconds_at(ledger,tick,quarter_ticks):
    tick=F(tick)
    if tick<0:raise ValueError('Negative performed tick unsupported')
    rows=ledger['bars'];row=next((r for r in rows if F(r['start'])<=tick<F(r['end'])),rows[-1])
    if tick<F(row['start']):raise ValueError('Tick outside performed clock')
    return F(row['start_seconds'])+(tick-F(row['start']))/quarter_ticks*60/F(row['bpm'])


def tempo_at_ledger(ledger,tick):
    row=next((r for r in ledger['bars']if F(r['start'])<=F(tick)<F(r['end'])),None)
    if row is None:raise ValueError('Note origin outside performed bars')
    return F(row['bpm'])


def native_model_scope(original,counterfactual,bar,before,after):
    expected=deepcopy(original);autos=expected['masterbars'][bar-1]['tempoautomations']
    if len(autos)!=1 or autos[0]['ratioposition']!=0 or autos[0]['value']!=before:raise ValueError('Unique exact bar-start native tempo required')
    autos[0]['value']=after
    if expected!=counterfactual:raise ValueError('Counterfactual native model contains a hidden non-tempo edit')


def canonical_model(model):
    """Rename imported chord UUIDs and their references together; retain topology."""
    model=deepcopy(model)
    for track in model.get('tracks',[]):
        for staff in track.get('staves',[]):
            chords=staff.get('chords',{});mapping={key:f'chord:{i}'for i,key in enumerate(chords)}
            staff['chords']={mapping[key]:value for key,value in chords.items()}
            for bar in staff.get('bars',[]):
                for voice in bar.get('voices',[]):
                    for beat in voice.get('beats',[]):
                        key=beat.get('chordid')
                        if key in(None,''):continue
                        if key not in mapping:raise ValueError('Native chord reference has no declaration')
                        beat['chordid']=mapping[key]
    return model


def verify_source_geometry(model,visits,frames,quarter_ticks):
    """Bind native written positions and every performed bar span to source time."""
    masters=model['masterbars']
    if len(masters)!=len(frames) or any(F(m['start'])!=F(f['start_q'])*quarter_ticks for m,f in zip(masters,frames)):
        raise ValueError('Native written bar starts differ from source geometry')
    for v in visits:
        if type(v['bar'])is not int or not 1<=v['bar']<=len(frames):raise ValueError('Native visit has no source bar identity')
        if F(v['end'])-F(v['start'])!=F(frames[v['bar']-1]['span_q'])*quarter_ticks:
            raise ValueError('Performed bar length differs from source geometry')


def gp_scope(before,changed,bar,old,new):
    result=deepcopy(changed);before_tempo=before.findall('./MasterTrack/Automations/Automation');after_tempo=result.findall('./MasterTrack/Automations/Automation')
    if len(before_tempo)!=len(after_tempo):raise ValueError('GP automation inventory changed')
    matches=[]
    for i,(a,b)in enumerate(zip(before_tempo,after_tempo)):
        if a.findtext('Type')=='Tempo' and a.findtext('Bar')==str(bar-1) and F(a.findtext('Position'))==0:matches.append((i,a,b))
    if len(matches)!=1:raise ValueError('Unique target GP tempo required')
    _,a,b=matches[0]
    if a.findtext('Value')!=f'{old} 2' or b.findtext('Value')!=f'{new} 2':raise ValueError('Actual GP target tempo value differs')
    b.find('Value').text=a.findtext('Value')
    if differences(before,result):raise ValueError('GP changed outside the selected tempo value')


def verify_clock(case,trace,marks,quarter_ticks):
    visits=trace['performed_bars'];ledger=performed_ledger(marks,visits,quarter_ticks)
    points={}
    for event in case['events']:
        if event['kind']!='TempoChangeEvent':continue
        d=event['data'];tick,bpm=F(d['tick']),F(str(d['beatsPerMinute']))
        if bpm<=0 or points.setdefault(tick,bpm)!=bpm:raise ValueError('Ambiguous native simultaneous tempo')
    if points!={F(e['tick']):F(e['bpm'])for e in ledger['events']}:raise ValueError('Actual performed tempo/reset map differs from source instructions')
    for v,row in zip(visits,ledger['bars']):
        if any(F(str(c['tempo']))!=F(row['bpm']) or F(c['tick'])!=F(row['start']) for c in v['tempo_changes']):raise ValueError('Native bar tempo differs from independent performed ledger')
        for k in('start_seconds','end_seconds'):
            if not math.isclose(v[k],float(F(row[k])),abs_tol=1e-8,rel_tol=1e-10):raise ValueError('Native seconds differ from rational performed clock')
    for origin in trace['note_calls']:
        if F(str(origin['tempo']))!=tempo_at_ledger(ledger,origin['beat_start']):raise ValueError('Native note received tempo before its actual influence interval')
    for call in trace['callbacks']:
        for k,tick in(('start_seconds',call['start']),('end_seconds',call['start']+call['length'])):
            if not math.isclose(call[k],float(seconds_at(ledger,tick,quarter_ticks)),abs_tol=1e-8,rel_tol=1e-10):raise ValueError('Native note seconds differ from global clock')
    return ledger


def verify_caps(trace,timing):
    count=0;split=0
    for call in trace['callbacks']:
        info=call['execution'];kind=info.get('cap_kind')if info else None
        if not kind:continue
        if kind not in('dead','palm_mute'):raise ValueError('Unknown native cap kind')
        if info['split_execution']:
            split+=1;continue  # Complete exact counterfactual still required; no simple-cap claim.
        constant=timing['dead_constant'if kind=='dead'else'palm_mute_constant']
        expected=min(F(info['beat_duration']),int(F(str(info['tempo']))*constant/timing['position_scale']))-F(info['brush_offset'])
        if F(call['length'])!=expected:raise ValueError('Native cap duration does not satisfy the independent equation')
        count+=1
    return dict(independently_checked_caps=count,split_executions_requiring_full_reference=split)


def native_scope(cases,supp,scope):
    timing=supp['timing'];qt=timing['quarter_ticks']
    traces={name:dict(t,model=canonical_model(t['model']))for name,t in supp['cases'].items()}
    reference=dict(supp['counterfactual'],model=canonical_model(supp['counterfactual']['model']))
    if any(cases[k]['midi_tick_shift']!=0 for k in cases):raise ValueError('Leading negative grace shift needs a separately proved clock mapping')
    if any(cases['source'][k]!=cases['zero'][k]for k in('notes','beats','callbacks','events')) or traces['source']!=traces['zero']:raise ValueError('Source/exact-zero native result differs')
    if cases['zero']['notes']!=cases['changed']['notes'] or cases['zero']['beats']!=cases['changed']['beats']:raise ValueError('Written note/beat fields changed')
    if len(cases['zero']['callbacks'])!=len(cases['changed']['callbacks']) or any({k:v for k,v in a.items()if k!='length'}!={k:v for k,v in b.items()if k!='length'}for a,b in zip(cases['zero']['callbacks'],cases['changed']['callbacks'])):
        raise ValueError('Tempo operation changed played attack count, pitch, tick onset, velocity or channel; this execution is outside the admitted artifact scope')
    native_model_scope(traces['source']['model'],reference['model'],scope['bar'],scope['before_bpm'],scope['after_bpm'])
    if reference['model']!=traces['changed']['model']:raise ValueError('Actual native model differs from sole-tempo counterfactual')
    if any(reference[k]!=traces['changed'][k]for k in('callbacks','events','origins','note_calls','performed_bars')):raise ValueError('Actual complete MIDI/origins differ from sole-tempo counterfactual')
    written={name:[{k:v for k,v in b.items()if k in('bar','start','end')}for b in t['performed_bars']]for name,t in traces.items()}
    if written['source']!=written['zero'] or written['zero']!=written['changed']:raise ValueError('Performed quarter clocks or visits changed')
    if 'frames'in scope:
        verify_source_geometry(traces['source']['model'],written['source'],scope['frames'],qt)
    ledgers={};caps={}
    for name,c in cases.items():
        t=traces[name]
        if t['events']!=c['events'] or len(t['origins'])!=len(c['events']):raise ValueError('Supplement event stream differs from independent native snapshot')
        callbacks=[{k:v for k,v in call.items()if k not in('execution','start_seconds','end_seconds')}for call in t['callbacks']]
        if callbacks!=c['callbacks']:raise ValueError('Supplement callbacks differ from independent snapshot')
        marks=deepcopy(scope['marks'])
        if name=='changed':next(m for m in marks if m['bar']==scope['bar'])['bpm']=scope['after_bpm']
        ledgers[name]=verify_clock(c,t,marks,qt);caps[name]=verify_caps(t,timing)
    old,new=ledgers['zero']['bars'],ledgers['changed']['bars'];affected=[(a,b)for a,b in zip(old,new)if a['bpm']!=b['bpm']]
    if not affected:raise ValueError('No performed tempo changed')
    first=F(affected[0][0]['start'])
    if [e for e in cases['zero']['events']if F(e['data']['tick'])<first]!=[e for e in cases['changed']['events']if F(e['data']['tick'])<first]:raise ValueError('MIDI changed before the first tempo influence')
    return dict(ledgers=ledgers,cap_checks=caps,affected_performed_bars=[a['bar']for a,_ in affected],
        exact_counterfactual_midi=True,shared_renderer_limit='Reference and actual output use the same pinned renderer; physical expression is not independently proven')


def capture_binding(qa,plan):
    hashes=plan['source_hashes']
    if not hashes:raise ValueError('Complete source capture hash inventory required')
    source=Path(next(iter(hashes))).parent
    if {Path(p).name for p in hashes}!={p.name for p in source.glob('*.json')} or any(Path(p).parent!=source or sha(p)!=h for p,h in hashes.items()):raise ValueError('Source capture inventory/hash changed')
    before=extract(source);zero=extract(qa/'zero-capture');after=extract(qa/'changed-capture')
    if before!=zero or read(qa/'zero-isolated/worker/output.json')!=zero or read(qa/'changed-isolated/worker/output.json')!=after:raise ValueError('Actual worker/capture binding differs')
    return source,before,after


def pcm_frame_clock(frames,nominal_seconds,sample_rate,micro_buffer):
    ideal=F(nominal_seconds)*sample_rate
    minimum=math.ceil(ideal/micro_buffer)*micro_buffer
    # Native export stops at microbuffer boundaries. One additional microbuffer
    # permits inclusive-end/floating boundary comparison, not arbitrary padding.
    if frames%micro_buffer or not minimum<=frames<=minimum+micro_buffer:raise ValueError('PCM frame count differs from source-bar seconds and native buffer quantization')


def render_scope(root,qa,cases,scope,ledgers,micro_buffer):
    demo=read(qa/'demonstration.json');renders=read(root/'audio-jobs.results.json');jobs=read(root/'audio-jobs.json')
    expected={(n,v)for n in cases for v in('focused','ensemble')}
    if len(jobs)!=6 or len(renders)!=6 or {(j['method'],j['mode'])for j in jobs}!=expected or {(r['method'],r['mode'])for r in renders}!=expected or len({r['font_sha256']for r in renders})!=1:raise ValueError('Complete six-render evidence required')
    jobmap={(j['method'],j['mode']):j for j in jobs};waves={};measurements=[]
    for r in renders:
        name,mode=r['method'],r['mode'];job=jobmap[name,mode];file=root/name/(mode+'.wav')
        if any(r.get(k)!=v for k,v in job.items()) or Path(job['file']).resolve()!=(root/name/'score.gp').resolve() or Path(job['out']).resolve()!=file.resolve():raise ValueError('Audio job/file binding differs')
        if r['gp_sha256']!=cases[name]['gp_sha256'] or r['midi_event_sha256']!=cases[name]['midi_event_sha256'] or r['audio_sha256']!=sha(file) or 'fixed .3 gain'not in r['renderer'] or not 0<r['peak']<1:raise ValueError('Audio renderer provenance/gain differs')
        if (r['track'],r['start_bar'],r['end_bar'],r['target_bar'])!=(scope['part'],demo['clip']['first'],demo['clip']['last'],scope['bar']) or F(r['target_offset_q'])!=0:raise ValueError('Audio source passage differs')
        rows=ledgers[name]['bars'];start=next(i for i,b in enumerate(rows)if b['bar']==job['start_bar']);end=next(i for i,b in enumerate(rows)if i>=start and b['bar']==job['end_bar'])
        cue=next(b for b in rows[start:end+1]if b['bar']==scope['bar'])
        if r['playback_range']!={'startTick':int(F(rows[start]['start'])),'endTick':int(F(rows[end]['end']))}:raise ValueError('Rendered native source-bar range differs')
        target_seconds=F(cue['start_seconds'])-F(rows[start]['start_seconds'])
        if not math.isclose(r['target_seconds'],float(target_seconds),abs_tol=1e-8,rel_tol=1e-10):raise ValueError('Audio cue seconds differ from rational source-bar clock')
        pcm,sr=audio(file);waves[name,mode]=pcm
        if sr!=44100 or not pcm or abs(r['seconds']-len(pcm)/sr)>1e-9 or any(abs(x)>=32767 for x in pcm):raise ValueError('PCM duration, sample rate or clipping differs')
        nominal=F(rows[end]['end_seconds'])-F(rows[start]['start_seconds'])
        pcm_frame_clock(len(pcm),nominal,sr,micro_buffer)
        measurements.append(dict(method=name,mode=mode,frames=len(pcm),source_bar_seconds=str(nominal),rendered_seconds=r['seconds'],renderer_padding_seconds=r['seconds']-float(nominal)))
    changes=[]
    for mode in('focused','ensemble'):
        source,zero,changed=(waves[n,mode]for n in('source','zero','changed'))
        if source!=zero:raise ValueError('Source/zero PCM differs')
        n=max(len(zero),len(changed));delta=sum(((zero[i]if i<len(zero)else 0)-(changed[i]if i<len(changed)else 0))**2 for i in range(n))
        changes.append(dict(mode=mode,source_zero_exact=True,before_frames=len(zero),after_frames=len(changed),pcm_difference_measured=zero!=changed,
            zero_padded_delta_rms=math.sqrt(delta/n)/32768,comparison='Same source bars; different real-time duration is permitted'))
    return dict(measurements=measurements,comparisons=changes,pcm_difference_measured=any(r['pcm_difference_measured']for r in changes))


def check(root,qa,*,fidelity_scope='gp_with_exact_model_bends'):
    root,qa=Path(root),Path(qa);issues=[];detail={}
    try:
        snapshot=read(root/'dynamic-native-snapshot.json');supp=read(root/'step-tempo-native-supplement.json');demo=read(qa/'demonstration.json');plan=read(qa/'plan.json')
        if snapshot['schema']!='native-dynamic-snapshot/1' or snapshot['fidelity_scope']!=fidelity_scope or set(snapshot['cases'])!={'source','zero','changed'}:raise ValueError('Complete native snapshot required')
        if supp['schema']!='native-step-tempo-supplement/1' or supp['shared_snapshot']!={'file':'dynamic-native-snapshot.json','sha256':sha(root/'dynamic-native-snapshot.json')} or supp['source_scope']!={'file':'tempo-source-scope.json','sha256':sha(root/'tempo-source-scope.json')} or supp['adapter_sha256']!=sha(Path(__file__).with_name('audit_step_tempo_gp.mjs')):raise ValueError('Tempo native reference binding changed')
        module=Path(snapshot['module_path'])
        if sha(module)!=snapshot['module_sha256'] or sha(module.with_name('alphaTab.core.mjs'))!=snapshot['core_sha256'] or snapshot['snapshot_script_sha256']!=sha(Path(__file__).with_name('audit_dynamic_gp.mjs')):raise ValueError('Native runtime/snapshot dependency changed')
        if plan['policy']!=demo['controls']['context_policy']:raise ValueError('Policy/demonstration binding differs')
        source,before,after=capture_binding(qa,plan);scope=source_scope(before,after,demo)
        declared=read(root/'tempo-source-scope.json')
        if declared!={k:v for k,v in scope.items()if k not in('docs','changed_docs')}:raise ValueError('Native audit source scope differs from independent derivation')
        if not scope['literal_changed']:raise ValueError('An actual tempo intervention is required; zero is a separate baseline')
        core=module.with_name('alphaTab.core.mjs').read_text(encoding='utf-8');timing=supp['timing']
        if set(timing)!={'quarter_ticks','dead_constant','palm_mute_constant','position_scale'}:raise ValueError('Known native timing parameters required')
        for key,symbol in(('quarter_ticks','QuarterTime'),('dead_constant','_defaultDurationDead'),('palm_mute_constant','_defaultDurationPalmMute'),('position_scale','MaxPosition')):
            values=re.findall(r'static\s+'+symbol+r'\s*=\s*(\d+)\s*;',core)
            if len(values)!=1 or type(timing[key])is not int or timing[key]!=int(values[0]):raise ValueError('Native cap/quarter parameters differ')
        cases=snapshot['cases'];trees={};assets={};inventories={};companions={};fidelity=[]
        folders={'source':source,'zero':qa/'zero-capture','changed':qa/'changed-capture'}
        for name,c in cases.items():
            out=root/name;fidelity.append(dict(method=name,**_fidelity(out,c,fidelity_scope,snapshot)))
            if sha(out/'score.gp')!=c['gp_sha256'] or c['capture_hashes']!={p.name:sha(p)for p in folders[name].glob('*.json')}:raise ValueError('Actual GP/capture snapshot binding differs')
            profile=out/'score.playback.json'
            if (read(profile)if profile.exists()else{})!=c['playback_profile']:raise ValueError('Playback profile changed')
            side=out/'score.exact-model-bends.json'
            if (sha(side)if side.exists()else None)!=c['sidecar_sha256']:raise ValueError('Bend companion hash changed')
            companions[name]=None
            if side.exists():
                data=read(side)
                if data['gp_sha256']!=c['gp_sha256']:raise ValueError('Bend companion not bound to actual GP')
                companions[name]={k:v for k,v in data.items()if k!='gp_sha256'}
            with zipfile.ZipFile(out/'score.gp')as z:
                names=z.namelist();gpif=[n for n in names if n.endswith('.gpif')]
                if len(names)!=len(set(names)) or len(gpif)!=1:raise ValueError('Unique complete native GP archive required')
                inventories[name]=set(names);trees[name]=ET.fromstring(z.read(gpif[0]));canonical_ids(trees[name]);assets[name]={n:z.read(n)for n in names if n!=gpif[0]}
            if len(c['notes'])!=len(trees[name].find('Notes')) or len({n['native_ref']for n in c['notes']})!=len(c['notes']):raise ValueError('Complete unique native note denominator required')
            raw=c['raw_midi_json']
            if hashlib.sha256(raw.encode()).hexdigest()!=c['midi_event_sha256'] or json.loads(raw)!=[e['data']for e in c['events']]:raise ValueError('Complete MIDI stream/hash differs')
            expected=Counter({(i,k):1 for i in range(len(c['callbacks']))for k in('NoteOnEvent','NoteOffEvent')})
            if Counter((e['binding'],e['kind'])for e in c['events']if e['binding']is not None)!=expected:raise ValueError('MIDI callback/event coverage differs')
            for e in c['events']:
                i=e['binding']
                if i is None:continue
                call=c['callbacks'][i];d=e['data']
                if (d['track'],d['channel'],d['noteKey'],d['noteVelocity'])!=(call['track'],call['channel'],call['key'],call['velocity']) or d['tick']!=call['start']+(call['length']if e['kind']=='NoteOffEvent'else 0):raise ValueError('Paired MIDI event differs from actual callback')
        for collection in(inventories,assets,companions):
            if collection['source']!=collection['zero'] or collection['zero']!=collection['changed']:raise ValueError('GP archive inventory/assets or bend companion changed')
        if any(c['playback_profile']!=cases['source']['playback_profile']for c in cases.values()) or differences(trees['source'],trees['zero']):raise ValueError('Source/zero GP or playback settings differ')
        gp_scope(trees['zero'],trees['changed'],scope['bar'],scope['before_bpm'],scope['after_bpm'])
        buffers=re.findall(r'static\s+MicroBufferSize\s*=\s*(\d+)\s*;',core)
        if len(buffers)!=1:raise ValueError('Pinned native audio buffer size unavailable')
        proof=native_scope(cases,supp,scope);renders=render_scope(root,qa,cases,scope,proof['ledgers'],int(buffers[0]))
        detail=dict(artifact_fidelity=fidelity,before_bpm=scope['before_bpm'],after_bpm=scope['after_bpm'],bar=scope['bar'],native_note_count=len(cases['source']['notes']),
            midi_attack_counts={n:len(c['callbacks'])for n,c in cases.items()},**proof,audio=renders,pcm_difference_measured=renders['pcm_difference_measured'])
    except Exception as exc:issues.append(str(exc))
    result=dict(status='FAIL'if issues else'PASS_NATIVE_STEP_TEMPO_PCM_CHANGED'if detail['pcm_difference_measured']else'PASS_NATIVE_STEP_TEMPO_PCM_IDENTICAL',issues=issues,**detail,
        evidence_label='PARTIAL',listening_judgment=None,artist_fit_validated=False)
    (root/'step-tempo-artifact-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    result=check(*sys.argv[1:3]);print(json.dumps(result,indent=2));raise SystemExit(result['status']=='FAIL')
