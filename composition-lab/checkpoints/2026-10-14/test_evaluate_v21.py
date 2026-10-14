import unittest
from fractions import Fraction as F
from joint_interpretation_v20 import _candidates
from evaluate_v21 import evaluate, track_candidates


def score_fixture():
    def event(t,p):
        return {'onset_q':str(t),'duration_q':'1','voice_index':0,'notes':[{'midi':x,'tie':None} for x in p]}
    return {'source_file':'fixture.gp','measure_count':2,'tracks':[{'index':0,'name':'Piano','tunings':[[40]],'measures':[
        {'number':1,'section':'Intro','onset_q':'0','voices':[[event(0,[60,64,67]),event(1,[62,65,69])]]},
        {'number':2,'section':'Verse','onset_q':'2','voices':[[event(2,[62,65,69]),event(3,[60,64,67])]]}]}]}


class EvaluationTests(unittest.TestCase):
    def test_not_misrepresent_accuracy(self):
        results,rows=evaluate(score_fixture(),0,sample_size=4)
        self.assertIsNone(results['true_chord_accuracy'])
        self.assertIsNone(results['true_phrase_boundary_precision'])
        self.assertEqual(results['attacks'],4)
        self.assertEqual(len(rows),4)
        self.assertTrue(all('human_chord_label' in r for r in rows))
        self.assertEqual(rows[2]['measure'],2)

    def test_section_proxy_is_not_ground_truth(self):
        results,rows=evaluate(score_fixture(),0,sample_size=4)
        self.assertEqual(results['section_markers_at_note_attacks'],1)
        self.assertTrue(results['unmarked_attacks_are_not_verified_non_boundaries'])

    def test_transposition_invariant_candidate_ranking(self):
        base={'pcs':frozenset({0,4,7}),'bass_pc':0}
        shifted={'pcs':frozenset({5,9,0}),'bass_pc':5}
        a=_candidates(base,8)
        b=_candidates(shifted,8)
        # Ranking ties may reorder by root, so check corresponding candidates score.
        original={(root,quality):score for (root,quality),score in a}
        corresponding={(root,quality):score for (root,quality),score in b}
        self.assertAlmostEqual(original[(0,'major')],corresponding[(5,'major')])

    def test_deterministic_stratified_review(self):
        a,r1=evaluate(score_fixture(),0,sample_size=4,seed=7)
        b,r2=evaluate(score_fixture(),0,sample_size=4,seed=7)
        self.assertEqual(a,b)
        self.assertEqual(r1,r2)

    def test_track_selection_uses_coverage_not_first(self):
        s=score_fixture()
        empty={'index':1,'name':'Silent Lead','tunings':[[40]],'measures':[{'voices':[[]]}]}
        s['tracks'].insert(0,empty)
        self.assertEqual(track_candidates(s)[0]['name'],'Piano')

if __name__=='__main__':unittest.main()