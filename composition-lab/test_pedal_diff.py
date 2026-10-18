import sys,unittest
from pathlib import Path
from fractions import Fraction as F
sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
from build_pedal_diff import union,subtract,after_spans


class DiffTests(unittest.TestCase):
    def test_overlap_is_not_counted_as_loss_or_gain(self):
        a=[('0','4'),('6','10')];b=[('2','8')]
        self.assertEqual(subtract(a,b),[(F(0),F(2)),(F(8),F(10))])
        self.assertEqual(subtract(b,a),[(F(4),F(6))])

    def test_fragmenting_identical_coverage_does_not_invent_changes(self):
        self.assertEqual(subtract([('0','4')],[('0','1'),('1','3'),('3','4')]),[])

    def test_exact_tuplet_boundary_and_duplicate_regions(self):
        self.assertEqual(union([('0','1/3'),('0','1/3'),('1/3','2/3')]),[(F(0),F(2,3))])
        self.assertEqual(subtract([('0','1')],[('1/3','2/3')]),[(F(0),F(1,3)),(F(2,3),F(1))])

    def test_interrupted_chains_are_not_joined_into_one_tag(self):
        track=dict(rows=[dict(occurrence=str(q),onset_q=str(q),duration_q='1') for q in (0,2,4,10,12,14)])
        item=dict(roles={n['occurrence']:'call' for n in track['rows']},cycles=[
            dict(call_start_q='0',return_q='4'),dict(call_start_q='10',return_q='14')])
        self.assertEqual(after_spans(item,track,F(15)),[(F(0),F(5)),(F(10),F(15))])


if __name__=='__main__':unittest.main()
