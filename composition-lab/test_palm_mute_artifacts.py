"""Synthetic artifact corruption tests; not actual GP or acoustic evidence."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,tempfile,unittest,zipfile
import xml.etree.ElementTree as ET

from source_fact_tier1 import extract,extract_documents,project_documents
from test_dynamic_artifacts import make as dynamic_fixture,dump,sha,wav
from palm_mute_opportunity_census import inventory
from check_palm_mute_artifacts import check,check_source


def read(path):return json.loads(path.read_bytes())


def seal(native,snapshot,supplement):
    for case in snapshot['cases'].values():
        case['events'].sort(key=lambda e:e['data']['tick'])
        case['raw_midi_json']=json.dumps([e['data']for e in case['events']])
        case['midi_event_sha256']=hashlib.sha256(case['raw_midi_json'].encode()).hexdigest()
    dump(native/'dynamic-native-snapshot.json',snapshot)
    supplement['shared_snapshot']={'file':'dynamic-native-snapshot.json','sha256':sha(native/'dynamic-native-snapshot.json')}
    dump(native/'palm-mute-native-supplement.json',supplement)
    renders=read(native/'audio-jobs.results.json')
    for r in renders:
        case=snapshot['cases'][r['method']]
        r.update(gp_sha256=case['gp_sha256'],midi_event_sha256=case['midi_event_sha256'],audio_sha256=sha(native/r['method']/(r['mode']+'.wav')))
    dump(native/'audio-jobs.results.json',renders)


def make(base,*,start_muted=False,literal_only=False):
    native,qa=dynamic_fixture(base);source=base/'source-capture'
    docs={p.name:read(p)for p in source.glob('*.json')}
    for vi in range(2):
        if start_muted:docs['track-0.json']['measures'][0]['voices'][vi]['beats'][0]['palmMute']=True
    before=extract_documents(docs);target=next(r for r in inventory(before)['coattacks']if r['coattack_ref']=='coattack:0:0')
    wanted={'kind':'absent'}if start_muted else{'kind':'explicit','value':not literal_only}
    changed=deepcopy(docs)
    for vi in range(2):
        beat=changed['track-0.json']['measures'][0]['voices'][vi]['beats'][0]
        if start_muted:beat.pop('palmMute')
        else:beat['palmMute']=not literal_only
    for folder,data in((source,docs),(qa/'zero-capture',docs),(qa/'changed-capture',changed)):
        for filename,value in data.items():dump(folder/filename,value)
    dump(qa/'zero-isolated/worker/output.json',before);dump(qa/'changed-isolated/worker/output.json',extract(qa/'changed-capture'))
    demo=dict(target=target,chosen=dict(states=[deepcopy(wanted)for _ in target['beat_refs']],donor_refs=[]),controls=dict(context_policy='source_local_palm_mute'),clip=dict(first=1,last=3,part=0))
    dump(qa/'demonstration.json',demo);dump(qa/'plan.json',dict(policy='source_local_palm_mute',source_hashes={str(p.resolve()):sha(p)for p in source.glob('*.json')}))
    snapshot=read(native/'dynamic-native-snapshot.json');snapshot['fidelity_scope']='gp_with_exact_model_bends'
    core=Path(snapshot['module_path']).with_name('alphaTab.core.mjs')
    core.write_text('static QuarterTime = 960; static MaxPosition = 60; static _defaultDurationPalmMute = 80;')
    snapshot['core_sha256']=sha(core)
    baseline=deepcopy(snapshot['cases']['zero']);supp=dict(schema='native-palm-mute-supplement/1',adapter_sha256=sha(Path(__file__).with_name('audit_palm_mute_gp.mjs')),timing=dict(quarter_ticks=960,palm_mute_constant=80,position_scale=60),cases={})
    with zipfile.ZipFile(native/'zero/score.gp')as z:archive={n:z.read(n)for n in z.namelist()}
    jobs=[];renders=[]
    for method,data,folder in(('source',docs,source),('zero',docs,qa/'zero-capture'),('changed',changed,qa/'changed-capture')):
        case=deepcopy(baseline);tree=ET.fromstring(archive['Content/score.gpif']);rows=[];events=[]
        muted=start_muted if method!='changed'else not(start_muted or literal_only)
        for i,n in enumerate(case['notes']):
            props=ET.SubElement(tree.find('Notes')[i],'Properties')
            selected=n['source_ref']in target['member_refs']
            if muted and selected:ET.SubElement(ET.SubElement(props,'Property',name='PalmMuted'),'Enable')
            rows.append(dict(native_ref=n['native_ref'],is_palm_muted=muted and selected,beat_duration_ticks=960))
        for i,call in enumerate(case['callbacks']):
            selected=call['source_ref']in target['member_refs'];call['length']=160 if muted and selected else 960
            for kind,tick,typ in(('NoteOnEvent',call['start'],128),('NoteOffEvent',call['start']+call['length'],144)):
                events.append(dict(kind=kind,binding=i,data=dict(track=call['track'],tick=tick,type=typ,channel=call['channel'],noteKey=call['key'],noteVelocity=call['velocity'])))
        events.append(dict(kind='TempoChangeEvent',binding=None,data=dict(track=0,tick=0,type=81,beatsPerMinute=120)));case['events']=events
        path=native/method/'score.gp'
        with zipfile.ZipFile(path,'w')as z:
            for name,value in archive.items():z.writestr(name,ET.tostring(tree)if name.endswith('.gpif')else value)
        case.update(gp_sha256=sha(path),capture_hashes={p.name:sha(p)for p in folder.glob('*.json')})
        snapshot['cases'][method]=case;supp['cases'][method]=dict(gp_sha256=sha(path),notes=rows)
        for mode in('focused','ensemble'):
            job=dict(method=method,mode=mode,file=str(path.resolve()),out=str((native/method/(mode+'.wav')).resolve()),track=0,start_bar=1,end_bar=3,target_bar=1,target_offset_q='0')
            jobs.append(job);renders.append(dict(**job,font_sha256='synthetic-same-font',peak=.1,renderer='Synthetic fixture, fixed .3 gain',seconds=64/44100,target_seconds=0))
    dump(native/'audio-jobs.json',jobs);dump(native/'audio-jobs.results.json',renders);seal(native,snapshot,supp)
    return native,qa


def edit(native,fn):
    snapshot=read(native/'dynamic-native-snapshot.json');supp=read(native/'palm-mute-native-supplement.json');fn(snapshot,supp);seal(native,snapshot,supp)


def mutate_json(path,fn):
    data=read(path);fn(data);dump(path,data)


def edit_gp(native,fn=None,asset=False):
    p=native/'changed/score.gp'
    with zipfile.ZipFile(p)as z:members={n:z.read(n)for n in z.namelist()}
    if asset:members['Content/locked.bin']=b'changed'
    else:
        tree=ET.fromstring(members['Content/score.gpif']);fn(tree);members['Content/score.gpif']=ET.tostring(tree)
    with zipfile.ZipFile(p,'w')as z:
        for n,v in members.items():z.writestr(n,v)
    edit(native,lambda s,x:(s['cases']['changed'].update(gp_sha256=sha(p)),x['cases']['changed'].update(gp_sha256=sha(p))))


class PalmMuteArtifactTests(unittest.TestCase):
    def run_case(self,mutation=None,**kwargs):
        with tempfile.TemporaryDirectory()as temp:
            native,qa=make(Path(temp),**kwargs)
            if mutation:mutation(native,qa)
            return check(native,qa)

    def test_whole_multi_voice_coattack_mute_and_unmute(self):
        for start_muted in(False,True):
            r=self.run_case(start_muted=start_muted)
            self.assertEqual(r['status'],'PASS_NATIVE_PALM_MUTE_PCM_CHANGED',r)
            self.assertEqual(len(r['gp_mute_changes']),2);self.assertEqual(len(r['midi_duration_changes']),2)

    def test_partial_coattack_or_unrelated_source_change_is_refused(self):
        with tempfile.TemporaryDirectory()as temp:
            n,q=make(Path(temp));before=extract(q/'zero-capture');docs=project_documents(before);demo=read(q/'demonstration.json')
            demo['target']['member_refs']=demo['target']['member_refs'][:1]
            demo['target']['beat_refs']=demo['target']['beat_refs'][:1]
            demo['target']['declarations']=demo['target']['declarations'][:1];demo['chosen']['states']=demo['chosen']['states'][:1]
            docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['palmMute']=True
            r=check_source(before,extract_documents(docs),demo)
            self.assertEqual(r['status'],'FAIL');self.assertIn('complete same-part',r['issues'][0])
        def unrelated(n,q):
            mutate_json(q/'changed-capture/track-0.json',lambda d:d['measures'][1]['voices'][0]['beats'][0]['notes'][0].update(fret=1))
            dump(q/'changed-isolated/worker/output.json',extract(q/'changed-capture'))
        r=self.run_case(unrelated);self.assertEqual(r['status'],'FAIL');self.assertIn('outside target',r['issues'][0])

    def test_unrelated_gp_fields_archive_assets_and_partial_flags_fail(self):
        for mutation in(
            lambda n,q:edit_gp(n,lambda t:t.find('Notes')[2].set('unrelated','changed')),
            lambda n,q:edit_gp(n,asset=True),
            lambda n,q:edit_gp(n,lambda t:t.find('Notes')[4].find('Properties').clear()),
        ):
            self.assertEqual(self.run_case(mutation)['status'],'FAIL')

    def test_archive_inventory_and_inactive_playback_profile_are_locked(self):
        def renamed(n,q):
            path=n/'changed/score.gp'
            with zipfile.ZipFile(path)as z:members={name:z.read(name)for name in z.namelist()}
            members['Content/renamed.gpif']=members.pop('Content/score.gpif')
            with zipfile.ZipFile(path,'w')as z:
                for name,value in members.items():z.writestr(name,value)
            edit(n,lambda s,p:(s['cases']['changed'].update(gp_sha256=sha(path)),p['cases']['changed'].update(gp_sha256=sha(path))))
        r=self.run_case(renamed);self.assertEqual(r['status'],'FAIL');self.assertIn('inventory changed',r['issues'][0])
        def profile(n,q):
            value={'noteSlightAmplitude':1.5};dump(n/'changed/score.playback.json',value)
            edit(n,lambda s,p:s['cases']['changed'].update(playback_profile=value))
        r=self.run_case(profile);self.assertEqual(r['status'],'FAIL');self.assertIn('across cases',r['issues'][0])

    def test_midi_pitch_attack_velocity_and_wrong_release_fail(self):
        for field in('key','start','velocity','length'):
            with self.subTest(field=field):
                def mutation(n,q):
                    def changed(s,p):
                        c=s['cases']['changed'];c['callbacks'][0][field]+=1
                        for row in c['events']:
                            if row['binding']!=0:continue
                            call=c['callbacks'][0];row['data'].update(noteKey=call['key'],noteVelocity=call['velocity'],tick=call['start']+(call['length']if row['kind']=='NoteOffEvent'else 0))
                    edit(n,changed)
                self.assertEqual(self.run_case(mutation)['status'],'FAIL')

    def test_every_repeated_attack_uses_its_actual_tempo(self):
        def repeated(n,q):
            def change(s,p):
                for name,c in s['cases'].items():
                    call=deepcopy(c['callbacks'][0]);call.update(start=10000,length=320 if name=='changed'else 960);index=len(c['callbacks']);c['callbacks'].append(call)
                    c['events'].append(dict(kind='TempoChangeEvent',binding=None,data=dict(track=0,tick=10000,type=81,beatsPerMinute=240)))
                    for kind,tick,typ in(('NoteOnEvent',10000,128),('NoteOffEvent',10000+call['length'],144)):
                        c['events'].append(dict(kind=kind,binding=index,data=dict(track=0,tick=tick,type=typ,channel=0,noteKey=call['key'],noteVelocity=call['velocity'])))
            edit(n,change)
        r=self.run_case(repeated);self.assertEqual(r['status'],'PASS_NATIVE_PALM_MUTE_PCM_CHANGED',r);self.assertEqual(len(r['midi_duration_changes']),3)

    def test_other_simultaneous_midi_event_order_stays_locked(self):
        def mutation(n,q):
            def change(s,p):
                rows=s['cases']['changed']['events'];indices=[i for i,e in enumerate(rows)if e['kind']=='NoteOnEvent'and e['data']['tick']==0]
                rows[indices[0]],rows[indices[1]]=rows[indices[1]],rows[indices[0]]
            edit(n,change)
        r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertIn('event order',r['issues'][0])

    def test_inaudible_result_is_honest_and_identical_midi_cannot_change_audio(self):
        def identical(n,q):
            for mode in('focused','ensemble'):(n/'changed'/(mode+'.wav')).write_bytes((n/'zero'/(mode+'.wav')).read_bytes())
            edit(n,lambda s,p:None)
        r=self.run_case(identical);self.assertEqual(r['status'],'PASS_NATIVE_PALM_MUTE_PCM_IDENTICAL',r);self.assertFalse(r['pcm_difference_measured'])
        r=self.run_case(literal_only=True);self.assertEqual(r['status'],'FAIL');self.assertIn('identical MIDI',r['issues'][0])
        r=self.run_case(identical,literal_only=True);self.assertEqual(r['status'],'PASS_NATIVE_PALM_MUTE_PCM_IDENTICAL',r);self.assertEqual(r['gp_mute_changes'],[])

    def test_complete_render_and_source_bindings_required(self):
        for mutation in(
            lambda n,q:mutate_json(n/'audio-jobs.results.json',lambda rows:rows.pop()),
            lambda n,q:mutate_json(n/'audio-jobs.results.json',lambda rows:rows[0].update(target_bar=2)),
            lambda n,q:mutate_json(q/'plan.json',lambda p:p.update(source_hashes={})),
            lambda n,q:dump(q/'changed-isolated/worker/output.json',{}),
            lambda n,q:edit(n,lambda s,p:p['timing'].update(palm_mute_constant=81)),
            lambda n,q:edit(n,lambda s,p:s['cases']['changed']['notes'].pop()),
            lambda n,q:edit(n,lambda s,p:s['cases']['changed']['events'].pop()),
        ):
            self.assertEqual(self.run_case(mutation)['status'],'FAIL')


if __name__=='__main__':unittest.main()
