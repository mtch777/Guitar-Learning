import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent/'songsterr_automation'/'songsterr_api'))
from source_slides import resolve_slides, slide_types


def row(i, onset, fret, slide=None, **extra):
    result = dict(occurrence=str(i), onset_q=str(onset), duration_q='1',
                  voice=0, string=0, bar=1, beat=i, note=0, midi=40+fret,
                  fret=fret, tie_destination=False, raw_note={'slide':slide})
    result.update(extra)
    return result


class SlideTests(unittest.TestCase):
    def test_contiguous_target_exact_fraction_and_reverse_direction(self):
        a=row(0,'1/3',8,'shift',duration_q='2/3');b=row(1,1,3)
        e=resolve_slides([a,b])['events'][0]
        self.assertEqual((e['destination'],e['interval_semitones'],e['transition_q']),('1',-5,'1'))

    def test_tie_continuation_extends_original_attack(self):
        e=resolve_slides([row(0,0,2,'legato'),row(1,1,2,tie_destination=True),row(2,2,6)])['events'][0]
        self.assertEqual(e['destination'],'2');self.assertEqual(e['tied_members'],['1'])
        self.assertEqual(e['sustained_origin_duration_q'],'2')
        self.assertEqual(e['status'],'target_after_tie_candidate')

    def test_wrong_voice_or_string_never_supplies_target(self):
        for change in [{'voice':1},{'string':1}]:
            e=resolve_slides([row(0,0,2,'shift'),row(1,1,6,**change)])['events'][0]
            self.assertEqual(e['status'],'no_next_same_string_note')

    def test_exclusions_do_not_invent_destinations(self):
        for target,expected in [(row(1,2,6),'gap_or_overlap'),(row(1,'1/2',6),'gap_or_overlap'),
                                (row(1,1,2),'same_fret'),(row(1,1,6,midi=None),'unknown_or_dead_pitch'),
                                (row(1,1,6,tie_destination=True),'target_tie_unresolved')]:
            e=resolve_slides([row(0,0,2,'shift'),target])['events'][0]
            self.assertEqual(e['status'],expected);self.assertIsNone(e['destination'])

    def test_grace_does_not_masquerade_as_contiguous_regular_target(self):
        a,b=row(0,0,2,'shift'),row(1,1,6)
        g=row(2,1,4,'legato')
        events=resolve_slides([a,b],[g])['events']
        self.assertEqual([e['status'] for e in events],['grace_at_transition','grace_origin_order_unresolved'])

    def test_entry_exit_endpoints_remain_unspecified(self):
        events=resolve_slides([row(0,0,2,'below'),row(1,1,3,'above'),row(2,2,4,'downwards')])['events']
        self.assertEqual([e['status'] for e in events],['entry_origin_unspecified']*2+['exit_target_unspecified'])
        self.assertIsNone(events[0]['origin']);self.assertIsNone(events[2]['destination'])

    def test_combined_types_and_unknown_raw_values(self):
        self.assertEqual(slide_types('belowlegato'),['below','legato'])
        self.assertEqual(slide_types('shiftjunk'),[])
        e=resolve_slides([row(0,0,2,'shiftjunk')])['events'][0]
        self.assertEqual(e['status'],'unsupported_slide_value');self.assertEqual(e['raw_value'],'shiftjunk')


if __name__ == '__main__':unittest.main()
