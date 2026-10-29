"""Strict native GP/MIDI/PCM audit for one source-owned dynamic declaration.

Only dynamic leaves and actual paired note velocities may differ. This is not
an acoustic loudness law, artist judgment, or a repair of baseline conversion.
"""
from collections import Counter
from copy import deepcopy
from functools import lru_cache
import hashlib,json,math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
from check_voicing_artifacts import canonical_ids,differences,audio
from source_fact_tier1 import extract
from check_local_dynamics import inventory,check as source_check,encoded,MARKINGS

STATUS='PASS_NATIVE_GP_AND_AUDIO_DYNAMICS'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _native_velocity(note):
    name=note['dynamic']
    if type(name)is not str or name.lower()not in MARKINGS:raise ValueError('Unsupported native dynamic')
    adjustment=int(note['accentuated']==1)+2*int(note['accentuated']==2)-int(note['ghost'])-int(not note['is_percussion']and note['hammer_pull_origin'])
    return min(127,max(1,15+16*(MARKINGS.index(name.lower())+adjustment)))
def _beat_states(docs):
    result={}
    for name,p in docs.items():
        if not name.startswith('track-'):continue
        state={}
        for mi,m in enumerate(p.get('measures',[])):
            for vi,v in enumerate(m.get('voices',[])):
                for bi,b in enumerate(v.get('beats',[])):
                    if b.get('velocity')is not None:state[vi]=b['velocity']
                    mark=state.get(vi)
                    result[f'{name}#/measures/{mi}/voices/{vi}/beats/{bi}']=mark if type(mark)is str and mark in MARKINGS else None
    return result

@lru_cache(maxsize=6)
def _gp_index(tree):
    tracks=list(tree.find('Tracks'));offsets=[];count=0
    for t in tracks:offsets.append(count);count+=len(t.find('Staves'))
    return (offsets,list(tree.find('MasterBars')),{n.get('id'):n for n in tree.find('Bars')},{n.get('id'):n for n in tree.find('Voices')},{n.get('id'):n for n in tree.find('Beats')})
def _gp_beat(tree,row):
    offsets,masters,bars,voices,beats=_gp_index(tree);bid=masters[row['bar']-1].findtext('Bars').split()[offsets[row['part']]];vid=bars[bid].findtext('Voices').split()[row['voice']];ident=voices[vid].findtext('Beats').split()[row['beat']];return beats[ident]

def check(root,qa,*,fidelity_scope='standalone_gp'):
    root=Path(root);qa=Path(qa);issues=[];baseline={};audio_report={};midi_changes=[];gp_changes=[];fidelity=[]
    try:
        if type(fidelity_scope)is not str or fidelity_scope not in ('standalone_gp','gp_with_exact_model_bends'):raise ValueError('Explicit supported artifact fidelity scope required')
        snapshot=read(root/'dynamic-native-snapshot.json');demo=read(qa/'demonstration.json');plan=read(qa/'plan.json')
        if snapshot['schema']!='native-dynamic-snapshot/1'or set(snapshot['cases'])!={'source','zero','changed'}:raise ValueError('Complete actual native snapshot required')
        if snapshot.get('fidelity_scope','standalone_gp')!=fidelity_scope:raise ValueError('Snapshot artifact fidelity scope differs')
        if fidelity_scope=='gp_with_exact_model_bends':
            extractor=snapshot['checked_model_extractor'];path=Path(extractor['path'])
            if sha(path)!=extractor['sha256']:raise ValueError('Original checked-model extractor changed')
            text=path.read_text(encoding='utf-8');lines=text.splitlines()
            for prefix,key in [('function curve(','curve_sha256'),('function snapshot(','snapshot_sha256')]:
                line=next(s for s in lines if s.startswith(prefix))
                if hashlib.sha256(line.encode()).hexdigest()!=extractor[key]:raise ValueError('Checked-model extractor definition changed')
        module=Path(snapshot['module_path']);core=module.with_name('alphaTab.core.mjs');script=Path(__file__).with_name('audit_dynamic_gp.mjs')
        if sha(module)!=snapshot['module_sha256']or sha(core)!=snapshot['core_sha256']or sha(script)!=snapshot['snapshot_script_sha256']:raise ValueError('Native snapshot dependency changed')
        sourcefolder=Path(next(iter(plan['source_hashes']))).parent
        for p,h in plan['source_hashes'].items():
            if sha(p)!=h:raise ValueError('Frozen original capture changed')
        before=extract(qa/'zero-capture');after=extract(qa/'changed-capture')
        if encoded(extract(sourcefolder))!=encoded(before):raise ValueError('Original and exact-zero captures differ')
        for value,p in [(before,qa/'zero-and-pair/zero-isolated/worker/output.json'),(after,qa/'changed-isolated/worker/output.json')]:
            if encoded(read(p))!=encoded(value):raise ValueError('Export capture not bound to actual worker')
        iv=inventory(before);av=inventory(after)
        if encoded(iv)!=encoded(read(qa/'inventory.json')):raise ValueError('Saved source dynamic inventory differs')
        target=next(d for d in iv['declarations']if d['fact_ref']==demo['target']['fact_ref'])
        if encoded(target)!=encoded(demo['target']):raise ValueError('Demonstration target differs from original raw source')
        audit=source_check(before,after,target['fact_ref'],demo['chosen']['donor_refs'],demo['decision'])
        if audit['status']!='PASS_INDEPENDENT_LOCAL_DYNAMICS':raise ValueError(audit)
        affected=set(audit['affected_refs'])
        if not affected:raise ValueError('Actual changed dynamic influence required for audible gate')
        states={name:{s['occurrence_ref']:s for s in view['states']}for name,view in [('source',iv),('zero',iv),('changed',av)]}
        docs={name:{p.name:read(p)for p in folder.glob('*.json')}for name,folder in [('source',sourcefolder),('zero',qa/'zero-capture'),('changed',qa/'changed-capture')]}
        beatstates={k:_beat_states(v)for k,v in docs.items()};cases=snapshot['cases'];trees={};archives={}
        for name in ('source','zero','changed'):
            c=cases[name];folder=root/name
            validation=read(folder/'gp7-validation.json')
            standalone=validation.get('roundtripPass')is True
            if validation.get('directSource',{}).get('differences')!=0:raise ValueError('Native GP direct source validation failed: '+name)
            paired=False
            if not standalone:
                if fidelity_scope!='gp_with_exact_model_bends':raise ValueError('Native GP full roundtrip/source validation failed: '+name)
                reference=c.get('pre_export_reference')
                if type(reference)is not dict or set(reference)!={'file','sha256'}or reference['file']!='roundtrip-before.json':raise ValueError('Untouched pre-export comparison required')
                before_path=folder/reference['file']
                if sha(before_path)!=reference['sha256']or encoded(read(before_path))!=encoded(c.get('checked_model'))or c.get('checked_field_comparison')!='MATCH':raise ValueError('Restored playback differs from pre-export checked model')
                if c.get('sidecar_sha256')is None or type(c.get('restored_curves'))is not int or c['restored_curves']<=0:raise ValueError('Hash-bound actual curve restoration required')
                model=c['checked_model']
                if type(model)is not dict or set(model)!={'bars','tracks'}or len(model['bars'])!=validation.get('bars')or len(model['tracks'])!=validation.get('tracks'):raise ValueError('Incomplete pre-export model denominator')
                count=sum(len(beat['notes'])for track in model['tracks']for staff in track['staves']for bar in staff['bars']for voice in bar for beat in voice)
                if count!=validation.get('notes')or count!=len(c['notes']):raise ValueError('Incomplete pre-export note denominator')
                sidecar=read(folder/'score.exact-model-bends.json')
                if sidecar.get('schema')!='composition-lab.exact-model-bends.v1'or sidecar.get('gp_sha256')!=c['gp_sha256']or len(sidecar.get('curves',[]))!=c['restored_curves']:raise ValueError('Exact-model companion GP/count binding differs')
                paired=True
            fidelity.append(dict(method=name,standalone_roundtrip_pass=standalone,paired_checked_fields_pass=paired,scope='GP+hash-bound bend companion'if paired else'Standalone existing checked model fields'))
            archives[name]=zipfile.ZipFile(folder/'score.gp')
            if sha(folder/'score.gp')!=c['gp_sha256']:raise ValueError('Snapshot GP hash differs')
            side=folder/'score.exact-model-bends.json'
            if (sha(side)if side.exists()else None)!=c['sidecar_sha256']:raise ValueError('Snapshot bend companion differs')
            profile=folder/'score.playback.json'
            if (read(profile)if profile.exists()else{})!=c['playback_profile']:raise ValueError('Snapshot playback profile differs')
            capturefolder=sourcefolder if name=='source'else qa/(name+'-capture')
            if set(c['capture_hashes'])!={p.name for p in capturefolder.glob('*.json')}:raise ValueError('Snapshot capture inventory omitted files')
            for filename,h in c['capture_hashes'].items():
                if sha((sourcefolder if name=='source'else qa/(name+'-capture'))/filename)!=h:raise ValueError('Native snapshot capture binding differs')
            gpif=next(n for n in archives[name].namelist()if n.endswith('.gpif'));trees[name]=ET.fromstring(archives[name].read(gpif));canonical_ids(trees[name])
            covered=set();qualifications=[];native_refs=set();native_by_ref={}
            native_beats={r['native_ref']:r for r in c['beats']};note_counts=Counter(n['native_beat_ref']for n in c['notes'])
            if len(native_beats)!=len(c['beats']):raise ValueError('Duplicate native beat identity')
            lanes={}
            for row in c['beats']:lanes.setdefault((row['part'],row['bar'],row['voice']),[]).append(row)
            for (part,bar,voice),lane in lanes.items():
                rawpart=docs[name][f'track-{part}.json'];rawvoices=rawpart['measures'][bar-1].get('voices',[]);rawbeats=rawvoices[voice].get('beats',[])if voice<len(rawvoices)else[]
                original=[i for i,b in enumerate(rawbeats)if not b.get('graceNote')];regular=sorted((b for b in lane if b['grace']==0 and not b['empty']),key=lambda b:b['beat'])
                mapping={b['native_ref']:f'track-{part}.json#/measures/{bar-1}/voices/{voice}/beats/{i}'for i,b in zip(original,regular)}if len(original)==len(regular)else{}
                for row in lane:
                    if row['source_beat_ref']!=mapping.get(row['native_ref']):raise ValueError('Native/source beat correspondence differs')
            for beatref,row in native_beats.items():
                xml=_gp_beat(trees[name],row);nids=(xml.findtext('Notes')or'').split()
                if len(nids)!=note_counts[beatref]:raise ValueError('Native snapshot omitted note occurrences')
                if xml.findtext('Dynamic')!=row['dynamic']:raise ValueError('Native beat snapshot differs from actual GP Dynamic')
            for note in c['notes']:
                if note['native_ref']in native_refs:raise ValueError('Duplicate native note identity')
                native_refs.add(note['native_ref']);native_by_ref[note['native_ref']]=note
                if note['native_beat_ref']not in native_beats or note['dynamic']!=native_beats[note['native_beat_ref']]['dynamic']or note['beat_dynamic']!=note['dynamic']:raise ValueError('Native note dynamic differs from actual GP beat')
                refs=[note['source_ref']]if note['source_ref']else note['source_group_refs']if note['is_percussion']else[]
                if any(r not in states[name]for r in refs):raise ValueError('Unknown source note binding')
                known={states[name][r]['marking']for r in refs if states[name][r]['known']}
                if note['source_ref']:
                    r=note['source_ref'];fields=r.split(':');pid,bar,voice,beat,ni=map(int,fields[2:]);raw=docs[name][f'track-{pid}.json']['measures'][bar-1]['voices'][voice]['beats'][beat]['notes'][ni]
                    if native_beats[note['native_beat_ref']]['source_beat_ref']!=f'track-{pid}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}':raise ValueError('Native note bound to another source beat')
                    if(pid,bar,voice)!=(note['part'],note['bar'],note['voice'])or docs[name][f'track-{pid}.json']['tuning'].__len__()-raw['string']!=note['string']or(not raw.get('dead')and raw['fret']!=note['fret']):raise ValueError('Native note/source physical address differs')
                if len(known)==1:
                    expected=next(iter(known)).upper()
                    if note['dynamic']!=expected:raise ValueError('Known source marking lost in native GP: '+str(refs))
                    covered.update(r for r in refs if states[name][r]['known'])
                elif len(known)>1:qualifications.append(dict(refs=refs,reason='NONUNIFORM_UNMAPPED_SOURCE_DYNAMICS'))
            unverified=sorted(r for r,s in states[name].items()if s['known']and r not in covered)
            if affected&set(unverified):raise ValueError('Affected source note lacks verified native dynamic mapping')
            if any(n['source_ref']in affected and n['is_percussion']for n in c['notes']):raise ValueError('Changed source scope requires exact pitched-note bindings')
            for call in c['callbacks']:
                note=native_by_ref.get(call['native_ref'])
                if note is not None and call['velocity']!=_native_velocity(note):raise ValueError('Actual MIDI callback velocity differs from pinned native mapping')
            if type(c.get('raw_midi_json'))is not str or hashlib.sha256(c['raw_midi_json'].encode()).hexdigest()!=c['midi_event_sha256']or json.loads(c['raw_midi_json'])!=[e['data']for e in c['events']]:raise ValueError('Complete raw MIDI stream/hash differs')
            if [e['data']['tick']for e in c['events']]!=sorted(e['data']['tick']for e in c['events']):raise ValueError('MIDI event clock order changed')
            bindings=Counter((e['binding'],e['kind'])for e in c['events']if e['binding']is not None)
            if bindings!=Counter({(i,k):1 for i in range(len(c['callbacks']))for k in ('NoteOnEvent','NoteOffEvent')}):raise ValueError('MIDI note-on/off callback denominator differs')
            for event in c['events']:
                bi=event['binding']
                if bi is None:continue
                if type(bi)is not int or not 0<=bi<len(c['callbacks']):raise ValueError('Invalid actual MIDI event binding')
                call=c['callbacks'][bi];d=event['data'];kind=event['kind']
                if kind not in ('NoteOnEvent','NoteOffEvent')or(d['track'],d['channel'],d['noteKey'])!=(call['track'],call['channel'],call['key'])or d['tick']!=call['start']+(call['length']if kind=='NoteOffEvent'else 0)or d['noteVelocity']!=call['velocity']:raise ValueError('Actual MIDI note event/callback mismatch')
            baseline[name]=dict(known_source_refs_verified=len(covered),unknown_source_refs=sum(not s['known']for s in states[name].values()),known_source_refs_unverified=unverified,qualifications=qualifications)
        names=archives['source'].namelist()
        if any(z.namelist()!=names for z in archives.values()):raise ValueError('GP archive structure changed')
        gpif=next(n for n in names if n.endswith('.gpif'))
        for filename in names:
            if filename!=gpif and any(z.read(filename)!=archives['source'].read(filename)for z in archives.values()):raise ValueError('Other GP archive asset changed')
        if differences(trees['source'],trees['zero']):raise ValueError('Original/exact-zero GPIF differs beyond generated chord IDs')
        if cases['source']['notes']!=cases['zero']['notes']or cases['source']['beats']!=cases['zero']['beats']or cases['source']['events']!=cases['zero']['events']or cases['source']['callbacks']!=cases['zero']['callbacks']:raise ValueError('Original/exact-zero native events differ')
        oldnotes={n['native_ref']:n for n in cases['source']['notes']};newnotes={n['native_ref']:n for n in cases['changed']['notes']}
        if set(oldnotes)!=set(newnotes):raise ValueError('Native note denominator changed')
        for ref,a in oldnotes.items():
            b=newnotes[ref];allowed=a['source_ref']in affected
            if {k:v for k,v in a.items()if k not in('dynamic','beat_dynamic')}!={k:v for k,v in b.items()if k not in('dynamic','beat_dynamic')}:raise ValueError('Other native note property changed')
            if not allowed and a['dynamic']!=b['dynamic']:raise ValueError('Outside native note dynamics changed')
        beats0={b['native_ref']:b for b in cases['source']['beats']};beats1={b['native_ref']:b for b in cases['changed']['beats']};gpbeats0=list(trees['source'].find('Beats'));gpbeats1=list(trees['changed'].find('Beats'))
        if len(gpbeats0)!=len(gpbeats1)or set(beats0)!=set(beats1):raise ValueError('Native beat denominator changed')
        # Each snapshot native beat is mapped through source part/bar/voice to GPIF IDs.
        for ref,a in beats0.items():
            b=beats1[ref]
            if {k:v for k,v in a.items()if k!='dynamic'}!={k:v for k,v in b.items()if k!='dynamic'}:raise ValueError('Other native beat property changed')
            old=_gp_beat(trees['source'],a);new=_gp_beat(trees['changed'],b);delta=differences(old,new)
            if not delta:continue
            rawref=a['source_beat_ref'];active=bool(affected&set(a['source_refs']))
            statechange=rawref is not None and beatstates['source'].get(rawref)!=beatstates['changed'].get(rawref)
            if not active and not statechange:raise ValueError('Outside GP beat changed')
            x=old.find('Dynamic');y=new.find('Dynamic')
            if x is None or y is None or x.attrib!=y.attrib or len(x)or len(y)or(x.text or'').strip()!=a['dynamic']or(y.text or'').strip()!=b['dynamic']:raise ValueError('GP Dynamic leaf/native snapshot differs')
            if not a['source_refs']:
                if a['dynamic']!=str(beatstates['source'].get(rawref)).upper()or b['dynamic']!=str(beatstates['changed'].get(rawref)).upper():raise ValueError('Rest dynamic has no verified state coupling')
            gp_changes.append(dict(native_ref=ref,gp_beat_id=old.get('id'),old=a['dynamic'],new=b['dynamic']))
            y.text=x.text
        if differences(trees['source'],trees['changed']):raise ValueError('Other GPIF fields changed')
        a=cases['source'];b=cases['changed']
        if len(a['callbacks'])!=len(b['callbacks'])or len(a['events'])!=len(b['events']):raise ValueError('MIDI note/event denominator changed')
        allowed_bindings=set()
        for i,(x,y)in enumerate(zip(a['callbacks'],b['callbacks'])):
            if {k:v for k,v in x.items()if k!='velocity'}!={k:v for k,v in y.items()if k!='velocity'}:raise ValueError('MIDI track/channel/key/time/duration changed')
            if x['velocity']!=y['velocity']:
                if x['source_ref']not in affected:raise ValueError('Outside MIDI velocity changed')
                allowed_bindings.add(i)
        for i,(x,y)in enumerate(zip(a['events'],b['events'])):
            if x==y:continue
            aa=deepcopy(x);bb=deepcopy(y)
            if x['kind']not in ('NoteOnEvent','NoteOffEvent')or x['binding']not in allowed_bindings:raise ValueError('Nonowned MIDI event changed')
            aa['data'].pop('noteVelocity',None);bb['data'].pop('noteVelocity',None)
            if aa!=bb:raise ValueError('Other MIDI note event property changed')
            midi_changes.append(dict(index=i,kind=x['kind'],binding=x['binding'],before=x['data']['noteVelocity'],after=y['data']['noteVelocity']))
        if not gp_changes or not allowed_bindings:raise ValueError('No actual native dynamic/velocity change')
        renders=read(root/'audio-jobs.results.json')
        if len(renders)!=6 or {(r['method'],r['mode'])for r in renders}!={(m,s)for m in ('source','zero','changed')for s in ('focused','ensemble')}:raise ValueError('Complete unique six-render provenance required')
        fonts={r['font_sha256']for r in renders}
        if len(fonts)!=1:raise ValueError('Render soundfont changed')
        for r in renders:
            if r['midi_event_sha256']!=cases[r['method']]['midi_event_sha256']or r['gp_sha256']!=cases[r['method']]['gp_sha256']or sha(root/r['method']/(r['mode']+'.wav'))!=r['audio_sha256']or not 0<r['peak']<1 or 'fixed .3 gain'not in r['renderer']:raise ValueError('Render provenance/gain/clipping mismatch')
        for mode in ('focused','ensemble'):
            source,rate=audio(root/'source'/(mode+'.wav'));zero,zr=audio(root/'zero'/(mode+'.wav'));changed,cr=audio(root/'changed'/(mode+'.wav'))
            if rate!=zr or rate!=cr or len(source)!=len(zero)or len(source)!=len(changed)or source!=zero:raise ValueError('Render clock/source-zero mismatch')
            if any(abs(v)>=32767 for a in (source,zero,changed)for v in a):raise ValueError('Clipped PCM')
            delta=[b-a for a,b in zip(source,changed)];nz=[i for i,d in enumerate(delta)if d]
            if not nz:raise ValueError('No actual rendered dynamic change')
            audio_report[mode]=dict(source_zero_sample_exact=True,changed_frames=len(nz),frames=len(source),rate=rate,delta_rms=math.sqrt(sum(d*d for d in delta)/len(delta))/32768,delta_start_seconds=nz[0]/rate,delta_end_seconds=nz[-1]/rate)
    except Exception as exc:issues.append(str(exc))
    report=dict(status=(STATUS if fidelity_scope=='standalone_gp'else'PASS_GP_BUNDLE_AND_AUDIO_DYNAMICS')if not issues else'FAIL',fidelity_scope=fidelity_scope,artifact_fidelity=fidelity,issues=issues,source_baseline=baseline,gp_dynamic_changes=gp_changes,midi_velocity_changes=midi_changes,audio=audio_report,
        scope='Known mapped written levels and their actual GP/MIDI/PCM consequences. Unmapped baseline refs explicitly qualified; affected unmapped refs refuse. NoteOff velocity is the pinned library mirror of NoteOn velocity, not a release-expression control. No linear loudness, taste or artist claim.')
    (root/'independent-dynamic-artifacts.json').write_text(json.dumps(report,indent=2));return report
