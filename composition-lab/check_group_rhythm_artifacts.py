"""Independent actual-GP, complete MIDI and rendered-wave check for rhythm.

Selected plain notes may change attack/end times only. Every other GP field,
MIDI event and source occurrence is compared. Human musical fit is not inferred.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import hashlib,json,sys,zipfile
import xml.etree.ElementTree as ET
from check_voicing_artifacts import canonical_ids,differences,audio
from check_dynamic_artifacts import _gp_beat
from source_fact_tier1 import extract


def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def normalized_events(case,origins,affected):
    if len(origins)!=len(case['events']):raise ValueError('Complete event-origin ledger required')
    calls={ref:[c for c in case['callbacks']if c['source_ref']==ref]for ref in affected};rows=[]
    for e,origin in zip(case['events'],origins):
        if origin['data']!=e['data']or origin['kind']!=e['kind']:raise ValueError('Independent MIDI stream/origin differs')
        row=deepcopy(e);i=e['binding'];ref=origin['origin_source_ref'];row['origin_source_ref']=ref
        if i is not None and case['callbacks'][i]['source_ref']in affected:row['data']['tick']='selected_group_time'
        elif ref in affected:
            # AlphaTab emits a center-pitch reset at each plain note attack.
            # Authenticate both its actual generating note and exact timing;
            # arbitrary bends, controllers and unbound changes remain forbidden.
            d=e['data'];matches=calls[ref]
            if e['kind']!='NoteBendEvent'or len(matches)!=1 or d['value']!=2147483648:raise ValueError('Unsupported selected-note MIDI control')
            call=matches[0]
            if(d['track'],d['channel'],d['noteKey'],d['tick'])!=(call['track'],call['channel'],call['key'],call['start']):raise ValueError('Reset not bound to actual selected attack')
            row['data']['tick']='selected_group_attack'
        rows.append(json.dumps(row,sort_keys=True))
    return Counter(rows)


def check(root,qa,capture):
    root,qa,capture=map(Path,(root,qa,capture));issues=[];details={}
    try:
        snapshot=read(root/'dynamic-native-snapshot.json');cases=snapshot['cases'];demo=read(qa/'demonstration.json');plan=read(qa/'plan.json')
        origins=read(root/'rhythm-midi-origins.json')
        if origins['schema']!='actual-native-midi-origins/1'or origins['snapshot_sha256']!=sha(root/'dynamic-native-snapshot.json')or origins['script_sha256']!=sha(Path(__file__).with_name('audit_group_rhythm_origins.mjs')):raise ValueError('Independent origin audit binding changed')
        if set(cases)!={'source','zero','changed'}:raise ValueError('All three actual native snapshots required')
        if snapshot['schema']!='native-dynamic-snapshot/1':raise ValueError('Actual score snapshot required')
        module=Path(snapshot['module_path'])
        if sha(module)!=snapshot['module_sha256']or sha(module.with_name('alphaTab.core.mjs'))!=snapshot['core_sha256']or sha(Path(__file__).with_name('audit_dynamic_gp.mjs'))!=snapshot['snapshot_script_sha256']:raise ValueError('Native runtime/snapshot code changed')
        extractor=snapshot['checked_model_extractor']
        if sha(extractor['path'])!=extractor['sha256']:raise ValueError('Checked model extractor changed')
        if not plan['source_hashes']or {Path(p).name for p in plan['source_hashes']}!={p.name for p in capture.glob('*.json')}:raise ValueError('Complete original capture inventory required')
        for p,h in plan['source_hashes'].items():
            if sha(p)!=h or sha(capture/Path(p).name)!=h:raise ValueError('Original source changed')
        for name,worker in(('zero','zero-isolated'),('changed','changed-isolated')):
            if read(qa/f'{worker}/worker/output.json')!=extract(qa/f'{name}-capture'):raise ValueError('Actual isolated worker output binding failed')
        if extract(capture)!=extract(qa/'zero-capture'):raise ValueError('Zero differs from original')
        refs=demo['target']['occurrence_refs'];shares=demo['chosen']['shares'];source_shares=demo['target']['shares'];span=F(demo['target']['span_q'])
        changed_beats={ref for ref,a,b in zip(demo['target']['beat_refs'],source_shares,shares)if a!=b};trees={};assets={}
        for name,c in cases.items():
            path=root/name/'score.gp';validation=read(root/name/'gp7-validation.json')
            if sha(path)!=c['gp_sha256']or validation.get('error')or validation.get('directSource',{}).get('differences')!=0:raise ValueError('Native file/source validation mismatch')
            # The exporter saves a before-model only when standalone comparison
            # fails. A true native roundtrip needs no recovery comparison file.
            if not validation['roundtripPass']:
                if c['sidecar_sha256']is None or c['checked_field_comparison']!='MATCH' or c['checked_model']!=read(root/name/'roundtrip-before.json'):raise ValueError('GP playback differs from preexport checked fields')
            side=root/name/'score.exact-model-bends.json'
            if(sha(side)if side.exists()else None)!=c['sidecar_sha256']:raise ValueError('Native bend companion changed')
            folder=capture if name=='source'else qa/(name+'-capture')
            if set(c['capture_hashes'])!={p.name for p in folder.glob('*.json')}or any(sha(folder/n)!=h for n,h in c['capture_hashes'].items()):raise ValueError('Native capture binding changed')
            with zipfile.ZipFile(path)as z:
                names=z.namelist();gpifs=[n for n in names if n.endswith('.gpif')]
                if len(names)!=len(set(names))or len(gpifs)!=1:raise ValueError('Ambiguous GP archive inventory')
                tree=ET.fromstring(z.read(gpifs[0]));assets[name]={n:z.read(n)for n in names if n!=gpifs[0]}
            canonical_ids(tree);trees[name]=tree
            if len(c['notes'])!=len(tree.find('Notes')):raise ValueError('Native note denominator mismatch')
            mapping={r:[]for r in refs}
            for n in c['notes']:
                if n['source_ref']in mapping:mapping[n['source_ref']].append(n)
            if any(len(v)!=1 for v in mapping.values()):raise ValueError('Selected notes need unique actual native correspondence')
            # Read actual GP rhythm definitions; source validation reports alone
            # cannot certify the lengths used by this specific intervention.
            rhythms={n.get('id'):n for n in tree.find('Rhythms')};types={'Whole':1,'Half':2,'Quarter':4,'Eighth':8,'16th':16,'32nd':32,'64th':64,'128th':128}
            for ref,share in zip(refs,shares if name=='changed'else source_shares):
                note=mapping[ref][0];beat=_gp_beat(tree,note);definition=rhythms[beat.find('Rhythm').get('ref')]
                if set(definition.attrib)!={'id'}:raise ValueError('Unknown GP rhythm attributes')
                if len(definition)!=1 or definition[0].tag!='NoteValue'or definition[0].text not in types or F(4,types[definition[0].text])!=span*F(share):raise ValueError('Selected GP note length differs from relationship')
            if hashlib.sha256(c['raw_midi_json'].encode()).hexdigest()!=c['midi_event_sha256']or json.loads(c['raw_midi_json'])!=[e['data']for e in c['events']]:raise ValueError('Full MIDI event hash conflict')
            expected=Counter({(i,k):1 for i in range(len(c['callbacks']))for k in('NoteOnEvent','NoteOffEvent')})
            if Counter((e['binding'],e['kind'])for e in c['events']if e['binding']is not None)!=expected:raise ValueError('Paired note-event coverage differs')
            for e in c['events']:
                i=e['binding']
                if i is None:continue
                call=c['callbacks'][i];d=e['data']
                if (d['track'],d['channel'],d['noteKey'],d['noteVelocity'])!=(call['track'],call['channel'],call['key'],call['velocity'])or d['tick']!=call['start']+(call['length']if e['kind']=='NoteOffEvent'else 0):raise ValueError('Actual MIDI event does not match note callback')
        if assets['source']!=assets['zero']or assets['zero']!=assets['changed']:raise ValueError('Unrelated GP archive assets changed')
        if differences(trees['source'],trees['zero'])or cases['source']['raw_midi_json']!=cases['zero']['raw_midi_json']:raise ValueError('Source/zero GP or MIDI differ')
        altered=deepcopy(trees['changed']);selected=[]
        for beat in cases['changed']['beats']:
            if beat['source_beat_ref']not in changed_beats:continue
            old=_gp_beat(trees['zero'],beat).find('Rhythm');new=_gp_beat(altered,beat).find('Rhythm')
            selected.append(dict(source_beat_ref=beat['source_beat_ref'],old=dict(old.attrib),new=dict(new.attrib)))
            new.attrib.clear();new.attrib.update(old.attrib)
        if len(selected)!=len(changed_beats)or differences(trees['zero'],altered):raise ValueError('GP changed outside selected note lengths')
        a,b=cases['zero'],cases['changed']
        if a['notes']!=b['notes']or a['beats']!=b['beats']:raise ValueError('Native note/beat fields outside time changed')
        if len(a['callbacks'])!=len(b['callbacks']):raise ValueError('MIDI note count changed')
        timing=[];before_prefix=after_prefix=F(0);expected={}
        for ref,x,y in zip(refs,source_shares,shares):
            expected[ref]=((after_prefix-before_prefix)*span*960,span*F(y)*960)
            before_prefix+=F(x);after_prefix+=F(y)
        for i,(old,new)in enumerate(zip(a['callbacks'],b['callbacks'])):
            ref=old['source_ref']
            if ref not in expected:
                if old!=new:raise ValueError('Outside MIDI note moved or changed')
            else:
                if {k:v for k,v in old.items()if k not in('start','length')}!={k:v for k,v in new.items()if k not in('start','length')}:raise ValueError('Selected MIDI pitch/velocity/channel changed')
                delta,length=expected[ref]
                if F(new['start']-old['start'])!=delta or F(new['length'])!=length:raise ValueError('MIDI timing differs from source-group equation')
                timing.append(dict(source_ref=ref,old_start=old['start'],new_start=new['start'],old_length=old['length'],new_length=new['length']))
        if len(timing)!=len(refs):raise ValueError('Selected MIDI note occurrence coverage differs')
        if normalized_events(a,origins['cases']['zero'],refs)!=normalized_events(b,origins['cases']['changed'],refs):raise ValueError('Unrelated MIDI events changed')
        renders=read(root/'audio-jobs.results.json');jobs=read(root/'audio-jobs.json')
        expected_jobs={(m,v)for m in('source','zero','changed')for v in('focused','ensemble')}
        if len(renders)!=6 or len(jobs)!=6 or {(r['method'],r['mode'])for r in renders}!=expected_jobs or {(j['method'],j['mode'])for j in jobs}!=expected_jobs or len({r['font_sha256']for r in renders})!=1:raise ValueError('Complete six-render receipts required')
        jobmap={(j['method'],j['mode']):j for j in jobs}
        for r in renders:
            method,mode=r['method'],r['mode'];job=jobmap[method,mode]
            if any(r.get(k)!=v for k,v in job.items()):raise ValueError('Render receipt/job mismatch')
            if Path(job['file']).resolve()!=(root/method/'score.gp').resolve()or Path(job['out']).resolve()!=(root/method/(mode+'.wav')).resolve():raise ValueError('Render file binding differs')
            if r['midi_event_sha256']!=cases[method]['midi_event_sha256']or r['gp_sha256']!=cases[method]['gp_sha256']or sha(root/method/(mode+'.wav'))!=r['audio_sha256']or not 0<r['peak']<1 or 'fixed .3 gain'not in r['renderer']:raise ValueError('Render hashes/gain/clipping differ')
            if(r['track'],r['start_bar'],r['end_bar'],r['target_bar'])!=(demo['clip']['part'],demo['clip']['first'],demo['clip']['last'],demo['target']['bar'])or F(r['target_offset_q'])!=F(demo['target']['context_key'][4]):raise ValueError('Wrong rendered passage/track/cue')
        audio_results=[]
        for mode in('focused','ensemble'):
            s,sr=audio(root/'source'/f'{mode}.wav');z,zr=audio(root/'zero'/f'{mode}.wav');c,cr=audio(root/'changed'/f'{mode}.wav')
            if(sr,zr,cr)!=(44100,44100,44100)or s!=z or len(z)!=len(c):raise ValueError('Source/zero audio or changed length differs')
            if any(abs(r['seconds']-len(z)/zr)>1e-9 for r in renders if r['mode']==mode):raise ValueError('Audio length differs from render receipt')
            delta=(sum((x-y)**2 for x,y in zip(z,c))/len(z))**.5/32768
            if delta<=0 or max(map(abs,c))>=32767:raise ValueError('Silent change or clipped audio')
            audio_results.append(dict(mode=mode,source_zero_exact=True,changed_rms_difference=delta,seconds=len(c)/cr))
        details=dict(gp_duration_changes=selected,midi_timing=timing,audio=audio_results,fidelity='Existing checked GP fields, with exact-model bend companion when needed; no acoustic realism claim.')
    except Exception as e:issues.append(str(e))
    result=dict(status='FAIL'if issues else'PASS_GROUP_RHYTHM_GP_MIDI_AUDIO',issues=issues,**details,listening_judgment=None)
    (root/'rhythm-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    r=check(*sys.argv[1:4]);print(json.dumps(r,indent=2));raise SystemExit(r['status']=='FAIL')
