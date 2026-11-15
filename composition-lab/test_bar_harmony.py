from bar_harmony import analyze_bar_harmony
from fractions import Fraction as Q

def test_behavior_contract():

    def cell(a, b, pcs, low=None, unk=False):
        return dict(start_q=str(a), end_q=str(b), pcs=pcs, low_pc=low, unknown_pitch=unk, source_ids=[], role_evidence=[])

    def run(cs, length='4'):
        return analyze_bar_harmony([dict(bar=1, start_q='0', span_q=length)], cs, {})[0]
    assert run([cell(0, 4, [])])['status'] == 'no_pitched_evidence'
    assert run([cell(0, 4, [0])])['status'] == 'unknown'
    assert run([cell(0, 4, [], unk=True)])['status'] == 'unknown'
    assert run([cell(0, 4, [0, 4, 7], 0)])['candidates'][0]['label'] == 'C:major'
    assert run([cell(0, 1, [0], 0), cell(1, 2, [4], 4), cell(2, 4, [7], 7)])['candidates'][0]['label'] == 'C:major'
    assert run([cell(0, 4, [4, 11], 4)])['candidates'][0]['label'] == 'E:power'
    assert run([cell(0, Q('7/2'), [0, 4, 7], 0)], '7/2')['length_q'] == '7/2'
    assert run([cell(0, 4, [0, 4, 7], 0)])['no_pitched_evidence_fraction'] == 0
    assert run([cell(0, 2, [0, 4, 7], 0), cell(2, 4, [])])['no_pitched_evidence_fraction'] == 0.5
    d = run([cell(0, 2, [0, 4, 7], 0), cell(2, 4, [9, 0, 4], 9)])
    assert any((h['root_pc'] == 0 and h['core_pcs'] == [0, 4, 7] for h in d['candidates'])) and any((h['root_pc'] == 9 and h['core_pcs'] == [0, 4, 9] for h in d['candidates']))
    assert abs(sum((h['relative_weight'] for h in d['candidates'])) + d['unknown_weight'] - 1) < 1e-09

def test_sustain_and_extended():
    cell = lambda a, b, pcs, low: dict(start_q=str(a), end_q=str(b), pcs=pcs, low_pc=low, unknown_pitch=False, source_ids=[], role_evidence=[])
    bs = [dict(bar=1, start_q='0', span_q='3'), dict(bar=2, start_q='3', span_q='7/2')]
    r = analyze_bar_harmony(bs, [cell(0, '13/2', [0, 4, 7], 0)])
    assert [x['length_q'] for x in r] == ['3', '7/2']
    assert r[0]['end_q'] == r[1]['start_q'] == '3'
    assert all((x['candidates'][0]['label'] == 'C:major' for x in r))
    r = analyze_bar_harmony(bs, [cell(0, '13/2', [0, 4, 7, 11], 0)])
    assert any((h['core_pcs'] == [0, 4, 7, 11] and h['terms']['unsupported_extension_union'] == 0 for h in r[0]['candidates']))

def test_validation_and_no_mutation():
    import copy
    bs = [dict(bar=1, start_q='0', span_q='4')]
    cs = [dict(start_q='0', end_q='4', pcs=[0, 4, 7], low_pc=0, unknown_pitch=False, source_ids=['n'], role_evidence=[])]
    before = copy.deepcopy((bs, cs))
    analyze_bar_harmony(bs, cs)
    assert (bs, cs) == before
    for bad in ([dict(bar=1, start_q='0', span_q='0')], [*bs, dict(bar=2, start_q='3', span_q='4')]):
        try:
            analyze_bar_harmony(bad, cs)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid bar accepted')
    try:
        analyze_bar_harmony(bs, cs + cs)
    except ValueError:
        pass
    else:
        raise AssertionError('overlapping cells accepted')
if __name__ == '__main__':
    test_behavior_contract()
    test_sustain_and_extended()
    test_validation_and_no_mutation()
    print('Bar harmony behavioral, meter/sustain, validation and nonmutation checks passed')

import unittest

class BarHarmonyTests(unittest.TestCase):
    def test_behavior_contract(self):
        test_behavior_contract()

    def test_sustain_and_extended(self):
        test_sustain_and_extended()

    def test_validation_and_no_mutation(self):
        test_validation_and_no_mutation()


class EvidenceValidationTests(unittest.TestCase):
    def test_invalid_evidence(self):
        bs=[dict(bar=1,start_q='0',span_q='4')]
        c=dict(start_q='0',end_q='4',pcs=[0],low_pc=0,unknown_pitch=False,source_ids=[])
        for patch in ({'pcs':[12]}, {'pcs':[0,0]}, {'role_evidence':[{'pcs':[4]}]}):
            with self.assertRaises(ValueError):
                analyze_bar_harmony(bs,[dict(c,**patch)])
        with self.assertRaises(ValueError):
            analyze_bar_harmony(bs,[c],{'original_report':{'ranked':[{'tonic':'C','score':float('nan')}]}})
        with self.assertRaises(ValueError):
            analyze_bar_harmony(bs,[c],{'selected_collections':[{'pcs':[12]}]})
        row=analyze_bar_harmony(bs,[])[0]
        self.assertEqual(row['status'],'no_pitched_evidence')
        self.assertEqual(row['unknown_weight'],0)
