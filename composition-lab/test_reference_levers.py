import tempfile
import unittest
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET
from reference_levers import propose, curve, write_property_edits, BEND_PROPERTIES, apply_bends, properties


class LeverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'source.gp'
        with zipfile.ZipFile(self.source,'w') as z:
            z.writestr('Content/score.gpif','<GPIF><Notes><Note id="1"><Properties><Property name="Fret"><Fret>5</Fret></Property></Properties><Tie origin="true"/></Note></Notes></GPIF>')
            z.writestr('locked.bin',b'unchanged\x00')
    def tearDown(self):self.temp.cleanup()
    def test_zero_transaction_is_byte_identity(self):
        audit=write_property_edits(self.source,self.root/'out.gp',{'1':[]},{'1':BEND_PROPERTIES})
        self.assertTrue(audit['byte_identity'])
    def test_only_declared_fields_change(self):
        audit=write_property_edits(self.source,self.root/'out.gp',{'1':curve(2)},{'1':BEND_PROPERTIES})
        self.assertTrue(audit['locked_xml_verified'])
        with zipfile.ZipFile(self.root/'out.gp') as z:
            r=ET.fromstring(z.read('Content/score.gpif'))
            self.assertEqual(r.findtext('.//Fret'),'5')
            self.assertEqual(r.find('.//Tie').get('origin'),'true')
    def test_locked_edits_and_overwrite_rejected(self):
        with self.assertRaises(ValueError):write_property_edits(self.source,self.root/'out.gp',{'1':['<Property name="Fret"/>']},{'1':BEND_PROPERTIES})
        with self.assertRaises(FileExistsError):write_property_edits(self.source,self.source,{}, {})
    def test_full_freedom_rejects_reference_or_hidden_bend_context(self):
        ctx=dict(id='1',duration=2,string=3,fret=8,monophonic=True)
        with self.assertRaises(ValueError):propose(ctx,'contextual',17,reference=curve(2))
        with self.assertRaises(ValueError):propose(dict(ctx,bend=2),'contextual',17)
        self.assertEqual(propose(ctx,'contextual',17),propose(ctx,'contextual',17))
    def test_full_freedom_can_agree_with_reference(self):
        ctx=dict(id='1',duration=2,string=3,fret=8,monophonic=True)
        results=[propose(ctx,'frequency',seed) for seed in range(100)]
        self.assertIn(None,results);self.assertIn(2,results)
    def test_strong_reference_preference_keeps_reference(self):
        ctx=dict(id='1',duration=2,string=3,fret=8,monophonic=True)
        self.assertEqual(propose(ctx,'contextual',17,reference=curve(2),strength=1),'reference')

    def authored_gp(self):
        from gp_author import write_gp
        score={'tracks':[{'index':0,'name':'Authored test','program':25,'tunings':[[40,45,50,55,59,64]],
                         'measures':[{'number':1,'onset_q':'0','time_signature':'4/4',
                                      'voices':[[{'onset_q':'0','local_onset_q':'0','duration_q':'4',
                                                  'notes':[{'midi':69,'string':5,'fret':5,'tie':None,'technique_tags':[]}]}]]}]}]}
        path=self.root/'authored.gp';write_gp(score,path);return path

    def test_actual_gp_zero_and_reference_perturbation(self):
        source=self.authored_gp()
        locked=self.root/'locked.gp';apply_bends(source,locked,0,0)
        self.assertEqual(source.read_bytes(),locked.read_bytes())
        bent=self.root/'bent.gp'
        write_property_edits(source,bent,{'0':curve(2)},{'0':BEND_PROPERTIES})
        a=self.root/'a.gp';b=self.root/'b.gp'
        apply_bends(source,a,0,100);apply_bends(bent,b,0,100)
        def signature(path):
            with zipfile.ZipFile(path) as z:r=ET.fromstring(z.read('Content/score.gpif'))
            return [properties(n,BEND_PROPERTIES) for n in r.findall('./Notes/Note')]
        self.assertEqual(signature(a),signature(b))

    def test_rendered_bend_changes_measured_frequency(self):
        try:import numpy as np
        except ImportError:self.skipTest('Optional diagnostic renderer requires NumPy')
        import wave
        from bend_lever_experiment import render
        source=self.authored_gp();bent=self.root/'bent.gp'
        write_property_edits(source,bent,{'0':curve(2)},{'0':BEND_PROPERTIES})
        peaks=[]
        for i,path in enumerate((source,bent)):
            wav=self.root/f'{i}.wav';render(path,wav,0,1,1,sample_rate=8000)
            with wave.open(str(wav)) as w:data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
            tail=data[12000:14400].astype(float)
            spectrum=np.abs(np.fft.rfft(tail*np.hanning(len(tail))))
            peaks.append(float(np.fft.rfftfreq(len(tail),1/8000)[np.argmax(spectrum)]))
        self.assertAlmostEqual(peaks[0],440,delta=4)
        self.assertAlmostEqual(peaks[1],440*2**(2/12),delta=4)


if __name__=='__main__':unittest.main()
