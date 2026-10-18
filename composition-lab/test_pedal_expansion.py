import copy
import unittest
from fractions import Fraction as F
from pedal_expansion import expand_phrases
from test_pedal_regions import rows


def fixture(groups, intervals):
    data=rows(groups)
    for i,n in enumerate(data):n['bar']=int(F(n['onset_q']))//4+1
    seeds=[]
    for ident,(lo,hi,anchor) in enumerate(intervals):
        selected=[n for n in data if lo<=F(n['onset_q'])<=hi]
        calls=[n for n in selected if n['midi']==anchor]
        cycles=[]
        for a,b in zip(calls,calls[1:]):
            answer=[n for n in selected if F(a['onset_q'])<F(n['onset_q'])<F(b['onset_q'])]
            if answer:cycles.append(dict(call_start_q=a['onset_q'],response_start_q=answer[0]['onset_q'],return_q=b['onset_q'],
                call_members=[a['occurrence']],response_members=[n['occurrence'] for n in answer]))
        seeds.append(dict(id=str(ident),start_q=str(lo),end_q=str(hi+1),members=[n['occurrence'] for n in selected],
            roles={n['occurrence']:('call' if n['midi']==anchor else 'response') for n in selected},cycles=cycles))
    return data,seeds


class ExpansionTests(unittest.TestCase):
    def check(self,groups,intervals,direction,bounds=None):
        data,seeds=fixture(groups,intervals);snapshot=copy.deepcopy((data,seeds))
        result=expand_phrases(data,seeds)
        self.assertEqual((data,seeds),snapshot)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['direction'],direction)
        if bounds:self.assertEqual((result[0]['start_q'],result[0]['end_q']),bounds)
        for c in result[0]['added_cycles']:
            self.assertLess(F(c['call_start_q']),F(c['response_start_q']))
            self.assertLess(F(c['response_start_q']),F(c['return_q']))
        return data,seeds,result[0]

    def test_after_one_complete_exchange(self):
        self.check([[40],[55],[40],[58],[40],[59],[40]],[(0,4,40)],'after',('0','7'))

    def test_before_needs_two_exchanges(self):
        self.check([[40],[55],[40],[58],[40],[59],[40],[61],[40]],[(4,8,40)],'before',('0','9'))
        self.check([[40],[55],[40],[58],[40],[59],[40]],[(2,6,40)],'unchanged',('2','7'))

    def test_both(self):
        self.check([[40],[55],[40],[58],[40],[59],[40],[61],[40],[63],[40]],[(4,8,40)],'both',('0','11'))

    def test_combines_only_when_bridge_has_answers(self):
        self.check([[40],[55],[40],[58],[40],[59],[40],[61],[40],[63],[40]],
                   [(0,4,40),(6,10,40)],'combined',('0','11'))

    def test_coattacks_are_not_answers(self):
        self.check([[40],[55],[40],[58],[40],[40,60],[40,61],[40]],[(0,4,40)],'unchanged',('0','5'))

    def test_new_anchor_cannot_extend(self):
        self.check([[40],[55],[40],[58],[40],[59],[41],[61],[41]],[(0,4,40)],'unchanged',('0','5'))

    def test_lower_accent_requires_upper_evidence(self):
        self.check([[63],[75],[63],[76],[63],[59],[63],[71],[63]],[(0,4,63)],'after',('0','9'))
        self.check([[63],[75],[63],[76],[63],[59],[63]],[(0,4,63)],'unchanged',('0','5'))

    def test_arpeggio_cannot_extend_established_phrase(self):
        self.check([[40],[55],[40],[58],[40],[44],[47],[44],[40],[44],[47],[44],[40]],
                   [(0,4,40)],'unchanged',('0','5'))

    def test_silence_and_ties_do_not_invent_returns(self):
        data,seeds=fixture([[40],[55],[40],[58],[40],[59],[40]],[(0,4,40)])
        for n in data[5:]:n['onset_q']=str(F(n['onset_q'])+100)
        self.assertEqual(expand_phrases(data,seeds)[0]['direction'],'unchanged')
        data,seeds=fixture([[40],[55],[40],[58],[40],[59],[40]],[(0,4,40)])
        data[-1]['tie_destination']=True
        self.assertEqual(expand_phrases(data,seeds)[0]['direction'],'unchanged')

    def test_different_existing_phrase_is_a_barrier(self):
        data,seeds=fixture([[40],[55],[40],[58],[40],[42],[56],[42],[60],[42],[40]],[(0,4,40),(5,9,42)])
        out=expand_phrases(data,seeds)
        self.assertEqual(len(out),2)
        self.assertEqual([r['direction'] for r in out],['unchanged','unchanged'])

    def test_no_seeds_cannot_discover_anything(self):
        data,_=fixture([[40],[55],[40],[58],[40]],[])
        self.assertEqual(expand_phrases(data,[]),[])

    def test_terminal_burst_is_kept_after_proven_continuation(self):
        self.check([[40],[55],[40],[58],[40],[59],[40],[40],[40]],[(0,4,40)],'after',('0','9'))

    def test_tied_tail_extends_sustain_not_attack_count(self):
        data,seeds=fixture([[40],[55],[40],[58],[40],[59],[40],[40]],[(0,4,40)])
        data[-1]['tie_destination']=True
        result=expand_phrases(data,seeds,sustain_chains=[dict(origin='6:0',members=['6:0','7:0'])])[0]
        self.assertEqual(result['end_q'],'8')
        self.assertIn('7:0',result['members'])
        self.assertNotIn('7:0',result['roles'])

    def test_coattacked_upper_at_seed_boundary_never_answers(self):
        data,seeds=fixture([[40],[55],[40],[58],[40],[59],[40]],[(0,4,40)])
        upper=dict(data[4],occurrence='upper',midi=72,string=2)
        data.append(upper)
        result=expand_phrases(data,seeds)[0]
        self.assertEqual(result['direction'],'after')
        self.assertNotIn('upper',result['roles'])
        self.assertNotIn('upper',result['added_cycles'][0]['response_members'])

    def test_full_evaluation_preserves_detector_roles(self):
        from evaluate_pedal_expansion import evaluate
        data,seeds=fixture([[40],[55],[40],[58],[40],[59],[40]],[(0,4,40)])
        seed=seeds[0]
        report=dict(songs=[dict(song_id=1,tracks=[dict(part_id=0,rows=data)])])
        analysis=dict(song_id=1,part_id=0,section_start=1,accepted=True,
            roles=seed['roles'],cycles=seed['cycles'],anchor_pitches=[40])
        r=evaluate(report,[analysis])
        self.assertEqual(r['counts']['input_seeds'],1)
        self.assertEqual(r['counts']['after'],1)
        self.assertEqual(r['counts']['added_exchanges'],1)


if __name__=='__main__':unittest.main()
