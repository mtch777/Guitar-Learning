"""Structure planner regression tests using synthetic phrase summaries."""
import unittest
from structure_model import select_track,events_for_track,train,plan,evaluate

def example(name):
    return {"song":name,"guitar_tracks":[{"track":"Rhythm Guitar","phrases":[
        {"start_measure":1,"bars":4,"motif_family":"F1","relationship":"new_candidate","note_count":8,"section":"Verse"},
        {"start_measure":5,"bars":4,"motif_family":"F1","relationship":"identical","note_count":8,"section":"Verse"},
        {"start_measure":9,"bars":4,"motif_family":"F2","relationship":"new_candidate","note_count":8,"section":"Verse"},
        {"start_measure":13,"bars":4,"motif_family":"F1","relationship":"varied","note_count":8,"section":"Verse"}]}]}
class StructureTests(unittest.TestCase):
    def setUp(self):self.songs=[example(x) for x in ("a","b","c")]
    def test_rhythm_track(self):
        self.assertEqual(select_track(self.songs[0])["track"],"Rhythm Guitar")
    def test_events(self):
        self.assertEqual([p["action"] for p in events_for_track(select_track(self.songs[0]))],
                         ["introduce","repeat","introduce","vary"])
    def test_transitions(self):
        self.assertEqual(train(self.songs)["transitions"]["introduce"]["repeat"],3)
    def test_16_bars(self):
        p=plan(train(self.songs),16,17)["phrase_plan"]
        self.assertEqual(sum(x["bars"] for x in p),16)
        self.assertEqual(p[-1]["end_measure"],16)
        self.assertGreaterEqual(len(set(x["family"] for x in p)),2)
        self.assertEqual(p[-1]["family"],"A")
    def test_backreferences(self):
        for p in plan(train(self.songs),21,24)["phrase_plan"]:
            if p["develops_phrase"] is not None:
                self.assertLess(p["develops_phrase"],p["phrase"])
    def test_deterministic(self):
        m=train(self.songs)
        self.assertEqual(plan(m,16,33),plan(m,16,33))
    def test_holdouts(self):
        self.assertEqual(len(evaluate(self.songs)),3)
    def test_bad_length(self):
        with self.assertRaises(ValueError):plan(train(self.songs),1)
if __name__=="__main__":unittest.main()
