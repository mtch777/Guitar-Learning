import unittest
from fretting_contacts import analyze, realize


class ContactTests(unittest.TestCase):
    def test_generated_barre_and_point_covers_use_same_equation(self):
        shape = [dict(string=i, fret=f) for i,f in enumerate([8,5,5,7])]
        result = analyze(shape)
        self.assertEqual(result['status'], 'COVERED')
        self.assertEqual(result['minimum_contacts'], 3)
        self.assertGreater(len(result['covers']), 1)
        for cover in result['covers']:
            self.assertEqual(realize([0,1,2,3], cover), shape)
        self.assertEqual(result['human_playability'], 'UNVERIFIED')

    def test_open_string_blocks_barre(self):
        result = analyze([dict(string=i,fret=f) for i,f in enumerate([5,0,5])])
        self.assertEqual(result['minimum_contacts'], 2)
        self.assertEqual(len(result['covers']), 1)
        self.assertTrue(all(c['first_string'] == c['last_string'] for c in result['covers'][0]))

    def test_missing_string_cannot_be_invented(self):
        result = analyze([dict(string=0,fret=5),dict(string=2,fret=5)])
        self.assertEqual(result['minimum_contacts'], 2)
        with self.assertRaises(ValueError):
            realize([0,2],[dict(fret=5,first_string=0,last_string=2)])

    def test_lower_required_fret_blocks_higher_barre(self):
        result = analyze([dict(string=i,fret=f) for i,f in enumerate([5,3,5])])
        self.assertEqual(result['minimum_contacts'], 3)
        self.assertTrue(any(c['fret']==3 and c['first_string']==0 and c['last_string']==2
                            for cover in result['covers'] for c in cover))
        self.assertFalse(any(c['fret']==5 and c['first_string']==0 and c['last_string']==2
                             for cover in result['covers'] for c in cover))

    def test_open_shape_and_distinct_digit_limit(self):
        self.assertEqual(analyze([dict(string=0,fret=0)])['covers'], [[]])
        result=analyze([dict(string=i,fret=i+1) for i in range(5)])
        self.assertEqual(result['status'],'NO_COVER_WITHIN_MODEL')

    def test_search_limit_never_returns_partial_covers(self):
        result=analyze([dict(string=0,fret=5),dict(string=1,fret=5)],search_limit=2)
        self.assertEqual(result['status'],'SEARCH_LIMIT')
        self.assertEqual(result['covers'],[])
        self.assertIsNone(result['minimum_contacts'])

    def test_rejects_ambiguous_or_malformed_input(self):
        for required in ([],[dict(string=0,fret=True)],[dict(string=0,fret=1.5)],
                         [dict(string=0,fret=-1)],[dict(string=0,fret=1)]*2):
            with self.assertRaises(ValueError):analyze(required)


if __name__=='__main__':unittest.main()
