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


if __name__=='__main__':unittest.main()
