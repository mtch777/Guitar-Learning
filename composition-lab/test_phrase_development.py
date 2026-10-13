import unittest
from phrase_development import (normalized_distance, segment_section, analyze_track,
                               phrase_events, boundary_strength)

class PhraseDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.pattern=[[(0,j*.25,.25,(40+[0,3,5,7][j],)) for j in range(4)] for _ in range(8)]
    def test_segment_without_markers(self):
        self.assertEqual(segment_section(self.pattern,0,8),[(0,4),(4,8)])
    def test_hard_section_boundaries(self):
        track={'name':'Guitar 1','measures':self.pattern}
        result=analyze_track(track,[(1,'A'),(5,'B')],8)
        self.assertEqual([(x['start_measure'],x['end_measure']) for x in result['phrases']],[(1,4),(5,8)])
    def test_transposed_equal(self):
        first=[(0,j*.25,.25,p) for j,p in enumerate([40,43,45,47])]
        second=[(0,j*.25,.25,p+5) for j,p in enumerate([40,43,45,47])]
        self.assertEqual(normalized_distance(first,second),0)
    def test_note_changes(self):
        first=[(0,j*.25,.25,p) for j,p in enumerate([40,43,45,47])]
        second=[(0,j*.25,.25,p) for j,p in enumerate([40,43,46,47])]
        self.assertGreater(normalized_distance(first,second),0)
        self.assertLessEqual(normalized_distance(first,second),.22)
    def test_contrast(self):
        a=[(0,j*.25,.25,p) for j,p in enumerate([40,43,45,47])]
        b=[(0,j*.25,.25,p) for j,p in enumerate([40,41,42,43])]
        self.assertGreater(normalized_distance(a,b),.22)
    def test_captures_primary_voice(self):
        m=[[(0,0,.25,(40,52)),(1,0,.25,(66,))]]
        self.assertEqual(phrase_events(m,0,1),[(0,0,.25,40)])
    def test_density_change(self):
        active=[(0,i*.25,.25,(40+i,)) for i in range(4)]
        self.assertGreater(boundary_strength([active,active,[],[]],2),0)

if __name__=='__main__':unittest.main()