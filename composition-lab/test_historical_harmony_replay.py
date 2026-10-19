import hashlib,types,unittest
from unittest.mock import patch
from historical_harmony_replay import accepted_attempt,recover,observe_positions

class HistoricalReplayTests(unittest.TestCase):
    def test_retry_requires_complete_ordered_failure_history(self):
        self.assertEqual(accepted_attempt(dict(rejected_proposals=[dict(piece=0,attempt=1),dict(piece=0,attempt=0)]),0),2)
        self.assertEqual(accepted_attempt(dict(rejected_proposals=[]),0),0)
        for failures in ([1],[0,0],[True]):
            with self.assertRaises(ValueError):accepted_attempt(dict(rejected_proposals=[dict(piece=0,attempt=a) for a in failures]),0)
    def test_recover_exact_blob_and_refuse_substitution(self):
        blob=b'example_value=7\n';digest=hashlib.sha256(blob).hexdigest()
        with patch('historical_harmony_replay.subprocess.check_output',side_effect=['abc\n',blob]):
            module,provenance=recover(digest)
        self.assertEqual(module.example_value,7);self.assertEqual(provenance['sha256'],digest)
        with patch('historical_harmony_replay.subprocess.check_output',side_effect=['abc\n',blob]):
            with self.assertRaisesRegex(ValueError,'not found'):recover('wrong')
    def test_observation_preserves_results_and_records_rejected_attempts(self):
        module=types.ModuleType('fixture')
        exec('''
def position_chord(pitches,tuning,**kwargs):
 if min(pitches)<min(tuning):raise ValueError('below open')
 return [(0,p-min(tuning)) for p in pitches]
def generate():
 role='harmony';bi=0;cursor='0';root=30;step=-2;target=28
 pattern={'song_id':1,'part_id':0,'bar':1};source_event={'intervals':[0]}
 for shift in (0,1):
  try:return position_chord([target+12*shift],[32])
  except ValueError:pass
''',module.__dict__)
        expected=module.generate();original,events,attempts=observe_positions(module)
        self.assertEqual(module.generate(),expected)
        self.assertEqual([a['success'] for a in attempts],[False,True]);self.assertEqual(len(events),1)
        self.assertEqual(events[0]['source_step'],-2);self.assertEqual(events[0]['octave_shift'],1);self.assertEqual(events[0]['actual_root'],40)

if __name__=='__main__':unittest.main()
