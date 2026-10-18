import unittest
from pedal_regions import detect_regions


def rows(groups):
    return [dict(occurrence=f'{i}:{j}',onset_q=str(i),duration_q='1',midi=p,string=j,tie_destination=False,section_start=1)
            for i,group in enumerate(groups) for j,p in enumerate(group)]


class PedalRegionTests(unittest.TestCase):
    def test_complete_repeated_chugs(self):
        data=rows([[40],[40],[52],[40],[40],[55],[40],[40],[52]])
        found=detect_regions(data)
        anchor=next(r for r in found if r['anchor_pitches']==[40])
        self.assertEqual(anchor['anchor_attacks'],6)
        self.assertEqual(len(anchor['anchor_occurrences']),6)

    def test_interval_anchor_and_chord_negative(self):
        found=detect_regions(rows([[28,35],[55],[28,35],[59],[28,35],[60]]))
        self.assertEqual(found[0]['anchor_pitches'],[28,35])
        self.assertEqual(found[0]['anchor_kind'],'interval')
        self.assertFalse(detect_regions(rows([[40,47,52],[42,49,54],[40,47,52],[44,51,56],[40,47,52]])))

    def test_sustained_anchor_not_called_separated(self):
        data=rows([[40],[52],[40],[55],[40]])
        for n in data:
            if n['midi']==40:n['duration_q']='3'
        self.assertFalse(detect_regions(data))

    def test_feedback_rejects_wrong_study(self):
        import sys
        from pathlib import Path
        sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
        from evaluate_pedal_regions import feedback_audit
        with self.assertRaises(ValueError):feedback_audit(dict(study='different-study'),[])

    def test_regular_chord_cycle_abstains_but_rhythmic_returns_survive(self):
        data=rows([[40],[44],[47],[44]]*3)
        self.assertFalse(detect_regions(data))
        for n in data:
            if n['midi']==40:n['duration_q']='1/2'
        self.assertEqual([r['anchor_pitches'] for r in detect_regions(data)],[[40]])

    def test_equal_repetition_prefers_lower_and_transposes(self):
        data=rows([[40],[41],[52]]*4)
        self.assertEqual([r['anchor_pitches'] for r in detect_regions(data)],[[40]])
        for n in data:n['midi']+=5
        self.assertEqual([r['anchor_pitches'] for r in detect_regions(data)],[[45]])

    def test_reduced_interval_voicing_is_retained(self):
        data=rows([[28,35],[55],[28,35],[59],[28,35],[60],[28]])
        detected=detect_regions(data)[0]
        self.assertEqual(detected['partial_voicing_attacks'],1)
        self.assertEqual(len(detected['anchor_occurrences']),7)
        self.assertEqual(detected['end_q'],'7')

    def test_sequential_low_anchors_are_not_suppressed(self):
        data=rows([[45],[57],[45],[59],[45],[57],[40],[52],[40],[55],[40]])
        self.assertEqual([r['anchor_pitches'] for r in detect_regions(data)],[[40],[45]])


if __name__=='__main__':unittest.main()
