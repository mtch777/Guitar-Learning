import unittest
from relationship_profile_summary import summarize


def fixture():
    rows=[dict(song_id=s,family=f,feature='bend',eligible_attack_groups=n,positive_attack_groups=y)
          for s,f,n,y in [(1,'a',2,1),(2,'a',4,4),(3,'b',10,0)]]
    return dict(scope='development_fit',artist='A',training_songs=[1,2,3],training_families=['a','b'],
        technique_song_summaries=rows,tables=[])


class SummaryTests(unittest.TestCase):
    def test_weightings_and_prevalence_are_distinct(self):
        f=summarize(fixture())['features']['bend']
        self.assertEqual(f['positive_groups'],5)
        self.assertEqual(f['pooled_rate'],5/16)
        self.assertEqual(f['equal_score_rate'],.5)
        self.assertEqual(f['equal_family_rate'],.375)
        self.assertEqual(f['positive_scores'],2)
        self.assertEqual(f['positive_families'],1)

    def test_output_has_no_private_identities(self):
        result=summarize(fixture())
        self.assertNotIn('song_id',str(result));self.assertNotIn('training_songs',result)

    def test_duplicate_invalid_and_heldout_fail(self):
        m=fixture();m['technique_song_summaries'].append(m['technique_song_summaries'][0])
        with self.assertRaises(ValueError):summarize(m)
        m=fixture();m['technique_song_summaries'][0]['positive_attack_groups']=99
        with self.assertRaises(ValueError):summarize(m)
        m=fixture();m['scope']='heldout_descriptive_only'
        with self.assertRaises(ValueError):summarize(m)

    def test_answer_counts_and_weights_stay_distinct(self):
        m=fixture();m['tables']=[dict(kind='same_pedal_call_answer_variation',outcomes=[
            dict(outcome=dict(response_pitch_same=True,response_rhythm_same=False),count=20,weight=.25),
            dict(outcome=dict(response_pitch_same=False,response_rhythm_same=False),count=2,weight=.75)])]
        r=summarize(m)['repeated_call_answer_variation']
        self.assertEqual(r['same_pitch_changed_rhythm']['count'],20)
        self.assertEqual(r['same_pitch_changed_rhythm']['family_weighted_share'],.25)

    def test_invalid_comparison_labels_and_counts_fail(self):
        for count, same in [(-1,True),(True,True),(1,'false')]:
            m=fixture();m['tables']=[dict(kind='same_pedal_call_answer_variation',outcomes=[
                dict(outcome=dict(response_pitch_same=same,response_rhythm_same=False),count=count,weight=1)])]
            with self.assertRaises(ValueError):summarize(m)


if __name__=='__main__':unittest.main()
