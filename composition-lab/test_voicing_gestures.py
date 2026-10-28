from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize,reconstruct
from voicing_register import apply_family_choices,apply_family_choice
from voicing_context_relations import check_paths,check_many
import voicing_gestures as v


def documents():
    bars=[]
    for bar in range(7):
        beats=[]
        for beat in range(4):
            notes=[dict(string=2,fret=2)]
            if bar in (1,3,5) and beat in (1,2):
                notes=[dict(string=3,fret=0),dict(string=2,fret=14 if bar in (3,5) else 2),dict(string=1,fret=3)]
            beats.append(dict(duration=[1,4],notes=notes))
        bars.append(dict(signature=[4,4],voices=[dict(beats=beats)]))
    return {'metadata.json':dict(songId=39,revisionId=1,title='Controlled joint source sequence',artist='Fixture',tracks=[dict(instrumentId=25)]),
        'track-0.json':dict(songId=39,revisionId=1,partId=0,instrumentId=25,frets=24,tuning=[64,59,55,50,45,40],measures=bars)}


class GestureTests(unittest.TestCase):
    def fixture(self):
        lower=extract_documents(documents());cat=v.catalog(lower)
        selected=next(r for r in cat['units'] if ':2:' in r['target_refs'][0])
        ev=v.options(cat,selected['id'])
        choice=next(o for o in ev['options'] if o['realizations']!=ev['original'])
        block,rows,targets=v.assignments(cat,selected['id'])
        return lower,cat,selected,choice,targets

    def test_joint_source_support_exists_but_either_single_change_refuses(self):
        lower,cat,selected,choice,targets=self.fixture()
        for target,value in zip(targets,choice['realizations']):
            self.assertEqual(check_paths(cat['base']['lane_relationships'],target,value,allow_string_changes=True)['status'],'REFUSED')
        self.assertEqual(check_many(cat['base']['lane_relationships'],list(zip(targets,choice['realizations'])),allow_string_changes=True)['status'],'PASS_OBSERVED_INCIDENT_MOTION')

    def test_atomic_reconstruction_order_independent_and_all_locks(self):
        lower,cat,selected,choice,targets=self.fixture();upper=strip_lower(analyze(lower,families=True))
        pairs=list(zip(targets,choice['realizations']))
        a=apply_family_choices(upper,pairs);b=apply_family_choices(upper,list(reversed(pairs)))
        self.assertEqual(a,b);changed=realize(a);self.assertNotEqual(changed,lower)
        v.validate_actual(lower,changed,targets,choice['realizations'],cat)
        from check_voicing_gesture import check
        rows={r['id']:r for r in cat['base']['units']}
        self.assertEqual(check(lower,changed,[t['member_refs'] for t in targets],
            [rows[r]['member_refs'] for r in choice['donor_sequences'][0]])['status'],'PASS_INDEPENDENT_VOICING_GESTURE')
        with self.assertRaises(ValueError):apply_family_choices(upper,pairs+pairs)

    def test_discovery_no_skip_no_overlap_replacement_and_resource_limit(self):
        lower,cat,selected,choice,targets=self.fixture()
        self.assertTrue(all(len(r['target_refs'])==2 for r in cat['units']))
        rows=deepcopy(cat['base']['units']);a=next(r for r in rows if r['id']==targets[0]['id']);a['refusal_reasons']=['TEST_UNKNOWN']
        matches=v.discover(rows)
        self.assertFalse(any(a['id'] in r['target_refs'] for r in matches['links']))
        self.assertEqual(v.discover(rows,max_pairs=0)['status'],'RESOURCE_BOUND_REFUSAL')

    def test_no_union_neighborhood_self_witness(self):
        lower,cat,selected,choice,targets=self.fixture();g=deepcopy(cat['base']['lane_relationships'])
        for n in g['nodes'].values():
            if n['bar']!=2:n['reasons']=['NO_INDEPENDENT_EVIDENCE']
        self.assertEqual(check_many(g,list(zip(targets,choice['realizations'])),allow_string_changes=True)['status'],'REFUSED')

    def test_actual_isolated_zero_and_nonzero_same_equations(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower,cat,selected,choice,targets=self.fixture();upper=strip_lower(analyze(lower,families=True))
        controls=dict(context_policy=v.POLICY,voicing=100,register=0,physical=100,target_ref=selected['id'],seed=0)
        changed=reconstruct(upper,controls)
        self.assertNotEqual(changed,lower)
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(execute(code,upper,{'variation':0},lower,Path(tmp)/'zero')['status'],'PASS')
            report=execute(code,upper,controls,changed,Path(tmp)/'changed',purpose='voicing_register_intervention')
            self.assertEqual(report['status'],'PASS',report)
        for strength in (0,50,100):
            for seed in range(100):
                controls.update(voicing=strength,physical=strength,seed=seed)
                value,decision=v.sample_choice(cat,controls)
                if strength==0:self.assertFalse(decision['changed'])
                if value is not None:
                    old=v.options(cat,selected['id'])['original']
                    if not decision['released']['voicing']:self.assertEqual([x['intervals'] for x in value],[x['intervals'] for x in old])
                    if not decision['released']['physical']:self.assertEqual([x['strings'] for x in value],[x['strings'] for x in old])


if __name__=='__main__':unittest.main()
