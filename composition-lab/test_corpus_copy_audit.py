import unittest
from corpus_copy_audit import fingerprint,source_streams

class CopyAuditTests(unittest.TestCase):
    def test_numeric_pitch_normalization_and_transposition(self):
        a=[dict(q='0',notes=[(40,'1')]),dict(q='1',notes=[(43,'2')])]
        b=[dict(q='10',notes=[(52.0,'1')]),dict(q='11',notes=[(55.0,'2')])]
        self.assertEqual(fingerprint(a),fingerprint(b))
        b[1]['notes']=[(55.0,'1')]
        self.assertNotEqual(fingerprint(a),fingerprint(b))

    def test_tied_source_equals_one_long_attack(self):
        rows=[dict(voice=0,onset_q='0',duration_q='1',occurrence='a',tie_destination=False,midi=40),
              dict(voice=0,onset_q='1',duration_q='1',occurrence='b',tie_destination=True,midi=40)]
        report=dict(songs=[dict(song_id=1,provisional_partition='development',tracks=[dict(guitar_or_bass=True,
            temporal_relationships_eligible=True,part_id=0,rows=rows,sustain_relationships=dict(chains=[dict(origin='a',end_q='2')]))])])
        streams,_=source_streams(report)
        self.assertEqual(fingerprint(streams[0]['events']),fingerprint([dict(q='0',notes=[(40,'2')])]))

if __name__=='__main__':unittest.main()
