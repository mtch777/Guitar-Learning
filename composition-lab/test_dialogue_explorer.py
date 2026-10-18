import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).parent/'songsterr_automation/songsterr_api'
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('explorer',ROOT/'build_dialogue_explorer.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def cycle():
    return dict(call=dict(pitch_signature='c',rhythm_signature='r',start_q='0',notated_duration_histogram={'1':2}),
                response=dict(pitch_signature='p',rhythm_signature='r',note_texture='monophonic',
                              semitone_dyad_attacks=0,end_q='4',notated_duration_histogram={'1':2}),
                response_to_call_span_ratio='1',call_sustain_into_response_q='0',right_censored=False)


class ExplorerTests(unittest.TestCase):
    def test_regular_and_changed_response_are_distinct(self):
        a,b=cycle(),cycle();region=dict(anchor_pitches=[40],cycles=[a,b],events=[])
        self.assertIn('regular',m.kinds(region,[a,b]))
        b['response']['pitch_signature']='new'
        self.assertNotIn('regular',m.kinds(region,[a,b]))
        self.assertIn('varied',m.kinds(region,[a,b]))

    def test_overlapping_tuplet_interval_case_keeps_all_tags(self):
        a=cycle();a['call']['notated_duration_histogram']={'1/3':3}
        a['response']['note_texture']='polyphonic';a['response']['semitone_dyad_attacks']=1
        a['call_sustain_into_response_q']='1/3';a['right_censored']=True
        region=dict(anchor_pitches=[28,35],cycles=[a],events=[])
        tags=m.kinds(region,[a])
        self.assertTrue({'interval','polyphony','close','overlap','subdivision','censored'}<=set(tags))


if __name__=='__main__':unittest.main()
