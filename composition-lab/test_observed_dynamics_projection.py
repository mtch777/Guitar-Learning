"""Authored insertion lineage preserves original dynamic evidence and choices."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest

import observed_dynamics as dynamic
from source_fact_tier1 import extract_documents
from source_observation_evidence import origin
from test_execution_dependencies import documents, n


def fact(beat,note=None):
    base=f'track-0.json#/measures/0/voices/0/beats/{beat}'
    return base+(f'/notes/{note}' if note is not None else '')+'/velocity'


def event(beat,note=0):return f'event:86:0:1:0:{beat}:{note}'


def fixture():
    return documents([n(0),n(2),n(4),n(5)],
                     {0:dict(velocity='f'),2:dict(velocity='mf'),3:dict(velocity='p')})


def split(docs,beat,count=2):
    changed=deepcopy(docs)
    old=docs['track-0.json']['measures'][0]['voices'][0]['beats']
    new=[];facts={};events={}
    for i,row in enumerate(old):
        copies=count if i==beat else 1
        positions=list(range(len(new),len(new)+copies))
        if 'velocity' in row:facts[fact(i)]=[fact(j) for j in positions]
        for ni,note in enumerate(row['notes']):
            events[event(i,ni)]=[event(j,ni) for j in positions]
            if 'velocity' in note:facts[fact(i,ni)]=[fact(j,ni) for j in positions]
        for _ in positions:
            value=deepcopy(row);duration=F(*value['duration'])/copies
            value['duration']=[duration.numerator,duration.denominator]
            new.append(value)
    changed['track-0.json']['measures'][0]['voices'][0]['beats']=new
    return changed,facts,events


def model(docs):
    lower=extract_documents(docs)
    return dynamic.lift(lower,origin(lower))


def expected_facts(docs):
    return sorted((r for r in extract_documents(docs)['facts']
                   if r['id'].endswith('/velocity')),key=lambda r:r['id'])


class DynamicProjectionTests(unittest.TestCase):
    def assert_realized(self,owner,docs):
        self.assertEqual(sorted(dynamic.realize(owner),key=lambda r:r['id']),expected_facts(docs))
        dynamic.validate_source(owner,extract_documents(docs))

    def test_duplicate_current_declaration_retains_one_original_vote(self):
        docs=fixture();owner=model(docs);before=deepcopy(owner)
        changed,facts,events=split(docs,0)
        projected=dynamic.project(owner,facts,events)
        self.assertEqual(projected['schema'],dynamic.PROJECTED_SCHEMA)
        self.assert_realized(projected,changed)
        self.assertEqual(dynamic.evidence(projected),dynamic.evidence(owner))
        self.assertEqual(projected['evidence_sha256'],owner['evidence_sha256'])
        self.assertEqual(dynamic.source_view(projected),dynamic.source_view(owner))
        self.assertEqual(projected['current'],owner['current'])
        self.assertEqual(len(projected['observations']),3)
        self.assertEqual(len(dynamic.realize(projected)),4)
        self.assertEqual(owner,before)

    def test_split_inside_unchanged_declarations_influence_and_shifted_later_declaration(self):
        docs=fixture();owner=model(docs)
        changed,facts,events=split(docs,1)
        # The source f declaration is unchanged, yet it now influences a new
        # child. The later unsplit mf declaration has moved from beat 2 to 3.
        projected=dynamic.project(owner,facts,events)
        self.assertEqual(projected['projection']['fact_map'][fact(0)],[fact(0)])
        self.assertEqual(projected['projection']['fact_map'][fact(2)],[fact(3)])
        self.assertEqual(projected['projection']['event_map'][event(1)],[event(1),event(2)])
        self.assert_realized(projected,changed)
        with self.assertRaises(ValueError):dynamic.validate_source(owner,extract_documents(changed))
        shifted_choice=dynamic.choose(json.loads(json.dumps(projected)),fact(2),'p')
        changed['track-0.json']['measures'][0]['voices'][0]['beats'][3]['velocity']='p'
        self.assert_realized(shifted_choice,changed)

    def test_choose_original_identity_after_save_changes_both_current_children(self):
        docs=fixture();owner=model(docs);changed,facts,events=split(docs,0)
        projected=json.loads(json.dumps(dynamic.project(owner,facts,events)))
        frozen=deepcopy(projected)
        chosen=dynamic.choose(projected,fact(0),'mf')
        beats=changed['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['velocity']=beats[1]['velocity']='mf'
        self.assert_realized(chosen,changed)
        self.assertEqual(dynamic.evidence(chosen),dynamic.evidence(owner))
        self.assertEqual(projected,frozen)
        self.assertEqual(dynamic.project(chosen,{},{}),chosen)
        reset=dynamic.choose(chosen,fact(0),'f')
        self.assertEqual(dynamic.realize(reset),dynamic.realize(projected))

    def test_successive_current_address_projection_and_independent_factor_four(self):
        docs=fixture();owner=model(docs)
        once,facts,events=split(docs,0)
        projected=dynamic.project(owner,facts,events)
        twice,next_facts,next_events=split(once,0)
        again=dynamic.project(projected,next_facts,next_events)
        self.assert_realized(again,twice)
        self.assertEqual(again['projection']['fact_map'][fact(0)],[fact(0),fact(1),fact(2)])
        four,facts4,events4=split(docs,0,4)
        projected4=dynamic.project(owner,facts4,events4)
        self.assert_realized(projected4,four)
        self.assertEqual(dynamic.evidence(again),dynamic.evidence(projected4))
        self.assertEqual(dynamic.project(owner,{},{}),owner)

    def test_note_override_children_and_unrelated_full_map_entries(self):
        docs=fixture();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['velocity']='p'
        owner=model(docs);changed,facts,events=split(docs,0)
        facts['track-1.json#/measures/0/voices/0/beats/0/velocity']=['track-1.json#/measures/0/voices/0/beats/1/velocity']
        events['event:86:1:1:0:0:0']=['event:86:1:1:0:1:0']
        projected=dynamic.project(owner,facts,events)
        self.assertNotIn('event:86:1:1:0:0:0',projected['projection']['event_map'])
        self.assert_realized(projected,changed)
        chosen=dynamic.choose(projected,fact(0,0),'mf')
        for beat in changed['track-0.json']['measures'][0]['voices'][0]['beats'][:2]:
            beat['notes'][0]['velocity']='mf'
        self.assert_realized(chosen,changed)

    def test_bad_mapping_refuses_atomically_instead_of_losing_or_merging_owners(self):
        owner=model(fixture());before=deepcopy(owner)
        cases=[({fact(0):[]},{}),({fact(0):[fact(0),fact(0)]},{}),
               ({fact(0):[fact(2)]},{}),({}, {event(0):[event(2)]}),
               ({fact(0):[fact(0,0)]},{}),
               ({},{event(0):['event:87:0:1:0:0:0']}),
               ({},{event(0):['event:86:0:1:1:0:0']}),
               ({},{event(0):['not-an-event']})]
        for facts,events in cases:
            with self.subTest(facts=facts,events=events),self.assertRaises(ValueError):
                dynamic.project(owner,facts,events)
            self.assertEqual(owner,before)

    def test_missing_children_and_forged_topology_fail_current_source_validation(self):
        docs=fixture();owner=model(docs);changed,facts,events=split(docs,0)
        projected=dynamic.project(owner,facts,events)
        for damage in ('missing-event','missing-declaration','extra-influence'):
            bad=deepcopy(projected)
            if damage=='missing-event':bad['projection']['event_map'][event(0)].pop()
            elif damage=='missing-declaration':bad['projection']['fact_map'][fact(0)].pop()
            else:bad['projection']['event_map'][event(0)].append(event(99))
            with self.subTest(damage=damage),self.assertRaises(ValueError):
                dynamic.validate_source(bad,extract_documents(changed))

    def test_saved_projection_cannot_change_original_evidence(self):
        docs=fixture();changed,facts,events=split(docs,0)
        projected=dynamic.project(model(docs),facts,events)
        for field in ('origin','definitions','observations','evidence_sha256'):
            bad=deepcopy(projected)
            if field=='origin':bad[field]['facts_sha256']='0'*64
            elif field=='definitions':bad[field]['dynamic-level:f']['symbol']='mf'
            elif field=='observations':bad[field][0]['definition_ref']='dynamic-level:mf'
            else:bad[field]='0'*64
            with self.subTest(field=field),self.assertRaises(ValueError):dynamic.realize(bad)

    def test_projected_choices_reconstruct_in_actual_source_denied_worker(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        docs=fixture();changed,facts,events=split(docs,0)
        projected=dynamic.choose(dynamic.project(model(docs),facts,events),fact(0),'mf')
        beats=changed['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['velocity']=beats[1]['velocity']='mf'
        expected=sorted(expected_facts(changed),key=lambda row:row['id'])
        code,_=bundle(Path(__file__).parent)
        code+='\ndef reconstruct(upper,controls):\n    if controls!={"variation":0}:raise ValueError("Zero only")\n    return sorted(sys.modules["observed_dynamics"].realize(upper),key=lambda row:row["id"])\n'
        with tempfile.TemporaryDirectory() as folder:
            receipt=execute(code,json.loads(json.dumps(projected)),dict(variation=0),expected,
                            Path(folder)/'projection',timeout=30)
            self.assertEqual(receipt['status'],'PASS',receipt)


if __name__=='__main__':unittest.main()
