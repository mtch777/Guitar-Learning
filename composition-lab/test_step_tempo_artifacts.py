"""Synthetic independent-oracle corruptions; no source song or audible claim."""
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import json,tempfile,unittest
import xml.etree.ElementTree as ET

from test_check_local_dynamics import documents
from source_fact_tier1 import extract,extract_documents
from check_step_tempo_artifacts import source_scope,capture_binding,performed_ledger,seconds_at,gp_scope,native_scope,canonical_model,pcm_frame_clock,verify_source_geometry,sha
from check_step_tempo_zero import source_binding as zero_source_binding


def source_fixture():
    docs=documents();docs['track-1.json']=deepcopy(docs['track-0.json']);docs['track-1.json']['partId']=1
    docs['metadata.json']['tracks'].append(deepcopy(docs['metadata.json']['tracks'][0]))
    for name in('track-0.json','track-1.json'):
        docs[name]['automations']={'tempo':[dict(measure=i,position=0,bpm=bpm,type=4)for i,bpm in enumerate((120,60,120))]}
    after=deepcopy(docs)
    for name in('track-0.json','track-1.json'):after[name]['automations']['tempo'][1]['bpm']=90
    refs=[f'track-{i}.json#/automations/tempo/1'for i in range(2)]
    demo=dict(target=dict(alias_refs=refs,bpm_refs=[r+'/bpm'for r in refs],onset_q='4',end_q='8',bar=2,position_q='0',quarter_bpm='60',component_ref='part:0:voice:0',evidence_label='PARTIAL'),chosen=dict(quarter_bpm='90'))
    return docs,after,demo


def native_fixture():
    marks=[dict(bar=i+1,bpm=bpm)for i,bpm in enumerate((120,60,120))]
    visits=[dict(bar=i+1,start=i*960,end=(i+1)*960)for i in range(3)]
    scope=dict(bar=2,before_bpm=60,after_bpm=90,marks=marks)
    timing=dict(quarter_ticks=960,dead_constant=30,palm_mute_constant=80,position_scale=60)
    traces={};cases={}
    for name in('source','zero','changed'):
        rowmarks=deepcopy(marks)
        if name=='changed':rowmarks[1]['bpm']=90
        ledger=performed_ledger(rowmarks,visits,960);calls=[];events=[];notes=[];model={'masterbars':[dict(tempoautomations=[dict(value=m['bpm'],ratioposition=0)])for m in rowmarks],'notes':[dict(fret=3,dynamic='F')]}
        for i,m in enumerate(rowmarks):
            start=i*960;length=int(F(m['bpm'])*80/60);ref=f'native:0:{i+1}:0:0:0'
            ex=dict(kind='note',ref=ref,beat_start=start,tempo=m['bpm'],beat_duration=960,brush_offset=0,cap_kind='palm_mute',split_execution=False)
            call=dict(native_ref=ref,source_ref=f'event:{i}',track=0,start=start,length=length,key=60,velocity=80,channel=0)
            calls.append(dict(**call,execution=ex,start_seconds=float(seconds_at(ledger,start,960)),end_seconds=float(seconds_at(ledger,start+length,960))))
            notes.append(ex)
            events.extend([dict(kind='TempoChangeEvent',binding=None,data=dict(tick=start,beatsPerMinute=m['bpm'])),dict(kind='NoteOnEvent',binding=i,data=dict(tick=start)),dict(kind='NoteOffEvent',binding=i,data=dict(tick=start+length))])
        events.sort(key=lambda e:e['data']['tick'])
        bars=[dict(**v,tempo_changes=[dict(tick=v['start'],tempo=m['bpm'])],start_seconds=float(F(l['start_seconds'])),end_seconds=float(F(l['end_seconds'])))for v,m,l in zip(visits,rowmarks,ledger['bars'])]
        traces[name]=dict(model=model,callbacks=calls,events=events,origins=[None]*len(events),note_calls=notes,performed_bars=bars)
        cases[name]=dict(notes=[],beats=[],callbacks=[{k:v for k,v in c.items()if k not in('execution','start_seconds','end_seconds')}for c in calls],events=deepcopy(events),midi_tick_shift=0)
    return cases,dict(timing=timing,cases=traces,counterfactual=deepcopy(traces['changed'])),scope


class StepTempoArtifactsTests(unittest.TestCase):
    def test_source_geometry_checks_written_positions_and_every_repeat_visit(self):
        model={'masterbars':[{'start':0},{'start':2880}]};frames=[dict(start_q='0',span_q='3'),dict(start_q='3',span_q='3/2')]
        visits=[dict(bar=1,start=0,end=2880),dict(bar=2,start=2880,end=4320),dict(bar=2,start=4320,end=5760)]
        verify_source_geometry(model,visits,frames,960)
        bad=deepcopy(model);bad['masterbars'][1]['start']=3840
        with self.assertRaisesRegex(ValueError,'bar starts'):verify_source_geometry(bad,visits,frames,960)
        bad=deepcopy(visits);bad[2]['end']=5761
        with self.assertRaisesRegex(ValueError,'bar length'):verify_source_geometry(model,bad,frames,960)
        bad=deepcopy(visits);bad[2]['bar']=3
        with self.assertRaisesRegex(ValueError,'source bar identity'):verify_source_geometry(model,bad,frames,960)

    def test_zero_only_needs_no_fake_changed_capture_or_demonstration(self):
        docs,_,_=source_fixture()
        with tempfile.TemporaryDirectory()as tmp:
            base=Path(tmp);source=base/'source';qa=base/'qa'
            for folder in(source,qa/'zero-capture'):
                folder.mkdir(parents=True)
                for name,value in docs.items():(folder/name).write_text(json.dumps(value))
            p=qa/'zero-isolated/worker';p.mkdir(parents=True);(p/'output.json').write_text(json.dumps(extract(qa/'zero-capture')))
            plan=dict(source_hashes={str(p.resolve()):sha(p)for p in source.glob('*.json')})
            zero_source_binding(qa,plan)
            self.assertFalse((qa/'demonstration.json').exists());self.assertFalse((qa/'changed-capture').exists())
            p=qa/'no-choice-isolated/worker';p.mkdir(parents=True);(p/'output.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'no-choice'):zero_source_binding(qa,plan)

    def test_pcm_length_follows_rational_source_bar_clock(self):
        pcm_frame_clock(445824,F(4640,459),44100,64)
        pcm_frame_clock(430464,F(4480,459),44100,64)
        for bad in(64,430400,445824):
            with self.subTest(frames=bad),self.assertRaisesRegex(ValueError,'frame count'):pcm_frame_clock(bad,F(4480,459),44100,64)

    def test_changed_attack_velocity_even_in_reference_is_rejected(self):
        cases,supp,scope=native_fixture();cases['changed']['callbacks'][1]['velocity']=81
        for t in(supp['cases']['changed'],supp['counterfactual']):t['callbacks'][1]['velocity']=81
        with self.assertRaisesRegex(ValueError,'velocity'):native_scope(cases,supp,scope)

    def test_chord_identifier_normalization_preserves_reference_topology(self):
        def model(a,b,selected):return {'tracks':[{'staves':[{'chords':{a:{'name':'C'},b:{'name':'G'}},'bars':[{'voices':[{'beats':[{'chordid':selected}]}]}]}]}]}
        self.assertEqual(canonical_model(model('a','b','a')),canonical_model(model('new-a','new-b','new-a')))
        self.assertNotEqual(canonical_model(model('a','b','a')),canonical_model(model('new-a','new-b','new-b')))
        with self.assertRaisesRegex(ValueError,'no declaration'):canonical_model(model('a','b','missing'))

    def test_complete_source_alias_scope_and_wrong_alias(self):
        docs,after,demo=source_fixture();self.assertEqual(source_scope(extract_documents(docs),extract_documents(after),demo)['after_bpm'],90)
        after['track-1.json']['automations']['tempo'][1]['bpm']=60
        with self.assertRaisesRegex(ValueError,'outside'):source_scope(extract_documents(docs),extract_documents(after),demo)

    def test_outside_note_flag_and_dynamic_are_rejected(self):
        for key,value in(('fret',9),('dead',True),('accentuated',True)):
            with self.subTest(field=key):
                docs,after,demo=source_fixture();after['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0][key]=value
                with self.assertRaisesRegex(ValueError,'outside'):source_scope(extract_documents(docs),extract_documents(after),demo)
        docs,after,demo=source_fixture();after['track-0.json']['measures'][0]['voices'][0]['beats'][0]['velocity']='ppp'
        with self.assertRaisesRegex(ValueError,'outside'):source_scope(extract_documents(docs),extract_documents(after),demo)

    def test_unknown_ramp_and_conflicting_source_alias_refused(self):
        for field,value in(('linear',False),('bpm',61)):
            docs,after,demo=source_fixture();docs['track-1.json']['automations']['tempo'][1][field]=value
            with self.assertRaises(ValueError):source_scope(extract_documents(docs),extract_documents(after),demo)

    def test_repeat_entry_and_explicit_redundant_reset(self):
        visits=[dict(bar=b,start=i*960,end=(i+1)*960)for i,b in enumerate((1,2,3,2,3))]
        marks=[dict(bar=1,bpm=120),dict(bar=3,bpm=60)]
        self.assertEqual(performed_ledger(marks,visits,960)['total_seconds'],'4')
        marks.insert(1,dict(bar=2,bpm=120))
        self.assertEqual(performed_ledger(marks,visits,960)['total_seconds'],'7/2')

    def test_seconds_offset_survives_next_tempo_reset(self):
        cases,supp,scope=native_fixture();r=native_scope(cases,supp,scope)
        self.assertEqual(r['ledgers']['zero']['total_seconds'],'2')
        self.assertEqual(r['ledgers']['changed']['total_seconds'],'5/3')
        self.assertEqual(F(r['ledgers']['changed']['bars'][2]['start_seconds'])-F(r['ledgers']['zero']['bars'][2]['start_seconds']),F(-1,3))

    def test_wrong_native_tempo_and_reset_fail(self):
        for tick in(960,1920):
            with self.subTest(tick=tick):
                cases,supp,scope=native_fixture()
                for t in(supp['cases']['changed'],supp['counterfactual']):next(e for e in t['events']if e['kind']=='TempoChangeEvent'and e['data']['tick']==tick)['data']['beatsPerMinute']=91
                cases['changed']['events']=deepcopy(supp['cases']['changed']['events'])
                with self.assertRaisesRegex(ValueError,'tempo/reset'):native_scope(cases,supp,scope)

    def test_wrong_seconds_even_when_reference_agrees_fail(self):
        cases,supp,scope=native_fixture()
        for t in(supp['cases']['changed'],supp['counterfactual']):t['performed_bars'][1]['end_seconds']+=.1
        with self.assertRaisesRegex(ValueError,'seconds'):native_scope(cases,supp,scope)

    def test_counterfactual_hidden_edit_fails(self):
        cases,supp,scope=native_fixture()
        for t in(supp['cases']['changed'],supp['counterfactual']):t['model']['notes'][0]['fret']=4
        with self.assertRaisesRegex(ValueError,'hidden'):native_scope(cases,supp,scope)

    def test_pre_influence_pitch_reset_change_is_rejected(self):
        cases,supp,scope=native_fixture()
        e=dict(kind='NoteBendEvent',binding=None,data=dict(tick=100,value=8193))
        for t in(supp['cases']['changed'],supp['counterfactual']):t['events'].insert(2,deepcopy(e));t['origins'].insert(2,None)
        cases['changed']['events']=deepcopy(supp['cases']['changed']['events'])
        with self.assertRaisesRegex(ValueError,'before the first'):native_scope(cases,supp,scope)

    def test_cap_equation_catches_matching_bad_reference(self):
        cases,supp,scope=native_fixture()
        for t in(supp['cases']['changed'],supp['counterfactual']):
            t['callbacks'][1]['length']=121;t['callbacks'][1]['end_seconds']=float(F(1,2)+F(121,960)*60/90)
        cases['changed']['callbacks'][1]['length']=121
        with self.assertRaisesRegex(ValueError,'cap duration'):native_scope(cases,supp,scope)

    def test_gp_only_tempo_and_no_unrelated_properties(self):
        before=ET.fromstring('<GPIF><MasterTrack><Automations><Automation><Type>Tempo</Type><Bar>1</Bar><Position>0</Position><Value>60 2</Value></Automation></Automations></MasterTrack><Notes><Note><Fret>3</Fret></Note></Notes></GPIF>')
        changed=deepcopy(before);changed.find('.//Value').text='90 2';gp_scope(before,changed,2,60,90)
        changed.find('.//Fret').text='4'
        with self.assertRaisesRegex(ValueError,'outside'):gp_scope(before,changed,2,60,90)

    def test_stale_capture_binding_fails(self):
        docs,after,_=source_fixture()
        with tempfile.TemporaryDirectory()as tmp:
            base=Path(tmp);source=base/'source';qa=base/'qa'
            for folder,data in((source,docs),(qa/'zero-capture',docs),(qa/'changed-capture',after)):
                folder.mkdir(parents=True)
                for name,value in data.items():(folder/name).write_text(json.dumps(value))
            for name in('zero','changed'):
                p=qa/(name+'-isolated')/'worker';p.mkdir(parents=True);(p/'output.json').write_text(json.dumps(extract(qa/(name+'-capture'))))
            plan=dict(source_hashes={str(p.resolve()):sha(p)for p in source.glob('*.json')});capture_binding(qa,plan)
            (source/'metadata.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'hash'):capture_binding(qa,plan)


if __name__=='__main__':unittest.main()
