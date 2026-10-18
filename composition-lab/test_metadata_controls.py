import copy,unittest
from test_corpus_composer import fixture,model_for
from corpus_composer import generate
from metadata_controls import apply,proposals

class MetadataTests(unittest.TestCase):
    def setup(self):
        report,raw=fixture();m=model_for(report,raw);s,_=generate(m,2,23)
        return m,s,['harmony','melody','bass']

    def test_zero_and_literal_other_locks(self):
        m,s,roles=self.setup();self.assertEqual(apply(s,roles,None,{})[0],s)
        out,a=apply(s,roles,m,dict(tempo=100,programs=100))
        for before,after in zip(s['tracks'],out['tracks']):self.assertEqual(before['measures'],after['measures']);self.assertEqual(before['tunings'],after['tunings'])

    def test_full_reference_metadata_invariance(self):
        m,s,roles=self.setup();other=copy.deepcopy(s);other['tempo_bpm']='89'
        for t in other['tracks']:t['program']=(t['program']+1)%128
        self.assertEqual(apply(s,roles,m,dict(tempo=100,programs=100))[0],apply(other,roles,m,dict(tempo=100,programs=100))[0])

    def test_nested_masks_and_invalid(self):
        m,s,roles=self.setup();last=set()
        for strength in (25,50,75,100):
            out,a=apply(s,roles,m,dict(tempo=strength,programs=strength));current={(d['dimension'],d.get('track')) for d in a['decisions'] if d['released']};self.assertLessEqual(last,current);last=current
        with self.assertRaises(ValueError):apply(s,roles,m,dict(tempo=True))

if __name__=='__main__':unittest.main()
