import copy
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from exact_score import extract_score
from musicxml_bridge import export_musicxml, audit_musicxml
from relational_graph import build_graph


def fixture():
    def beat(onset, duration, pitches, **extra):
        return dict(onset_q=str(onset), local_onset_q=str(onset), duration_q=str(duration),
                    notes=[dict(midi=p, string=i, tie=None) for i,p in enumerate(pitches)], **extra)
    a = beat(0, '1/3', [60,64]); b = beat('1/3', '8/3', [62])
    b['notes'][0]['tie'] = dict(origin='true')
    c = beat(3, '5/2', [62]); c['local_onset_q']='0'
    c['notes'][0]['tie'] = dict(destination='true')
    d = beat(0, 3, [48])
    return dict(tracks=[dict(index=0, name='Guitar', tunings=[[40,45,50,55,59,64]], measures=[
        dict(number=1, onset_q='0', time_signature='3/4', section='A', voices=[[a,b],[],[d]]),
        dict(number=2, onset_q='3', time_signature='5/8', section=None, voices=[[c]])])])


class RelationalTests(unittest.TestCase):
    def test_exact_overlap_tie_and_voice(self):
        score=fixture(); original=copy.deepcopy(score); graph=build_graph(score)
        edges={(e['source'],e['relation'],e['target']) for e in graph['edges']}
        self.assertIn(('t0:m0:v0:b1:n0','SUSTAINS_INTO','t0:m1:v0:b0:n0'),edges)
        self.assertIn(('t0:m0:v0:b0:n0','NEXT_IN_VOICE','t0:m0:v0:b1:n0'),edges)
        self.assertTrue(any(r=='SIMULTANEOUS' for _,r,_ in edges))
        self.assertTrue(any(r=='OVERLAPS' and a=='t0:m0:v2:b0:n0' for a,r,b in edges))
        self.assertEqual(score,original)
        self.assertFalse(graph['warnings'])

    def test_ambiguity_and_no_implicit_phrase_truth(self):
        h=dict(kind='harmony', root=[0,9], quality=['major','minor'], confidence=.4,
               provenance='synthetic_test', members=['t0:m0:v0:b0:n0'])
        graph=build_graph(fixture(),[h])
        self.assertEqual(graph['nodes']['hypothesis:0']['evidence'],h)
        with self.assertRaises(ValueError): build_graph(fixture(),[dict(members=['absent'])])

    def test_musicxml_exact_and_detects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'view.musicxml'; score=fixture()
            report=export_musicxml(score,path)
            self.assertTrue(report['exact_note_timing_pitch_voice'])
            root=ET.parse(path); root.find('.//note/duration').text='2'; root.write(path)
            self.assertFalse(audit_musicxml(score,path)['exact_note_timing_pitch_voice'])

    def test_overfull_rejected_not_stretched(self):
        score=fixture(); score['tracks'][0]['measures'][0]['voices'][0][1]['duration_q']='4'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'Overfull'):
                export_musicxml(score,Path(tmp)/'bad.xml')

    def test_sparse_voice_indices_and_raw_metadata(self):
        root=ET.fromstring('''<GPIF><Tracks><Track id="0"><Name>Test</Name></Track></Tracks>
        <MasterBars><MasterBar><Time>4/4</Time><Bars>0</Bars></MasterBar></MasterBars>
        <Bars><Bar id="0"><Voices>-1 9</Voices></Bar></Bars><Voices><Voice id="9"><Beats>5</Beats></Voice></Voices>
        <Beats><Beat id="5"><Rhythm ref="0"/><Notes>7</Notes><Dynamic>F</Dynamic></Beat></Beats>
        <Notes><Note id="7"><Tie origin="true"/><Properties><Property name="Midi"><Number>60</Number></Property></Properties></Note></Notes>
        <Rhythms><Rhythm id="0"><NoteValue>Whole</NoteValue></Rhythm></Rhythms></GPIF>''')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sparse.gp'
            with zipfile.ZipFile(path,'w') as z: z.writestr('Content/score.gpif',ET.tostring(root))
            score=extract_score(path)
        voices=score['tracks'][0]['measures'][0]['voices']
        self.assertEqual(voices[0],[])
        self.assertEqual(voices[1][0]['voice_index'],1)
        self.assertIn('origin="true"',voices[1][0]['notes'][0]['note_xml'])


if __name__=='__main__': unittest.main()
