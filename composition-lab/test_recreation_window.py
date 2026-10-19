import copy
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path

from recreation_window import redact,replay,overlay,api_to_gpif_string
from engine_contract import _read,_value,sha
from test_learned_performance import fixture
from learned_performance import apply
from gp_author import write_gp


class RecreationWindowTests(unittest.TestCase):
    def test_replay_rejects_redacted_archive_tampering(self):
        score,_,_=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'source.gp')
            redact(p/'source.gp',p/'hidden.gp','bend')
            with zipfile.ZipFile(p/'hidden.gp','a') as archive:archive.comment=b'changed'
            with self.assertRaises(ValueError):replay(p/'source.gp',p/'hidden.gp',p/'bad.gp','bend')
            self.assertFalse((p/'bad.gp').exists())

    def test_shared_definition_cannot_change_an_occurrence_outside_scope(self):
        score,_,_=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'source.gp')
            with zipfile.ZipFile(p/'source.gp') as source,zipfile.ZipFile(p/'aliased.gp','w') as output:
                xml=ET.fromstring(source.read('Content/score.gpif'))
                refs=xml.findall('./Beats/Beat/Notes')
                refs[-1].text=refs[0].text
                for member in source.infolist():output.writestr(member,ET.tostring(xml) if member.filename=='Content/score.gpif' else source.read(member.filename))
            with self.assertRaises(ValueError):redact(p/'aliased.gp',p/'bad.gp','bend',window=(0,2,2))
            self.assertFalse((p/'bad.gp').exists())

    def test_string_coordinate_conversion_requires_actual_tuning_agreement(self):
        for size in (6,7,8):
            tuning=[64-5*i for i in range(size)]
            for i in range(size):
                mapped=api_to_gpif_string(i,tuning,list(reversed(tuning)))
                self.assertEqual(list(reversed(tuning))[mapped],tuning[i])
        with self.assertRaises(ValueError):api_to_gpif_string(0,[64,59],[64,59])
        with self.assertRaises(ValueError):api_to_gpif_string(True,[64,59],[59,64])

    def test_replay_and_overlay_keep_other_regions_and_features(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'source.gp')
            audit=apply(p/'source.gp',p/'expressive.gp',model,shapes,'Artist',{'bend':100})
            redact(p/'expressive.gp',p/'hidden.gp','bend')
            replay(p/'expressive.gp',p/'hidden.gp',p/'replayed.gp','bend')
            _,_,_,source=_read(p/'expressive.gp');_,_,_,restored=_read(p/'replayed.gp')
            self.assertTrue(all(_value(source[o]['note'],'property',{'Bended'})==_value(restored[o]['note'],'property',{'Bended'}) for o in source))
            proposal=apply(p/'hidden.gp',p/'proposal.gp',model,shapes,'Artist',{'bend':100})
            result=overlay(p/'expressive.gp',p/'hidden.gp',p/'proposal.gp',p/'out.gp','bend',(0,2,2),proposal)
            self.assertTrue(result['decisions'])
            self.assertTrue(all(d['occurrence'].startswith('0:2:') for d in result['decisions']))
            _,_,_,actual=_read(p/'out.gp')
            self.assertTrue(all(source[o]['note']['note_xml']==actual[o]['note']['note_xml'] for o in source if o.startswith('0:1:')))
            self.assertEqual(result['proposal_input_sha256'],sha(p/'hidden.gp'))

    def test_unredacted_target_and_false_audit_are_rejected(self):
        score,model,shapes=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'source.gp')
            a=apply(p/'source.gp',p/'expressive.gp',model,shapes,'Artist',{'bend':100})
            with self.assertRaises(ValueError):overlay(p/'source.gp',p/'expressive.gp',p/'expressive.gp',p/'bad.gp','bend',(0,1,2),a)
            redact(p/'expressive.gp',p/'hidden.gp','bend')
            broken=copy.deepcopy(a);broken['sha256']='0'*64
            with self.assertRaises(ValueError):overlay(p/'source.gp',p/'hidden.gp',p/'expressive.gp',p/'bad.gp','bend',(0,1,2),broken)
            self.assertFalse((p/'bad.gp').exists())


if __name__=='__main__':unittest.main()
