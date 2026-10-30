"""Exercise the runner with authored positive and no-choice fixtures."""
from pathlib import Path
import json
import tempfile
import unittest
from test_melodic_contour_choices import documents
from run_melodic_contour_qa import run


class MelodyRunnerTests(unittest.TestCase):
    def test_positive_and_no_choice_are_distinct(self):
        with tempfile.TemporaryDirectory()as folder:
            base=Path(folder)
            for name in('positive','no-choice'):
                capture=base/name;capture.mkdir();docs=documents()
                if name=='no-choice':
                    for m in docs['track-0.json']['measures']:
                        m['voices'][0]['beats'][1]['notes'][0]['fret']=4
                for filename,data in docs.items():(capture/filename).write_text(json.dumps(data),encoding='utf-8')
                result=run(capture,base/(name+'-qa'))
                wanted='PASS_SOURCE_MELODIC_CHANGE'if name=='positive'else'PASS_SOURCE_MELODIC_NO_CHOICE'
                self.assertEqual(result['status'],wanted,result)
                self.assertEqual(result['counts']['neighborhoods'],32)
                self.assertEqual(result['rates']['0']['changed'],0)
                self.assertEqual(result['rates']['100']['released'],32*32)
                self.assertEqual(result['full_melody_lever'],'OPEN')


if __name__=='__main__':unittest.main()
