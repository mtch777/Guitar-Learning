"""Exact source timing/technique semantics, not music-quality assertions."""
import importlib.util
from fractions import Fraction as F
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
import source_semantics as s
import analyze_relationships as a


def b(notes=None,d=(1,4),**kw):return dict(duration=list(d),notes=notes or [],**kw)
def n(f=0,string=0,**kw):return dict(fret=f,string=string,**kw)
def m(beats=None,**kw):return dict(voices=[dict(beats=beats or [])],**kw)
def t(measures,**kw):return dict(partId=0,instrumentId=30,tuning=[40,45],measures=measures,**kw)


class SourceSemanticsTests(unittest.TestCase):
    def test_shared_meter_pickup_and_marker_normalization(self):
        parts=[t([m([b([n()],d=(1,8))],signature=[4,4],marker=dict(text='Intro',width=90)),m([b([n()])])],anacrusis=True),
               t([m([b([n()],d=(1,8))]),m([b([n()])],signature=[3,4])])]
        headers,w=s.layout(parts)
        self.assertEqual(w,[]);self.assertEqual(headers[0]['span_q'],'1/2')
        self.assertEqual(headers[1]['start_q'],'1/2');self.assertEqual(headers[1]['span_q'],'3')
        rows,_,sections,_=a.occurrences(parts[0],headers)
        self.assertEqual(rows[1]['onset_q'],'1/2');self.assertEqual(sections[0]['label'],'Intro')

    def test_conflicting_meter_is_explicit(self):
        _,w=s.layout([t([m(signature=[3,4])]),t([m(signature=[4,4])])])
        self.assertEqual(w[0]['reason'],'conflicting_track_meter')

    def test_whole_rest_spans_and_conflicting_flags(self):
        part=t([dict(rest=True,signature=[3,8]),dict(voices=[dict(rest=True)]),m([b([n()],rest=True)])])
        headers,_=s.layout([part]);rows,w=s.rests(part,headers)
        self.assertEqual([r['duration_q'] for r in rows],['3/2','3/2'])
        self.assertEqual(w[0]['reason'],'beat_rest_conflicts_with_notes')
        self.assertFalse(a.track_analysis(part)['temporal_relationships_eligible'])

    def test_repeat_first_and_second_endings(self):
        part=t([m(repeatStart=True),m(alternateEnding=[1],repeat=2),m(alternateEnding=[2]),m()])
        order=s.playback_order(s.layout([part])[0])
        self.assertTrue(order['complete']);self.assertEqual([x['bar'] for x in order['order']],[1,2,1,3,4])

    def test_nested_repeats_and_expansion_limit(self):
        headers=s.layout([t([m(repeatStart=True),m(repeatStart=True),m(repeat=2),m(repeat=2)])])[0]
        order=s.playback_order(headers)
        self.assertEqual([x['bar'] for x in order['order']],[1,2,3,2,3,4,1,2,3,2,3,4])
        self.assertFalse(s.playback_order(headers,limit=3)['complete'])

    def test_bend_scale_precise_positions_point_vibrato_and_slopes(self):
        shape=s.curve(dict(tone=50,points=[dict(position=0,tone=0),dict(position=30,precisePosition=51,tone=50,vibrato=True),dict(position=60,tone=50)]),'2')
        self.assertEqual(shape['peak_semitones'],'1')
        self.assertEqual(shape['first_peak_fraction'],'51/100')
        self.assertEqual(shape['slopes_semitones_per_quarter'][0],'50/51')
        self.assertEqual(shape['point_vibrato_flags'],1)
        self.assertEqual(s.curve_at(shape,F(51,200)),F(1,2))
        self.assertTrue(shape['declared_peak_agrees'])

    def test_invalid_curve_order_and_declared_peak_mismatch(self):
        shape=s.curve(dict(tone=50,points=[dict(position=30,tone=100),dict(position=0,tone=0)]),'1')
        self.assertFalse(shape['valid']);self.assertFalse(shape['declared_peak_agrees'])
        self.assertIsNone(s.curve_at(shape,0))

    def test_tremolo_and_brush_keep_units_separate(self):
        part=t([m([b([n(tremolo=[1,16])],brushStroke=dict(direction='down',duration=235,shift=100))])])
        report=a.track_analysis(part);v=report['technique_values'][0]
        self.assertEqual(v['tremolo_period_q'],'1/4');self.assertEqual(v['tremolo_attacks_per_quarter'],'4')
        self.assertEqual(v['brush']['duration_native'],235)
        self.assertEqual(v['brush']['time_unit'],'unverified_native_unit')
        part['measures'][0]['voices'][0]['beats'][0]['upStroke']=True
        changed=a.track_analysis(part)['technique_values'][0]['brush']
        self.assertEqual(changed['direction'],'down')
        self.assertEqual(changed['effective_direction'],'up')
        self.assertEqual(changed['direction_source'],'upStroke_override')

    def test_tempo_changes_and_sound_ticks(self):
        part=t([m([b([n()]),b([n()],tempo=dict(bpm=60,type=4))]),m()],
               automations=dict(tempo=[dict(measure=0,position=0,bpm=120,type=4)]),
               sounds=[dict(instrumentId=30,label='D'),dict(instrumentId=29,label='O')],
               trackAutomations=dict(trackSoundAutomations=[dict(measure=1,position=1200,soundId=1)]))
        time=s.timeline([part],s.layout([part])[0])
        self.assertEqual(s.seconds_between(0,2,time),1.5)
        self.assertEqual(time['sound_changes'][0]['onset_q'],'21/4')
        self.assertEqual(time['sound_changes'][0]['program'],29)

    def test_conflicting_tempo_or_unverified_ramp_does_not_invent_seconds(self):
        p=t([m()],automations=dict(tempo=[dict(measure=0,position=0,bpm=120,type=4,linear=True)]))
        time=s.timeline([p],s.layout([p])[0]);self.assertIsNone(s.seconds_between(0,1,time))
        q=t([m()],automations=dict(tempo=[dict(measure=0,position=0,bpm=90,type=4)]))
        time=s.timeline([p,q],s.layout([p,q])[0]);self.assertTrue(time['warnings']);self.assertIsNone(s.seconds_between(0,1,time))

    def test_tie_chain_and_held_bend_pitch_center(self):
        curve=dict(tone=50,points=[dict(position=0,tone=0),dict(position=60,tone=50)])
        part=t([dict(signature=[4,4],voices=[dict(beats=[b([n(bend=curve)],d=(1,2)),b([n(tie=True)],d=(1,4))]),
                                                    dict(beats=[b([dict(rest=True)]),b([n(f=1,string=1)],palmMute=True)])])])
        report=a.track_analysis(part);rels=report['sustain_relationships']
        chain=next(c for c in rels['chains'] if len(c['members'])==2)
        self.assertEqual(chain['end_q'],'3')
        held=next(c for c in rels['technique_contexts'] if c['held_neighbors'])['held_neighbors'][0]
        self.assertEqual(held['notated_center_interval_from_target'],'-11/2')
        self.assertEqual(held['written_interval_from_target'],-6)

    def test_vocal_metadata_excluded_from_guitar_statistics_without_erasing_notes(self):
        report=a.track_analysis(t([m([b([n()])])]),catalog=dict(isVocalTrack=True))
        self.assertFalse(report['guitar_or_bass']);self.assertTrue(report['program_guitar_or_bass'])
        self.assertEqual(report['summary']['note_segments'],1)


if __name__=='__main__':unittest.main()
