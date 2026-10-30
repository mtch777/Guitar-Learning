"""Synthetic corruption tests: these fixtures do not claim real GP/audio execution."""
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import hashlib,json,tempfile,unittest,zipfile
import xml.etree.ElementTree as E
from source_fact_tier1 import extract,extract_documents
from test_check_group_rhythm import source
from test_dynamic_artifacts import dump,sha,wav
from check_group_rhythm_artifacts import check,normalized_events
import local_group_rhythm as rhythm


def seal(native,snapshot,origins=None):
    for case in snapshot['cases'].values():
        case['raw_midi_json']=json.dumps([e['data']for e in case['events']])
        case['midi_event_sha256']=hashlib.sha256(case['raw_midi_json'].encode()).hexdigest()
    dump(native/'dynamic-native-snapshot.json',snapshot)
    if origins is None:
        origins={name:[dict(origin_source_ref=e.pop('_origin'),kind=e['kind'],data=deepcopy(e['data']))for e in deepcopy(c['events'])]for name,c in snapshot['cases'].items()}
    dump(native/'rhythm-midi-origins.json',dict(schema='actual-native-midi-origins/1',script_sha256=sha(Path(__file__).with_name('audit_group_rhythm_origins.mjs')),snapshot_sha256=sha(native/'dynamic-native-snapshot.json'),cases=origins))


def make(base):
    qa,native,capture=base/'qa',base/'native',base/'source-capture';docs=source();before=extract_documents(docs)
    inventory=rhythm.inventory(before);target=next(g for g in inventory['groups']if not g['reasons']);options=rhythm.options(before,target['id'])
    seed=next(s for s in range(64)if rhythm.sample(options,dict(context_policy=rhythm.POLICY,rhythm=100,target_ref=target['id'],seed=s))[1]['changed'])
    controls=dict(context_policy=rhythm.POLICY,rhythm=100,target_ref=target['id'],seed=seed);chosen,decision=rhythm.sample(options,controls)
    changed=deepcopy(docs)
    for beat,share in zip(changed['track-0.json']['measures'][0]['voices'][0]['beats'],chosen['shares']):
        beat['type']=int(4/F(share));beat['duration']=[3,3*beat['type']]
    for folder,data in((capture,docs),(qa/'zero-capture',docs),(qa/'changed-capture',changed)):
        for name,value in data.items():dump(folder/name,value)
    dump(qa/'zero-isolated/worker/output.json',extract(capture));dump(qa/'changed-isolated/worker/output.json',extract(qa/'changed-capture'))
    dump(qa/'demonstration.json',dict(target=target,chosen=chosen,decision=decision,controls=controls,clip=dict(first=1,last=3,part=0)))
    dump(qa/'plan.json',dict(policy=rhythm.POLICY,source_hashes={str(p.resolve()):sha(p)for p in capture.glob('*.json')}))
    module=base/'alphaTab.mjs';module.write_text('// Synthetic module');core=base/'alphaTab.core.mjs';core.write_text('// Synthetic core')
    snapshot=dict(schema='native-dynamic-snapshot/1',fidelity_scope='gp_with_exact_model_bends',module_path=str(module.resolve()),module_sha256=sha(module),core_sha256=sha(core),snapshot_script_sha256=sha(Path(__file__).with_name('audit_dynamic_gp.mjs')),cases={});origins={};renders=[]
    exporter=Path(__file__).parent/'songsterr_automation/songsterr_api/export_csv_gp7.mjs';lines=exporter.read_text(encoding='utf-8').splitlines()
    snapshot['checked_model_extractor']=dict(path=str(exporter.resolve()),sha256=sha(exporter),curve_sha256=hashlib.sha256(next(l for l in lines if l.startswith('function curve(')).encode()).hexdigest(),snapshot_sha256=hashlib.sha256(next(l for l in lines if l.startswith('function snapshot(')).encode()).hexdigest())
    for name,data,folder in(('source',docs,capture),('zero',docs,qa/'zero-capture'),('changed',changed,qa/'changed-capture')):
        out=native/name;out.mkdir(parents=True);tree=E.Element('GPIF');tracks=E.SubElement(tree,'Tracks');E.SubElement(E.SubElement(E.SubElement(tracks,'Track'),'Staves'),'Staff')
        masters=E.SubElement(tree,'MasterBars');bars=E.SubElement(tree,'Bars');voices=E.SubElement(tree,'Voices');beats=E.SubElement(tree,'Beats');notes=E.SubElement(tree,'Notes');types=E.SubElement(tree,'Rhythms')
        for value,label in((4,'Quarter'),(8,'Eighth'),(16,'16th')):E.SubElement(E.SubElement(types,'Rhythm',id=f'r{value}'),'NoteValue').text=label
        native_notes=[];native_beats=[];callbacks=[];events=[];event_origins=[]
        for mi,measure in enumerate(data['track-0.json']['measures']):
            E.SubElement(E.SubElement(masters,'MasterBar'),'Bars').text=str(mi);bar=E.SubElement(bars,'Bar',id=str(mi));E.SubElement(bar,'Voices').text=str(mi);voice=E.SubElement(voices,'Voice',id=str(mi));ids=[];position=F(mi*4)
            for bi,raw in enumerate(measure['voices'][0]['beats']):
                index=len(ids)+mi*6;ids.append(str(index));ref=f'event:888:0:{mi+1}:0:{bi}:0';nr=f'native:0:{mi+1}:0:{bi}';beat=E.SubElement(beats,'Beat',id=str(index));E.SubElement(beat,'Dynamic').text='MF';E.SubElement(beat,'Notes').text=str(index);E.SubElement(beat,'Rhythm',ref=f'r{raw["type"]}')
                note=E.SubElement(notes,'Note',id=str(index));properties=E.SubElement(note,'Properties');E.SubElement(E.SubElement(properties,'Property',name='String'),'String').text='0';E.SubElement(E.SubElement(properties,'Property',name='Fret'),'Fret').text='3'
                for tag in('ConcertPitch','TransposedPitch'):
                    p=E.SubElement(note,tag);E.SubElement(p,'Step').text='G';E.SubElement(p,'Accidental').text='';E.SubElement(p,'Octave').text='2'
                native_beats.append(dict(native_ref=nr,source_beat_ref=f'track-0.json#/measures/{mi}/voices/0/beats/{bi}',part=0,bar=mi+1,voice=0,beat=bi,dynamic='MF',grace=0,empty=False,source_refs=[ref]))
                native_notes.append(dict(native_ref=nr+':0',native_beat_ref=nr,source_ref=ref,source_group_refs=[ref],part=0,bar=mi+1,voice=0,beat=bi,note=0,dynamic='MF',beat_dynamic='MF',pitch=43,string=1,fret=3,is_percussion=False,dead=False,ghost=False,accentuated=0,hammer_pull_origin=False,tie_destination=False,slide_origin_legato=False))
                duration=F(*raw['duration'])*4;start=int(position*960);length=int(duration*960);binding=len(callbacks);callbacks.append(dict(native_ref=nr+':0',source_ref=ref,track=0,start=start,length=length,key=43,velocity=79,channel=0))
                events.append(dict(kind='NoteBendEvent',binding=None,data=dict(track=0,tick=start,type=96,channel=0,noteKey=43,value=2147483648),_origin=ref))
                for kind,tick,typ in(('NoteOnEvent',start,128),('NoteOffEvent',start+length,144)):events.append(dict(kind=kind,binding=binding,data=dict(track=0,tick=tick,type=typ,channel=0,noteKey=43,noteVelocity=79),_origin=ref))
                position+=duration
            E.SubElement(voice,'Beats').text=' '.join(ids)
        with zipfile.ZipFile(out/'score.gp','w')as z:z.writestr('Content/score.gpif',E.tostring(tree));z.writestr('Content/locked.bin',b'locked')
        dump(out/'gp7-validation.json',dict(roundtripPass=True,sha256=sha(out/'score.gp'),directSource=dict(differences=0),directPitchedGraces=dict(status='PASS_INDEPENDENT_PITCHED_SOURCE_GRACES',differences=[])))
        events.sort(key=lambda e:e['data']['tick']);origins[name]=[dict(origin_source_ref=e.pop('_origin'),kind=e['kind'],data=deepcopy(e['data']))for e in events]
        snapshot['cases'][name]=dict(gp_sha256=sha(out/'score.gp'),sidecar_sha256=None,playback_profile={},capture_hashes={p.name:sha(p)for p in folder.glob('*.json')},notes=native_notes,beats=native_beats,mapping_qualifications=[],callbacks=callbacks,events=events,midi_tick_shift=0,checked_field_comparison='MATCH')
        for mode in('focused','ensemble'):
            wav(out/(mode+'.wav'),name=='changed');renders.append(dict(case_id=name+'-'+mode,method=name,mode=mode,file=str((out/'score.gp').resolve()),out=str((out/(mode+'.wav')).resolve()),track=0,start_bar=1,end_bar=3,target_bar=1,target_offset_q='0',playback_profile={},font_sha256='same-fixed-font',gp_sha256=sha(out/'score.gp'),audio_sha256=sha(out/(mode+'.wav')),seconds=64/44100,peak=.1,target_seconds=0,reader='Synthetic fixture',renderer='Synthetic test, fixed .3 gain',exact_model_bend_restore=None))
    seal(native,snapshot,origins)
    for r in renders:r['midi_event_sha256']=snapshot['cases'][r['method']]['midi_event_sha256']
    dump(native/'audio-jobs.results.json',renders)
    fields=('case_id','method','mode','file','out','track','start_bar','end_bar','target_bar','target_offset_q')
    dump(native/'audio-jobs.json',[{k:r[k]for k in fields}for r in renders])
    return native,qa,capture


def mutate_json(path,fn):
    data=json.loads(path.read_bytes());fn(data);dump(path,data)


def edit_snapshot(native,fn):
    s=json.loads((native/'dynamic-native-snapshot.json').read_bytes());origins=json.loads((native/'rhythm-midi-origins.json').read_bytes())['cases'];fn(s,origins);seal(native,s,origins)


def edit_gp(native,fn,asset=False):
    p=native/'changed/score.gp'
    with zipfile.ZipFile(p)as z:members={k:z.read(k)for k in z.namelist()}
    if asset:members['Content/locked.bin']=b'changed'
    else:
        t=E.fromstring(members['Content/score.gpif']);fn(t);members['Content/score.gpif']=E.tostring(t)
    with zipfile.ZipFile(p,'w')as z:
        for k,v in members.items():z.writestr(k,v)
    edit_snapshot(native,lambda s,o:s['cases']['changed'].update(gp_sha256=sha(p)))
    mutate_json(native/'changed/gp7-validation.json',lambda v:v.update(sha256=sha(p)))
    mutate_json(native/'audio-jobs.results.json',lambda rows:[r.update(gp_sha256=sha(p))for r in rows if r['method']=='changed'])


class GroupRhythmArtifactTests(unittest.TestCase):
    def case(self,mutation=None):
        with tempfile.TemporaryDirectory()as tmp:
            n,q,c=make(Path(tmp))
            if mutation:mutation(n,q,c)
            return check(n,q,c)

    def test_synthetic_locked_pitch_and_changed_rhythm(self):
        r=self.case();self.assertEqual(r['status'],'PASS_GROUP_RHYTHM_GP_MIDI_AUDIO',r)
        self.assertEqual(len(r['midi_timing']),3)

    def test_wrong_gp_note_property_or_archive_asset(self):
        for mutation in(lambda t:t.find('Notes')[5].set('unrelated','changed'),lambda t:t.find('Beats')[3].find('Dynamic').__setattr__('text','F')):
            self.assertEqual(self.case(lambda n,q,c:edit_gp(n,mutation))['status'],'FAIL')
        self.assertEqual(self.case(lambda n,q,c:edit_gp(n,None,asset=True))['status'],'FAIL')

    def test_selected_gp_duration_must_equal_the_rhythm_relationship(self):
        self.assertEqual(self.case(lambda n,q,c:edit_gp(n,lambda t:t.find('Beats')[0].find('Rhythm').set('ref','r4')))['status'],'FAIL')

    def test_complete_source_capture_and_dependency_hashes_required(self):
        for mutation in(
            lambda n,q,c:mutate_json(q/'plan.json',lambda d:d.update(source_hashes={})),
            lambda n,q,c:edit_snapshot(n,lambda s,o:s.update(snapshot_script_sha256='0'*64)),
            lambda n,q,c:edit_snapshot(n,lambda s,o:s['cases']['changed'].update(capture_hashes={})),
        ):
            self.assertEqual(self.case(mutation)['status'],'FAIL')

    def test_wrong_or_missing_render_and_changed_wav_receipt(self):
        for kind in('clip','missing','duplicate','audio_hash','duration'):
            def mutation(n,q,c):
                def edit(rows):
                    if kind=='clip':
                        for r in rows:r['start_bar']=2
                    elif kind=='missing':rows.pop()
                    elif kind=='duplicate':rows[-1]=deepcopy(rows[0])
                    elif kind=='audio_hash':rows[-1]['audio_sha256']='0'*64
                    else:rows[-1]['seconds']=99
                mutate_json(n/'audio-jobs.results.json',edit)
            self.assertEqual(self.case(mutation)['status'],'FAIL',kind)

    def test_missing_event_wrong_time_or_outside_controller(self):
        for kind in('missing','time','controller'):
            def mutation(n,q,c):
                def edit(s,o):
                    case=s['cases']['changed']
                    if kind=='missing':case['events'].pop();o['changed'].pop()
                    elif kind=='time':case['callbacks'][0]['start']+=1
                    else:
                        row=next(i for i,e in enumerate(case['events'])if e['kind']=='NoteBendEvent'and o['changed'][i]['origin_source_ref'].endswith(':3:0'))
                        case['events'][row]['data']['tick']+=1;o['changed'][row]['data']['tick']+=1
                edit_snapshot(n,edit)
            self.assertEqual(self.case(mutation)['status'],'FAIL',kind)

    def test_other_note_cannot_claim_selected_reset_and_noncenter_bend_cannot_move(self):
        for kind in('owner','value'):
            def mutation(n,q,c):
                def edit(s,o):
                    case=s['cases']['changed'];i=next(i for i,e in enumerate(case['events'])if e['kind']=='NoteBendEvent')
                    if kind=='owner':o['changed'][i]['origin_source_ref']='event:888:0:1:0:3:0'
                    else:case['events'][i]['data']['value']+=1;o['changed'][i]['data']['value']+=1
                edit_snapshot(n,edit)
            self.assertEqual(self.case(mutation)['status'],'FAIL',kind)

    def test_worker_output_or_source_zero_audio_cannot_drift(self):
        for mutation in(
            lambda n,q,c:dump(q/'changed-isolated/worker/output.json',{}),
            lambda n,q,c:wav(n/'zero/focused.wav',True),
        ):self.assertEqual(self.case(mutation)['status'],'FAIL')


if __name__=='__main__':unittest.main()
