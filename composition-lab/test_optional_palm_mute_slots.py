"""Exact optional Boolean/container topology, including source child order."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents,validate,project_documents
import optional_palm_mute_slots as slots


def source(beats):return extract_documents({'track-0.json':dict(measures=[dict(voices=[dict(beats=beats)])])})


def merge(lower,model):
    original=slots.realize(slots.lift(lower));owned={r['id']for r in original}
    index={r['id']:deepcopy(r)for r in lower['facts']if r['id']not in owned}
    for row in slots.realize(model):
        if row['id']in index:raise ValueError('Overlapping source owner')
        index[row['id']]=row
    ordered=[]
    def walk(ref):
        row=index[ref];ordered.append(row)
        for child in row.get('children',[]):walk(child)
    for d in lower['documents']:walk(d['fact_ref'])
    result=deepcopy(lower);result['facts']=ordered;validate(result);return result


class PalmMuteSlotTests(unittest.TestCase):
    def test_exact_absent_false_true_and_child_order(self):
        lower=source([dict(notes=[]),dict(notes=[],palmMute=False,duration=[1,4]),dict(palmMute=True,notes=[])])
        model=slots.lift(lower);self.assertEqual(merge(lower,model),lower)
        self.assertEqual([g['state']for g in model['groups']],[dict(kind='absent'),dict(kind='explicit',value=False,child_index=1),dict(kind='explicit',value=True,child_index=0)])
        for g in model['groups']:
            self.assertNotIn(g['beat_structure']['id']+'/palmMute',g['beat_structure']['children'])
            self.assertNotIn('value',g['beat_structure'])

    def test_same_expansion_adds_removes_and_changes_only_optional_boolean(self):
        lower=source([dict(notes=[])]);model=slots.lift(lower);g=model['groups'][0]
        self.assertEqual(len(slots.coverage(model)),1)
        g['state']=dict(kind='explicit',value=True,child_index=1)
        actual=merge(lower,model);self.assertEqual(project_documents(actual)['track-0.json']['measures'][0]['voices'][0]['beats'][0],dict(notes=[],palmMute=True))
        self.assertEqual(len(slots.coverage(model)),2)
        g['state']=dict(kind='explicit',value=False,child_index=1)
        self.assertFalse(project_documents(merge(lower,model))['track-0.json']['measures'][0]['voices'][0]['beats'][0]['palmMute'])
        g['state']=dict(kind='absent');self.assertEqual(merge(lower,model),lower)

    def test_unknown_typed_declarations_not_lifted_or_coerced(self):
        lower=source([dict(palmMute=v,notes=[])for v in(None,0,1,1.0,'true',{},[])]+[dict(palmMute=False,notes=[])])
        model=slots.lift(lower);self.assertEqual(len(model['groups']),1);self.assertEqual(merge(lower,model),lower)

    def test_exact_types_no_hidden_fields_and_no_escaped_ownership(self):
        original=slots.lift(source([dict(notes=[])]))
        for state in(dict(kind='absent',value=False),dict(kind='explicit',value=1,child_index=0),dict(kind='explicit',value=True,child_index=True),dict(kind='explicit',value=False,child_index=2),dict(kind='explicit',value=True,child_index=0,raw=False)):
            model=deepcopy(original);model['groups'][0]['state']=state
            with self.assertRaises(ValueError):slots.realize(model)
        for case in('duplicate','child','grandchild','other_beat','bad_slot','hidden_original'):
            model=deepcopy(original);group=model['groups'][0];beat=group['beat_structure']
            if case=='duplicate':model['groups'].append(deepcopy(group))
            elif case=='child':beat['children'].append(beat['id']+'/palmMute')
            elif case=='grandchild':beat['children'].append(beat['id']+'/notes/0')
            elif case=='other_beat':beat['children'].append(beat['id'][:-1]+'1/notes')
            elif case=='bad_slot':beat['slot']=False
            else:group['original']=True
            with self.assertRaises(ValueError):slots.realize(model)

    def test_ownership_is_typed_to_beats_not_notes_or_arbitrary_containers(self):
        model=slots.lift(source([dict(notes=[]),dict(notes=[])]));model['groups'].reverse()
        with self.assertRaises(ValueError):slots.realize(model)
        model=slots.lift(source([dict(notes=[])]));model['groups'][0]['beat_structure']['id']+='/notes/0'
        with self.assertRaises(ValueError):slots.realize(model)


if __name__=='__main__':unittest.main()
