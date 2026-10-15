import tempfile
import unittest
from pathlib import Path
from controlled_generation import demo_plan, generate, realize, position_chord, distance
from gp_author import write_gp
from musicxml_bridge import occurrence_rows


class GenerationTests(unittest.TestCase):
    def test_zero_is_exact_identity(self):
        plan=demo_plan(); chosen,score,report=generate(plan,{},candidates=8)
        self.assertEqual(chosen,plan)
        self.assertTrue(report['target_reached'])
        self.assertEqual(occurrence_rows(score),occurrence_rows(realize(plan)))

    def test_harmony_change_preserves_rhythm_melody_and_form(self):
        plan=demo_plan(); chosen,score,report=generate(plan,dict(harmony=75))
        self.assertEqual(report['measured']['harmony'],75)
        for d in ['rhythm','melody','structure']: self.assertEqual(distance(plan,chosen,d),0)
        self.assertNotEqual(occurrence_rows(score),occurrence_rows(realize(plan)))

    def test_seed_determinism_and_input_immutable(self):
        plan=demo_plan(); a=generate(plan,dict(harmony=75,rhythm=25,melody=25),seed=21)
        self.assertEqual(a,generate(plan,dict(harmony=75,rhythm=25,melody=25),seed=21))
        self.assertEqual(plan,demo_plan())

    def test_unattainable_reported(self):
        _,_,r=generate(demo_plan(),dict(harmony=13),candidates=32)
        self.assertFalse(r['target_reached'])
        with self.assertRaises(ValueError): generate(demo_plan(),dict(rhythm=-1))

    def test_playable_simultaneous_notes_and_new_gp(self):
        plan=demo_plan(); score=realize(plan)
        for t in score['tracks']:
            for m in t['measures']:
                for e in m['voices'][0]:
                    self.assertEqual(len({n['string'] for n in e['notes']}),len(e['notes']))
        with tempfile.TemporaryDirectory() as tmp:
            restored=write_gp(score,Path(tmp)/'original.gp')
        self.assertEqual(occurrence_rows(score),occurrence_rows(restored))
        with self.assertRaises(ValueError): position_chord([5],[40,45,50,55,59,64])


if __name__=='__main__': unittest.main()
