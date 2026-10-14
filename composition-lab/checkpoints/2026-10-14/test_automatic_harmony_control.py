import unittest, tempfile
from pathlib import Path
from extract import extract_score
from automatic_harmony_control import candidate_chords,infer_harmony,selected_harmony,run

SOURCE=Path('/mnt/data/Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp')

class AutomaticHarmonyTests(unittest.TestCase):
    def test_triads(self):
        self.assertEqual(candidate_chords([50,53,57])[0][0],'minor')
        self.assertEqual(candidate_chords([50,54,57])[0][0],'major')
        self.assertEqual(candidate_chords([50,53]),[])
        self.assertEqual(candidate_chords([50,53,57,60,64])[0][0],'minor9')  # now recognized
    def test_shared_chord_vocabulary_beyond_triads(self):
        cases=[([60,64,67,71],'major7'),([60,63,67,70],'minor7'),
               ([60,64,67,70],'dom7'),([60,63,66],'dim'),
               ([60,62,67],'sus2'),([60,65,67],'sus4'),([60,67],'5')]
        for pitches,quality in cases:
            with self.subTest(quality=quality):
                self.assertEqual(candidate_chords(pitches)[0][0],quality)
        self.assertEqual(candidate_chords([60,61,62,63]),[])
    def test_extended_and_altered_chords(self):
        from harmonic_inference import CHORDS
        cases = ['add9','major9','minor9','dom9','minor11','dom11',
                 'major13','minor13','dom13','7b9','7#9','7#11','7b13','13#11']
        for name in cases:
            with self.subTest(name=name):
                notes=[60+i for i in CHORDS[name]]
                candidates=candidate_chords(notes)
                self.assertTrue(candidates, f'Not recognized: {name}')
                self.assertEqual(candidates[0][0],name)
                self.assertEqual(len(candidates[0][1].degrees),len(CHORDS[name]))

    def test_extension_mapping_retains_function_and_octave(self):
        from harmonic_relative import Chord,analyze_note,map_note
        from harmonic_inference import CHORDS
        source=Chord(48,tuple((d,i) for d,i in ((1,0),(3,4),(5,7),(7,10),(9,14),(11,18),(13,21))))
        target=Chord(50,tuple((d,i) for d,i in ((1,0),(3,3),(5,7),(7,10),(9,13),(11,17),(13,20))))
        # Altered 9/11/13 keep their degree function, with the octave unchanged.
        for pitch,expected in [(62,63),(66,67),(69,70),(50,51)]:
            self.assertEqual(map_note(analyze_note(pitch,source),target),expected)

    def test_seventh_degree_maps_to_new_chord_quality(self):
        from harmonic_relative import Chord,analyze_note,map_note
        src=candidate_chords([60,64,67,71])[0][1]
        dst=candidate_chords([62,65,69,72])[0][1]
        self.assertEqual(dst.degrees[-1],(7,10))
        self.assertEqual([map_note(analyze_note(p,src),dst) for p in (60,64,67,71)],
                         [62,65,69,72])
    def test_change_probability_zero_and_seed(self):
        score=extract_score(SOURCE)
        spans,_=infer_harmony(score,0)
        a=selected_harmony(spans,0,5)
        self.assertTrue(all(x['target']==x['chord'] for x in a))
        self.assertEqual(selected_harmony(spans,.5,5),selected_harmony(spans,.5,5))
        self.assertTrue(any(x['target']!=x['chord'] for x in selected_harmony(spans,1,5)))
    def test_reharmonization_preserves_all_beat_durations_and_nonselected_pitches(self):
        if not SOURCE.exists():self.skipTest('Source unavailable')
        original=extract_score(SOURCE)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'reharm.gp'
            report=run(SOURCE,out,0,1,17)
            self.assertGreater(report['changed_source_note_ids'],0)
            modified=extract_score(out)
            self.assertEqual(original['measure_count'],modified['measure_count'])
            changed=0
            for src_track,dst_track in zip(original['tracks'],modified['tracks']):
                for sm,dm in zip(src_track['measures'],dst_track['measures']):
                    self.assertEqual(sm['time_signature'],dm['time_signature'])
                    for sv,dv in zip(sm['voices'],dm['voices']):
                        self.assertEqual([x['duration_q'] for x in sv],[x['duration_q'] for x in dv])
                        for se,de in zip(sv,dv):
                            self.assertEqual([n['note_id'] for n in se['notes']],[n['note_id'] for n in de['notes']])
                            for sn,dn in zip(se['notes'],de['notes']):
                                changed+=sn['midi']!=dn['midi']
            self.assertGreater(changed,0)
    def test_zero_change_is_identity(self):
        original=extract_score(SOURCE)
        with tempfile.TemporaryDirectory() as td:
            modified=extract_score(Path(td)/'identity.gp') if False else None
            out=Path(td)/'identity.gp';r=run(SOURCE,out,0,0,17)
            self.assertEqual(r['changed_source_note_ids'],0)
            modified=extract_score(out)
            def sig(s):
                return [(n['note_id'],n['midi']) for t in s['tracks'] for m in t['measures'] for v in m['voices'] for e in v for n in e['notes']]
            self.assertEqual(sig(original),sig(modified))

if __name__=='__main__':unittest.main()