import hashlib,json,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch
from build_continuity_review import build

class ContinuityReviewTests(unittest.TestCase):
    def fixture(self,root):
        root=root/'local-artifacts';root.mkdir();rows=[]
        score=dict(tempo_bpm='120',tracks=[dict(name=n,measures=[dict(onset_q='0',number=1)]) for n in ('harmony','melody','bass')])
        for method in ('bar_reset','carry','register_carry'):
            gp=root/(method+'.gp');gp.write_bytes(b'fixture');gp.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8')
            audio=root/(method+'.wav')
            with wave.open(str(audio),'wb') as out:out.setnchannels(1);out.setsampwidth(2);out.setframerate(100);out.writeframes(b'\0\0'*100)
            rows.append(dict(core=1,method=method,gp=str(gp),audio=str(audio),seconds=1,audio_sha256=hashlib.sha256(audio.read_bytes()).hexdigest()))
        manifest=root/'manifest.json';manifest.write_text(json.dumps(dict(cases=rows)),encoding='utf-8');return manifest,root/'review.html',rows
    def run_build(self,manifest,output):
        with patch('build_continuity_review.read_midi_notes',return_value=(1,[(0,.5,60,100,c) for c in (0,2,4)])),patch('compose_controlled.plain_core'):
            return build(manifest,output)
    def test_all_methods_and_real_audio_links_with_blank_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            m,o,_=self.fixture(Path(directory));result=self.run_build(m,o);self.assertEqual(result['cases'],3);self.assertEqual(result['human_reviews'],0)
            text=o.read_text(encoding='utf-8');self.assertIn('"number":1',text)
            self.assertIn('These are generated pieces',text);self.assertNotIn('__DATA__',text)
            with self.assertRaises(FileExistsError):self.run_build(m,o)
    def test_checksum_and_duration_mismatch_refused_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            m,o,rows=self.fixture(Path(directory));rows[0]['audio_sha256']='wrong';m.write_text(json.dumps(dict(cases=rows)),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'checksum'):self.run_build(m,o)
            self.assertFalse(o.exists());rows[0]['audio_sha256']=hashlib.sha256(Path(rows[0]['audio']).read_bytes()).hexdigest();rows[0]['seconds']=2;m.write_text(json.dumps(dict(cases=rows)),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'duration'):self.run_build(m,o)
            self.assertFalse(o.exists())
    def test_missing_comparison_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            m,o,rows=self.fixture(Path(directory));m.write_text(json.dumps(dict(cases=rows[:2])),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'three matched'):self.run_build(m,o)
            self.assertFalse(o.exists())

if __name__=='__main__':unittest.main()
