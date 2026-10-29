"""Exact optional topology ownership, independently checked against raw facts."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents,validate,project_documents
import optional_accent_slots as slots


def source(notes):
    return extract_documents({'track-0.json':{'measures':[{'voices':[{'beats':[{'notes':notes}]}]}]}})


def merge(lower,model):
    # Independent test assembly: replace emitted owners, then traverse unchanged
    # parent references. Production integration is tested separately by root.
    original=slots.realize(slots.lift(lower));owned={r['id']for r in original}
    index={r['id']:deepcopy(r)for r in lower['facts']if r['id']not in owned}
    for r in slots.realize(model):
        if r['id']in index:raise ValueError('Overlapping owner')
        index[r['id']]=r
    ordered=[]
    def walk(ref):
        r=index[ref];ordered.append(r)
        for c in r.get('children',[]):walk(c)
    for d in lower['documents']:walk(d['fact_ref'])
    result=deepcopy(lower);result['facts']=ordered;validate(result);return result


class OptionalAccentTests(unittest.TestCase):
    def test_exact_absence_zero_normal_heavy_and_original_field_order(self):
        lower=source([{'fret':2,'string':0},{'fret':3,'accentuated':0,'string':1},{'accentuated':1,'fret':4,'string':2},{'fret':5,'string':3,'accentuated':2}])
        model=slots.lift(lower)
        self.assertEqual(len(model['groups']),4)
        self.assertEqual(merge(lower,model),lower)
        self.assertEqual([g['state']for g in model['groups']],[{'kind':'absent'},{'kind':'explicit','value':0,'child_index':1},{'kind':'explicit','value':1,'child_index':0},{'kind':'explicit','value':2,'child_index':2}])
        for g in model['groups']:
            self.assertNotIn(g['note_structure']['id']+'/accentuated',g['note_structure']['children'])
            self.assertNotIn('value',g['note_structure'])

    def test_known_edits_use_same_expansion_and_conditional_coverage(self):
        lower=source([{'fret':2,'string':0}]);model=slots.lift(lower)
        self.assertEqual(len(slots.coverage(model)),1)
        g=model['groups'][0];g['state']={'kind':'explicit','value':1,'child_index':len(g['note_structure']['children'])}
        changed=merge(lower,model)
        self.assertEqual(project_documents(changed)['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0],{'fret':2,'string':0,'accentuated':1})
        self.assertEqual(len(slots.coverage(model)),2)
        self.assertEqual(slots.coverage(model),[{'fact_ref':r['id'],'owner':'optional_note_accent'}for r in slots.realize(model)])
        g['state']={'kind':'absent'}
        self.assertEqual(merge(lower,model),lower)

    def test_unknown_typed_values_remain_completely_outside_owner(self):
        unknown=[None,False,True,1.0,'1',3,-1,{},[]]
        lower=source([{'fret':2,'accentuated':v}for v in unknown]+[{'accentuated':0}])
        model=slots.lift(lower);self.assertEqual(len(model['groups']),1)
        self.assertEqual(merge(lower,model),lower)

    def test_exact_keysets_and_strict_state_types(self):
        base=slots.lift(source([{'fret':2}]))
        bad=[{'kind':'absent','value':0},{'kind':'absent','child_index':0},{'kind':'explicit','value':True,'child_index':0},{'kind':'explicit','value':1.0,'child_index':0},{'kind':'explicit','value':3,'child_index':0},{'kind':'explicit','value':1,'child_index':False},{'kind':'explicit','value':1,'child_index':-1},{'kind':'explicit','value':1,'child_index':2},{'kind':'explicit','value':1,'child_index':0,'raw':7},None]
        for state in bad:
            with self.subTest(state=state):
                m=deepcopy(base);m['groups'][0]['state']=state
                with self.assertRaises(ValueError):slots.realize(m)
        for obj in ('wrapper','group','structure'):
            m=deepcopy(base);dest=m if obj=='wrapper'else m['groups'][0]if obj=='group'else m['groups'][0]['note_structure'];dest['raw_notes']=[60]
            with self.assertRaises(ValueError):slots.realize(m)

    def test_duplicate_and_escaped_ownership_refused(self):
        base=slots.lift(source([{'fret':2,'string':0}]))
        for mutation in ('duplicate_group','duplicate_child','accent_child','grandchild','other_note','invalid_escape','wrong_parent','wrong_slot','wrong_id'):
            m=deepcopy(base);g=m['groups'][0];n=g['note_structure']
            if mutation=='duplicate_group':m['groups'].append(deepcopy(g))
            elif mutation=='duplicate_child':n['children'].append(n['children'][0])
            elif mutation=='accent_child':n['children'].append(n['id']+'/accentuated')
            elif mutation=='grandchild':n['children'].append(n['id']+'/bend/tone')
            elif mutation=='other_note':n['children'].append(n['id'][:-1]+'1/fret')
            elif mutation=='invalid_escape':n['children'].append(n['id']+'/~9')
            elif mutation=='wrong_parent':n['parent']+='bad'
            elif mutation=='wrong_slot':n['slot']=False
            else:g['id']+='bad'
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):slots.realize(m)

    def test_not_a_generic_container_or_hidden_scalar_codec(self):
        lower=source([{'accentuated':1,'fret':2}]);model=slots.lift(lower);group=model['groups'][0]
        for field,value in [('type','array'),('id','metadata.json#/notes/0'),('document','track-1.json'),('pointer','/other/0')]:
            m=deepcopy(model);m['groups'][0]['note_structure'][field]=value
            with self.assertRaises(ValueError):slots.realize(m)
        emitted=slots.realize(model);note,accent=emitted
        self.assertEqual(slots.build(note,accent),group)
        for change in ({'value':True},{'type':'float','value':1.0},{'parent':note['parent']},{'slot':'velocity'},{'value':3}):
            bad=dict(accent,**change)
            with self.assertRaises(ValueError):slots.build(note,bad)
        with self.assertRaises(ValueError):slots.build(note,None)
        for field in ('id','document','pointer','parent','type'):
            bad=deepcopy(note);bad[field]=7
            with self.assertRaises(ValueError):slots.build(bad,accent)

    def test_detached_ownership_and_canonical_group_order(self):
        lower=source([{'fret':2},{'fret':3}]);model=slots.lift(lower)
        model['groups'][0]['note_structure']['children'].clear()
        self.assertTrue(any(r.get('slot')=='fret'for r in lower['facts']))
        m=slots.lift(lower);m['groups'].reverse()
        with self.assertRaises(ValueError):slots.coverage(m)
        m=slots.lift(lower);rows=slots.realize(m);rows[0]['children'].clear()
        self.assertTrue(m['groups'][0]['note_structure']['children'])


if __name__=='__main__':unittest.main()
