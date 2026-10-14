import unittest, zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
from extract import extract_score
from automatic_harmony_control import _write_note, _position
from gp_occurrence_writer import apply_occurrence_edits
from gp_similarity_export import export

SOURCE=Path('/mnt/data/Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp')

class OccurrenceWriterTests(unittest.TestCase):
    def test_only_one_shared_note_occurrence_changes(self):
        score=extract_score(SOURCE)
        uses=defaultdict(list)
        for mi,m in enumerate(score['tracks'][0]['measures']):
            for vi,v in enumerate(m['voices']):
                for ei,e in enumerate(v):
                    for ni,n in enumerate(e['notes']):
                        if n['midi'] is not None: uses[n['note_id']].append((mi,vi,ei,ni,n))
        shared=next((items for items in uses.values() if len(items)>1 and any(
            _position(items[0][4]['midi']+delta,score['tracks'][0]['tunings'][0],items[0][4]['string'])
            is not None for delta in (1,-1,2,-2))),None)
        self.assertIsNotNone(shared)
        mi,vi,ei,ni,n=shared[0]
        pitch=next(n['midi']+delta for delta in (1,-1,2,-2) if _position(n['midi']+delta,score['tracks'][0]['tunings'][0],n['string']) is not None)
        pos=_position(pitch,score['tracks'][0]['tunings'][0],n['string'])
        with zipfile.ZipFile(SOURCE) as z:
            root=ET.fromstring(z.read('Content/score.gpif'))
        stats=apply_occurrence_edits(root,score,0,{(mi,vi,ei,ni):(pitch,*pos)},_write_note)
        self.assertEqual(stats['changed_note_occurrences'],1)
        self.assertEqual(score['tracks'][0]['measures'][mi]['voices'][vi][ei]['notes'][ni]['midi'],n['midi'])
        # Verify all references after round-trip, including the other shared uses.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'isolated.gp'
            with zipfile.ZipFile(SOURCE) as zi,zipfile.ZipFile(path,'w') as zo:
                for info in zi.infolist():
                    zo.writestr(info,ET.tostring(root,encoding='utf-8',xml_declaration=True) if info.filename=='Content/score.gpif' else zi.read(info.filename))
            newer=extract_score(path)
        actual=newer['tracks'][0]['measures'][mi]['voices'][vi][ei]['notes'][ni]['midi']
        self.assertEqual(actual,pitch)
        for m2,v2,e2,n2,old in shared[1:]:
            self.assertEqual(newer['tracks'][0]['measures'][m2]['voices'][v2][e2]['notes'][n2]['midi'],old['midi'])

    def test_learned_melody_changes_real_song(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'melody.gp'
            report=export(SOURCE,path,melody=100,learned=True)
            self.assertGreater(report['changed_note_occurrences'],10)
            old=extract_score(SOURCE);new=extract_score(path)
            changes=0
            for ti,(ot,nt) in enumerate(zip(old['tracks'],new['tracks'])):
                for om,nm in zip(ot['measures'],nt['measures']):
                    for ov,nv in zip(om['voices'],nm['voices']):
                        for a,b in zip(ov,nv):
                            self.assertEqual((a['onset_q'],a['duration_q']),(b['onset_q'],b['duration_q']))
                            if ti==0:
                                changes+=sum(x['midi']!=y['midi'] for x,y in zip(a['notes'],b['notes']))
                            else:
                                self.assertEqual([x['midi'] for x in a['notes']],[x['midi'] for x in b['notes']])
            self.assertEqual(changes,report['changed_note_occurrences'])

if __name__=='__main__':unittest.main()