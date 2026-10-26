"""Independent exactness contracts for source-owned spacing families."""
from copy import deepcopy
import unittest
from musical_tier2 import analyze, strip_lower, reconstruct
from test_musical_tier2 import facts


def core_for(pitches):
    return strip_lower(analyze(facts([(0,p,0,1) for p in pitches])))


def scalar_paths(value, name):
    if isinstance(value,dict):
        for key,child in value.items():
            if key==name:yield child
            yield from scalar_paths(child,name)
    elif isinstance(value,list):
        for child in value:yield from scalar_paths(child,name)


class VoicingFamilyTests(unittest.TestCase):
    def api(self):
        import voicing_families
        return voicing_families

    def exact(self,core):
        api=self.api();before=deepcopy(core);shared=api.lift(core)
        self.assertEqual(core,before,'lift mutated its preceding input')
        frozen=deepcopy(shared);api.validate(shared)
        self.assertEqual(api.realize(shared),before)
        self.assertEqual(shared,frozen,'realize or validate mutated its input')
        self.assertNotIn('input',shared)
        self.assertNotIn('derived_views',shared)
        return shared

    def test_all_pc_wraps_duplicate_classes_and_source_orders(self):
        for shift in range(12):
            for pitches in ([59,62,66,71],[71,59,66,62],[60,60,72,67],[72,67,60,60]):
                with self.subTest(shift=shift,pitches=pitches):
                    self.exact(core_for([p+shift for p in pitches]))

    def test_exact_full_core_and_same_lower_reconstruction(self):
        lower=facts([(0,60,0,1),(0,64,0,1),(0,67,0,1),(0,62,1,1),(0,65,1,1),(0,69,1,1)])
        core=strip_lower(analyze(lower));shared=self.exact(core)
        self.assertEqual(reconstruct(self.api().realize(shared),dict(variation=0)),lower)

    def test_unknown_and_singleton_groups_exact(self):
        for pitches in ([60],[None],[60,None],[60,64,None]):
            with self.subTest(pitches=pitches):self.exact(core_for(pitches))

    def test_eligible_intervals_not_duplicated_in_family_payload(self):
        shared=self.exact(core_for([60,64,67,72]))
        self.assertEqual(list(scalar_paths(shared,'voicing_interval')),[],
                         'eligible intervals survived as a second authority')

    def test_reject_lower_payload_and_source_cache_injection(self):
        for field in ('input','derived_views','source_cache'):
            shared=self.exact(core_for([60,64,67]));shared[field]={'notes':[60,64,67]}
            with self.subTest(field=field):
                with self.assertRaises(ValueError):self.api().validate(shared)
                with self.assertRaises(ValueError):self.api().realize(shared)




class VoicingFamilyOwnershipTests(unittest.TestCase):
    """Malformed ownership differs from a structurally valid musical edit."""
    api=VoicingFamilyTests.api
    exact=VoicingFamilyTests.exact

    def group(self,shared):
        return next(g for g in shared['core']['coattacks'] if 'spacing_ref' in g)

    def refused(self,shared):
        with self.assertRaises(ValueError):self.api().validate(shared)
        with self.assertRaises(ValueError):self.api().realize(shared)

    def test_exact_outer_and_deduplicated_spacing_definition(self):
        lower=facts([(0,60,0,1),(0,64,0,1),(0,67,0,1),(0,72,1,1),(0,76,1,1),(0,79,1,1)])
        shared=self.exact(strip_lower(analyze(lower)))
        self.assertEqual(set(shared),{'schema','core','spacings'})
        self.assertEqual(shared['schema'],'source-voicing-families/1')
        self.assertEqual(len(shared['spacings']),1)
        for field in ('ensemble_coattacks','nominal_written_spans','tonal_evidence','temporal_tonal_evidence'):
            self.assertNotIn(field,shared['core'])
        for group in shared['core']['coattacks']:
            self.assertNotIn('interpretation',group)

    def test_bad_permutations_and_missing_owners_rejected(self):
        for permutation in ([0,0,2],[0,1],[0,1,3],[False,1,2],[0.0,1,2],['0',1,2]):
            shared=self.exact(core_for([60,64,67]));self.group(shared)['member_permutation']=permutation
            with self.subTest(permutation=permutation):self.refused(shared)
        for field in ('spacing_ref','member_permutation'):
            shared=self.exact(core_for([60,64,67]));self.group(shared).pop(field)
            with self.subTest(missing=field):self.refused(shared)
        shared=self.exact(core_for([60,64,67]));self.group(shared)['spacing_ref']='spacing:missing';self.refused(shared)

    def test_duplicate_unused_noncanonical_and_raw_definition_rejected(self):
        for mode in ('duplicate','missing','id','interval','extra','raw_member','extra_group'):
            shared=self.exact(core_for([60,64,67]));definition=shared['spacings'][0]
            if mode=='duplicate':shared['spacings'].append(deepcopy(definition))
            elif mode=='missing':shared['spacings']=[]
            elif mode=='id':definition['id']='spacing:not-canonical'
            elif mode=='interval':definition['intervals'][1]='4.0'
            elif mode=='extra':definition['source_notes']=[60,64,67]
            elif mode=='raw_member':self.group(shared)['members'][0]['voicing_interval']='0'
            elif mode=='extra_group':self.group(shared)['cached_intervals']=['0','4','7']
            with self.subTest(mode=mode):self.refused(shared)
        shared=self.exact(core_for([60,64,67]));other=self.exact(core_for([60,63,67]))
        shared['spacings']+=deepcopy(other['spacings']);shared['spacings'].sort(key=lambda row:row['id']);self.refused(shared)

    def test_equal_interval_slots_have_canonical_source_id_order(self):
        shared=self.exact(core_for([60,60,67]));g=self.group(shared)
        permutation=g['member_permutation'];permutation[0],permutation[1]=permutation[1],permutation[0]
        self.refused(shared)

if __name__=='__main__':unittest.main()
