"""Recognized declarations reverse exactly; unknown structures are not smuggled."""
from copy import deepcopy
import json
import unittest
from source_fact_tier1 import extract_documents
from technique_observation_relations import lift,realize,scalar_relation


def facts(note,beat=None):
    return extract_documents({'track-0.json':dict(measures=[dict(voices=[dict(beats=[dict(beat or {},notes=[note])])])])})


class TechniqueObservationRelationTests(unittest.TestCase):
    def test_curve_exact_type_units_presence_and_negative_zero(self):
        lower=facts(dict(bend=dict(tone=100,points=[dict(position=0,tone=-0.0),dict(position=60,precisePosition=99.5,tone=100,vibrato=False)]),hp=None,ghost=False),dict(tremolo=[1,16],letRing=True))
        model=lift(lower);actual=realize(model);refs={r['id'] for r in actual}
        expected=[r for r in lower['facts'] if r['id'] in refs]
        self.assertEqual(json.dumps(sorted(actual,key=lambda r:r['id']),sort_keys=True),json.dumps(sorted(expected,key=lambda r:r['id']),sort_keys=True))
        self.assertEqual(len(model['groups']),5)
        peak=next(p for g in model['groups'] if g['field']=='bend' for p in g['parameters'] if p['fact_ref'].endswith('/bend/tone'))
        self.assertEqual(peak['parameter']['normalized'],'2')

    def test_unknown_nested_note_payload_is_not_a_generic_codec(self):
        model=lift(facts(dict(bend=dict(points=[],hidden_notes=[60,64,67]))))
        self.assertEqual(model['groups'],[])
        self.assertEqual(model['unsupported'][0]['reason'],'UNREGISTERED_TECHNIQUE_STRUCTURE')

    def test_inverse_rejects_unknown_scalar_nested_and_disconnected_children(self):
        original=facts(dict(bend=dict(tone=100,points=[])))
        for extra in (dict(secret=60),dict(secret=dict(notes=[60,64]))):
            injected=facts(dict(bend=dict(tone=100,points=[],**extra)))
            # Construct an adversarial inverse model; forward correctly refuses it.
            model=lift(original);group=model['groups'][0]
            root=group['source_fact_ref']
            rows=[r for r in injected['facts'] if r['id']==root or r['id'].startswith(root+'/')]
            group['structure']=[{k:v for k,v in r.items() if k!='value'} for r in rows]
            group['parameters']=[dict(fact_ref=r['id'],unit='50' if r['slot']=='tone' else '1',parameter=scalar_relation(r['type'],source=r['value'],unit='50' if r['slot']=='tone' else '1')) for r in rows if 'value' in r]
            with self.assertRaises(ValueError):realize(model)
        model=lift(original);model['groups'][0]['structure'][0]['children']=[]
        with self.assertRaises(ValueError):realize(model)

    def test_shared_scalar_equation_rejects_conflicting_type(self):
        p=scalar_relation('integer',source=100,unit='50')
        self.assertEqual(scalar_relation('integer',parameter=p,unit='50'),100)
        with self.assertRaises(ValueError):scalar_relation('integer',source=True)
        with self.assertRaises(ValueError):scalar_relation('integer',parameter=dict(normalized='1/3',negative_zero=False))

    def test_unit_or_owner_payload_cannot_smuggle_unregistered_facts(self):
        model=lift(facts(dict(bend=dict(tone=100,points=[]))))
        changed=deepcopy(model);changed['groups'][0]['parameters'][0]['unit']='100'
        with self.assertRaises(ValueError):realize(changed)
        changed=deepcopy(model);changed['groups'][0]['hidden_notes']=[60,64]
        with self.assertRaises(ValueError):realize(changed)


if __name__=='__main__':unittest.main()
