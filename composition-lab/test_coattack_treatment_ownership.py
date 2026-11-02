"""Authored coattack contrasts; these fixtures are not musical style evidence."""
from copy import deepcopy
from fractions import Fraction as F
import json
import unittest

import coattack_treatment_ownership as treatment
import backing_pitch_ownership as backing
import group_rhythm_relations as rhythm
from connected_tier2 import analyze, strip_lower, realize, reconstruct
from source_fact_tier1 import extract_documents, project_documents


def documents():
    def beat(notes, duration):return dict(notes=notes,duration=duration)
    def chord(high,low):return [dict(string=2,fret=high),dict(string=3,fret=0,dead=True),dict(string=4,fret=low)]
    def melody(high,low):return dict(signature=[4,4],voices=[dict(beats=[beat(chord(high,low),[1,16]) for _ in range(4)]+[beat([dict(rest=True)],[3,4])])])
    def bar(beats):return dict(signature=[4,4],voices=[dict(beats=beats)])
    source_backing=bar([beat([dict(string=4,fret=4),dict(string=5,fret=4),dict(string=6,fret=2)],[1,1])])
    target_backing=bar([beat([dict(string=3,fret=7),dict(string=4,fret=7),dict(string=5,fret=5)],[1,16]),
                        beat([dict(string=3,fret=5),dict(string=4,fret=5),dict(string=6,fret=8)],[15,16])])
    unrelated=bar([beat([dict(string=5,fret=5)],[1,1])])
    return {'metadata.json':dict(songId=995,revisionId=1,artist='Authored',title='Coattack treatment',tracks=[dict(name='Focal',instrumentId=27),dict(name='Backing',instrumentId=30),dict(name='Other',instrumentId=27)]),
     'track-0.json':dict(songId=995,revisionId=1,partId=0,instrumentId=27,tuning=[64,59,55,50,45,40],frets=24,measures=[melody(17,15),melody(13,11)]),
     'track-1.json':dict(songId=995,revisionId=1,partId=1,instrumentId=30,tuning=[59,54,50,45,40,35,30],frets=24,measures=[source_backing,target_backing]),
     'track-2.json':dict(songId=995,revisionId=1,partId=2,instrumentId=27,tuning=[64,59,55,50,45,40],frets=24,measures=[deepcopy(unrelated),deepcopy(unrelated)])}


def bindings():
    return [dict(reference_anchor_ref=f'event:995:0:1:0:{i}:2',target_anchor_ref=f'event:995:0:2:0:{i}:2',
                 source_backing_ref='event:995:1:1:0:0:2',target_backing_ref=f'event:995:1:2:0:{0 if i==0 else 1}:2') for i in range(4)]


def model(docs=None):
    before=extract_documents(documents() if docs is None else docs)
    upper=strip_lower(analyze(before))
    upper['musical_relationships']=treatment.lift(upper['musical_relationships'],before,bindings(),source_origin=upper['source_origin'])
    return before,upper


def controls(level=100,intent='repeat_reference_pitch',seed=0,octaves=True):
    return dict(context_policy=treatment.POLICY,melody=level,intent=intent,allow_note_octave_changes=octaves,seed=seed)


def expected(intent):
    docs=documents(); beats=docs['track-0.json']['measures'][1]['voices'][0]['beats']
    for i,beat in enumerate(beats[:4]):
        a,b=(17,15) if intent=='repeat_reference_pitch' else ((13,11) if i==0 else (11,9))
        beat['notes'][0]['fret']=a;beat['notes'][2]['fret']=b
    return docs


class CoattackTreatmentTests(unittest.TestCase):
    def test_equation_forward_backward_and_typed_coordinates(self):
        a=treatment.relation(reference='60',source_backing='32',target_backing='40',residual='-12',follow=1)
        self.assertEqual(a['target'],'56')
        self.assertEqual(treatment.relation(reference='60',source_backing='32',target_backing='40',target='56',follow=1),a)
        for v in (True,0.0,None,2):
            with self.assertRaises(ValueError):treatment.relation(reference='60',source_backing='32',target_backing='40',residual='0',follow=v)
        for v in ('01','1/2',False):
            with self.assertRaises(ValueError):treatment.relation(reference=v,source_backing='32',target_backing='40',residual='0',follow=0)

    def test_exact_original_complete_dead_ownership_no_target_anchor_backup(self):
        before,upper=model(); wrapper=upper['musical_relationships']; idx=backing._index(wrapper['core'])
        self.assertEqual(realize(upper),before)
        for row in bindings():
            group=idx[row['target_anchor_ref']][0]
            self.assertNotIn('bass_register_anchor',group)
            self.assertEqual([m['voicing_interval'] for m in group['members']],['12',None,'0'])
        self.assertEqual(wrapper['parameters'],dict(residual='-4',follow=0))
        self.assertEqual(wrapper['observations']['coattack_count'],4)
        self.assertEqual(wrapper['observations']['backing_occurrence_count'],1)

    def test_two_intents_raw_fact_locks_and_same_inverse(self):
        before,upper=model(); snapshot=deepcopy(upper)
        for intent in treatment.INTENTS:
            changed,decision=treatment.intervene(upper,controls(intent=intent))
            self.assertEqual(project_documents(realize(changed)),expected(intent))
            self.assertEqual(reconstruct(upper,controls(intent=intent)),realize(changed))
            self.assertTrue(decision['released']);self.assertTrue(decision['changed'])
            treatment.assert_preserved(upper['musical_relationships'],changed['musical_relationships'])
        self.assertEqual(upper,snapshot);self.assertEqual(realize(upper),before)

    def test_current_zero_saved_switches_and_coincidence(self):
        _,upper=model(); repeat,_=treatment.intervene(upper,controls())
        saved=json.loads(json.dumps(repeat)); evidence=deepcopy(saved['musical_relationships']['observations'])
        self.assertEqual(treatment.intervene(saved,controls(0))[0],saved)
        coincident,decision=treatment.intervene(saved,controls())
        self.assertEqual(coincident,saved);self.assertTrue(decision['released']);self.assertFalse(decision['changed'])
        follow,_=treatment.intervene(saved,controls(intent=treatment.INTENTS[1]))
        self.assertEqual(project_documents(realize(follow)),expected(treatment.INTENTS[1]))
        self.assertEqual(follow['musical_relationships']['observations'],evidence)
        self.assertEqual(treatment.intervene(follow,controls(0,intent=treatment.INTENTS[0]))[0],follow)

    def test_seeded_half_release_and_octave_permission(self):
        _,upper=model(); states=[]
        for seed in range(8):
            changed,decision=treatment.intervene(upper,controls(50,seed=seed))
            self.assertEqual(decision['released'],treatment.release(controls(50,seed=seed)))
            self.assertEqual(changed==upper,not decision['released']);states.append(decision['released'])
        self.assertEqual(set(states),{False,True})
        snapshot=deepcopy(upper)
        with self.assertRaisesRegex(ValueError,'NOTE_OCTAVE_PERMISSION_REQUIRED'):
            treatment.intervene(upper,controls(octaves=False))
        self.assertEqual(upper,snapshot)
        treatment.intervene(upper,controls(intent=treatment.INTENTS[1],octaves=False))

    def test_live_backing_dependency_hold_versus_follow_after_reload(self):
        _,upper=model()
        for intent,delta in ((treatment.INTENTS[0],0),(treatment.INTENTS[1],1)):
            edited,_=treatment.intervene(upper,controls(intent=intent));edited=json.loads(json.dumps(edited))
            baseline=project_documents(realize(edited)); idx=backing._index(edited['musical_relationships']['core'])
            g=idx[bindings()[0]['target_backing_ref']][0];g['bass_register_anchor']=str(F(g['bass_register_anchor'])+1)
            after=project_documents(realize(edited))
            for ni in (0,2):
                self.assertEqual(after['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][ni]['fret'],baseline['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][ni]['fret']+delta)
            # The unchanged existing backing voicing also moves all its members.
            for n in after['track-1.json']['measures'][1]['voices'][0]['beats'][0]['notes']:
                self.assertGreaterEqual(n['fret'],0)

    def test_live_reference_propagates_but_cannot_become_new_evidence(self):
        _,upper=model(); edited,_=treatment.intervene(upper,controls());original_obs=deepcopy(edited['musical_relationships']['observations'])
        idx=backing._index(edited['musical_relationships']['core'])
        for row in bindings():
            g=idx[row['reference_anchor_ref']][0];g['bass_register_anchor']=str(F(g['bass_register_anchor'])+1)
        after=project_documents(realize(edited))
        self.assertEqual(after['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0]['fret'],18)
        self.assertEqual(edited['musical_relationships']['observations'],original_obs)
        self.assertEqual(treatment.intervene(edited,controls(0))[0],edited)
        snapshot=deepcopy(edited)
        with self.assertRaisesRegex(ValueError,'ORIGINAL_REFERENCE_EVIDENCE_CHANGED'):
            treatment.intervene(edited,controls())
        self.assertEqual(edited,snapshot)

    def test_unrelated_authority_survives_and_still_propagates(self):
        _,upper=model(); changed,_=treatment.intervene(upper,controls());idx=backing._index(changed['musical_relationships']['core'])
        ref='event:995:2:2:0:0:0';group=idx[ref][0];group['bass_register_anchor']=str(F(group['bass_register_anchor'])+2)
        self.assertEqual(project_documents(realize(changed))['track-2.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0]['fret'],7)
        with self.assertRaisesRegex(ValueError,'COATTACK_AUTHORITY_LOSS'):
            treatment.assert_preserved(upper['musical_relationships'],changed['musical_relationships'])

    def test_bad_bindings_residuals_wrappers_and_voice_scope_refuse(self):
        before=extract_documents(documents());upper=strip_lower(analyze(before));core=upper['musical_relationships'];snapshot=deepcopy(core)
        for mutate in ('duplicate','overlap','future','wrong_lowest','mixed_part'):
            rows=bindings()
            if mutate=='duplicate':rows[1]=deepcopy(rows[0])
            elif mutate=='overlap':rows[0]['reference_anchor_ref']=rows[0]['target_anchor_ref']
            elif mutate=='future':rows[0]['target_backing_ref']=rows[1]['target_backing_ref']
            elif mutate=='wrong_lowest':rows[0]['target_anchor_ref']=rows[0]['target_anchor_ref'][:-1]+'0'
            else:rows[1]['target_backing_ref']='event:995:2:2:0:0:0'
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):treatment.lift(core,before,rows)
        other=deepcopy(core);idx=backing._index(other);idx[bindings()[1]['target_anchor_ref']][0]['bass_register_anchor']='57';rhythm.refresh(other)
        with self.assertRaisesRegex(ValueError,'shared original residual'):treatment.lift(other,before,bindings())
        with self.assertRaisesRegex(ValueError,'Unsupported existing ownership wrapper'):
            treatment.lift(dict(schema=backing.EXECUTION_SCHEMA,core=core),before,bindings())
        self.assertEqual(core,snapshot)

    def test_duplicate_anchor_evidence_origin_and_foreign_data_tampering(self):
        _,upper=model()
        for name in ('absolute','evidence','origin','dead_shape'):
            bad=deepcopy(upper);w=bad['musical_relationships'];idx=backing._index(w['core'])
            if name=='absolute':idx[bindings()[0]['target_anchor_ref']][0]['bass_register_anchor']='56'
            elif name=='evidence':w['observations']['coattack_count']=5
            elif name=='origin':bad['source_origin']['facts_sha256']='0'*64
            else:idx[bindings()[0]['target_anchor_ref']][0]['members'][1]['voicing_interval']='1'
            with self.subTest(name=name),self.assertRaises(ValueError):realize(bad)

    def test_changed_target_string_or_dead_fret_refuses_current_inverse(self):
        before,upper=model();w=upper['musical_relationships']
        for tail in ('/notes/0/string','/notes/1/fret'):
            forged=deepcopy(before);ident='track-0.json#/measures/1/voices/0/beats/0'+tail
            fact=next(r for r in forged['facts'] if r['id']==ident);fact['value']+=1
            with self.assertRaises(ValueError):treatment.validate_execution(w,forged)

    def test_invalid_controls_are_strict_and_atomic(self):
        _,upper=model();snapshot=deepcopy(upper)
        for key,value in (('melody',None),('melody',True),('melody',float('nan')),('seed',True),('intent','guess'),('allow_note_octave_changes',1)):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):treatment.intervene(upper,dict(controls(),**{key:value}))
        self.assertEqual(upper,snapshot)

    def test_actual_source_denied_zero_and_changed_workers(self):
        from pathlib import Path
        import tempfile
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before,upper=model(); code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as directory:
            for level in (0,100):
                intent=treatment.INTENTS[1]
                answer=before if level==0 else extract_documents(expected(intent))
                receipt=execute(code,upper,controls(level,intent=intent),answer,
                    Path(directory)/str(level),timeout=50,purpose='coattack_treatment')
                self.assertEqual(receipt['status'],'PASS',receipt)
                self.assertFalse(receipt['parent_expected_staged'])


if __name__=='__main__':unittest.main()
