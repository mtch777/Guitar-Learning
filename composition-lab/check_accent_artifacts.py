"""Strict one-note accent GP/MIDI/PCM proof; dynamics remain locked.

Uses shared read-only snapshot/XML/PCM helpers, never dynamics-policy acceptance.
"""
from collections import Counter
from copy import deepcopy
import hashlib,json,math,zipfile
from fractions import Fraction as F
from pathlib import Path
import xml.etree.ElementTree as ET
from source_fact_tier1 import extract
from check_local_accents import Oracle,POLICY
from check_local_dynamics import inventory as dynamics
from check_dynamic_artifacts import read,sha,_native_velocity,_gp_beat
from check_voicing_artifacts import canonical_ids,differences,audio

STATUS='PASS_NATIVE_GP_AND_AUDIO_ACCENTS'
def _encoded(x):return json.dumps(x,sort_keys=True,separators=(',',':'))


def _gp_note(tree,row):
    ids=(_gp_beat(tree,row).findtext('Notes')or'').split()
    if type(row['note'])is not int or not 0<=row['note']<len(ids):raise ValueError('Native note ordinal outside GP beat')
    return next(n for n in tree.find('Notes')if n.get('id')==ids[row['note']])


def _accent(xml):
    value=xml.findtext('Accent');flags=int(value)if value is not None else 0
    if flags<0:raise ValueError('Invalid GP accent flags')
    return (1 if flags&8 else 2 if flags&4 else 3 if flags&16 else 0),flags


def _fidelity(folder,c,scope,snapshot):
    v=read(folder/'gp7-validation.json');standalone=v.get('roundtripPass')is True
    if v.get('directSource',{}).get('differences')!=0 or v.get('error'):raise ValueError('Native direct source check failed')
    if not standalone:
        if scope!='gp_with_exact_model_bends':raise ValueError('Standalone GP roundtrip failed')
        x=snapshot['checked_model_extractor'];text=Path(x['path']).read_text(encoding='utf-8')
        if sha(x['path'])!=x['sha256']:raise ValueError('Checked-model extractor changed')
        for prefix,key in(('function curve(','curve_sha256'),('function snapshot(','snapshot_sha256')):
            line=next(s for s in text.splitlines()if s.startswith(prefix))
            if hashlib.sha256(line.encode()).hexdigest()!=x[key]:raise ValueError('Checked-model definition changed')
        ref=c.get('pre_export_reference');model=c.get('checked_model')
        if type(ref)is not dict or set(ref)!={'file','sha256'}or ref['file']!='roundtrip-before.json' or sha(folder/ref['file'])!=ref['sha256']or _encoded(read(folder/ref['file']))!=_encoded(model)or c.get('checked_field_comparison')!='MATCH':raise ValueError('Restored checked model differs from original')
        if type(model)is not dict or set(model)!={'bars','tracks'}or len(model['bars'])!=v.get('bars')or len(model['tracks'])!=v.get('tracks'):raise ValueError('Incomplete checked-model denominator')
        count=sum(len(b['notes'])for t in model['tracks']for s in t['staves']for bar in s['bars']for voice in bar for b in voice)
        if count!=v.get('notes')or count!=len(c['notes']):raise ValueError('Incomplete checked-note denominator')
        side=read(folder/'score.exact-model-bends.json')
        if side.get('schema')!='composition-lab.exact-model-bends.v1'or side.get('gp_sha256')!=c['gp_sha256']or type(c.get('restored_curves'))is not int or c['restored_curves']<=0 or len(side.get('curves',[]))!=c['restored_curves']:raise ValueError('Hash-bound bend restoration differs')
    return dict(standalone_roundtrip_pass=standalone,paired_checked_fields_pass=not standalone,scope='Standalone checked fields'if standalone else'GP plus hash-bound exact-model bends')


def check(root,qa,*,fidelity_scope='standalone_gp'):
    root=Path(root);qa=Path(qa);issues=[];fidelity=[];baseline={};gp_changes=[];midi_changes=[];audio_report={}
    try:
        if fidelity_scope not in('standalone_gp','gp_with_exact_model_bends'):raise ValueError('Explicit supported fidelity scope required')
        s=read(root/'accent-native-snapshot.json');original=read(root/'dynamic-native-snapshot.json')
        if s['schema']!='native-accent-snapshot/1'or s.get('fidelity_scope','standalone_gp')!=fidelity_scope or set(s['cases'])!={'source','zero','changed'}:raise ValueError('Complete accent snapshot required')
        if s['shared_snapshot']!={'file':'dynamic-native-snapshot.json','sha256':sha(root/'dynamic-native-snapshot.json')}:raise ValueError('Original native snapshot binding differs')
        expected=deepcopy(s);expected.pop('shared_snapshot');expected.pop('accent_adapter_sha256');expected['schema']='native-dynamic-snapshot/1'
        if expected!=original:raise ValueError('Adapter changed actual native evidence')
        module=Path(s['module_path']);here=Path(__file__).parent
        if sha(module)!=s['module_sha256']or sha(module.with_name('alphaTab.core.mjs'))!=s['core_sha256']or sha(here/'audit_dynamic_gp.mjs')!=s['snapshot_script_sha256']or sha(here/'audit_local_accent_gp.mjs')!=s['accent_adapter_sha256']:raise ValueError('Snapshot dependency drift')
        demo=read(qa/'demonstration.json');plan=read(qa/'plan.json');target_ref=demo['target']['occurrence_ref']
        if demo['controls']['context_policy']!=POLICY or plan['policy']!=POLICY:raise ValueError('Accent policy differs')
        source=Path(next(iter(plan['source_hashes']))).parent
        if set(Path(f).name for f in plan['source_hashes'])!={p.name for p in source.glob('*.json')}:raise ValueError('Frozen capture inventory incomplete')
        if any(sha(p)!=h for p,h in plan['source_hashes'].items()):raise ValueError('Frozen source changed')
        before=extract(source);zero=extract(qa/'zero-capture');after=extract(qa/'changed-capture')
        if before!=zero or read(qa/'zero-and-pair/zero-isolated/worker/output.json')!=zero or read(qa/'changed-isolated/worker/output.json')!=after:raise ValueError('Actual worker/capture binding differs')
        oracle=Oracle(before);view=oracle.inventory()
        if view!=read(qa/'inventory.json')or demo['target']!=oracle.rows[target_ref]:raise ValueError('Raw source accent inventory/target differs')
        raw=oracle.check(after,target_ref,demo['chosen']['donor_refs'],demo['decision']);draw=oracle.check_sample(target_ref,demo['controls'],demo['chosen'],demo['decision'])
        if raw['status']!='PASS_INDEPENDENT_LOCAL_ACCENTS'or draw['issues']or not raw['changed']:raise ValueError('Independent actual accent/source draw failed')
        cases=s['cases'];trees={};archives={};native={};rawdocs={};dynamic_states={}
        folders={'source':source,'zero':qa/'zero-capture','changed':qa/'changed-capture'}
        for method,folder in folders.items():
            c=cases[method];out=root/method;fidelity.append(dict(method=method,**_fidelity(out,c,fidelity_scope,s)))
            if sha(out/'score.gp')!=c['gp_sha256']:raise ValueError('Actual GP hash differs')
            side=out/'score.exact-model-bends.json';profile=out/'score.playback.json'
            if(sha(side)if side.exists()else None)!=c['sidecar_sha256']or(read(profile)if profile.exists()else{})!=c['playback_profile']:raise ValueError('Playback companion/profile differs')
            if c['capture_hashes']!={p.name:sha(p)for p in folder.glob('*.json')}:raise ValueError('Snapshot capture inventory/hash differs')
            archives[method]=zipfile.ZipFile(out/'score.gp');gpif=next(n for n in archives[method].namelist()if n.endswith('.gpif'));tree=ET.fromstring(archives[method].read(gpif));canonical_ids(tree);trees[method]=tree
            docs={p.name:read(p)for p in folder.glob('*.json')};rawdocs[method]=docs
            states={r['occurrence_ref']:r for r in dynamics(before if method!='changed'else after)['states']};dynamic_states[method]=states
            beats={b['native_ref']:b for b in c['beats']};notes={n['native_ref']:n for n in c['notes']};native[method]=notes
            if len(beats)!=len(c['beats'])or len(notes)!=len(c['notes']):raise ValueError('Duplicate native identities')
            lanes={};counts=Counter(n['native_beat_ref']for n in c['notes'])
            for b in c['beats']:lanes.setdefault((b['part'],b['bar'],b['voice']),[]).append(b)
            for(part,bar,voice),lane in lanes.items():
                voices=docs[f'track-{part}.json']['measures'][bar-1].get('voices',[]);rawbeats=voices[voice].get('beats',[])if voice<len(voices)else[]
                indices=[i for i,b in enumerate(rawbeats)if not b.get('graceNote')];regular=sorted((b for b in lane if b['grace']==0 and not b['empty']),key=lambda b:b['beat'])
                mapping={b['native_ref']:f'track-{part}.json#/measures/{bar-1}/voices/{voice}/beats/{i}'for i,b in zip(indices,regular)}if len(indices)==len(regular)else{}
                if any(b['source_beat_ref']!=mapping.get(b['native_ref'])for b in lane):raise ValueError('Source/native beat alignment differs')
            covered=set();unknown=[]
            for ref,b in beats.items():
                xml=_gp_beat(tree,b)
                if len((xml.findtext('Notes')or'').split())!=counts[ref]or xml.findtext('Dynamic')!=b['dynamic']:raise ValueError('GP beat/note denominator or written dynamic differs')
            if len(tree.find('Notes'))!=len(notes):raise ValueError('Native snapshot omits GP note occurrences')
            for n in c['notes']:
                b=beats.get(n['native_beat_ref']);xml=_gp_note(tree,n)
                if b is None or n['dynamic']!=b['dynamic']or n['beat_dynamic']!=b['dynamic']or _accent(xml)[0]!=n['accentuated']:raise ValueError('Native note differs from actual GP accent/dynamic')
                ref=n['source_ref']
                if not ref:continue
                if ref not in states:raise ValueError('Unknown native/source note binding')
                _,_,pid,bar,voice,beat,ni=ref.split(':');pid,bar,voice,beat,ni=map(int,(pid,bar,voice,beat,ni));part=docs[f'track-{pid}.json'];rn=part['measures'][bar-1]['voices'][voice]['beats'][beat]['notes'][ni]
                if b['source_beat_ref']!=f'track-{pid}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}'or(pid,bar,voice)!=(n['part'],n['bar'],n['voice'])or len(part['tuning'])-rn['string']!=n['string']or(not rn.get('dead')and rn['fret']!=n['fret']):raise ValueError('Raw note/native physical correspondence differs')
                a=rn.get('accentuated',0)
                if type(a)is int and a in(0,1,2):
                    if n['accentuated']!=a:raise ValueError('Known source accent lost in native GP')
                    covered.add(ref)
                else:unknown.append(ref)
                if states[ref]['known']and n['dynamic']!=states[ref]['marking'].upper():raise ValueError('Known source written dynamic lost')
            affected=[n for n in c['notes']if n['source_ref']==target_ref]
            if len(affected)!=1 or target_ref not in covered or affected[0]['tie_destination']or affected[0]['is_percussion']:raise ValueError('Affected attack lacks unique pitched native mapping')
            for call in c['callbacks']:
                n=notes.get(call['native_ref'])
                if n is not None and call['velocity']!=_native_velocity(n):raise ValueError('Actual callback velocity differs from native accent equation')
            rawjson=c.get('raw_midi_json')
            if type(rawjson)is not str or hashlib.sha256(rawjson.encode()).hexdigest()!=c['midi_event_sha256']or json.loads(rawjson)!=[e['data']for e in c['events']]:raise ValueError('Complete MIDI stream/hash differs')
            if [e['data']['tick']for e in c['events']]!=sorted(e['data']['tick']for e in c['events']):raise ValueError('MIDI clock order differs')
            if Counter((e['binding'],e['kind'])for e in c['events']if e['binding']is not None)!=Counter({(i,k):1 for i in range(len(c['callbacks']))for k in('NoteOnEvent','NoteOffEvent')}):raise ValueError('MIDI callback/event denominator differs')
            for e in c['events']:
                i=e['binding']
                if i is None:continue
                if type(i)is not int or not 0<=i<len(c['callbacks']):raise ValueError('Invalid MIDI callback binding')
                call=c['callbacks'][i];d=e['data']
                if e['kind']not in('NoteOnEvent','NoteOffEvent')or(d['track'],d['channel'],d['noteKey'])!=(call['track'],call['channel'],call['key'])or d['tick']!=call['start']+(call['length']if e['kind']=='NoteOffEvent'else 0)or d['noteVelocity']!=call['velocity']:raise ValueError('MIDI callback/event identity differs')
            source_rows={r['occurrence_ref']:r for r in view['occurrences']if r['occurrence_ref']in states}
            known_refs={ref for ref,r in source_rows.items()if r['sound_level']is not None}
            unknown_refs=sorted(set(source_rows)-known_refs)
            baseline[method]=dict(source_occurrences=len(states),known_mapped_accent_refs=len(covered),
                known_source_refs_unverified=sorted(known_refs-covered),unknown_accent_refs=unknown_refs,affected_source_refs=[target_ref])
        names=archives['source'].namelist()
        if any(z.namelist()!=names for z in archives.values()):raise ValueError('GP archive inventory differs')
        gpif=next(n for n in names if n.endswith('.gpif'))
        if any(z.read(n)!=archives['source'].read(n)for n in names if n!=gpif for z in archives.values()):raise ValueError('Other GP archive asset changed')
        if differences(trees['source'],trees['zero'])or any(cases['source'][k]!=cases['zero'][k]for k in('notes','beats','callbacks','events')):raise ValueError('Source/exact-zero GP/native differs')
        if cases['source']['beats']!=cases['changed']['beats']:raise ValueError('Written dynamics or other beat state changed')
        if set(native['source'])!=set(native['changed']):raise ValueError('Native note denominator changed')
        for ref,a in native['source'].items():
            b=native['changed'][ref];allowed=a['source_ref']==target_ref
            if {k:v for k,v in a.items()if k!='accentuated'}!={k:v for k,v in b.items()if k!='accentuated'}or not allowed and a['accentuated']!=b['accentuated']:raise ValueError('Other native note property changed')
            if a['accentuated']==b['accentuated']:continue
            x=_gp_note(trees['source'],a);y=_gp_note(trees['changed'],b);oldvalue,oldflags=_accent(x);newvalue,newflags=_accent(y)
            if(oldflags&~12)!=(newflags&~12):raise ValueError('Non-accent GP flags changed')
            gp_changes.append(dict(source_ref=target_ref,native_ref=ref,gp_note_id=x.get('id'),before=oldvalue,after=newvalue))
            # Restore ONLY this permitted XML child in a comparison copy.
            old=x.find('Accent');new=y.find('Accent')
            if old is None and new is not None:y.remove(new)
            elif old is not None and new is None:y.insert(list(x).index(old),deepcopy(old))
            elif old is not None:new.text=old.text
        if differences(trees['source'],trees['changed']):raise ValueError('Other GPIF field/dynamic changed')
        a=cases['source'];b=cases['changed'];allowed=set()
        if len(a['callbacks'])!=len(b['callbacks'])or len(a['events'])!=len(b['events']):raise ValueError('MIDI event/attack denominator changed')
        for i,(x,y)in enumerate(zip(a['callbacks'],b['callbacks'])):
            if {k:v for k,v in x.items()if k!='velocity'}!={k:v for k,v in y.items()if k!='velocity'}:raise ValueError('MIDI track/key/time/duration changed')
            if x['source_ref']==target_ref:
                if x['velocity']==y['velocity']:raise ValueError('Affected attack clamped or did not change velocity')
                allowed.add(i)
            elif x['velocity']!=y['velocity']:raise ValueError('Outside MIDI velocity changed')
        for i,(x,y)in enumerate(zip(a['events'],b['events'])):
            if x==y:continue
            xx=deepcopy(x);yy=deepcopy(y)
            if x['kind']not in('NoteOnEvent','NoteOffEvent')or x['binding']not in allowed:raise ValueError('Unowned MIDI event changed')
            xx['data'].pop('noteVelocity',None);yy['data'].pop('noteVelocity',None)
            if xx!=yy:raise ValueError('Other MIDI event property changed')
            midi_changes.append(dict(index=i,kind=x['kind'],binding=x['binding'],before=x['data']['noteVelocity'],after=y['data']['noteVelocity']))
        if len(gp_changes)!=1 or not allowed:raise ValueError('Actual one-note accent/attack change required')
        renders=read(root/'audio-jobs.results.json')
        if len(renders)!=6 or {(r['method'],r['mode'])for r in renders}!={(m,v)for m in('source','zero','changed')for v in('focused','ensemble')}or len({r['font_sha256']for r in renders})!=1:raise ValueError('Complete six-render provenance required')
        for r in renders:
            if r['midi_event_sha256']!=cases[r['method']]['midi_event_sha256']or r['gp_sha256']!=cases[r['method']]['gp_sha256']or sha(root/r['method']/(r['mode']+'.wav'))!=r['audio_sha256']or not 0<r['peak']<1 or 'fixed .3 gain'not in r['renderer']:raise ValueError('Render hash/gain/clipping differs')
            if(r['track'],r['start_bar'],r['end_bar'],r['target_bar'])!=(demo['clip']['part'],demo['clip']['first'],demo['clip']['last'],demo['target']['bar'])or F(r['target_offset_q'])!=F(demo['target']['position_q']):raise ValueError('Render clip/cue differs from actual target')
        for mode in('focused','ensemble'):
            source,sr=audio(root/'source'/(mode+'.wav'));zero,zr=audio(root/'zero'/(mode+'.wav'));changed,cr=audio(root/'changed'/(mode+'.wav'))
            if sr!=zr or sr!=cr or len(source)!=len(zero)or len(source)!=len(changed)or source!=zero:raise ValueError('PCM clock/source-zero differs')
            if any(abs(r['seconds']-len(source)/sr)>1e-9 for r in renders if r['mode']==mode):raise ValueError('PCM length differs from render receipt')
            if any(abs(v)>=32767 for seq in(source,zero,changed)for v in seq):raise ValueError('Clipped PCM')
            delta=[y-x for x,y in zip(source,changed)];nz=[i for i,d in enumerate(delta)if d]
            if not nz:raise ValueError('No actual PCM accent change')
            audio_report[mode]=dict(source_zero_sample_exact=True,changed_frames=len(nz),frames=len(source),rate=sr,delta_rms=math.sqrt(sum(d*d for d in delta)/len(delta))/32768)
    except Exception as exc:issues.append(str(exc))
    report=dict(status=(STATUS if fidelity_scope=='standalone_gp'else'PASS_GP_BUNDLE_AND_AUDIO_ACCENTS')if not issues else'FAIL',fidelity_scope=fidelity_scope,issues=issues,artifact_fidelity=fidelity,source_baseline=baseline,gp_accent_changes=gp_changes,midi_velocity_changes=midi_changes,audio=audio_report,
        scope='Source-observed notation accent on one regular pitched note; written dynamics and all other fields locked. Every actual repeated attack checked. No comfort, phrase intent, artist fit or listening judgment.')
    (root/'independent-accent-artifacts.json').write_text(json.dumps(report,indent=2));return report
