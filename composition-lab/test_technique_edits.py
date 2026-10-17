import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from technique_edits import transact,generate_hopo,enable_property


class TechniqueEditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        from gp_author import write_gp
        notes=[]
        for i,f in enumerate((0,2,4,0)):
            notes.append(dict(onset_q=str(i),local_onset_q=str(i),duration_q='1',notes=[dict(midi=64+f,string=5,fret=f,tie=None,technique_tags=[])]))
        score=dict(tracks=[dict(index=0,name='Authored',program=25,tunings=[[40,45,50,55,59,64]],measures=[dict(number=1,onset_q='0',time_signature='4/4',voices=[notes])])])
        self.source=self.root/'source.gp';write_gp(score,self.source)
    def tearDown(self):self.tmp.cleanup()
    def test_zero_literal_and_full_freedom_perturbation(self):
        locked=self.root/'locked.gp';generate_hopo(self.source,locked,0,'hammer_on_from_open',0)
        self.assertEqual(locked.read_bytes(),self.source.read_bytes())
        marked=self.root/'marked.gp'
        transact(self.source,marked,{('note','0','property'):[enable_property('HopoOrigin')],('note','1','property'):[enable_property('HopoDestination')]},
                 {('note','0','property'):{'HopoOrigin'},('note','1','property'):{'HopoDestination'}})
        a=self.root/'a.gp';b=self.root/'b.gp'
        generate_hopo(self.source,a,0,'hammer_on_from_open');generate_hopo(marked,b,0,'hammer_on_from_open')
        from exact_score import extract_score
        from technique_analysis import analyze
        self.assertEqual(analyze(extract_score(a))['tracks'][0]['explicit_hopo'],analyze(extract_score(b))['tracks'][0]['explicit_hopo'])
    def test_directed_pair_survives_independent_reextract(self):
        from technique_analysis import analyze
        from exact_score import extract_score
        out=self.root/'open.gp';audit=generate_hopo(self.source,out,0,'pull_off_to_open',method='long_arrivals')
        pairs=analyze(extract_score(out))['tracks'][0]['explicit_hopo']
        self.assertEqual(audit['selected'],1)
        self.assertEqual(pairs[0]['context'],'to_open');self.assertEqual(pairs[0]['direction'],'pull_off')
        self.assertTrue(audit['locked_xml_verified'])
    def test_note_tag_edit_retains_every_other_field(self):
        out=self.root/'vibrato.gp'
        audit=transact(self.source,out,{('note','1','tag'):['<Vibrato>Wide</Vibrato>']},{('note','1','tag'):{'Vibrato'}})
        self.assertTrue(audit['locked_xml_verified'])
        with zipfile.ZipFile(out) as z:r=ET.fromstring(z.read('Content/score.gpif'))
        self.assertEqual(r.findtext('./Notes/Note[@id="1"]/Vibrato'),'Wide')
    def test_structural_and_undeclared_changes_rejected(self):
        with self.assertRaises(ValueError):transact(self.source,self.root/'out.gp',{}, {('note','1','tag'):{'Tie'}})
        with self.assertRaises(ValueError):transact(self.source,self.root/'out.gp',{('note','1','tag'):['<Tie/>']}, {('note','1','tag'):{'Vibrato'}})
    def test_full_freedom_ignores_malformed_reference_hopo(self):
        bad=self.root/'bad.gp'
        transact(self.source,bad,{('note','0','property'):[enable_property('HopoOrigin')]},{('note','0','property'):{'HopoOrigin'}})
        a=self.root/'a.gp';b=self.root/'b.gp'
        x=generate_hopo(self.source,a,0,'hammer_on_from_open')
        y=generate_hopo(bad,b,0,'hammer_on_from_open')
        self.assertEqual(x['decisions'],y['decisions'])
    def test_vibrato_excludes_open_strings_and_changes_only_tag(self):
        from technique_edits import generate_vibrato
        p=self.root/'vib.gp';audit=generate_vibrato(self.source,p,0)
        self.assertEqual(audit['selected'],2);self.assertTrue(audit['locked_xml_verified']);self.assertIsNone(audit['rate_hz'])
    def test_vibrato_full_freedom_ignores_existing_width_and_invalid_open_marker(self):
        from technique_edits import generate_vibrato
        marked=self.root/'marked.gp'
        transact(self.source,marked,{('note','0','tag'):['<Vibrato>Wide</Vibrato>'],('note','1','tag'):['<Vibrato>Wide</Vibrato>']},
                 {('note','0','tag'):{'Vibrato'},('note','1','tag'):{'Vibrato'}})
        a=self.root/'a.gp';b=self.root/'b.gp';generate_vibrato(self.source,a,0);generate_vibrato(marked,b,0)
        def tags(p):
            with zipfile.ZipFile(p) as z:r=ET.fromstring(z.read('Content/score.gpif'))
            return [(n.get('id'),n.findtext('Vibrato')) for n in r.findall('./Notes/Note')]
        self.assertEqual(tags(a),tags(b))


if __name__=='__main__':unittest.main()
