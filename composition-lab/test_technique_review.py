import tempfile
import unittest
from pathlib import Path
from build_technique_review import fixture
from gp_author import write_gp
from exact_score import extract_score
from technique_analysis import analyze
from technique_edits import generate_hopo
from technique_report import summarize


class ReviewCoverageTests(unittest.TestCase):
    def test_fixture_has_distinct_nonempty_methods_and_high_positions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.gp';write_gp(fixture(),source)
            for family in ('hammer_on_fretted','pull_off_fretted','hammer_on_from_open','pull_off_to_open'):
                selected=[]
                for method in ('short_intervals','long_arrivals'):
                    out=root/(family+method+'.gp');audit=generate_hopo(source,out,0,family,method=method)
                    self.assertGreater(audit['selected'],0)
                    selected.append({(p['origin'],p['destination']) for p in analyze(extract_score(out))['tracks'][0]['explicit_hopo']})
                self.assertNotEqual(*selected)
            self.assertTrue(any(n['fret']>=12 for m in fixture()['tracks'][0]['measures'] for e in m['voices'][0] for n in e['notes']))

    def test_report_keeps_unknown_phrase_and_marker_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.gp';write_gp(fixture(),source)
            report=summarize(extract_score(source))
            self.assertFalse(report['phrase_inference_used']);self.assertFalse(report['artist_inference_used'])
            track=report['tracks'][0];self.assertIsNone(track['phrase_metrics'])
            self.assertEqual(track['attacks'],32)
            self.assertTrue(all(r['numerator']==0 and r['denominator']>0 for r in track['hopo_rates'].values()))


if __name__=='__main__':unittest.main()
