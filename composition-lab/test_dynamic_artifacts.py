"""Self-contained synthetic artifact-lock tests, not real converter/audio claims."""
from copy import deepcopy
import hashlib,json,tempfile,unittest,wave,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
from source_fact_tier1 import extract_documents
from check_local_dynamics import inventory,choices
from check_dynamic_artifacts import check,STATUS
from test_check_local_dynamics import documents,TARGET

def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wav(p,changed=False,clip=False):
    with wave.open(str(p),'wb')as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100)
        values=[(32767 if clip and i==5 else(1200 if changed else 1000)+(i%4)*100)for i in range(64)]
        w.writeframes(b''.join(v.to_bytes(2,'little',signed=True)for v in values))
def make(base):
    qa=base/'qa';native=base/'native';source=base/'source-capture';d=documents();changed=deepcopy(d);changed['track-0.json']['measures'][0]['voices'][0]['beats'][0]['velocity']='mf'
    for folder,docs in [(source,d),(qa/'zero-capture',d),(qa/'changed-capture',changed)]:
        for name,v in docs.items():dump(folder/name,v)
    before=extract_documents(d);after=extract_documents(changed);inv=inventory(before);target=next(x for x in inv['declarations']if x['fact_ref']==TARGET);chosen=next(o for o in choices(before,TARGET)['options']if o['marking']=='mf')
    dump(qa/'inventory.json',inv);dump(qa/'demonstration.json',dict(target=target,chosen=chosen,decision=dict(released=True,changed=True,chosen=chosen),controls=dict(context_policy='source_local_dynamic_level'),clip=dict(first=1,last=3,part=0)))
    dump(qa/'plan.json',dict(policy='source_local_dynamic_level',source_hashes={str(p.resolve()):sha(p)for p in source.glob('*.json')}))
    dump(qa/'zero-and-pair/zero-isolated/worker/output.json',before);dump(qa/'changed-isolated/worker/output.json',after)
    module=base/'alphaTab.mjs';module.write_text('// Synthetic test dependency, no actual alphaTab execution');core=base/'alphaTab.core.mjs';core.write_text('// Synthetic core')
    snapshot=dict(schema='native-dynamic-snapshot/1',module_path=str(module.resolve()),module_sha256=sha(module),core_sha256=sha(core),snapshot_script_sha256=sha(Path(__file__).with_name('audit_dynamic_gp.mjs')),cases={});renders=[]
    for method,data,folder in [('source',before,source),('zero',before,qa/'zero-capture'),('changed',after,qa/'changed-capture')]:
        out=native/method;out.mkdir(parents=True)
        states=inventory(data)['states'];state={x['occurrence_ref']:x for x in states};tree=E.Element('GPIF');tracks=E.SubElement(tree,'Tracks');E.SubElement(E.SubElement(E.SubElement(tracks,'Track'),'Staves'),'Staff');masters=E.SubElement(tree,'MasterBars');bars=E.SubElement(tree,'Bars');voices=E.SubElement(tree,'Voices');beats=E.SubElement(tree,'Beats');notes=E.SubElement(tree,'Notes');native_notes=[];native_beats=[];callbacks=[];events=[]
        for mi in range(3):
            E.SubElement(E.SubElement(masters,'MasterBar'),'Bars').text=str(mi);bar=E.SubElement(bars,'Bar',id=str(mi));E.SubElement(bar,'Voices').text=f'{mi*2} {mi*2+1}'
            for vi in range(2):
                voice=E.SubElement(voices,'Voice',id=str(mi*2+vi));ids=[]
                for bi in range(4):
                    index=(mi*2+vi)*4+bi;ids.append(str(index));ref=f'event:93:0:{mi+1}:{vi}:{bi}:0';mark=state[ref]['marking'].upper();beat=E.SubElement(beats,'Beat',id=str(index));E.SubElement(beat,'Dynamic').text=mark;E.SubElement(beat,'Notes').text=str(index);E.SubElement(notes,'Note',id=str(index));nr=f'native:0:{mi+1}:{vi}:{bi}';native_beats.append(dict(native_ref=nr,source_beat_ref=f'track-0.json#/measures/{mi}/voices/{vi}/beats/{bi}',part=0,bar=mi+1,voice=vi,beat=bi,dynamic=mark,grace=0,empty=False,source_refs=[ref]));native_notes.append(dict(native_ref=nr+':0',native_beat_ref=nr,source_ref=ref,source_group_refs=[ref],part=0,bar=mi+1,voice=vi,beat=bi,note=0,dynamic=mark,beat_dynamic=mark,pitch=60,string=1,fret=0,is_percussion=False,dead=False,ghost=False,accentuated=0,hammer_pull_origin=False,tie_destination=False,slide_origin_legato=False));vel={'PPP':15,'PP':31,'P':47,'MP':63,'MF':79,'F':95,'FF':111,'FFF':127}[mark];tick=mi*3840+bi*960;binding=len(callbacks);callbacks.append(dict(native_ref=nr+':0',source_ref=ref,track=0,start=tick,length=900,key=60,velocity=vel,channel=0))
                    for kind,t,typ in [('NoteOnEvent',tick,128),('NoteOffEvent',tick+900,144)]:events.append(dict(kind=kind,data=dict(track=0,tick=t,type=typ,channel=0,noteKey=60,noteVelocity=vel),binding=binding))
                E.SubElement(voice,'Beats').text=' '.join(ids)
        with zipfile.ZipFile(out/'score.gp','w')as z:z.writestr('Content/score.gpif',E.tostring(tree));z.writestr('Content/locked.bin',b'locked')
        dump(out/'gp7-validation.json',dict(roundtripPass=True,directSource=dict(differences=0)));events.sort(key=lambda x:x['data']['tick'])
        raw_midi=json.dumps([x['data']for x in events]);midi_hash=hashlib.sha256(raw_midi.encode()).hexdigest();snapshot['cases'][method]=dict(gp_sha256=sha(out/'score.gp'),sidecar_sha256=None,playback_profile={},capture_hashes={p.name:sha(p)for p in folder.glob('*.json')},notes=native_notes,beats=native_beats,mapping_qualifications=[],callbacks=callbacks,events=events,raw_midi_json=raw_midi,midi_event_sha256=midi_hash,midi_tick_shift=0)
        for mode in ('focused','ensemble'):
            wav(out/(mode+'.wav'),method=='changed');renders.append(dict(method=method,mode=mode,font_sha256='same-fixed-font',midi_event_sha256=midi_hash,gp_sha256=sha(out/'score.gp'),audio_sha256=sha(out/(mode+'.wav')),peak=.1,renderer='Synthetic test, fixed .3 gain'))
    dump(native/'dynamic-native-snapshot.json',snapshot);dump(native/'audio-jobs.results.json',renders);return native,qa

def paired_fixture(native):
    path=native/'dynamic-native-snapshot.json';snap=json.loads(path.read_text());snap['fidelity_scope']='gp_with_exact_model_bends'
    exporter=Path(__file__).parent/'songsterr_automation/songsterr_api/export_csv_gp7.mjs';lines=exporter.read_text().splitlines()
    snap['checked_model_extractor']=dict(path=str(exporter.resolve()),sha256=sha(exporter),curve_sha256=hashlib.sha256(next(l for l in lines if l.startswith('function curve(')).encode()).hexdigest(),snapshot_sha256=hashlib.sha256(next(l for l in lines if l.startswith('function snapshot(')).encode()).hexdigest())
    for method,case in snap['cases'].items():
        model=dict(bars=[[4,4,False,0,0]for _ in range(3)],tracks=[dict(staves=[dict(bars=[[[dict(notes=[dict(bend=[0]*61)])for _ in range(4)]for _ in range(2)]for _ in range(3)])])])
        dump(native/method/'roundtrip-before.json',model)
        side=dict(schema='composition-lab.exact-model-bends.v1',gp_sha256=case['gp_sha256'],curves=[dict(synthetic=True)],continuations=[])
        dump(native/method/'score.exact-model-bends.json',side)
        case.update(sidecar_sha256=sha(native/method/'score.exact-model-bends.json'),checked_model=model,pre_export_reference=dict(file='roundtrip-before.json',sha256=sha(native/method/'roundtrip-before.json')),checked_field_comparison='MATCH',restored_curves=1)
        dump(native/method/'gp7-validation.json',dict(roundtripPass=False,directSource=dict(differences=0),tracks=1,bars=3,notes=24))
    dump(path,snap)

def mutate_json(path,fn):
    x=json.loads(path.read_text());fn(x);dump(path,x)

class DynamicArtifactTests(unittest.TestCase):
 def run_case(self,mutation=None):
    with tempfile.TemporaryDirectory()as tmp:
        native,qa=make(Path(tmp))
        if mutation:mutation(native,qa)
        return check(native,qa)
 def test_exact_native_locks_and_coupled_midi_velocities(self):
    r=self.run_case();self.assertEqual(r['status'],STATUS,r);self.assertTrue(r['gp_dynamic_changes']);self.assertEqual({r['kind']for r in r['midi_velocity_changes']},{'NoteOnEvent','NoteOffEvent'})
 def test_unknown_or_changed_policy_cannot_downgrade_the_checker(self):
    def mutation(n,q):mutate_json(q/'demonstration.json',lambda j:j['controls'].update(context_policy='source_local_dynamic_transition'))
    r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertIn('policy differs',r['issues'][0])
    def unknown(n,q):
        mutate_json(q/'demonstration.json',lambda j:j['controls'].update(context_policy='pretend'))
        mutate_json(q/'plan.json',lambda j:j.update(policy='pretend'))
    r=self.run_case(unknown);self.assertEqual(r['status'],'FAIL');self.assertIn('Unknown dynamic',r['issues'][0])
 def test_roundtrip_failure_is_not_repaired_or_ignored(self):
    r=self.run_case(lambda n,q:mutate_json(n/'source/gp7-validation.json',lambda x:x.update(roundtripPass=False)))
    self.assertEqual(r['status'],'FAIL');self.assertIn('full roundtrip',r['issues'][0])
 def test_source_override_loss_fails_baseline(self):
    def mutation(n,q):
        mutate_json(n/'dynamic-native-snapshot.json',lambda x:x['cases']['source']['notes'][1].update(dynamic='F'))
    r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertTrue('Known source marking'in r['issues'][0]or'note dynamic'in r['issues'][0])
 def test_wrong_callback_velocity_fails(self):
    r=self.run_case(lambda n,q:mutate_json(n/'dynamic-native-snapshot.json',lambda x:x['cases']['changed']['callbacks'][0].update(velocity=80)))
    self.assertEqual(r['status'],'FAIL');self.assertIn('callback velocity',r['issues'][0])
 def test_changed_note_off_is_exactly_coupled_not_a_free_release_parameter(self):
    def mutation(n,q):
        def edit(x):
            row=next(e for e in x['cases']['changed']['events']if e['kind']=='NoteOffEvent');row['data']['noteVelocity']=1
        mutate_json(n/'dynamic-native-snapshot.json',edit)
    r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertTrue('event/callback'in r['issues'][0]or'raw MIDI'in r['issues'][0])
 def test_other_gp_property_change_fails(self):
    def mutation(n,q):
        p=n/'changed/score.gp'
        with zipfile.ZipFile(p)as z:members={k:z.read(k)for k in z.namelist()}
        root=E.fromstring(members['Content/score.gpif']);root.find('Notes')[0].set('unrelated','changed');members['Content/score.gpif']=E.tostring(root)
        with zipfile.ZipFile(p,'w')as z:
            for k,v in members.items():z.writestr(k,v)
        mutate_json(n/'dynamic-native-snapshot.json',lambda x:x['cases']['changed'].update(gp_sha256=sha(p)))
    r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertIn('Other GPIF',r['issues'][0])
 def test_no_pcm_change_cannot_claim_audible_change(self):
    def mutation(n,q):
        (n/'changed/focused.wav').write_bytes((n/'source/focused.wav').read_bytes())
        def edit(x):
            for r in x:
                if r['method']=='changed'and r['mode']=='focused':r['audio_sha256']=sha(n/'changed/focused.wav')
        mutate_json(n/'audio-jobs.results.json',edit)
    r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertIn('No actual rendered',r['issues'][0])
 def test_clipped_pcm_fails_even_when_report_claims_safe_peak(self):
    def mutation(n,q):
        wav(n/'changed/focused.wav',True,True)
        def edit(x):
            for r in x:
                if r['method']=='changed'and r['mode']=='focused':r['audio_sha256']=sha(n/'changed/focused.wav')
        mutate_json(n/'audio-jobs.results.json',edit)
    r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertIn('Clipped PCM',r['issues'][0])
 def test_omitted_midi_note_off_cannot_pass_complete_stream_binding(self):
    def mutation(n,q):
        snap=json.loads((n/'dynamic-native-snapshot.json').read_text());case=snap['cases']['changed'];case['events'].pop(1)
        case['raw_midi_json']=json.dumps([e['data']for e in case['events']]);case['midi_event_sha256']=hashlib.sha256(case['raw_midi_json'].encode()).hexdigest();dump(n/'dynamic-native-snapshot.json',snap)
        def update(rows):
            for r in rows:
                if r['method']=='changed':r['midi_event_sha256']=case['midi_event_sha256']
        mutate_json(n/'audio-jobs.results.json',update)
    r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertIn('denominator',r['issues'][0])
 def test_omitted_native_note_occurrence_fails(self):
    r=self.run_case(lambda n,q:mutate_json(n/'dynamic-native-snapshot.json',lambda x:x['cases']['source']['notes'].pop()))
    self.assertEqual(r['status'],'FAIL');self.assertIn('omitted note',r['issues'][0])
 def test_other_archive_asset_cannot_change(self):
    def mutation(n,q):
        p=n/'changed/score.gp'
        with zipfile.ZipFile(p)as z:members={k:z.read(k)for k in z.namelist()}
        members['Content/locked.bin']=b'changed'
        with zipfile.ZipFile(p,'w')as z:
            for k,v in members.items():z.writestr(k,v)
        mutate_json(n/'dynamic-native-snapshot.json',lambda x:x['cases']['changed'].update(gp_sha256=sha(p)))
    r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertIn('Other GP archive asset',r['issues'][0])
 def test_explicit_bundle_scope_preserves_standalone_failure(self):
    with tempfile.TemporaryDirectory()as tmp:
        n,q=make(Path(tmp));paired_fixture(n)
        report=check(n,q,fidelity_scope='gp_with_exact_model_bends');self.assertEqual(report['status'],'PASS_GP_BUNDLE_AND_AUDIO_DYNAMICS',report)
        self.assertTrue(all(not r['standalone_roundtrip_pass']and r['paired_checked_fields_pass']for r in report['artifact_fidelity']))
        self.assertEqual(check(n,q)['status'],'FAIL')
        self.assertFalse(json.loads((n/'source/gp7-validation.json').read_text())['roundtripPass'])
 def test_bundle_cannot_drop_mismatching_model_fields(self):
    with tempfile.TemporaryDirectory()as tmp:
        n,q=make(Path(tmp));paired_fixture(n)
        mutate_json(n/'dynamic-native-snapshot.json',lambda x:x['cases']['source']['checked_model']['tracks'][0].update(unexpected='difference'))
        r=check(n,q,fidelity_scope='gp_with_exact_model_bends');self.assertEqual(r['status'],'FAIL');self.assertIn('pre-export checked model',r['issues'][0])
 def test_bundle_reference_and_sidecar_tamper_fail(self):
    for filename in ('roundtrip-before.json','score.exact-model-bends.json'):
        with tempfile.TemporaryDirectory()as tmp:
            n,q=make(Path(tmp));paired_fixture(n);(n/'source'/filename).write_text('{}')
            r=check(n,q,fidelity_scope='gp_with_exact_model_bends');self.assertEqual(r['status'],'FAIL')
 def test_bundle_empty_model_does_not_fake_full_checked_coverage(self):
    with tempfile.TemporaryDirectory()as tmp:
        n,q=make(Path(tmp));paired_fixture(n);dump(n/'source/roundtrip-before.json',dict(bars=[],tracks=[]))
        def edit(x):
            c=x['cases']['source'];c['checked_model']=dict(bars=[],tracks=[]);c['pre_export_reference']['sha256']=sha(n/'source/roundtrip-before.json')
        mutate_json(n/'dynamic-native-snapshot.json',edit)
        r=check(n,q,fidelity_scope='gp_with_exact_model_bends');self.assertEqual(r['status'],'FAIL');self.assertIn('model denominator',r['issues'][0])
 def test_forged_source_beat_binding_is_not_accepted_by_matching_pitch(self):
    def mutation(n,q):
        def edit(x):x['cases']['source']['notes'][0]['source_ref']='event:93:0:1:0:2:0'
        mutate_json(n/'dynamic-native-snapshot.json',edit)
    r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertIn('another source beat',r['issues'][0])
 def test_missing_or_duplicated_render_receipt_is_not_a_complete_audit(self):
    for duplicate in (False,True):
        def mutation(n,q):
            def edit(rows):
                if duplicate:rows[-1]=deepcopy(rows[0])
                else:rows.pop()
            mutate_json(n/'audio-jobs.results.json',edit)
        r=self.run_case(mutation);self.assertEqual(r['status'],'FAIL');self.assertIn('six-render provenance',r['issues'][0])
if __name__=='__main__':unittest.main()
