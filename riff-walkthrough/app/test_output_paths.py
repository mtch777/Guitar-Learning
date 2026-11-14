import os,pathlib,tempfile,unittest
from unittest.mock import patch
from runtime_options import output_path,temporary_directory
class OutputPathTests(unittest.TestCase):
 @unittest.skipUnless(os.name=='nt','Windows drive policy')
 def test_reject_c_without_creating(self):
  target=pathlib.Path('C:/never-created-riff-output-test')
  before=target.exists()
  with self.assertRaises(ValueError):output_path(target)
  self.assertEqual(target.exists(),before)
 @unittest.skipUnless(os.name=='nt','Windows drive policy')
 def test_bad_temp_override_fails_closed(self):
  with patch.dict(os.environ,{'RIFF_TEMP_DIR':'C:/never-created-riff-output-test'}):
   with self.assertRaises(ValueError):temporary_directory('guard-test-')
 def test_explicit_temp_ignores_os_default(self):
  wanted=pathlib.Path(__file__).resolve().parent.parent/'temp'
  with patch.dict(os.environ,{'RIFF_TEMP_DIR':str(wanted)}),patch.object(tempfile,'tempdir','C:/invalid-os-temp'):
   with temporary_directory('guard-test-') as actual:
    self.assertEqual(pathlib.Path(actual).parent,wanted.resolve())
   self.assertFalse(pathlib.Path(actual).exists())
if __name__=='__main__':unittest.main()
