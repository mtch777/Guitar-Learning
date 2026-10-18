import sys
import unittest
from pathlib import Path
from pedal_evidence import analyze_evidence
from test_pedal_regions import rows
sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
from build_pedal_evidence_review import support_regions


class SupportBoundsTests(unittest.TestCase):
    def test_terminal_sustain_extends_display_without_inventing_attack(self):
        data=rows([[40],[55],[40],[59],[40],[40]])
        for i,n in enumerate(data):n['bar']=i+1
        data[-1]['tie_destination']=True
        result=analyze_evidence(data)
        region=support_regions(result,data,[dict(origin='4:0',members=['4:0','5:0'],end_q='6')])[0]
        self.assertEqual(region['end_bar'],6)
        self.assertEqual(region['end_q'],'6')
        self.assertNotIn('5:0',region['return_members'])

    def test_short_excerpt_does_not_erase_preceding_support(self):
        data=rows([[40],[55],[40],[59],[40],[40],[40]])
        for i,n in enumerate(data):n['bar']=i//2+1
        full=analyze_evidence(data)
        self.assertTrue(full['accepted'])
        self.assertFalse(analyze_evidence(data[4:])['accepted'])
        regions=support_regions(full,data)
        self.assertEqual(len(regions),1)
        self.assertEqual(regions[0]['start_bar'],1)
        self.assertEqual(regions[0]['end_bar'],4)
        self.assertEqual(regions[0]['return_members'],{'4:0','5:0','6:0'})
        self.assertEqual(regions[0]['end_q'],'7')

    def test_one_exchange_cannot_supply_a_complete_support_region(self):
        data=rows([[40],[55],[40]])
        for n in data:n['bar']=1
        fake=dict(roles={n['occurrence']:('call' if n['midi']==40 else 'response') for n in data},
            cycles=[dict(call_start_q='0',response_start_q='1',return_q='2',call_members=['0:0'],response_members=['1:0'])])
        with self.assertRaises(ValueError):support_regions(fake,data)


if __name__=='__main__':unittest.main()
