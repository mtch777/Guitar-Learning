"""Synthetic corruption tests only; not converter or audio quality evidence."""
from copy import deepcopy
import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from source_fact_tier1 import extract_documents,extract
from check_local_accents import Oracle,POLICY
from check_accent_artifacts import check,STATUS
from test_dynamic_artifacts import make as base_fixture,dump,sha,wav,paired_fixture

TARGET='event:93:0:1:0:0:0'


def seal(native,snapshot):
    original=deepcopy(snapshot);original.pop('shared_snapshot',None);original.pop('accent_adapter_sha256',None);original['schema']='native-dynamic-snapshot/1'
    dump(native/'dynamic-native-snapshot.json',original)
    snapshot['shared_snapshot']=dict(file='dynamic-native-snapshot.json',sha256=sha(native/'dynamic-native-snapshot.json'))
    snapshot['accent_adapter_sha256']=sha(Path(__file__).with_name('audit_local_accent_gp.mjs'))
    dump(native/'accent-native-snapshot.json',snapshot)


def make(base,mark='mf'):
    native,qa=base_fixture(base);source=base/'source-capture';docs={p.name:json.loads(p.read_text())for p in source.glob('*.json')}
    for mi,m in enumerate(docs['track-0.json']['measures']):
        for vi,v in enumerate(m['voices']):
            for bi,b in enumerate(v['beats']):
                b.pop('velocity',None)
                if mi==0 and bi==0:b['velocity']=mark
                for n in b['notes']:n.pop('velocity',None)
    docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0]['accentuated']=1
    changed=deepcopy(docs);changed['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['accentuated']=1
    for folder,d in((source,docs),(qa/'zero-capture',docs),(qa/'changed-capture',changed)):
        for name,value in d.items():dump(folder/name,value)
    before=extract(source);after=extract(qa/'changed-capture');oracle=Oracle(before);ev=oracle.options(TARGET)
    from declared_degree_choices import sample
    for seed in range(32):
        chosen,decision=sample(ev,dict(voicing=100,seed=seed))
        if chosen['state']=={'kind':'explicit','value':1}:break
    demo=dict(target=ev['target'],chosen=chosen,decision=decision,controls=dict(context_policy=POLICY,accents=100,target_ref=TARGET,seed=seed),clip=dict(first=1,last=3,part=0))
    dump(qa/'demonstration.json',demo);dump(qa/'inventory.json',oracle.inventory());dump(qa/'plan.json',dict(policy=POLICY,source_hashes={str(p.resolve()):sha(p)for p in source.glob('*.json')}))
    dump(qa/'zero-and-pair/zero-isolated/worker/output.json',before);dump(qa/'changed-isolated/worker/output.json',after)
    s=json.loads((native/'dynamic-native-snapshot.json').read_text());s['schema']='native-accent-snapshot/1'
    renders=json.loads((native/'audio-jobs.results.json').read_text())
    for r in renders:r.update(track=0,start_bar=1,end_bar=3,target_bar=1,target_offset_q='0',seconds=64/44100)
    for method,c in s['cases'].items():
        folder=source if method=='source'else qa/(method+'-capture');c['capture_hashes']={p.name:sha(p)for p in folder.glob('*.json')}
        for b in c['beats']:b['dynamic']=mark.upper()
        for n in c['notes']:
            n['dynamic']=n['beat_dynamic']=mark.upper();n['accentuated']=int(n['source_ref']=='event:93:0:2:0:0:0'or method=='changed'and n['source_ref']==TARGET)
        notes={n['native_ref']:n for n in c['notes']}
        for call in c['callbacks']:call['velocity']=min(127,15+16*(('ppp','pp','p','mp','mf','f','ff','fff').index(mark)+notes[call['native_ref']]['accentuated']))
        for event in c['events']:event['data']['noteVelocity']=c['callbacks'][event['binding']]['velocity']
        c['raw_midi_json']=json.dumps([e['data']for e in c['events']]);c['midi_event_sha256']=hashlib.sha256(c['raw_midi_json'].encode()).hexdigest()
        gp=native/method/'score.gp'
        with zipfile.ZipFile(gp)as z:members={k:z.read(k)for k in z.namelist()}
        tree=ET.fromstring(members['Content/score.gpif'])
        for b in tree.find('Beats'):b.find('Dynamic').text=mark.upper()
        for n,row in zip(tree.find('Notes'),c['notes']):
            if row['accentuated']:ET.SubElement(n,'Accent').text='8'
        members['Content/score.gpif']=ET.tostring(tree)
        with zipfile.ZipFile(gp,'w')as z:
            for k,v in members.items():z.writestr(k,v)
        c['gp_sha256']=sha(gp)
        for r in renders:
            if r['method']==method:r.update(gp_sha256=c['gp_sha256'],midi_event_sha256=c['midi_event_sha256'])
    seal(native,s);dump(native/'audio-jobs.results.json',renders);return native,qa


def change_gp(native,mutation):
    gp=native/'changed/score.gp'
    with zipfile.ZipFile(gp)as z:members={k:z.read(k)for k in z.namelist()}
    tree=ET.fromstring(members['Content/score.gpif']);mutation(tree);members['Content/score.gpif']=ET.tostring(tree)
    with zipfile.ZipFile(gp,'w')as z:
        for k,v in members.items():z.writestr(k,v)
    s=json.loads((native/'accent-native-snapshot.json').read_text());s['cases']['changed']['gp_sha256']=sha(gp);seal(native,s)
    rows=json.loads((native/'audio-jobs.results.json').read_text())
    for r in rows:
        if r['method']=='changed':r['gp_sha256']=sha(gp)
    dump(native/'audio-jobs.results.json',rows)


class AccentArtifactTests(unittest.TestCase):
    def run_case(self,mutation=None):
        with tempfile.TemporaryDirectory()as tmp:
            n,q=make(Path(tmp))
            if mutation:mutation(n,q)
            return check(n,q)

    def test_one_accent_with_locked_dynamics_and_actual_velocity(self):
        r=self.run_case();self.assertEqual(r['status'],STATUS,r);self.assertEqual(len(r['gp_accent_changes']),1);self.assertEqual(len(r['midi_velocity_changes']),2)

    def test_capture_directory_enumeration_does_not_change_worker_fixture(self):
        from unittest.mock import patch
        original=Path.glob
        with patch.object(Path,'glob',lambda p,pattern:iter(sorted(original(p,pattern),key=lambda f:f.name,reverse=True))):
            r=self.run_case()
        self.assertEqual(r['status'],STATUS,r)

    def test_native_json_unicode_does_not_depend_on_windows_locale(self):
        from unittest.mock import patch
        from check_dynamic_artifacts import read
        original=Path.read_text
        def legacy_locale(path,*args,**kwargs):
            if not args and not kwargs.get('encoding'):kwargs['encoding']='cp1252'
            return original(path,*args,**kwargs)
        value={'source_title':'C\u266f_4: \u201csource\u201d'}
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'native.json';p.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
            with patch.object(Path,'read_text',legacy_locale):self.assertEqual(read(p),value)

    def test_wrong_note_or_written_dynamic_or_unrelated_gp_field(self):
        for mutation in(lambda t:t.find('Beats')[0].find('Dynamic').__setattr__('text','F'),lambda t:t.find('Notes')[1].set('other','changed'),lambda t:ET.SubElement(t.find('Notes')[1],'Accent').__setattr__('text','8')):
            r=self.run_case(lambda n,q:change_gp(n,mutation));self.assertEqual(r['status'],'FAIL')

    def test_forged_raw_outside_field_and_chosen_evidence(self):
        def edit(n,q):
            p=q/'changed-capture/track-0.json';d=json.loads(p.read_text());d['measures'][2]['voices'][0]['beats'][0]['notes'][0]['fret']=5;dump(p,d)
        self.assertEqual(self.run_case(edit)['status'],'FAIL')
        def forged(n,q):
            p=q/'demonstration.json';d=json.loads(p.read_text());d['chosen']['donor_refs']=[];dump(p,d)
        self.assertEqual(self.run_case(forged)['status'],'FAIL')

    def test_wrong_midi_attack_clock_velocity_or_missing_event(self):
        for kind in('velocity','clock','missing'):
            def edit(n,q):
                s=json.loads((n/'accent-native-snapshot.json').read_text());c=s['cases']['changed']
                if kind=='velocity':c['callbacks'][0]['velocity']=1
                elif kind=='clock':c['events'][0]['data']['tick']+=1
                else:c['events'].pop()
                c['raw_midi_json']=json.dumps([e['data']for e in c['events']]);c['midi_event_sha256']=hashlib.sha256(c['raw_midi_json'].encode()).hexdigest();seal(n,s)
            self.assertEqual(self.run_case(edit)['status'],'FAIL')

    def test_unchanged_or_clipped_pcm_with_aligned_receipts_fails(self):
        for clipped in(False,True):
            def edit(n,q):
                p=n/'changed/focused.wav'
                if clipped:wav(p,True,True)
                else:p.write_bytes((n/'source/focused.wav').read_bytes())
                rows=json.loads((n/'audio-jobs.results.json').read_text())
                for r in rows:
                    if r['method']=='changed'and r['mode']=='focused':r['audio_sha256']=sha(p)
                dump(n/'audio-jobs.results.json',rows)
            self.assertEqual(self.run_case(edit)['status'],'FAIL')

    def test_aligned_audio_from_wrong_clip_cannot_pass_hash_receipts(self):
        def edit(n,q):
            rows=json.loads((n/'audio-jobs.results.json').read_text())
            for r in rows:r.update(start_bar=2,target_offset_q='1')
            dump(n/'audio-jobs.results.json',rows)
        self.assertEqual(self.run_case(edit)['status'],'FAIL')

    def test_standalone_failure_or_snapshot_dependency_cannot_be_waived(self):
        def edit(n,q):dump(n/'source/gp7-validation.json',dict(roundtripPass=False,directSource=dict(differences=0)))
        self.assertEqual(self.run_case(edit)['status'],'FAIL')
        def drift(n,q):
            s=json.loads((n/'accent-native-snapshot.json').read_text());s['snapshot_script_sha256']='0'*64;seal(n,s)
        self.assertEqual(self.run_case(drift)['status'],'FAIL')

    def test_clamped_attack_is_not_audible_even_with_forged_pcm_difference(self):
        with tempfile.TemporaryDirectory()as tmp:
            n,q=make(Path(tmp),mark='fff');r=check(n,q)
            self.assertEqual(r['status'],'FAIL');self.assertIn('clamped',r['issues'][0])

    def test_all_repeated_target_attacks_are_owned_and_verified(self):
        with tempfile.TemporaryDirectory()as tmp:
            n,q=make(Path(tmp));s=json.loads((n/'accent-native-snapshot.json').read_text())
            for c in s['cases'].values():
                call=deepcopy(c['callbacks'][0]);call['start']+=20000;binding=len(c['callbacks']);c['callbacks'].append(call)
                for kind,delta,typ in(('NoteOnEvent',0,128),('NoteOffEvent',call['length'],144)):
                    c['events'].append(dict(kind=kind,binding=binding,data=dict(track=call['track'],channel=call['channel'],noteKey=call['key'],noteVelocity=call['velocity'],tick=call['start']+delta,type=typ)))
                c['events'].sort(key=lambda e:e['data']['tick']);c['raw_midi_json']=json.dumps([e['data']for e in c['events']]);c['midi_event_sha256']=hashlib.sha256(c['raw_midi_json'].encode()).hexdigest()
            seal(n,s);renders=json.loads((n/'audio-jobs.results.json').read_text())
            for r in renders:r['midi_event_sha256']=s['cases'][r['method']]['midi_event_sha256']
            dump(n/'audio-jobs.results.json',renders);r=check(n,q)
            self.assertEqual(r['status'],STATUS,r);self.assertEqual(len(r['midi_velocity_changes']),4)

    def test_bundle_scope_explicit_and_restored_model_stays_bound(self):
        with tempfile.TemporaryDirectory()as tmp:
            n,q=make(Path(tmp));paired_fixture(n);s=json.loads((n/'dynamic-native-snapshot.json').read_text());s['schema']='native-accent-snapshot/1';seal(n,s)
            self.assertEqual(check(n,q)['status'],'FAIL')
            r=check(n,q,fidelity_scope='gp_with_exact_model_bends');self.assertEqual(r['status'],'PASS_GP_BUNDLE_AND_AUDIO_ACCENTS',r)
            s['cases']['source']['checked_model']['tracks'][0]['forged']=1;seal(n,s)
            self.assertEqual(check(n,q,fidelity_scope='gp_with_exact_model_bends')['status'],'FAIL')


if __name__=='__main__':unittest.main()
