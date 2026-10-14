import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as ET
from sequence_model import SequenceModel
from sequence_generator_v6 import generate, export_score, playable_positions, compose

ROOT=Path('/mnt/data')
TEMPLATE=ROOT/'Cloud Cascade (Tuned Down).gp'
SOURCE=ROOT/'Immolation of Night (Tuned Down).gp'

class GeneratorV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=SequenceModel(2)
        cls.model.add_sequence([(2,None,(0,)),(2,7,(0,)),(2,-7,(0,))]*24,48)

    def test_variable_meter_bar_count(self):
        for meter,count in [('2/4',5),('3/4',7),('4/4',3),('5/4',2)]:
            bars,_=generate(self.model,[40,45,50,55,59,64],count,meter,17)
            self.assertEqual(len(bars),count)
            self.assertTrue(all(sum(ev['units'] for ev in m)==4*int(meter.split('/')[0]) for m in bars))

    def test_no_prescribed_arrangement(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'x.gp'
            events,_=generate(self.model,[26,31,38,43,48,53,57,62],5,'3/4',21)
            info=export_score(TEMPLATE,out,events,'3/4',1)
            self.assertEqual(info['measures'],5)
            with zipfile.ZipFile(out) as z:root=ET.fromstring(z.read('Content/score.gpif'))
            self.assertEqual([x.findtext('Time') for x in root.findall('./MasterBars/MasterBar')],['3/4']*5)
            self.assertFalse(root.findall('./MasterBars/MasterBar/Section'))
            self.assertEqual(len(root.findall('./Tracks/Track')),1)

    def test_six_string_template(self):
        with tempfile.TemporaryDirectory() as folder:
            six=Path(folder)/'six.gp'
            with zipfile.ZipFile(TEMPLATE) as src,zipfile.ZipFile(six,'w') as dst:
                for name in src.namelist():
                    blob=src.read(name)
                    if name=='Content/score.gpif':
                        root=ET.fromstring(blob)
                        track=root.findall('./Tracks/Track')[1]
                        track.find("./Staves/Staff/Properties/Property[@name='Tuning']/Pitches").text='40 45 50 55 59 64'
                        blob=ET.tostring(root,encoding='utf-8',xml_declaration=True)
                    dst.writestr(name,blob)
            out=Path(folder)/'out.gp'
            bars,_=generate(self.model,[40,45,50,55,59,64],3,'4/4',4)
            info=export_score(six,out,bars,'4/4',1)
            self.assertEqual(info['strings'],6)
            with zipfile.ZipFile(out) as z:root=ET.fromstring(z.read('Content/score.gpif'))
            self.assertEqual(len(root.findall('./MasterBars/MasterBar')),3)

    def test_same_seed_same_file(self):
        bars,_=generate(self.model,[26,31,38,43,48,53,57,62],5,'3/4',12)
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/'a.gp';b=Path(folder)/'b.gp'
            export_score(TEMPLATE,a,bars,'3/4',1)
            export_score(TEMPLATE,b,bars,'3/4',1)
            self.assertEqual(hashlib.sha256(a.read_bytes()).digest(),hashlib.sha256(b.read_bytes()).digest())

    def test_different_source_counts_change_model(self):
        other=SequenceModel(2)
        other.add_sequence([(4,None,(0,4,7)),(4,None,())]*20,50)
        self.assertNotEqual(self.model.distribution([])[0],other.distribution([])[0])

    def test_invalid_configuration(self):
        with self.assertRaises(ValueError):generate(self.model,[40,45,50,55,59,64],4,'7/8')
        with self.assertRaises(ValueError):generate(self.model,[40,45,50,55,59,64],0,'4/4')
        with self.assertRaises(ValueError):export_score(TEMPLATE,Path('/tmp/bad.gp'),[[{'units':2,'positions':[]}]],'4/4',1)

    def test_preserves_all_chord_intervals(self):
        result=playable_positions(48,(0,4,7),[40,45,50,55,59,64],14)
        self.assertEqual(tuple(p-result[0][0] for p,_,_ in result),(0,4,7))
        self.assertIsNone(playable_positions(48,tuple(range(12)),[40,45,50,55,59,64],14))

if __name__=='__main__':unittest.main()