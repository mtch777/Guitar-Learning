"""Authored source contrasts for census counting; no performance claims."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from palm_mute_opportunity_census import declaration,inventory,opportunities


def documents():
    measures=[]
    for bar in range(7):
        beats=[]
        for i,d in enumerate(([1,4],[1,4],[1,2])):
            b=dict(duration=d,velocity='f',notes=[dict(string=0,fret=i),dict(string=1,fret=i)])
            if bar in(2,4):b['palmMute']=True
            elif bar in(1,5):b['palmMute']=False
            beats.append(b)
        measures.append(dict(signature=[4,4],voices=[dict(beats=beats)]))
    return {'metadata.json':dict(songId=77,revisionId=3,tracks=[dict(name='Authored guitar',instrumentId=25)]),
        'track-0.json':dict(songId=77,revisionId=3,partId=0,instrumentId=25,tuning=[48,55],measures=measures)}


class PalmMuteCensusTests(unittest.TestCase):
    def test_literal_values_not_coerced(self):
        self.assertEqual(declaration({}),dict(kind='absent'))
        self.assertEqual(declaration({'palmMute':False}),dict(kind='explicit',value=False))
        self.assertEqual(declaration({'palmMute':True}),dict(kind='explicit',value=True))
        for value in(None,0,1,'true',[],{}):self.assertEqual(declaration({'palmMute':value})['kind'],'unknown')

    def test_complete_chords_and_independent_on_off_witnesses(self):
        before=extract_documents(documents());copied=deepcopy(before);view=inventory(before);result=opportunities(view)
        self.assertEqual(before,copied);self.assertEqual(len(view['coattacks']),21)
        self.assertTrue(all(len(r['member_refs'])==2 for r in view['coattacks']))
        self.assertEqual(result['counts']['declaration_states'],dict(absent=9,explicit_false=6,explicit_true=6))
        self.assertGreater(result['counts']['independent_on_off_pairs'],0)
        self.assertGreater(result['counts']['leave_target_out_opportunities'],0)
        rows={r['coattack_ref']:r for r in view['coattacks']}
        for item in result['targets']:
            a,b=(rows[r]for r in item['witness_pair']);t=rows[item['target_ref']]
            self.assertEqual([a['mute_mode'],b['mute_mode']],['on','off'])
            self.assertTrue(set(a['closure_refs']).isdisjoint(b['closure_refs']))
            self.assertTrue(set(t['closure_refs']).isdisjoint(a['closure_refs']))
            self.assertTrue(set(t['closure_refs']).isdisjoint(b['closure_refs']))

    def test_false_versus_absent_is_not_muting_alternative(self):
        docs=documents()
        for m in docs['track-0.json']['measures']:
            for b in m['voices'][0]['beats']:
                if b.get('palmMute')is True:b['palmMute']=False
        result=opportunities(inventory(extract_documents(docs)))
        self.assertEqual(result['counts']['independent_on_off_pairs'],0)
        self.assertEqual(result['counts']['leave_target_out_opportunities'],0)
        self.assertEqual(set(result['counts']['declaration_states']),{'absent','explicit_false'})

    def test_unknown_and_other_execution_stay_refused(self):
        for field,value in [('palmMute',1),('letRing',True),('bend',{}),('hp',True),('unknownExecution',True)]:
            docs=documents();beat=docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]
            (beat if field in('palmMute','letRing')else beat['notes'][0])[field]=value
            row=next(r for r in inventory(extract_documents(docs))['coattacks']if r['onset_q']=='1')
            self.assertTrue(row['reasons'],(field,value))

    def test_any_pitch_duration_or_dynamic_difference_prevents_context_match(self):
        base=inventory(extract_documents(documents()))['coattacks'][1]['context_key']
        for kind in('pitch','duration','dynamic'):
            docs=documents();b=docs['track-0.json']['measures'][2]['voices'][0]['beats'][1]
            if kind=='pitch':b['notes'][0]['fret']=9
            elif kind=='duration':b['duration']=[1,8]
            else:b['velocity']='p'
            row=next(r for r in inventory(extract_documents(docs))['coattacks']if r['onset_q']=='9')
            self.assertNotEqual(row['context_key'],base,kind)


if __name__=='__main__':unittest.main()
