from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize
from test_check_declared_allocation import fixture
from declared_degree_choices import catalog,options,apply,sample,NOMINAL_POLICY
from voicing_context_relations import graph,paths


def dead_fixture():
    docs,_,_,_=fixture()
    for measure in docs['track-0.json']['measures']:
        beats=[]
        for beat in measure['voices'][0]['beats']:
            beat['duration']=[1,8];beats.append(beat)
            for _ in range(2):beats.append(dict(duration=[1,16],notes=[dict(string=s,fret=0,dead=True) for s in range(4)]))
        measure['voices'][0]['beats']=beats
    refs=[f'event:19:0:2:0:3:{i}'for i in range(4)]
    return docs,refs


class NominalIncidenceTests(unittest.TestCase):
    def test_fully_pitched_default_paths_are_identical(self):
        docs,_,_,_=fixture();lower=extract_documents(docs)
        self.assertEqual(paths(graph(lower)),paths(graph(lower,typed_nominal=True),typed_nominal=True))

    def test_long_dead_runs_retain_all_slots_and_bracketing_register(self):
        docs,_=dead_fixture();g=graph(extract_documents(docs),typed_nominal=True)
        p=paths(g,typed_nominal=True);key=('unpitched_span','event:19:0:1:0:1:0')
        span=p[key];self.assertEqual(len(span['refs']),4)
        self.assertEqual(span['nominal_incidence']['slot_kinds'],['PITCHED_WRITTEN_SLOT','UNPITCHED_NOMINAL_SLOT','UNPITCHED_NOMINAL_SLOT','PITCHED_WRITTEN_SLOT'])
        self.assertEqual(span['nominal_incidence']['known_pitch_pairs'],[[0,3,'0','bracketing_known_pitches']])
        changed=deepcopy(g);changed['nodes'][span['refs'][-1]]['pitch']=str(int(changed['nodes'][span['refs'][-1]]['pitch'])+12)
        self.assertNotEqual(paths(changed,typed_nominal=True)[key]['key'],span['key'])
        for ref in span['refs'][1:3]:self.assertIsNone(g['nodes'][ref]['pitch'])

    def test_false_absent_wrongtype_spelling_and_slide_do_not_become_plain_dead(self):
        for mode in ('absent','false','integer','spelling','slide'):
            docs,_=dead_fixture();note=docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]
            if mode=='absent':note.pop('dead')
            if mode=='false':note['dead']=False
            if mode=='integer':note['dead']=1
            if mode=='spelling':note['spn']=[0,4,0]
            if mode=='slide':note['slide']=1
            g=graph(extract_documents(docs),typed_nominal=True);p=paths(g,typed_nominal=True)
            entry=p['triple','event:19:0:1:0:1:0']
            if mode in ('absent','false'):
                self.assertNotEqual(entry.get('nominal_incidence',{}).get('slot_kinds',[None]*3)[1],'UNPITCHED_NOMINAL_SLOT')
            else:self.assertTrue(entry['reasons'],mode)

    def test_same_inverse_changes_chord_without_changing_dead_events(self):
        docs,refs=dead_fixture();lower=extract_documents(docs);upper=strip_lower(analyze(lower,declared_chords=True))
        c=catalog(upper,typed_nominal=True);target=next(u for u in c['units'] if u['member_refs']==refs)
        e=options(upper,target['id'],c,typed_nominal=True);changed=[o for o in e['options'] if o['changed']]
        self.assertTrue(changed,e['rejected']);after=realize(apply(upper,target,changed[0]['roles']))
        control=dict(voicing=100,register=0,target_ref=target['id'],seed=0,context_policy=NOMINAL_POLICY)
        control['seed']=next(i for i in range(1000) if sample(e,dict(control,seed=i))[0]==changed[0])
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as tmp:
            z=execute(code,upper,dict(variation=0),lower,Path(tmp)/'zero',timeout=30)
            r=execute(code,upper,control,after,Path(tmp)/'changed',timeout=30,purpose='voicing_register_intervention')
            self.assertEqual(z['status'],'PASS',z);self.assertEqual(r['status'],'PASS',r)
        allowed={f"track-0.json#/measures/1/voices/0/beats/3/notes/{i}/fret"for i in range(4)}
        self.assertEqual([f for f in lower['facts'] if f['id']not in allowed],[f for f in after['facts'] if f['id']not in allowed])

    def test_legacy_policy_stays_strict_and_missing_bracketing_witness_refuses(self):
        docs,refs=dead_fixture();upper=strip_lower(analyze(extract_documents(docs),declared_chords=True));old=catalog(upper)
        target=next(u for u in old['units'] if u['member_refs']==refs)
        self.assertFalse(any(o['changed'] for o in options(upper,target['id'],old)['options']))
        for i in (11,13):docs['track-0.json']['measures'][i//4]['voices'][0]['beats'][(i%4)*3]['notes'][0]['fret']=9
        upper=strip_lower(analyze(extract_documents(docs),declared_chords=True));c=catalog(upper,typed_nominal=True)
        e=options(upper,target['id'],c,typed_nominal=True)
        self.assertFalse(any(o['changed'] for o in e['options']))
        self.assertTrue(any('NO_INDEPENDENT_SOURCE_UNPITCHED_SPAN' in o['reason'] for o in e['rejected']),e)

    def test_dead_fret_presence_and_type_are_context_not_pitch(self):
        docs,_=dead_fixture();g=graph(extract_documents(docs),typed_nominal=True)
        key=('unpitched_span','event:19:0:1:0:1:0');keys=[]
        for mode in ('int','float','different','absent'):
            changed=deepcopy(docs);note=changed['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]
            if mode=='float':note['fret']=0.0
            if mode=='different':note['fret']=12
            if mode=='absent':note.pop('fret')
            result=graph(extract_documents(changed),typed_nominal=True)
            self.assertIsNone(result['nodes'][key[1]]['pitch'])
            keys.append(paths(result,typed_nominal=True)[key]['key'])
        self.assertEqual(len(set(keys)),4)


if __name__=='__main__':unittest.main()
