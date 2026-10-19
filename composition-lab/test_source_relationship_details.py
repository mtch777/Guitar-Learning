import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
import analyze_relationships as a


def note(fret=0,string=0,**kw):return dict(fret=fret,string=string,**kw)
def beat(*notes,duration=(1,4)):return dict(notes=list(notes),duration=list(duration))
def measure(*beats):return dict(signature=[4,4],voices=[dict(beats=list(beats))])
def part(*measures):return dict(partId=0,instrumentId=30,tuning=[40,45],measures=list(measures))


class RelationshipDetailsTests(unittest.TestCase):
    def test_local_recovery_does_not_enable_global_detectors_or_cross_intrusion(self):
        dyad=lambda:beat(note(),note(string=1,fret=2))
        p=part(measure(dyad()),measure(beat(note(),duration=(2,1))),
               measure(dyad()),measure(dyad()))
        raw=copy.deepcopy(p);t=a.track_analysis(p)
        self.assertFalse(t['temporal_relationships_eligible'])
        self.assertEqual(t['coattack_groups'],[])
        self.assertEqual(t['pedal_candidates'],[])
        recovered=t['relationship_details']['recovered_coattack_groups']
        self.assertEqual([g['onset_q'] for g in recovered],['0','12'])
        self.assertTrue(all('power_chord' in g['labels'] for g in recovered))
        self.assertEqual(p,raw)

    def test_slide_target_in_bad_bar_stays_candidate_without_pitched_claim(self):
        t=a.track_analysis(part(measure(beat(note(slide='shift'),duration=(1,1))),
                                measure(beat(note(fret=5),duration=(2,1)))))
        event=t['relationship_details']['slides']['events'][0]
        self.assertEqual(event['status'],'excluded_for_timing')
        self.assertIsNotNone(event['candidate_destination'])
        self.assertIsNone(event['destination'])
        self.assertIsNone(event['interval_semitones'])

    def test_unpitched_links_are_separate_from_existing_sounding_chains(self):
        t=a.track_analysis(part(measure(beat(note(dead=True)),
               beat(note(dead=True,tie=True)),beat(note(tie=True)))))
        details=t['relationship_details']['unpitched_ties']
        self.assertEqual(len(details['links']),1)
        self.assertIsNone(details['links'][0]['sounding_pitch'])
        self.assertEqual(details['unresolved'][0]['reason'],'dead_to_pitched')
        self.assertEqual(len(t['sustain_relationships']['warnings']),2)
        self.assertEqual(len(t['sustain_relationships']['chains']),3)

    def test_tie_extended_slide_candidate_cannot_claim_unsafe_destination(self):
        t=a.track_analysis(part(measure(beat(note(slide='shift')),
                                        beat(note(tie=True),duration=(3,4))),
                                measure(beat(note(fret=5),duration=(2,1)))))
        event=t['relationship_details']['slides']['events'][0]
        self.assertEqual(event['status'],'excluded_for_timing')
        self.assertEqual(event['status_before_timing_gate'],'target_after_tie_candidate')
        self.assertIsNone(event['destination'])
        self.assertIsNone(event['interval_semitones'])

    def test_identity_warning_blocks_additional_relationship_claims(self):
        p=part(measure(beat(note(slide='shift')),beat(note(fret=5))))
        t=a.track_analysis(p,identity_warnings=[dict(reason='mismatched_revision')])
        d=t['relationship_details']
        self.assertEqual(d['local_timing']['all_voice_regions'],[])
        self.assertEqual(d['slides']['events'][0]['status'],'excluded_for_timing')
        self.assertEqual(d['recovered_coattack_groups'],[])


if __name__=='__main__':unittest.main()
