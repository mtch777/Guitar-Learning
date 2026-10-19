import unittest
from copy import deepcopy
from joint_motion_contract import observe,permission,proposal_view,verify


class JointMotionContractTests(unittest.TestCase):
    def fixture(self):
        score=dict(tracks=[])
        for ti,(name,tuning,pitches) in enumerate((('harmony',40,[40,40]),('melody',40,[60,62]),('bass',28,[28,28]))):
            events=[dict(local_onset_q=str(i*2),onset_q=str(i*2),duration_q='2',notes=[dict(midi=p,string=0,fret=p-tuning,tie=None,technique_tags=[])]) for i,p in enumerate(pitches)]
            score['tracks'].append(dict(index=ti,name=name,tunings=[[tuning]],program=25,measures=[dict(number=1,onset_q='0',time_signature='4/4',voices=[events])]))
        return score

    def support(self):return dict(known=True,eligible_mass_q='1',denominator_unit='family_weighted_mass',model_sha256='a'*64)

    def shift(self,score,ti,amount):
        for e in score['tracks'][ti]['measures'][0]['voices'][0]:
            for n in e['notes']:n['midi']+=amount;n['fret']+=amount

    def test_zero_locks_changes_not_absolute_pitch_and_harmony_stays_locked(self):
        source=self.fixture();candidate=deepcopy(source);self.shift(candidate,1,-5)
        self.assertEqual(verify(source,candidate,1,0)['status'],'verified_contract_only')
        candidate['tracks'][1]['measures'][0]['voices'][0][1]['notes'][0].update(midi=56,fret=16)
        self.assertEqual(verify(source,candidate,1,0)['reason'],'literal_relationship_changed')
        candidate=deepcopy(source);self.shift(candidate,0,2);self.shift(candidate,1,2)
        self.assertEqual(verify(source,candidate,1,0)['reason'],'non_target_dimension_changed')

    def test_unlocked_view_hides_source_targets_and_support_payload(self):
        source=self.fixture();other=deepcopy(source);self.shift(other,1,-5);support=self.support();support['original_target']={'pitches':[60,62]}
        self.assertEqual(proposal_view(source,1,100,support),proposal_view(other,1,100,support))
        self.assertNotIn('original_target',str(proposal_view(source,1,100,support)))
        self.assertEqual(verify(source,source,1,100,support)['forced_difference'],False)

    def test_explicit_unsupported_conflicts_and_missingness(self):
        source=self.fixture();record=observe(source,1)
        self.assertEqual(permission(record,50)['reason'],'unsupported_partial_control')
        self.assertEqual(permission(record,100)['reason'],'unknown_support')
        self.assertEqual(permission(record,100,self.support(),literal_melody_lock=True)['reason'],'target_determined_by_literal_pitch_lock')
        self.assertEqual(permission(record,0,function_lock=True)['reason'],'unsupported_function_or_octave_lock')
        self.assertEqual(verify(source,source,1,0,literal_melody_lock=True)['status'],'verified_contract_only')
        unknown=deepcopy(source);unknown['tracks'][1]['measures'][0]['voices'][0][0]['notes'][0]['midi']=None
        self.assertEqual(observe(unknown,1)['status'],'unknown')
        no_edge=deepcopy(source)
        for t in no_edge['tracks']:
            t['measures'][0]['voices'][0]=[dict(t['measures'][0]['voices'][0][0],duration_q='4')]
        self.assertEqual(observe(no_edge,1)['status'],'not_applicable')

    def test_protected_tempo_and_other_bars_refused_at_both_endpoints(self):
        source=self.fixture();source['tempo_bpm']=120
        candidate=deepcopy(source);candidate['tempo_bpm']=121
        for amount in (0,100):
            self.assertEqual(verify(source,candidate,1,amount,self.support())['reason'],'protected_metadata_or_topology_changed')
        for t in source['tracks']:
            second=deepcopy(t['measures'][0]);second.update(number=2,onset_q='4')
            for e in second['voices'][0]:e['onset_q']=str(4+int(e['local_onset_q']))
            t['measures'].append(second)
        candidate=deepcopy(source);candidate['tracks'][1]['measures'][1]['voices'][0][0]['notes'][0].update(midi=59,fret=19)
        for amount in (0,100):self.assertEqual(verify(source,candidate,1,amount,self.support())['reason'],'outside_selected_bar')

    def test_rest_separated_components_have_no_invented_connecting_edge(self):
        source=self.fixture()
        for ti,t in enumerate(source['tracks']):
            events=[]
            for i in range(4):
                e=deepcopy(t['measures'][0]['voices'][0][min(i//2,1)]);e.update(onset_q=str(i),local_onset_q=str(i),duration_q='1')
                if ti==1:
                    if i==1:e['notes']=[]
                    else:e['notes'][0].update(midi=62 if i==3 else 60,fret=22 if i==3 else 20)
                events.append(e)
            t['measures'][0]['voices']=[events]
        candidate=deepcopy(source)
        for i,amount in ((0,-5),(2,-2),(3,-2)):
            n=candidate['tracks'][1]['measures'][0]['voices'][0][i]['notes'][0];n['midi']+=amount;n['fret']+=amount
        self.assertEqual(observe(source,1)['edges'],[dict(from_q='2',to_q='3',delta=2)])
        self.assertEqual(verify(source,candidate,1,0)['status'],'verified_contract_only')


if __name__=='__main__':unittest.main()
