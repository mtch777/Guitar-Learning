import copy
import unittest
from test_corpus_composer import fixture,model_for
from corpus_composer import generate
from generation_freedom import mix
from profile_controls import locked_context,propose


class ProfileControlTests(unittest.TestCase):
    def test_reference_pitches_never_reach_proposal(self):
        report,raw=fixture();model=model_for(report,raw);reference,_=generate(model,4,17)
        other=copy.deepcopy(reference)
        for t in other['tracks']:
            for m in t['measures']:
                for v in m['voices']:
                    for e in v:
                        for n in e['notes']:n['midi']+=1;n['fret']+=1
        self.assertEqual(locked_context(reference),locked_context(other))
        proposal=propose(model,locked_context(reference),['harmony','melody','bass'])
        a,_=mix(reference,proposal,dict(harmony=100,melody=100,bass=100),['harmony','melody','bass'])
        b,_=mix(other,proposal,dict(harmony=100,melody=100,bass=100),['harmony','melody','bass'])
        self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
