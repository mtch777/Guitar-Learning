import unittest
from pedal_dialogue import analyze_dialogue


def track(groups):
    rows=[]
    for i,ps in enumerate(groups):
        for j,p in enumerate(ps):rows.append(dict(occurrence=f'{i}:{j}',onset_q=str(i),duration_q='1',midi=p,
            string=j,fret=0,voice=0,tie_destination=False,section_start=1,effects=[],bar=1,bar_offset_q=str(i)))
    return dict(rows=rows,sections=[dict(id=1,end_q=str(len(groups)))])


class DialogueTests(unittest.TestCase):
    def test_calls_repeat_while_responses_change(self):
        t=track([[40],[40],[52],[40],[40],[55],[40]])
        r=analyze_dialogue(t,dict(anchor_pitches=[40],start_q='0',section_start=1))
        self.assertEqual(len(r['cycles']),2)
        self.assertEqual(r['cycles'][0]['call']['attack_groups'],2)
        self.assertEqual(r['cycles'][0]['response']['intervals_from_lowest_anchor'],[[12]])
        self.assertEqual(r['cycles'][1]['response']['intervals_from_lowest_anchor'],[[15]])
        self.assertEqual(r['consistency']['same_call_changed_response']['count'],1)
        self.assertEqual(r['cycles'][0]['anchor_return_period_q'],'3')
        self.assertEqual(r['call_response_families'][0]['distinct_responses'],2)

    def test_tie_sustain_overlap_is_not_an_extra_attack(self):
        t=track([[40],[40],[52],[40]])
        t['rows'][1]['tie_destination']=True
        t['sustain_relationships']=dict(chains=[dict(origin='0:0',members=['0:0','1:0'],end_q='3')])
        r=analyze_dialogue(t,dict(anchor_pitches=[40],start_q='0',section_start=1))
        self.assertEqual(r['cycles'][0]['call']['attack_groups'],1)
        self.assertEqual(r['cycles'][0]['call_sustain_into_response_q'],'1')

    def test_mixed_unknown_and_polyphony_not_invented_melody(self):
        t=track([[28,35],[55,59],[28,35],[28,60],[None],[28,35],[62,65]])
        r=analyze_dialogue(t,dict(anchor_pitches=[28,35],start_q='0',section_start=1))
        self.assertEqual(r['event_kind_counts']['mixed'],1)
        self.assertEqual(r['event_kind_counts']['unknown'],1)
        self.assertIsNone(r['cycles'][0]['response']['melodic_steps'])
        self.assertTrue(r['cycles'][-1]['right_censored'])
        self.assertEqual(r['consistency']['call_same_pitch']['compared'],0)

    def test_next_anchor_scope_and_exact_tuplets(self):
        t=track([[40],[52],[40],[55]])
        t['rows'][1]['onset_q']='1/3';t['rows'][1]['duration_q']='1/6'
        r=analyze_dialogue(t,dict(anchor_pitches=[40],start_q='0',section_start=1,scope_end_q='2'))
        self.assertEqual(r['scope_end_q'],'2')
        self.assertEqual(r['cycles'][0]['response']['notated_duration_histogram'],{'1/6':1})
        self.assertFalse(r['cycles'][0]['closed_by_anchor_return'])


if __name__=='__main__':unittest.main()
