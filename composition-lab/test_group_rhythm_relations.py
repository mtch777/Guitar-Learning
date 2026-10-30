import unittest
import tempfile
from copy import deepcopy
from pathlib import Path
from fractions import Fraction as F
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize,validate
from group_rhythm_relations import relation,expand


def documents():
    measures=[]
    for types in ((8,16,16),(16,16,8),(8,16,16)):
        beats=[dict(type=t,duration=[2,2*t],notes=[dict(string=0,fret=5)])for t in (*types,4,4,4)]
        beats[0].update(beamStart=True,velocity='f');beats[2]['beamStop']=True
        measures.append(dict(signature=[4,4],voices=[dict(beats=beats)]))
    return {'metadata.json':dict(songId=77,revisionId=3,artist='Fixture',title='Rhythm',tracks=[dict(name='Bass',instrumentId=33)]),
            'track-0.json':dict(songId=77,revisionId=3,partId=0,name='Bass',instrumentId=33,tuning=[40,45],measures=measures)}


class RhythmRelationsTests(unittest.TestCase):
    def test_same_equation_and_bad_parameters(self):
        r=relation(start_q='7/3',span_q='1',durations_q=['1/2','1/4','1/4'])
        self.assertEqual(r,relation(start_q='7/3',span_q='1',shares=r['shares']))
        self.assertEqual(r['onsets_q'],['7/3','17/6','37/12'])
        for shares in (['0','1'],['-1','2'],['1/2','1/3'],['2/4','1/2'],['1']):
            with self.subTest(shares=shares),self.assertRaises(ValueError):relation(start_q='0',span_q='1',shares=shares)

    def test_exact_zero_and_existing_owner_composition(self):
        before=extract_documents(documents())
        for mode in ({},{'families':True},{'declared_chords':True},{'note_accent_slots':True},{'families':True,'note_accent_slots':True}):
            with self.subTest(mode=mode):
                upper=analyze(before,rhythm_groups=True,**mode);model=upper['musical_relationships']
                self.assertEqual(len(model['groups']),3)
                self.assertEqual(realize(strip_lower(upper)),before);self.assertEqual(validate(upper),before)
                owned=set(expand(model)[1])
                self.assertFalse(owned & {x['fact_ref']for x in upper['owned_parameters']['source_choices']})

    def test_changed_group_exact_other_fields_and_clock(self):
        before=extract_documents(documents());upper=strip_lower(analyze(before,rhythm_groups=True))
        upper['musical_relationships']['groups'][0]['shares']=['1/4','1/4','1/2']
        after=realize(upper);expected=documents()
        for b,t in zip(expected['track-0.json']['measures'][0]['voices'][0]['beats'],(16,16,8)):
            b['type']=t;b['duration']=[2,2*t]
        self.assertEqual(project_documents(after),expected)
        self.assertEqual(validate(upper),after)
        from run_reversible_tier_qa import extract_documents as events
        old=events(documents())['events'];new=events(expected)['events']
        self.assertEqual(old[3:],new[3:])
        self.assertEqual([e['pitch']for e in old],[e['pitch']for e in new])

    def test_ownership_and_unsupported_notation_rejections(self):
        base=strip_lower(analyze(extract_documents(documents()),rhythm_groups=True))
        for kind in ('old_onset','old_duration','duplicate_group','wrong_address','bad_scale','tuplets','stale_view','raw_choice'):
            upper=deepcopy(base);model=upper['musical_relationships'];g=model['groups'][0];core=model['pitch_relationships'];m=g['members'][0]
            node=next(c for c in core['coattacks']if c['id']==m['coattack_ref'])
            if kind=='old_onset':node['onset_q']='0'
            elif kind=='old_duration':node['members'][0]['duration_q']='1/2'
            elif kind=='duplicate_group':model['groups'].append(deepcopy(g))
            elif kind=='wrong_address':m['beat_ref']='fake'
            elif kind=='bad_scale':m['fraction_scale']=0
            elif kind=='tuplets':g['shares']=['1/3','1/3','1/3']
            elif kind=='stale_view':core['ensemble_coattacks']=[]
            else:
                legacy=analyze(extract_documents(documents()))
                upper['owned_parameters']['source_choices'].append(next(x for x in legacy['owned_parameters']['source_choices']if x['fact_ref']==m['beat_ref']+'/type'))
            with self.subTest(kind=kind),self.assertRaises((ValueError,KeyError)):realize(upper)

    def test_other_voice_and_expression_are_not_silently_retimed(self):
        from source_rhythm_groups import inventory
        for edit in ('voice','bend','dots','restart','unknown_boundary','unapproved_program'):
            d=documents();part=d['track-0.json'];m=part['measures'][0];b=m['voices'][0]['beats']
            if edit=='voice':m['voices'].append(dict(beats=[dict(type=1,duration=[1,1],notes=[dict(string=1,fret=3)])]))
            elif edit=='bend':b[1]['notes'][0]['bend']={'tone':100}
            elif edit=='dots':b[1]['dots']=1
            elif edit=='restart':b[1]['beamStart']=True
            elif edit=='unknown_boundary':b[1]['beamStart']=1
            else:part['instrumentId']=35
            rows=inventory(extract_documents(d))['groups']
            self.assertFalse(any(r['bar']==1 and not r['reasons']for r in rows),edit)

    def test_actual_isolated_inverse(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        before=extract_documents(documents());upper=strip_lower(analyze(before,rhythm_groups=True,note_accent_slots=True))
        with tempfile.TemporaryDirectory()as temp:
            for stage in ('zero','changed'):
                if stage=='changed':upper['musical_relationships']['groups'][0]['shares']=['1/4','1/4','1/2']
                result=execute(code,upper,dict(variation=0),realize(upper),Path(temp)/stage,timeout=45)
                self.assertEqual(result['status'],'PASS',result)


if __name__=='__main__':unittest.main()
