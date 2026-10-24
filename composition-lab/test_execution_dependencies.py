"""Incident source endpoints versus contextual execution uncertainty."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from execution_dependencies import build


def documents(notes,extras=None):
    beats=[]
    for i,note in enumerate(notes):
        beat=dict(duration=[1,4],notes=[]if note is None else[dict(note)])
        if extras and i in extras:beat.update(deepcopy(extras[i]))
        beats.append(beat)
    return {'metadata.json':dict(songId=86,revisionId=1,artist='Fixture',title='Source endpoints',tracks=[dict(name='Guitar',instrumentId=25)]),
        'track-0.json':dict(songId=86,revisionId=1,partId=0,instrumentId=25,tuning=[64,59,55,50,45,40],frets=24,measures=[dict(signature=[4,4],voices=[dict(beats=beats)])])}


def n(fret,**fields):return dict(string=5,fret=fret,**fields)


class ExecutionDependencyTests(unittest.TestCase):
    def test_hopo_origin_and_destination_beyond_halfopen_boundary_pinned(self):
        graph=build(extract_documents(documents([n(0,hp=True),n(2),n(4),n(5)])))
        edge=next(e for e in graph['edges']if e['kind']=='hopo')
        self.assertEqual(edge['status'],'source_transition_candidate')
        self.assertEqual(edge['member_refs'],['event:86:0:1:0:0:0','event:86:0:1:0:1:0'])
        self.assertEqual(edge['semantics']['direction'],'hammer_on');self.assertEqual(edge['semantics']['context'],'from_open')
        self.assertEqual(edge['semantics']['fret_distance'],2)
        self.assertEqual(graph['pinned_members'],edge['member_refs'])

    def test_same_fret_unresolved_signature_detects_new_relationship(self):
        docs=documents([n(0,hp=True),n(0),n(4),n(5)]);before=build(extract_documents(docs))
        self.assertEqual(before['signature']['parts'][0]['hopo_unresolved'][0]['reason'],'same_fret')
        self.assertNotIn('event:86:0:1:0:1:0',before['pinned_members'])
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['fret']=2
        after=build(extract_documents(docs));self.assertNotEqual(before['signature'],after['signature'])
        self.assertTrue(after['signature']['parts'][0]['hopo_pairs'])

    def test_resolved_slide_and_tied_candidate_keep_distinct_source_statuses(self):
        direct=build(extract_documents(documents([n(2,slide='shift'),n(4),n(5),n(6)])))
        edge=next(e for e in direct['edges']if e['kind']=='slide')
        self.assertEqual(edge['status'],'resolved_written_target');self.assertEqual(edge['semantics']['interval_semitones'],2)
        tied=build(extract_documents(documents([n(2,slide='legato'),n(2,tie=True),n(4),None])))
        edge=next(e for e in tied['edges']if e['kind']=='slide')
        self.assertEqual(edge['status'],'target_after_tie_candidate')
        self.assertEqual(edge['semantics']['tied_members'],['event:86:0:1:0:1:0'])
        self.assertEqual(set(edge['member_refs']),{'event:86:0:1:0:0:0','event:86:0:1:0:1:0','event:86:0:1:0:2:0'})
        self.assertTrue(tied['uncertainty'])

    def test_entry_exit_grace_and_invalid_timing_do_not_invent_endpoints(self):
        graph=build(extract_documents(documents([n(2,slide='belowdownwards'),n(4),n(5),n(6)])))
        events=[e for e in graph['edges']if e['kind']=='slide']
        entry=next(e for e in events if e['status']=='entry_origin_unspecified');exit=next(e for e in events if e['status']=='exit_target_unspecified')
        self.assertIsNone(entry['semantics']['origin']);self.assertIsNone(exit['semantics']['destination'])
        grace=build(extract_documents(documents([n(2,slide='shift',hp=True),n(4),n(5),n(6)],{0:dict(graceNote='beforeBeat')})))
        self.assertTrue(any(e['status']=='grace_origin_order_unresolved'for e in grace['edges']))
        self.assertTrue(any(e['status']=='grace_origin_not_analyzed'for e in grace['edges']))
        docs=documents([n(0,slide='shift',hp=True),n(2)])
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['duration']=[1,1]
        bad=build(extract_documents(docs));slide=next(e for e in bad['edges']if e['kind']=='slide')
        self.assertEqual(slide['status'],'excluded_for_timing');self.assertIsNone(slide['semantics']['destination'])
        self.assertIsNotNone(slide['semantics']['candidate_destination']);self.assertFalse(slide['semantics']['timing_eligible'])
        self.assertFalse(bad['signature']['parts'][0]['hopo_eligible'])

    def test_rolls_and_ringing_preserve_declaration_without_performed_time(self):
        docs=documents([n(0),n(2),None,None],{0:dict(arpeggio=dict(direction='down',duration=57,shift=100),letRing=True),1:dict(brushStroke={},letRing=False)})
        lower=extract_documents(docs);original=deepcopy(lower);graph=build(lower)
        self.assertEqual(lower,original)
        ring=next(e for e in graph['edges']if e['kind']=='letRing')
        self.assertIsNone(ring['semantics']['performed_end_q'])
        for e in graph['edges']:
            if e['kind']in('arpeggio','brushStroke'):self.assertIsNone(e['semantics']['performed_note_offsets'])
        self.assertEqual(len(graph['signature']['declarations']),4)
        self.assertEqual(len([e for e in graph['edges']if e['kind']=='letRing']),1)

    def test_unrelated_plain_register_change_has_no_fake_held_context_in_signature(self):
        docs=documents([n(0,hp=True),n(2),n(4),n(5)])
        extra=deepcopy(docs['track-0.json']);extra['partId']=1
        extra['measures'][0]['voices'][0]['beats']=[dict(duration=[1,1],notes=[dict(string=0,fret=0,vibrato=True)])]
        docs['track-1.json']=extra;docs['metadata.json']['tracks'].append(dict(name='Other',instrumentId=25))
        before=build(extract_documents(docs))
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][2]['notes'][0]['fret']=16
        after=build(extract_documents(docs));self.assertEqual(before['signature'],after['signature'])

    def test_actual_intervention_cannot_resolve_old_same_fret_hopo(self):
        from connected_tier2 import analyze,strip_lower
        from voicing_register import inventory,intervene,empirical_options
        docs=documents([]);part=docs['track-0.json'];part['measures']=[]
        for i in range(3):
            shift=0 if i==0 else 12
            part['measures'].append(dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,4],notes=[n(shift,**({'hp':True}if i==0 else{}))]),
                dict(duration=[3,4],notes=[dict(string=s,fret=f+shift)for s,f in zip((5,4,3),(0,2,2))])])]))
        lower=extract_documents(docs);catalog=inventory(lower,'incident_dependencies');target=catalog['units'][1]['id']
        self.assertEqual(empirical_options(catalog,target,'incident_dependencies')['status'],'SUPPORTED_EMPIRICAL_ALTERNATIVES')
        with self.assertRaisesRegex(ValueError,'Locked execution dependency semantics changed'):
            intervene(strip_lower(analyze(lower)),dict(voicing=100,register=100,target_ref=target,seed=9427,context_policy='incident_dependencies'))


if __name__=='__main__':unittest.main()

