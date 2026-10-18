import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).parent/'songsterr_automation/songsterr_api'
spec=importlib.util.spec_from_file_location('pedal_review',ROOT/'build_pedal_identification_review.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ReviewTests(unittest.TestCase):
    def test_source_identity_and_plain_question(self):
        songs=[]
        with tempfile.TemporaryDirectory() as tmp:
            corpus=Path(tmp)/'songs';corpus.mkdir()
            for i,family in enumerate(['alpha','bravo','charlie','delta','echo','foxtrot']):
                folder=corpus/str(i);folder.mkdir()
                (folder/'metadata.json').write_text(json.dumps(dict(aiGenerated=False,isJunk=False)),encoding='utf-8')
                (folder/'gp7-validation.json').write_text('{"roundtripPass":true}',encoding='utf-8')
                (folder/'score.gp').write_bytes(b'unchanged-source')
                rows=[dict(occurrence=str(j),onset_q=str(j/2),duration_q='1/2',midi=40 if j%2==0 else 47,
                           bar=1,bar_offset_q=str(j/2)) for j in range(6)]
                candidate=dict(relative_period_error='0' if i<3 else '1/4',anchor_midi=40,members=[[[str(j)]] for j in range(6)])
                songs.append(dict(song_id=i,title='<source>',revision_id=1,candidate_work_family=family,
                                  playback=dict(order=[dict(bar=1)]),shared_layout=[dict(start_q='0',span_q='4')],
                                  tracks=[dict(guitar_or_bass=True,temporal_relationships_eligible=True,name='',rows=rows,pedal_candidates=[candidate])]))
            out=Path(tmp)/'out';result=m.build(dict(songs=songs),corpus,out)
            self.assertEqual(result['cases'],6)
            for gp in out.glob('*.gp'):self.assertEqual(gp.read_bytes(),b'unchanged-source')
            page=(out/'index.html').read_text(encoding='utf-8')
            self.assertIn('&lt;source&gt;',page)
            self.assertIn('Does the gold note act as a repeating anchor',page)
            self.assertNotIn('brush',page)
            self.assertEqual(len(json.loads((out/'render-jobs.json').read_text())),12)
            with self.assertRaises(FileExistsError):m.build(dict(songs=songs),corpus,out)


if __name__=='__main__':unittest.main()
