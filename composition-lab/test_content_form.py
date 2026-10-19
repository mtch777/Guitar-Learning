import copy,unittest
from content_form import signature,timeline_signature
from fractions import Fraction as F
from unittest.mock import patch
import content_form

def bar(roots):
    return dict(meter='4/4',events=[dict(duration_q='1',intervals=[0]) for _ in roots],root_events=[dict(root=p) for p in roots])

class ContentFormTests(unittest.TestCase):
    def test_grace_has_zero_metric_time_and_preserves_written_length(self):
        rows=[dict(occurrence=str(i),voice=0,tie_destination=False,onset_q=str(i),duration_q='1',midi=40+i) for i in range(4)]
        grace=dict(occurrence='g',voice=0,tie_destination=False,onset_q='1/2',duration_q='1/4',midi=55)
        track=dict(rows=rows,grace_rows=[grace]);headers=[dict(start_q='0',span_q='4',signature=[4,4])];captured=[]
        def record(value):captured.append(value);return str(value)
        with patch.object(content_form,'stable_hash',record):timeline_signature(track,headers,F(0),F(4))
        ornaments=[e for obj in captured if isinstance(obj,dict) for e in obj.get('events',[]) if e[3]]
        self.assertEqual(ornaments[0][2],'0');self.assertEqual(ornaments[0][4],'1/4')
    def test_original_ties_match_long_written_note(self):
        rows=[dict(occurrence=str(i),voice=0,tie_destination=False,onset_q=str(q),duration_q=str(d),midi=p) for i,(q,d,p) in enumerate([(0,1,40),(2,1,42),(3,1,43),(4,1,40)])]
        track=dict(rows=rows,sustain_relationships=dict(chains=[dict(origin='0',end_q='2',orphan_tie=False)]))
        headers=[dict(start_q=str(q),span_q='4',signature=[4,4]) for q in (0,4)]
        a=timeline_signature(track,headers,F(0),F(8));other=copy.deepcopy(track);other['rows'][0]['duration_q']='2';other['sustain_relationships']={}
        self.assertIsNotNone(a);self.assertEqual(a,timeline_signature(other,headers,F(0),F(8)))
        track['sustain_relationships']['chains'][0]['orphan_tie']=True
        self.assertIsNone(timeline_signature(track,headers,F(0),F(8)))
    def test_transposition_and_exact_repeat(self):
        a=[bar([40,42,40,43]),bar([45,42,40,43])]
        b=copy.deepcopy(a)
        for p in b:
            for e in p['root_events']:e['root']+=12
        self.assertEqual(signature(a),signature(b));self.assertEqual(signature(a),signature(a+a))

    def test_contour_and_rhythm_change_not_identity(self):
        a=[bar([40,42,40,43])];b=copy.deepcopy(a);b[0]['root_events'][2]['root']=45
        self.assertNotEqual(signature(a),signature(b));b=copy.deepcopy(a);b[0]['events'][0]['duration_q']='1/2'
        self.assertNotEqual(signature(a),signature(b))

    def test_static_texture_and_short_input_abstain(self):
        self.assertIsNone(signature([bar([40,40,40,40])]))
        self.assertIsNone(signature([bar([40,42])]))

if __name__=='__main__':unittest.main()
