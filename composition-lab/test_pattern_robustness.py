import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).parent/'songsterr_automation/songsterr_api'
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('robustness',ROOT/'analyze_pattern_robustness.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def row(key,pitch,string,start,duration):
    return dict(occurrence=key,midi=pitch,string=string,onset_q=str(start),duration_q=str(duration),pitch_effects=False)


class RobustnessTests(unittest.TestCase):
    def test_held_notes_and_half_open_boundaries(self):
        rows=[row('a',40,0,0,2),row('b',41,1,1,1),row('c',47,1,2,1)]
        intervals=m.sustained_groups(rows)
        self.assertEqual(len(intervals),1)
        self.assertEqual(intervals[0]['start_q'],'1')
        self.assertTrue(intervals[0]['includes_held_notes'])
        self.assertIn('close_interval_texture',intervals[0]['labels'])
        # Ending at two cannot overlap the new note at two.
        self.assertNotIn('power_chord',intervals[0]['labels'])

    def test_same_string_is_not_a_double_stop(self):
        self.assertEqual(m.sustained_groups([row('a',40,0,0,2),row('b',41,0,1,1)]),[])

    def test_overlap_collapse_and_section_scope(self):
        records=[dict(anchor=40,section=1,start_q='0',end_q='4',signature='s',unit_q='1'),
                 dict(anchor=40,section=1,start_q='2',end_q='6',signature='s',unit_q='1'),
                 dict(anchor=42,section=2,start_q='8',end_q='12',signature='s',unit_q='2')]
        self.assertEqual([r['windows'] for r in m.episodes(records)],[2,1])
        groups=m.recurrences(records)
        self.assertEqual(len(groups),1)
        self.assertEqual(len(groups[0]['occurrences']),2)
        self.assertTrue(groups[0]['transposed']);self.assertTrue(groups[0]['time_scaled'])
        self.assertEqual(groups[0]['sections'],2)


if __name__=='__main__':unittest.main()
