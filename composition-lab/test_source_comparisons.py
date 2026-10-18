import importlib.util
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as E
import zipfile
from technique_edits import transact

spec=importlib.util.spec_from_file_location('source_comparisons',Path(__file__).parent/'songsterr_automation/songsterr_api/build_source_comparisons.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


class SourceComparisonTests(unittest.TestCase):
    def test_xproperty_edit_locks_all_other_extensions_and_archive_members(self):
        xml=b'<GPIF><Notes/><Beats><Beat id="1"><Rhythm ref="r"/><XProperties><XProperty id="687935489"><Int>30</Int></XProperty><XProperty id="other"><Int>99</Int></XProperty></XProperties></Beat></Beats></GPIF>'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.gp'
            with zipfile.ZipFile(source,'w') as z:z.writestr('Content/score.gpif',xml);z.writestr('locked.bin',b'locked')
            key=('beat','1','xproperty');dest=root/'edit.gp'
            audit=transact(source,dest,{key:['<XProperty id="687935489"><Int>240</Int></XProperty>']},{key:{'687935489'}})
            self.assertTrue(audit['locked_xml_verified']);self.assertTrue(audit['archive_members_verified'])
            with zipfile.ZipFile(dest) as z:
                score=E.fromstring(z.read('Content/score.gpif'));self.assertEqual(z.read('locked.bin'),b'locked')
                self.assertEqual(score.findtext("./Beats/Beat/XProperties/XProperty[@id='other']/Int"),'99')
            zero=root/'zero.gp';self.assertTrue(transact(source,zero,{}, {})['byte_identity'])
            with self.assertRaises(ValueError):transact(source,root/'bad.gp',{key:['<XProperty id="other"><Int>1</Int></XProperty>']},{key:{'687935489'}})

    def test_bend_variants_change_offsets_and_lock_pitch_values(self):
        xml='<Note><Properties><Property name="BendOriginOffset"><Float>0</Float></Property><Property name="BendDestinationOffset"><Float>100</Float></Property><Property name="BendOriginValue"><Float>0</Float></Property><Property name="BendDestinationValue"><Float>100</Float></Property></Properties></Note>'
        early=c.replacements(xml,'bend_arrival','earlier_arrival');late=c.replacements(xml,'bend_arrival','later_arrival')
        self.assertEqual(early[1],{'BendOriginOffset','BendDestinationOffset'})
        self.assertNotEqual(early[2],late[2])
        self.assertTrue(all('Value' not in x for x in early[2]+late[2]))

    def test_whammy_offsets_preserve_all_value_attributes(self):
        xml='<Beat><Whammy originOffset="0" originValue="0" middleOffset1="50" middleOffset2="50" middleValue="-50" destinationOffset="100" destinationValue="-100"/></Beat>'
        for method in ('earlier_arrival','later_arrival'):
            domain,names,changes=c.replacements(xml,'whammy_arrival',method)
            node=E.fromstring(changes[0]);original=E.fromstring(xml).find('Whammy')
            self.assertEqual(domain,'tag');self.assertEqual(names,{'Whammy'})
            self.assertEqual({k:v for k,v in node.attrib.items() if k.endswith('Value')},{k:v for k,v in original.attrib.items() if k.endswith('Value')})


if __name__=='__main__':unittest.main()
