import unittest
from technique_effects import normalize_effect


class EffectTests(unittest.TestCase):
    def effect(self,name,scope,xml):return normalize_effect(dict(name=name,scope=scope,xml=xml))
    def test_finger_and_arm_remain_separate(self):
        a=self.effect('Vibrato','note','<Vibrato>Wide</Vibrato>')
        b=self.effect('VibratoWTremBar','beat','<Property name="VibratoWTremBar"><Strength>Slight</Strength></Property>')
        self.assertEqual(a['family'],'finger_vibrato');self.assertEqual(b['family'],'arm_vibrato')
        self.assertIsNone(a['rate_hz']);self.assertIsNone(b['width_cents'])
    def test_tremolo_code_is_slashes_not_absolute_duration(self):
        a=self.effect('Tremolo','beat','<Tremolo>1/8</Tremolo>')
        self.assertEqual(a['marks'],3);self.assertIsNone(a['rate_hz'])
        self.assertEqual(self.effect('Tremolo','beat','<Tremolo>unknown</Tremolo>')['status'],'unsupported_notation_value')
    def test_unknown_and_trill_not_silently_vibrato(self):
        self.assertEqual(self.effect('OtherVibrato','note','<OtherVibrato/>')['status'],'unsupported_effect')
        self.assertEqual(self.effect('Trill','note','<Trill/>')['family'],'trill')


if __name__=='__main__':unittest.main()
