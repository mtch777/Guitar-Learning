"""Independent source-scope, complete native GP/MIDI and PCM mute audit.

This does not certify the donor sampler or artistic suitability. It validates
the actual inverse output, whole same-part coattack and its playback footprint.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import hashlib,json,math,re,sys,zipfile
import xml.etree.ElementTree as ET

from source_fact_tier1 import extract,extract_documents,project_documents
from source_tie_tier1 import extract_documents as located_documents
from check_accent_artifacts import _fidelity
from check_dynamic_artifacts import _gp_beat,read,sha
from check_voicing_artifacts import canonical_ids,differences,audio

POLICY='source_local_palm_mute'


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def source_beat(docs,ref):
    match=re.fullmatch(r'(track-\d+\.json)#/measures/(\d+)/voices/(\d+)/beats/(\d+)',ref)
    if not match:raise ValueError('Original source beat reference required')
    name,bar,voice,beat=match.groups()
    return docs[name]['measures'][int(bar)]['voices'][int(voice)]['beats'][int(beat)]


def state(beat):
    if 'palmMute'not in beat:return dict(kind='absent')
    if type(beat['palmMute'])is not bool:raise ValueError('Unknown typed source mute state')
    return dict(kind='explicit',value=beat['palmMute'])


def source_scope(before,after,demo):
    """Rebuild the declared raw change; no selector/owner implementation used."""
    docs=project_documents(before);expected=deepcopy(docs);target=demo['target'];chosen=demo['chosen']
    refs=target['beat_refs'];states=chosen['states']
    if not refs or refs!=sorted(set(refs))or len(states)!=len(refs):raise ValueError('Complete ordered beat/state scope required')
    declarations=[dict(beat_ref=r,state=state(source_beat(docs,r)))for r in refs]
    if declarations!=target['declarations']:raise ValueError('Demonstration mute declarations differ from source')
    for ref,wanted in zip(refs,states):
        beat=source_beat(expected,ref)
        if wanted=={'kind':'absent'}:beat.pop('palmMute',None)
        elif type(wanted)is dict and set(wanted)=={'kind','value'}and wanted['kind']=='explicit'and type(wanted['value'])is bool:beat['palmMute']=wanted['value']
        else:raise ValueError('Known optional mute state required')
    if extract_documents(expected)!=after:raise ValueError('Inverse changed a source field outside target mute declarations')
    located=located_documents(docs);events=located['events'];byref={e['id']:e for e in events}
    members=target['member_refs']
    if not members or len(members)!=len(set(members))or any(r not in byref for r in members):raise ValueError('Original coattack members required')
    first=byref[members[0]];pid=first['part_id'];onset=F(first['onset_q'])
    complete=sorted((e for e in events if e['part_id']==pid and F(e['onset_q'])==onset),key=lambda e:(e['voice'],e['beat'],e['note'],e['id']))
    if [e['id']for e in complete]!=members or target['coattack_ref']!=f'coattack:{pid}:{onset}':raise ValueError('Target is not the complete same-part coattack')
    if target['part_id']!=pid or F(target['onset_q'])!=onset or F(target['end_q'])!=max(F(e['onset_q'])+F(e['duration_q'])for e in complete):raise ValueError('Target part/time differs from source')
    beats=sorted({f"track-{e['part_id']}.json#/measures/{e['bar']-1}/voices/{e['voice']}/beats/{e['beat']}"for e in complete})
    if refs!=beats:raise ValueError('Target beat/member scope differs')
    frame=next(f for f in located['measure_geometry']['frames']if f['ordinal']==first['bar'])
    return dict(docs=docs,changed_docs=expected,members=members,events={e['id']:e for e in complete},part=pid,
        bar=first['bar'],position_q=str(onset-F(frame['start_q'])),literal_changed=before!=after)


def check_source(before,after,demonstration):
    try:
        scope=source_scope(before,after,demonstration)
        return dict(status='PASS_INDEPENDENT_PALM_MUTE_SOURCE_SCOPE',issues=[],
            affected_member_refs=scope['members'],affected_beat_refs=demonstration['target']['beat_refs'],
            literal_changed=scope['literal_changed'],sampler_or_artist_fit_validated=False)
    except Exception as exc:
        return dict(status='FAIL',issues=[str(exc)],sampler_or_artist_fit_validated=False)


@lru_cache(maxsize=6)
def note_index(tree):
    return {n.get('id'):n for n in tree.find('Notes')}


def _gp_note(tree,row):
    ids=(_gp_beat(tree,row).findtext('Notes')or'').split()
    if type(row['note'])is not int or not 0<=row['note']<len(ids):raise ValueError('Native note outside actual GP beat')
    return note_index(tree)[ids[row['note']]]


def palm_property(note):
    nodes=note.findall("./Properties/Property[@name='PalmMuted']")
    if not nodes:return False
    if len(nodes)!=1 or nodes[0].attrib!={'name':'PalmMuted'}or len(nodes[0])!=1 or nodes[0][0].tag!='Enable' or nodes[0][0].attrib or len(nodes[0][0]) or nodes[0][0].text not in(None,''):
        raise ValueError('Unknown native palm-mute property')
    return True


def tempo_at(case,tick):
    points={}
    for row in case['events']:
        if row['kind']!='TempoChangeEvent':continue
        d=row['data'];value=d['beatsPerMinute']
        if type(value)not in(int,float)or not math.isfinite(value)or value<=0:raise ValueError('Known native tempo required')
        previous=points.setdefault(d['tick'],value)
        if previous!=value:raise ValueError('Ambiguous simultaneous native tempo')
    eligible=[t for t in points if t<=tick]
    if not eligible:raise ValueError('No native tempo at target attack')
    return F(str(points[max(eligible)]))


def normalize_events(case,affected):
    rows=[]
    for row in case['events']:
        value=deepcopy(row);binding=value['binding']
        if value['kind']=='NoteOffEvent'and binding is not None and case['callbacks'][binding]['source_ref']in affected:
            value['data']['tick']='permitted_selected_release'
        rows.append(encoded(value))
    return Counter(rows)


def untouched_events(case,affected):
    return [row for row in case['events']if not(row['kind']=='NoteOffEvent'and row['binding']is not None
        and case['callbacks'][row['binding']]['source_ref']in affected)]


def check(root,qa,*,fidelity_scope='gp_with_exact_model_bends'):
    root,qa=Path(root),Path(qa);issues=[];detail={}
    try:
        if fidelity_scope not in('standalone_gp','gp_with_exact_model_bends'):raise ValueError('Explicit artifact fidelity scope required')
        snapshot=read(root/'dynamic-native-snapshot.json');supp=read(root/'palm-mute-native-supplement.json');demo=read(qa/'demonstration.json');plan=read(qa/'plan.json')
        if snapshot['schema']!='native-dynamic-snapshot/1'or snapshot.get('fidelity_scope','standalone_gp')!=fidelity_scope or set(snapshot['cases'])!={'source','zero','changed'}:raise ValueError('Complete actual native snapshot required')
        if supp['schema']!='native-palm-mute-supplement/1'or supp['shared_snapshot']!={'file':'dynamic-native-snapshot.json','sha256':sha(root/'dynamic-native-snapshot.json')}or supp['adapter_sha256']!=sha(Path(__file__).with_name('audit_palm_mute_gp.mjs'))or set(supp['cases'])!=set(snapshot['cases']):raise ValueError('Native mute supplement binding differs')
        module=Path(snapshot['module_path'])
        if sha(module)!=snapshot['module_sha256']or sha(module.with_name('alphaTab.core.mjs'))!=snapshot['core_sha256']or sha(Path(__file__).with_name('audit_dynamic_gp.mjs'))!=snapshot['snapshot_script_sha256']:raise ValueError('Native snapshot dependency changed')
        if plan['policy']!=POLICY or demo['controls']['context_policy']!=POLICY:raise ValueError('Mute policy differs from demonstration')
        hashes=plan['source_hashes']
        if not hashes:raise ValueError('Complete original capture inventory required')
        source=Path(next(iter(hashes))).parent
        if {Path(p).name for p in hashes}!={p.name for p in source.glob('*.json')}or any(Path(p).parent!=source or sha(p)!=h for p,h in hashes.items()):raise ValueError('Original capture inventory/hash differs')
        before=extract(source);zero=extract(qa/'zero-capture');after=extract(qa/'changed-capture')
        if before!=zero or read(qa/'zero-isolated/worker/output.json')!=zero or read(qa/'changed-isolated/worker/output.json')!=after:raise ValueError('Actual inverse worker/capture binding differs')
        scope=source_scope(before,after,demo);affected=set(scope['members'])
        if not scope['literal_changed']:raise ValueError('An actual notation intervention is required; zero baseline is separate')
        timing=supp['timing']
        if set(timing)!={'quarter_ticks','palm_mute_constant','position_scale'}or any(type(v)is not int or v<=0 for v in timing.values()):raise ValueError('Known native timing constants required')
        core_text=module.with_name('alphaTab.core.mjs').read_text(encoding='utf-8')
        for field,symbol in (('quarter_ticks','QuarterTime'),('palm_mute_constant','_defaultDurationPalmMute'),('position_scale','MaxPosition')):
            values=re.findall(r'static\s+'+symbol+r'\s*=\s*(\d+)\s*;',core_text)
            if len(values)!=1 or int(values[0])!=timing[field]:raise ValueError('Mute timing parameters differ from pinned native runtime')
        cases=snapshot['cases'];trees={};assets={};inventories={};flags={};note_maps={};extra_maps={};fidelity=[];companions={}
        folders={'source':source,'zero':qa/'zero-capture','changed':qa/'changed-capture'}
        for name,c in cases.items():
            out=root/name;fidelity.append(dict(method=name,**_fidelity(out,c,fidelity_scope,snapshot)))
            if sha(out/'score.gp')!=c['gp_sha256']or supp['cases'][name]['gp_sha256']!=c['gp_sha256']:raise ValueError('Actual GP hash differs')
            if c['capture_hashes']!={p.name:sha(p)for p in folders[name].glob('*.json')}:raise ValueError('Snapshot source capture differs')
            profile=out/'score.playback.json'
            if (read(profile)if profile.exists()else{})!=c['playback_profile']:raise ValueError('Playback profile changed')
            side=out/'score.exact-model-bends.json'
            if (sha(side)if side.exists()else None)!=c['sidecar_sha256']:raise ValueError('Bend companion changed')
            companions[name]=None
            if side.exists():
                sidecar=read(side)
                if sidecar['gp_sha256']!=c['gp_sha256']:raise ValueError('Bend companion not bound to GP')
                companions[name]={k:v for k,v in sidecar.items()if k!='gp_sha256'}
            with zipfile.ZipFile(out/'score.gp')as archive:
                names=archive.namelist();gpif=[n for n in names if n.endswith('.gpif')]
                if len(names)!=len(set(names))or len(gpif)!=1:raise ValueError('Unique complete GP archive required')
                inventories[name]=set(names)
                trees[name]=ET.fromstring(archive.read(gpif[0]));canonical_ids(trees[name]);assets[name]={n:archive.read(n)for n in names if n!=gpif[0]}
            notes={n['native_ref']:n for n in c['notes']};extra={n['native_ref']:n for n in supp['cases'][name]['notes']}
            if len(notes)!=len(c['notes'])or set(extra)!=set(notes)or len(extra)!=len(supp['cases'][name]['notes'])or len(notes)!=len(trees[name].find('Notes')):raise ValueError('Complete unique native note denominator required')
            note_maps[name]=notes;extra_maps[name]=extra;flags[name]={};seen=Counter()
            docs=scope['changed_docs']if name=='changed'else scope['docs']
            for ref,n in notes.items():
                xml=_gp_note(trees[name],n);muted=palm_property(xml);flags[name][ref]=muted
                if extra[ref]['is_palm_muted']is not muted:raise ValueError('Supplement differs from actual GP mute property')
                sr=n['source_ref']
                if sr not in affected:continue
                seen[sr]+=1;e=scope['events'][sr];raw=docs[f"track-{e['part_id']}.json"]['measures'][e['bar']-1]['voices'][e['voice']]['beats'][e['beat']]
                expected=state(raw)=={'kind':'explicit','value':True}
                native_beat=next(b for b in c['beats']if b['native_ref']==n['native_beat_ref'])
                br=f"track-{e['part_id']}.json#/measures/{e['bar']-1}/voices/{e['voice']}/beats/{e['beat']}"
                rn=raw['notes'][e['note']];tuning=docs[f"track-{e['part_id']}.json"]['tuning']
                if native_beat['source_beat_ref']!=br or (n['part'],n['bar'],n['voice'])!=(e['part_id'],e['bar'],e['voice'])or n['string']!=len(tuning)-rn['string']or n['fret']!=rn['fret']or F(n['pitch'])!=F(e['pitch']):raise ValueError('Affected native/source note correspondence differs')
                if n['is_percussion']or n['tie_destination']or n['hammer_pull_origin']or n['slide_origin_legato']or n['dead']or n['ghost']or native_beat['grace']!=0:raise ValueError('Unsupported affected native execution')
                if muted!=expected or F(extra[ref]['beat_duration_ticks'])!=F(e['duration_q'])*timing['quarter_ticks']:raise ValueError('Actual GP mute state or written time differs from source')
            if seen!=Counter({r:1 for r in affected}):raise ValueError('Whole coattack needs unique native/source note coverage')
            rawjson=c['raw_midi_json']
            if hashlib.sha256(rawjson.encode()).hexdigest()!=c['midi_event_sha256']or json.loads(rawjson)!=[e['data']for e in c['events']]:raise ValueError('Full MIDI stream/hash differs')
            ticks=[e['data']['tick']for e in c['events']]
            if ticks!=sorted(ticks):raise ValueError('MIDI events are not in playback order')
            expected=Counter({(i,k):1 for i in range(len(c['callbacks']))for k in('NoteOnEvent','NoteOffEvent')})
            if Counter((e['binding'],e['kind'])for e in c['events']if e['binding']is not None)!=expected:raise ValueError('MIDI callback/event coverage differs')
            for row in c['events']:
                i=row['binding']
                if i is None:continue
                if type(i)is not int or not 0<=i<len(c['callbacks']):raise ValueError('Invalid callback identity')
                call=c['callbacks'][i];d=row['data']
                if (d['track'],d['channel'],d['noteKey'],d['noteVelocity'])!=(call['track'],call['channel'],call['key'],call['velocity'])or d['tick']!=call['start']+(call['length']if row['kind']=='NoteOffEvent'else 0):raise ValueError('Actual paired MIDI events differ from callback')
            for call in c['callbacks']:
                if call['source_ref']in affected:
                    n=notes.get(call['native_ref'])
                    if n is None or n['source_ref']!=call['source_ref']or n['pitch']!=call['key']:raise ValueError('Selected MIDI callback belongs to another native note')
        if inventories['source']!=inventories['zero']or inventories['zero']!=inventories['changed']:raise ValueError('GP archive inventory changed')
        if any(c['playback_profile']!=cases['source']['playback_profile']for c in cases.values()):raise ValueError('Playback profile changed across cases')
        if assets['source']!=assets['zero']or assets['zero']!=assets['changed']or companions['source']!=companions['zero']or companions['zero']!=companions['changed']:raise ValueError('Unrelated GP archive asset or bend companion changed')
        if differences(trees['source'],trees['zero'])or any(cases['source'][k]!=cases['zero'][k]for k in('notes','beats','callbacks','events'))or supp['cases']['source']['notes']!=supp['cases']['zero']['notes']:raise ValueError('Source/exact-zero native output differs')
        if cases['zero']['notes']!=cases['changed']['notes']or cases['zero']['beats']!=cases['changed']['beats']:raise ValueError('Native note/beat fields outside mute changed')
        changed_tree=deepcopy(trees['changed']);gp_changes=[]
        for ref,n in note_maps['zero'].items():
            old,new=flags['zero'][ref],flags['changed'][ref]
            old_extra=extra_maps['zero'][ref];new_extra=extra_maps['changed'][ref]
            if {k:v for k,v in old_extra.items()if k!='is_palm_muted'}!={k:v for k,v in new_extra.items()if k!='is_palm_muted'}:raise ValueError('Native written durations changed')
            if old==new:continue
            if n['source_ref']not in affected:raise ValueError('Outside native mute flag changed')
            original=_gp_note(trees['zero'],n);altered=_gp_note(changed_tree,n);op=original.find('Properties');np=altered.find('Properties');prev=op.find("Property[@name='PalmMuted']");newprop=np.find("Property[@name='PalmMuted']")
            if newprop is not None:np.remove(newprop)
            if prev is not None:np.insert(list(op).index(prev),deepcopy(prev))
            gp_changes.append(dict(source_ref=n['source_ref'],native_ref=ref,before=old,after=new))
        if differences(trees['zero'],changed_tree):raise ValueError('GP changed outside target PalmMuted properties')
        a,b=cases['zero'],cases['changed'];midi_changes=[];coverage=Counter()
        if len(a['callbacks'])!=len(b['callbacks']):raise ValueError('MIDI note occurrence count changed')
        for i,(x,y)in enumerate(zip(a['callbacks'],b['callbacks'])):
            if x['source_ref']not in affected:
                if x!=y:raise ValueError('Outside MIDI attack changed')
                continue
            coverage[x['source_ref']]+=1
            if {k:v for k,v in x.items()if k!='length'}!={k:v for k,v in y.items()if k!='length'}:raise ValueError('Selected MIDI pitch/onset/velocity/channel changed')
            written=F(scope['events'][x['source_ref']]['duration_q'])*timing['quarter_ticks']
            for case,name,call in ((a,'zero',x),(b,'changed',y)):
                tempo=tempo_at(case,call['start']);cap=int(tempo*timing['palm_mute_constant']/timing['position_scale'])
                length=min(written,cap)if flags[name][call['native_ref']]else written
                if F(call['length'])!=length:raise ValueError('Selected MIDI release differs from native mute-duration equation')
            if x['length']!=y['length']:midi_changes.append(dict(callback=i,source_ref=x['source_ref'],before=x['length'],after=y['length']))
        if set(coverage)!=affected:raise ValueError('Affected native note has no MIDI attack')
        if normalize_events(a,affected)!=normalize_events(b,affected):raise ValueError('MIDI changed outside selected note releases')
        if untouched_events(a,affected)!=untouched_events(b,affected):raise ValueError('Unrelated simultaneous MIDI event order changed')
        renders=read(root/'audio-jobs.results.json');jobs=read(root/'audio-jobs.json');expected={(m,v)for m in cases for v in('focused','ensemble')}
        if len(renders)!=6 or len(jobs)!=6 or {(r['method'],r['mode'])for r in renders}!=expected or {(j['method'],j['mode'])for j in jobs}!=expected or len({r['font_sha256']for r in renders})!=1:raise ValueError('Complete six-render provenance required')
        jobmap={(j['method'],j['mode']):j for j in jobs}
        for r in renders:
            name,mode=r['method'],r['mode'];job=jobmap[name,mode]
            if any(r.get(k)!=v for k,v in job.items())or Path(job['file']).resolve()!=(root/name/'score.gp').resolve()or Path(job['out']).resolve()!=(root/name/(mode+'.wav')).resolve():raise ValueError('Render job/file binding differs')
            if r['gp_sha256']!=cases[name]['gp_sha256']or r['midi_event_sha256']!=cases[name]['midi_event_sha256']or r['audio_sha256']!=sha(root/name/(mode+'.wav'))or not 0<r['peak']<1 or 'fixed .3 gain'not in r['renderer']:raise ValueError('Render hashes/gain differ')
            if(r['track'],r['start_bar'],r['end_bar'],r['target_bar'])!=(scope['part'],demo['clip']['first'],demo['clip']['last'],scope['bar'])or F(r['target_offset_q'])!=F(scope['position_q']):raise ValueError('Rendered passage/target differs')
        waves=[]
        for mode in('focused','ensemble'):
            original,sr=audio(root/'source'/(mode+'.wav'));zero,zr=audio(root/'zero'/(mode+'.wav'));changed,cr=audio(root/'changed'/(mode+'.wav'))
            if(sr,zr,cr)!=(44100,44100,44100)or original!=zero or len(zero)!=len(changed):raise ValueError('PCM clock/source-zero differs')
            if any(abs(r['seconds']-len(zero)/zr)>1e-9 for r in renders if r['mode']==mode)or any(abs(v)>=32767 for wave in(original,zero,changed)for v in wave):raise ValueError('PCM length or clipping differs')
            delta=sum((x-y)**2 for x,y in zip(zero,changed));changed_frames=sum(x!=y for x,y in zip(zero,changed))
            if not midi_changes and changed_frames:raise ValueError('PCM changed despite identical MIDI')
            waves.append(dict(mode=mode,source_zero_exact=True,frames=len(zero),changed_frames=changed_frames,delta_rms=math.sqrt(delta/len(zero))/32768,pcm_difference_measured=changed_frames>0))
        audible=any(w['changed_frames']for w in waves)
        detail=dict(artifact_fidelity=fidelity,affected_member_refs=scope['members'],gp_mute_changes=gp_changes,midi_duration_changes=midi_changes,audio=waves,
            pcm_difference_measured=audible,inaudible_reason=None if audible else'No PCM difference in the pinned renderer; no audible-change claim',timing=timing)
    except Exception as exc:issues.append(str(exc))
    result=dict(status='FAIL'if issues else'PASS_NATIVE_PALM_MUTE_PCM_CHANGED'if detail['pcm_difference_measured']else'PASS_NATIVE_PALM_MUTE_PCM_IDENTICAL',issues=issues,**detail,listening_judgment=None,
        scope='Whole source coattack mute declaration; unchanged written pitch/time and other markings. Measured renderer duration damping, not physical palm-contact timbre or artistic acceptance.')
    (root/'palm-mute-artifact-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    result=check(*sys.argv[1:3]);print(json.dumps(result,indent=2));raise SystemExit(result['status']=='FAIL')
