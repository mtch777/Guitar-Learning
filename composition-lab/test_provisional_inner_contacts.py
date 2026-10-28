from copy import deepcopy
import unittest
from unittest.mock import patch
from test_inner_voicing import fixture,analyzed
from inner_voicing import options,verify,apply,component_links,PREVIEW_POLICY
from connected_tier2 import realize


class ProvisionalContacts(unittest.TestCase):
    def test_optin_replaces_only_whole_geometry_witness(self):
        docs,refs,_=fixture()
        for n,f in zip(docs['track-0.json']['measures'][4]['voices'][0]['beats'][2]['notes'],[8,10,9,7]):n['fret']=f
        lower,upper,c=analyzed(docs)
        old=options(upper,refs[0],c)
        self.assertFalse(any(o['changed'] for o in old['options']))
        self.assertIn('NO_INDEPENDENT_WHOLE_GEOMETRY',str(old['rejected']))
        new=options(upper,refs[0],c,physical_policy=PREVIEW_POLICY)
        changed=[o for o in new['options'] if o['changed']]
        self.assertTrue(changed,new)
        for o in changed:
            self.assertEqual(o['relationship']['status'],'PROVISIONAL_INNER_CONTACT_RELATIONSHIPS')
            self.assertEqual(o['relationship']['human_playability'],'UNVERIFIED')
        self.assertEqual(realize(upper),lower)

    def test_later_technique_guard_cannot_be_bypassed(self):
        docs,refs,_=fixture();_,upper,c=analyzed(docs)
        target=next(u for u in c['units'] if u['id']==refs[0])
        link=next(l for l in component_links(c,target) if l['changed'])
        after=realize(apply(upper,target,link['roles']))
        with patch('technique_analysis.classify_group',side_effect=[['old'],['different']]):
            with self.assertRaisesRegex(ValueError,'TECHNIQUE_CLASS_CHANGED'):
                verify(c,after,target,link['donor'],physical_policy=PREVIEW_POLICY)

    def test_later_pedal_guard_cannot_be_bypassed(self):
        docs,refs,_=fixture();_,upper,c=analyzed(docs)
        target=next(u for u in c['units'] if u['id']==refs[0]);link=next(l for l in component_links(c,target) if l['changed'])
        after=realize(apply(upper,target,link['roles']))
        with patch('freeze_technique_baseline.retained',side_effect=[{'tracks':[{'approved_pedal_phrases':[]}]},{'tracks':[{'approved_pedal_phrases':[1]}]}]):
            with self.assertRaisesRegex(ValueError,'APPROVED_PEDAL_CHANGED'):
                verify(c,after,target,link['donor'],physical_policy=PREVIEW_POLICY)

    def test_source_fingering_declaration_still_refused(self):
        docs,refs,_=fixture()
        _,_,c=analyzed(docs)
        docs['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][1]['leftFinger']=1
        # This field currently fails earlier full-source ownership as well.
        # Neither that refusal nor the explicit geometry guard may be waived.
        with self.assertRaisesRegex(ValueError,'Unsupported source facts'):
            analyzed(docs)
        from inner_voicing import geometry
        result=geometry(docs,c['lane_graph']['nodes'],refs,c['pinned'])
        self.assertIn('UNCOUPLED_FINGER_DECLARATION',result['reasons'])


if __name__=='__main__':unittest.main()
