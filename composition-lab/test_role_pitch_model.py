import unittest
from role_pitch_model import select,fit,distribution,evaluate

def events():
    return [dict(role=role,song_id=song,family='f'+str(song),target=40+i%4+shift,previous=40+(i-1)%4+shift,
        anchor=40+i%4) for song in range(1,5) for role,shift in [('melody',12),('bass',-12)] for i in range(16)]

class RolePitchTests(unittest.TestCase):
    def test_nonfinite_weights_and_invalid_folds_rejected(self):
        model=select(events())
        for weights in ([float('nan'),0,1],[float('inf'),0,0],[True,0,0]):
            with self.assertRaises(ValueError):distribution(model,'melody',None,None,weights)
        for folds in (0,1,True,2.5):
            with self.assertRaises(ValueError):select(events(),folds)

    def test_duplicate_events_do_not_change_balanced_selection(self):
        data=events();a=select(data)
        duplicate=[e for e in data if e['song_id']==1]*3;b=select(data+duplicate)
        self.assertEqual(a['weights'],b['weights'])
        for role,scores in a['selection']['scores'].items():
            for x,y in zip(scores,b['selection']['scores'][role]):self.assertAlmostEqual(x['nll'],y['nll'])

    def test_development_selection_and_normalized_distribution(self):
        model=select(events());self.assertEqual(model,select(events()))
        for role in ('melody','bass'):
            for previous,anchor in [(None,None),(0,127),(127,0),(52,40)]:
                ps=distribution(model,role,previous,anchor);self.assertAlmostEqual(sum(ps),1);self.assertTrue(all(p>0 for p in ps))

    def test_leakage_and_insufficient_families_rejected(self):
        model=select(events())
        with self.assertRaises(ValueError):evaluate(model,events())
        with self.assertRaises(ValueError):select([e for e in events() if e['song_id']==1])

    def test_no_reference_forced_difference(self):
        model=select(events());ps=distribution(model,'melody',52,40)
        self.assertEqual(max(range(128),key=lambda p:ps[p]),52)

if __name__=='__main__':unittest.main()
