"""Adversarial raw source checks, independent of the accent producer."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from check_local_accents import Oracle,POLICY
from test_dynamic_context import documents

TARGET='event:93:0:1:0:1:0'


def fixture(levels=(None,1,0,2,None,1,0,2)):
    docs=documents()
    part=docs['track-0.json'];part['tuning']=[60,55]
    part['measures'].extend(deepcopy(part['measures'][:2]))
    for mi,m in enumerate(docs['track-0.json']['measures']):
        for bi,b in enumerate(m['voices'][0]['beats']):
            b.pop('velocity',None)
            if mi==0 and bi==0:b['velocity']='mf'
            for n in b['notes']:n.pop('accentuated',None)
            if bi==1 and levels[mi]is not None:b['notes'][0]['accentuated']=levels[mi]
    return docs


def note(docs,bar=1,beat=1):return docs['track-0.json']['measures'][bar-1]['voices'][0]['beats'][beat]['notes'][0]


class IndependentAccentTests(unittest.TestCase):
    def test_complete_typed_states_context_and_occurrence_votes(self):
        oracle=Oracle(extract_documents(fixture()));ev=oracle.options(TARGET)
        self.assertEqual(len(oracle.inventory()['occurrences']),32)
        self.assertEqual(ev['target']['context_key'],[0,0,'mf',[4,4],'1','1'])
        self.assertEqual([o['state']for o in ev['options']],[{'kind':'absent'},{'kind':'explicit','value':0},{'kind':'explicit','value':1},{'kind':'explicit','value':2}])
        self.assertEqual([len(o['donor_refs'])for o in ev['options']],[1,2,2,2])
        self.assertEqual(ev['witness_pair'],['event:93:0:2:0:1:0','event:93:0:3:0:1:0'])

    def test_target_outcome_not_context_and_whole_target_beat_excluded(self):
        docs=fixture();before=Oracle(extract_documents(docs)).options(TARGET)
        note(docs)['accentuated']=2
        after=Oracle(extract_documents(docs)).options(TARGET)
        self.assertEqual(before['target']['context_key'],after['target']['context_key'])
        self.assertEqual([(o['state'],o['donor_refs'])for o in before['options']],[(o['state'],o['donor_refs'])for o in after['options']])
        docs=fixture((None,)*8);b=docs['track-0.json']['measures'][0]['voices'][0]['beats'][1];b['notes'].append(dict(fret=2,string=1,accentuated=1))
        ev=Oracle(extract_documents(docs)).options(TARGET)
        self.assertFalse(ev['options'])
        self.assertTrue(all(not ref.startswith('event:93:0:1:0:1:')for o in ev['observed_options']for ref in o['donor_refs']))

    def test_distinct_donor_beats_not_just_distinct_notes_required(self):
        docs=fixture((None,)*8)
        # Only one donor beat contains both states; no independent beat pair.
        b=docs['track-0.json']['measures'][1]['voices'][0]['beats'][1];b['notes'].append(dict(fret=2,string=1,accentuated=1))
        for mi,m in enumerate(docs['track-0.json']['measures']):
            if mi>1:m['voices'][0]['beats'][1]['notes'][0]['ghost']=True
        ev=Oracle(extract_documents(docs)).options(TARGET)
        self.assertEqual(len(ev['observed_options']),2);self.assertEqual(ev['options'],[])

    def test_rational_phase_not_beat_array_index(self):
        docs=fixture();beats=docs['track-0.json']['measures'][4]['voices'][0]['beats'];first=deepcopy(beats[0]);first['duration']=[1,8];other=deepcopy(first);beats[:1]=[first,other]
        ev=Oracle(extract_documents(docs)).options(TARGET)
        self.assertIn('event:93:0:5:0:2:0',[r for o in ev['options']for r in o['donor_refs']])

    def test_meter_missing_or_conflicting_fails_closed(self):
        for kind in('missing','conflict'):
            docs=fixture()
            if kind=='missing':
                for m in docs['track-0.json']['measures']:m.pop('signature',None)
            else:
                p=deepcopy(docs['track-0.json']);p['partId']=1;p['measures'][0]['signature']=[3,4];docs['track-1.json']=p
            with self.assertRaises(ValueError):Oracle(extract_documents(docs))

    def test_unknown_ghost_dead_and_grace_not_accent_permissions(self):
        for field,value in(('accentuated',False),('accentuated',1.0),('accentuated',3),('ghost',True),('dead',True),('hp',True),('staccato',True)):
            docs=fixture();note(docs)[field]=value;ev=Oracle(extract_documents(docs)).options(TARGET)
            self.assertTrue(ev['target']['reasons']);self.assertIsNone(ev['target']['context_key']);self.assertFalse(ev['options'])
        docs=fixture();docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['graceNote']=True
        self.assertFalse(Oracle(extract_documents(docs)).options(TARGET)['options'])

    def test_fractional_pitch_frame_crossing_and_whole_measure_rest(self):
        docs=fixture();note(docs)['fret']=0.5
        ev=Oracle(extract_documents(docs)).options(TARGET)
        self.assertIn('UNKNOWN_OR_FRACTIONAL_WRITTEN_PITCH',ev['target']['reasons'])
        docs=fixture();docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['duration']=[1,2]
        ev=Oracle(extract_documents(docs)).options('event:93:0:1:0:3:0')
        self.assertIn('SOURCE_FRAME_CROSSING',ev['target']['reasons']);self.assertIsNone(ev['target']['context_key'])
        docs=fixture();measure=docs['track-0.json']['measures'][1];measure['rest']=True
        measure['voices']=[dict(rest=True,beats=[dict(rest=True,type=1,duration=[1,1],notes=[dict(rest=True)])])]
        ev=Oracle(extract_documents(docs)).options('event:93:0:2:0:0:0')
        self.assertIn('SOURCE_REST',ev['target']['reasons']);self.assertIn('NO_NORMALIZED_SOURCE_EVENT',ev['target']['reasons']);self.assertFalse(ev['options'])

    def test_added_and_removed_field_exact_raw_guard_and_existing_order(self):
        docs=fixture();before=extract_documents(docs);oracle=Oracle(before);ev=oracle.options(TARGET);chosen=next(o for o in ev['options']if o['state']=={'kind':'explicit','value':1})
        note(docs)['accentuated']=1;after=extract_documents(docs);decision=dict(released=True,changed=True,chosen=chosen)
        self.assertEqual(oracle.check(after,TARGET,chosen['donor_refs'],decision)['status'],'PASS_INDEPENDENT_LOCAL_ACCENTS')
        for kind in('outside','dynamic','order','type','donors'):
            altered=deepcopy(docs);donors=chosen['donor_refs']
            if kind=='outside':note(altered,bar=3)['fret']=5
            elif kind=='dynamic':altered['track-0.json']['measures'][0]['voices'][0]['beats'][0]['velocity']='f'
            elif kind=='order':
                n=note(altered);v=n.pop('fret');n['fret']=v
            elif kind=='type':note(altered)['accentuated']=True
            else:donors=donors[:1]
            with self.subTest(kind=kind):self.assertTrue(oracle.check(extract_documents(altered),TARGET,donors,decision)['issues'])
        explicit=Oracle(after);ev=explicit.options(TARGET);chosen=next(o for o in ev['options']if o['state']=={'kind':'absent'});note(docs).pop('accentuated')
        self.assertEqual(explicit.check(extract_documents(docs),TARGET,chosen['donor_refs'],dict(released=True,changed=True,chosen=chosen))['status'],'PASS_INDEPENDENT_LOCAL_ACCENTS')

    def test_unknown_and_empty_context_zero_no_choice_is_exact(self):
        for unknown in(False,1.0,3,None,{},[],{'unknown':7}):
            docs=fixture((None,)*8);note(docs)['accentuated']=unknown;t=extract_documents(docs);o=Oracle(t)
            self.assertEqual(o.check(t,TARGET,[],dict(released=True,changed=False,status='NO_ADMITTED_CHOICE'))['status'],'PASS_INDEPENDENT_LOCAL_ACCENTS')
        t=extract_documents(fixture((None,)*8));o=Oracle(t)
        self.assertFalse(o.options(TARGET)['options'])
        self.assertEqual(o.check(t,TARGET,[],dict(released=True,changed=False,status='NO_ADMITTED_CHOICE'))['status'],'PASS_INDEPENDENT_LOCAL_ACCENTS')

    def test_all_seeded_release_draws_and_corruption(self):
        from declared_degree_choices import sample
        oracle=Oracle(extract_documents(fixture()));ev=oracle.options(TARGET)
        for strength in(0,50,100):
            for seed in range(32):
                chosen,decision=sample(ev,dict(voicing=strength,seed=seed));controls=dict(context_policy=POLICY,accents=strength,target_ref=TARGET,seed=seed)
                self.assertEqual(oracle.check_sample(TARGET,controls,chosen,decision)['status'],'PASS_INDEPENDENT_LOCAL_ACCENT_SAMPLE')
        chosen,decision=sample(ev,dict(voicing=100,seed=1));decision['changed']=not decision['changed']
        self.assertTrue(oracle.check_sample(TARGET,dict(context_policy=POLICY,accents=100,target_ref=TARGET,seed=1),chosen,decision)['issues'])


if __name__=='__main__':unittest.main()

