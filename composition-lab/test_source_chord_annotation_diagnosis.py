"""Diagnostic dependency is optional; no parsed-symbol inverse is claimed."""
from importlib.util import find_spec
import unittest
from unittest.mock import patch
import warnings

HAS_MUSIC21=find_spec('music21') is not None
if HAS_MUSIC21:
    from diagnose_source_chord_annotations import annotation_inventory,parse_symbol,set_comparison
    from test_contextual_chord_motion import source
    from experiment_chord_glyph_adapter import normalize_roots,restore_roots,glyph_map


@unittest.skipUnless(HAS_MUSIC21,'Optional pinned music21 diagnostic runtime')
class AnnotationDiagnosisTests(unittest.TestCase):
    def test_root_and_slash_accidentals_are_lossless_without_quality_rewriting(self):
        for letter in 'ABCDEFG':
            for glyph,modifier in glyph_map().items():
                raw=letter+glyph+'m7/G'+glyph
                normalized,trace=normalize_roots(raw)
                self.assertEqual(normalized,letter+modifier+'m7/G'+modifier)
                self.assertEqual(restore_roots(normalized,trace),raw)
                self.assertEqual(len(trace),2)
        for raw in ('F#m3','Cmaj7♯11','not a chord',''):
            normalized,trace=normalize_roots(raw)
            self.assertEqual(normalized,raw)
            self.assertEqual(trace,[])
        self.assertEqual(parse_symbol(normalize_roots('F♯m3')[0])['status'],'UNPARSED_RETAINED')

    def test_inverse_rejects_conflicting_modifier(self):
        normalized,trace=normalize_roots('A♭m')
        with self.assertRaises(ValueError):restore_roots(normalized.replace('-','#'),trace)

    def test_warning_survives_parser_failure(self):
        def fail(text):
            warnings.warn('retained diagnostic',UserWarning)
            raise ValueError('deliberate parser refusal')
        with patch('diagnose_source_chord_annotations.harmony.ChordSymbol',fail):
            result=parse_symbol('C')
        self.assertEqual(result['status'],'UNPARSED_RETAINED')
        self.assertEqual(result['warnings'],[dict(category='UserWarning',message='retained diagnostic')])

    def test_literal_slash_chord_root_bass_and_refused_text(self):
        parsed=parse_symbol('Gm/D')
        self.assertEqual(parsed['status'],'PARSED_LIBRARY_INTERPRETATION')
        self.assertEqual((parsed['root_pc'],parsed['bass_pc']),(7,2))
        self.assertEqual(parsed['pitch_classes'],[2,7,10])
        self.assertEqual(parse_symbol('not a chord label')['status'],'UNPARSED_RETAINED')
        self.assertEqual(parse_symbol('')['status'],'UNPARSED_RETAINED')

    def test_annotation_point_scope_and_grace_do_not_invent_duration(self):
        docs=source();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats.insert(0,dict(duration=[1,16],graceNote=True,notes=[dict(string=0,fret=26)]))
        beats[1]['chord']=dict(text='E7');beats[2]['chord']=dict(text='Am')
        rows,problems=annotation_inventory(docs)
        self.assertEqual([r['at_q'] for r in rows],['0','1'])
        self.assertEqual([r['beat'] for r in rows],[1,2])
        self.assertTrue(all(r['annotation_duration_q'] is None and r['part_id']==0 for r in rows))
        self.assertEqual(rows[0]['literal_text'],'E7');self.assertEqual(problems,[])

    def test_set_disagreement_is_observation_not_annotation_accuracy(self):
        parsed=parse_symbol('C')
        observed=dict(pitch_classes=[0,4],unknown_or_noninteger_pitch=[],lowest_known_pc=4)
        result=set_comparison(observed,parsed)
        self.assertEqual(result['status'],'OBSERVED_SUBSET_OF_SYMBOL')
        self.assertEqual(result['symbol_tones_not_observed'],[7])
        self.assertFalse(result['lowest_known_pc_matches_declared_bass'])
        observed['unknown_or_noninteger_pitch']=[dict(occurrence_ref='unresolved')]
        self.assertTrue(set_comparison(observed,parsed)['partial_known_pitch_evidence'])
        self.assertNotIn('accuracy',result)


if __name__=='__main__':unittest.main()
