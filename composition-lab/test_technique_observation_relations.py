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





class NewLiteralTechniqueTests(unittest.TestCase):
    def test_extend_and_arbitrary_string_markings_exact_units(self):
        for flag in (False,True):
            lower=facts({},dict(tremoloBar=dict(extend=flag,points=[dict(tone=-50,position=30,precisePosition=37.5)]),wahwah='unknown future value',golpe=''))
            model=lift(lower);self.assertFalse(model['unsupported'])
            rows=realize(model);expected=[r for r in lower['facts'] if r['id'] in {x['id'] for x in rows}]
            self.assertEqual(sorted(rows,key=lambda r:r['id']),sorted(expected,key=lambda r:r['id']))
            extend=next(p for g in model['groups'] for p in g['parameters'] if p['fact_ref'].endswith('/extend'))
            self.assertEqual(extend,dict(fact_ref=extend['fact_ref'],unit='1',parameter={'symbol':flag}))
    def test_new_declarations_bad_types_refused_both_directions(self):
        for field in ('wahwah','golpe'):
            for value in (True,0,0.0,None,[],{}):
                model=lift(facts({}, {field:value}))
                self.assertEqual(model['groups'],[])
                self.assertEqual(len(model['unsupported']),1)
        for value in (0,1,'true',None,[],{}):
            model=lift(facts({},dict(tremoloBar=dict(points=[],extend=value))))
            self.assertEqual(model['groups'],[])
        good=lift(facts({},dict(tremoloBar=dict(points=[],extend=True))))
        bad=deepcopy(good);g=bad['groups'][0]
        shape=next(r for r in g['structure'] if r['pointer'].endswith('/extend'));shape['type']='integer'
        param=next(p for p in g['parameters'] if p['fact_ref']==shape['id']);param['parameter']={'normalized':'1','negative_zero':False}
        with self.assertRaises(ValueError):realize(bad)

    def test_independent_complete_new_root_inventory_and_omissions(self):
        from test_declared_chord_ownership import documents
        from connected_tier2 import analyze
        from check_technique_connections import check
        docs=documents();beat=docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]
        beat.update(wahwah='open',golpe='future-value',tremoloBar=dict(points=[dict(tone=0,position=0,precisePosition=0)],extend=False))
        upper=analyze(extract_documents(docs),declared_chords=True)
        self.assertFalse(upper['unsupported'])
        self.assertEqual(check(docs,upper)['status'],'PASS_SOURCE_BACKED_RELATIONSHIPS')
        for field in ('wahwah','golpe','tremoloBar'):
            bad=deepcopy(upper);model=bad['owned_parameters']['technique_declarations']
            model['groups']=[g for g in model['groups'] if g['field']!=field]
            self.assertEqual(check(docs,bad)['status'],'FAIL')




class SustainPedalDeclarationTests(unittest.TestCase):
    def test_boolean_false_true_absence_and_bad_types(self):
        for value in (False,True):
            lower=facts({},dict(sustainPedal=value));model=lift(lower)
            self.assertFalse(model['unsupported']);self.assertEqual(len(model['groups']),1)
            self.assertEqual(model['groups'][0]['parameters'][0]['unit'],'1')
            self.assertEqual(model['groups'][0]['parameters'][0]['parameter'],{'symbol':value})
            self.assertEqual(realize(model)[0]['value'],value)
        self.assertEqual(lift(facts({}))['groups'],[])
        for value in (0,1,0.0,'true',None,[],{}):
            model=lift(facts({},dict(sustainPedal=value)))
            self.assertEqual(model['groups'],[]);self.assertEqual(len(model['unsupported']),1)
        model=lift(facts({},dict(sustainPedal=True)));bad=deepcopy(model)
        bad['groups'][0]['parameters'][0]['parameter']={'symbol':1}
        with self.assertRaises(ValueError):realize(bad)
    def test_complete_source_and_independent_false_inventory(self):
        from test_declared_chord_ownership import documents
        from connected_tier2 import analyze,strip_lower,reconstruct
        from check_technique_connections import check
        for flag in (False,True):
            docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['sustainPedal']=flag
            lower=extract_documents(docs);upper=analyze(lower,declared_chords=True)
            self.assertFalse(upper['unsupported']);self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)
            self.assertEqual(check(docs,upper)['status'],'PASS_SOURCE_BACKED_RELATIONSHIPS')
            bad=deepcopy(upper);model=bad['owned_parameters']['technique_declarations']
            model['groups']=[g for g in model['groups'] if g['field']!='sustainPedal']
            self.assertEqual(check(docs,bad)['status'],'FAIL')

if __name__=='__main__':unittest.main()
