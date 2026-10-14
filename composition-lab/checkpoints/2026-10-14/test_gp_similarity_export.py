import hashlib
import tempfile
import unittest
from pathlib import Path
from extract import extract_score
from gp_similarity_export import export

SOURCE=Path('/mnt/data/Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp')

class TestGpExport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'export.gp'
        self.original=extract_score(SOURCE)

    def test_zero_is_byte_identical(self):
        r=export(SOURCE,self.path)
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).digest(),hashlib.sha256(self.path.read_bytes()).digest())
        self.assertEqual(r['rhythm_swaps'],0)
        self.assertEqual(r['changed_note_definitions'],0)

    def test_chords_only_locks_all_timing(self):
        r=export(SOURCE,self.path,chords=100)
        self.assertGreater(r['changed_note_definitions'],0)
        self._compare(rhythm_locked=True)

    def test_melody_only_locks_all_timing(self):
        r=export(SOURCE,self.path,melody=100)
        self.assertGreater(r['changed_note_definitions'],0)
        self._compare(rhythm_locked=True)

    def test_rhythm_only_locks_all_pitches(self):
        r=export(SOURCE,self.path,rhythm=100)
        self.assertGreater(r['rhythm_swaps'],0)
        after=extract_score(self.path)
        for before_track,after_track in zip(self.original['tracks'],after['tracks']):
            for bm,am in zip(before_track['measures'],after_track['measures']):
                for bv,av in zip(bm['voices'],am['voices']):
                    self.assertEqual([[n['midi'] for n in b['notes']] for b in bv],[[n['midi'] for n in b['notes']] for b in av])
                    self.assertEqual(sum((__import__('fractions').Fraction(b['duration_q']) for b in bv),__import__('fractions').Fraction(0)),sum((__import__('fractions').Fraction(b['duration_q']) for b in av),__import__('fractions').Fraction(0)))

    def test_combined_determinism(self):
        a=export(SOURCE,self.path,chords=100,melody=70,rhythm=80,seed=19)
        first=self.path.read_bytes()
        b=export(SOURCE,self.path,chords=100,melody=70,rhythm=80,seed=19)
        self.assertEqual(first,self.path.read_bytes())
        self.assertEqual(a['changed_note_definitions'],b['changed_note_definitions'])

    def test_reject_overwrite(self):
        with self.assertRaises(ValueError):export(SOURCE,SOURCE)

    def test_invalid_slider(self):
        with self.assertRaises(ValueError):export(SOURCE,self.path,rhythm=101)

    def _compare(self,rhythm_locked):
        after=extract_score(self.path)
        self.assertEqual(after['measure_count'],self.original['measure_count'])
        for bt,at in zip(self.original['tracks'],after['tracks']):
            for bm,am in zip(bt['measures'],at['measures']):
                for bv,av in zip(bm['voices'],am['voices']):
                    for b,a in zip(bv,av):
                        if rhythm_locked:self.assertEqual((a['onset_q'],a['duration_q']),(b['onset_q'],b['duration_q']))
                        self.assertEqual([n['note_id'] for n in b['notes']],[n['note_id'] for n in a['notes']])

if __name__=='__main__':unittest.main()