import copy,unittest
from joint_register_harmony_audit import summarize,compare,source_rows,run
import test_role_pitch_transfer as fixture

class JointAuditTests(unittest.TestCase):
    def test_equal_family_song_weights_and_identity(self):
        a=dict(family='a',song_id=1,R=10,D=10,H=0);b=dict(family='b',song_id=2,R=30,D=10,H=20)
        result=summarize([a]*100+[b]);self.assertAlmostEqual(result['means']['H'],10);self.assertAlmostEqual(result['means']['R'],20)
        with self.assertRaises(ValueError):summarize([dict(a,H=1)])
    def test_exact_tradeoff_bound(self):
        a=summarize([dict(family='a',song_id=1,R=29,D=20,H=9)]);b=summarize([dict(family='x',song_id=2,R=30,D=6,H=24)])
        result=compare(a,b);self.assertEqual(result['locked_H_mean_shift'],15);self.assertEqual(result['minimum_unavoidable_max_mean_error'],7.5);self.assertEqual(result['unseen_H_share'],1)
    def source(self):
        return dict(events=[dict(partition='development',role='melody',song_id=1,family='a',part_id=1,bar=2,target=60,anchor=40,register=29)])
    def test_missingness_heldout_and_duplicate_support(self):
        source=self.source();source['events'] += [dict(source['events'][0],bar=3,anchor=None),dict(source['events'][0],partition='held_out')]
        rows,unknown=source_rows(source);self.assertEqual(len(rows),1);self.assertEqual(unknown,1)
        source['events'].append(copy.deepcopy(source['events'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate'):source_rows(source)
    def test_locked_context_mismatch_refused(self):
        _,score,_,roles=fixture.TransferTests().setup()
        for t in score['tracks']:
            for mi,m in enumerate(t['measures']):
                m['voices']=[[dict(onset_q=str(mi*4+i),local_onset_q=str(i),duration_q='1',notes=[dict(midi=t['tunings'][0][0]+5,string=0,fret=5,tie=None,technique_tags=[])]) for i in range(4)]]
        sections=[dict(start=0,length=2,identity=0)];changed=copy.deepcopy(score);n=changed['tracks'][0]['measures'][1]['voices'][0][0]['notes'][0];n['midi']+=1;n['fret']+=1
        cases=[dict(core=1,seed=17,method='reset',score=score,sections=sections),dict(core=1,seed=17,method='carry',score=changed,sections=sections)]
        with self.assertRaisesRegex(ValueError,'context changed'):run(self.source(),cases)

if __name__=='__main__':unittest.main()
