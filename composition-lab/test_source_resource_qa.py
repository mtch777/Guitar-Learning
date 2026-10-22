import json
from pathlib import Path
import tempfile
import unittest
from source_resource_qa import audit, digest


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capture = self.root / 'capture'; self.capture.mkdir()
        self.source = dict(songId=7, artistId=2, artist='Fixture artist', title='Fixture', revisionId=19, hasChords=True)
        self.supplement = dict(songId=7, artistId=2, artist='Fixture artist', title='Fixture', chordsRevisionId=31)
        self.metadata = self.root / 'supplement.json'
        self.text = self.root / 'supplement.chordpro'
        self.baseline = self.root / 'baseline.json'
        self.save(self.capture / 'metadata.json', self.source)
        self.save(self.capture / 'track-0.json', {'measures': []})
        self.save(self.metadata, self.supplement)
        self.text.write_text('[SyntheticChord] fixture, no time mapping')
        self.seal()

    def save(self, p, v): p.write_text(json.dumps(v))

    def seal(self):
        self.save(self.baseline, dict(original_hashes={p.name:digest(p) for p in self.capture.iterdir()},
                  separate_resource_hashes={p.name:digest(p) for p in (self.metadata,self.text)},
                  frozen_score_unchanged=True,automatic_score_time_alignment=True))

    def run_audit(self, **kw):
        return audit(self.capture,self.baseline,self.metadata,self.text,**kw)

    def test_independent_revisions_available_unaligned(self):
        r=self.run_audit()
        self.assertEqual(r['status'],'PASS_PROVENANCE_ONLY',r)
        self.assertEqual((r['notation_revision'],r['chord_revision']),(19,31))
        self.assertEqual(r['alignment'],'UNKNOWN')
        self.assertFalse(r['timed_truth_accepted'])

    def test_actual_bytes_not_asserted_boolean(self):
        (self.capture/'track-0.json').write_text('{}')
        r=self.run_audit();self.assertEqual(r['status'],'FAIL')
        self.assertIn('Original source bytes differ from baseline',r['issues'])

    def test_source_file_population(self):
        (self.capture/'track-1.json').write_text('{}')
        self.assertEqual(self.run_audit()['status'],'FAIL')
        (self.capture/'track-1.json').unlink();(self.capture/'track-0.json').unlink()
        self.assertEqual(self.run_audit()['status'],'FAIL')

    def test_identity_and_revision_types(self):
        for key,value in [('songId',8),('songId','7'),('artistId',False),('title',None),('chordsRevisionId',True)]:
            self.save(self.metadata,self.supplement|{key:value});self.seal()
            self.assertEqual(self.run_audit()['status'],'FAIL',(key,value))

    def test_supplement_changed_or_unsealed(self):
        self.text.write_text('changed')
        self.assertEqual(self.run_audit()['status'],'FAIL')
        (self.root/'renamed.json').write_bytes(self.metadata.read_bytes())
        self.assertEqual(audit(self.capture,self.baseline,self.root/'renamed.json',self.text)['status'],'FAIL')

    def test_no_supplement_is_explicitly_unavailable(self):
        r=audit(self.capture,self.baseline)
        self.assertEqual(r['status'],'PASS_PROVENANCE_ONLY')
        self.assertEqual(r['supplement_status'],'UNAVAILABLE')
        self.assertEqual(r['alignment'],'UNKNOWN')
        self.assertEqual(audit(self.capture,self.baseline,self.metadata)['status'],'FAIL')
        missing=audit(self.capture,self.baseline,self.metadata,self.root/'missing.chordpro')
        self.assertEqual(missing['supplement_status'],'UNAVAILABLE')
        self.assertEqual(missing['status'],'FAIL')

    def test_availability_and_untimed_text_cannot_be_timed_truth(self):
        for k in ('availability_as_timed_truth','supplement_as_timed_truth','automatic_time_alignment'):
            self.assertEqual(self.run_audit(claims={k:True})['status'],'FAIL')
            self.assertEqual(self.run_audit(claims={k:'false'})['status'],'FAIL')
        self.assertEqual(self.run_audit(claims={'invented':False})['status'],'FAIL')

    def test_supplement_resource_identity_cannot_collapse(self):
        self.assertEqual(audit(self.capture,self.baseline,self.metadata,self.metadata)['status'],'FAIL')
        other=self.root/'other';other.mkdir()
        alias=other/self.metadata.name;alias.write_bytes(self.metadata.read_bytes())
        self.assertEqual(audit(self.capture,self.baseline,self.metadata,alias)['status'],'FAIL')
        link=self.root/'metadata-alias.json'
        try:
            link.symlink_to(self.metadata)
        except (OSError,NotImplementedError):
            pass  # Canonical alias branch is independently covered when symlinks exist.
        else:
            self.assertEqual(audit(self.capture,self.baseline,self.metadata,link)['status'],'FAIL')

    def test_invalid_baseline_missing_and_duplicate_metadata(self):
        self.save(self.baseline,{'original_hashes':{'../source':'0'*64}})
        self.assertEqual(self.run_audit()['status'],'FAIL')
        self.seal();self.metadata.write_text('{"songId":7,"songId":8}')
        self.assertEqual(self.run_audit()['status'],'FAIL')
        self.assertEqual(audit(self.capture,self.root/'absent.json')['status'],'FAIL')

if __name__=='__main__':unittest.main()
