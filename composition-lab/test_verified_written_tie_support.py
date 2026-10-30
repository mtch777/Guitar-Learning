"""Same written tie relations qualify context; no inferred acoustic sustain."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import context_membership as membership
from check_context_membership import check,expected as independent
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize

TARGET='event:77:0:2:0:0:0'
REQUEST=dict(edited_refs=[TARGET],scope='ensemble_minus_edited')


def documents():
    parts=[]
    for pid,tuning in [(0,[64]),(1,[48,52,55])]:
        measures=[]
        for bar in range(3):
            notes=[dict(string=s,fret=0)for s in range(len(tuning))]
            if pid==1 and bar>0:
                for note in notes:note['tie']=True
            measures.append(dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],type=1,velocity='f',notes=notes)])]))
        parts.append(dict(songId=77,revisionId=3,partId=pid,name=str(pid),instrumentId=25,tuning=tuning,measures=measures))
    return {'metadata.json':dict(songId=77,revisionId=3,tracks=[dict(name=p['name'],instrumentId=25)for p in parts]),
        **{f'track-{p["partId"]}.json':p for p in parts}}


def compile(docs=None,request=REQUEST):
    return membership.compile_lock(extract_documents(documents()if docs is None else docs),request,pitch_support='verified_written_ties')


class VerifiedTieSupportTests(unittest.TestCase):
    def test_default_stays_strict_but_complete_crossbar_tie_supplies_written_pitch(self):
        before=extract_documents(documents())
        self.assertEqual(membership.compile_lock(before,REQUEST)['status'],'MISSING')
        result=compile();self.assertEqual(result['status'],'SUPPORTED',result)
        packet=result['packet'];self.assertEqual(packet['version'],membership.TIED_VERSION)
        self.assertEqual(len(packet['written_tie_support']),3)
        self.assertTrue(all(len(r['occurrence_refs'])==3 for r in packet['written_tie_support']))
        self.assertEqual(membership.verify(before,packet)['status'],'SUPPORTED')
        self.assertEqual(check(before,before,packet)['status'],'PASS_INDEPENDENT_CONTEXT_MEMBERSHIP')

    def test_unknown_source_clock_never_qualifies_ties(self):
        docs=documents();docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]['duration']=[2,1]
        result=compile(docs)
        self.assertEqual(result['status'],'MISSING')
        self.assertEqual(independent(extract_documents(docs),REQUEST,pitch_support='verified_written_ties')['status'],'MISSING')

    def test_origin_deletion_pitch_change_and_time_gap_rejected(self):
        for edit in ('deleted_origin','different_pitch','gap','ambiguous'):
            docs=documents();part=docs['track-1.json'];beats=part['measures'][0]['voices'][0]['beats']
            if edit=='deleted_origin':beats[0]['notes'][0]={'rest':True}
            elif edit=='different_pitch':beats[0]['notes'][0]['fret']=1
            elif edit=='gap':beats[0]['duration']=[1,2]
            else:beats[0]['notes'].append(dict(string=0,fret=0))
            self.assertEqual(compile(docs)['status'],'MISSING',edit)
            self.assertEqual(independent(extract_documents(docs),REQUEST,pitch_support='verified_written_ties')['status'],'MISSING',edit)

    def test_expression_anywhere_in_chain_remains_unresolved(self):
        for bar in (0,1,2):
            for effect in ({'bend':{}},{'dead':True},{'vibrato':True},{'tie':'unknown'}):
                docs=documents();docs['track-1.json']['measures'][bar]['voices'][0]['beats'][0]['notes'][0].update(effect)
                self.assertEqual(compile(docs)['status'],'MISSING',(bar,effect))
                self.assertEqual(independent(extract_documents(docs),REQUEST,pitch_support='verified_written_ties')['status'],'MISSING',(bar,effect))

    def test_unsupported_outgoing_tie_does_not_hide_after_good_chain(self):
        docs=documents();notes=docs['track-1.json']['measures'][2]['voices'][0]['beats'][0]['notes']
        notes[0]['fret']=1
        self.assertEqual(compile(docs)['status'],'MISSING')

    def test_non_pitch_execution_and_unknown_declarations_on_origin_stay_refused(self):
        for field,at_beat in [('hp',False),('ghost',False),('newTechnique',False),('palmMute',True),('letRing',True),('brushStroke',True)]:
            docs=documents();beat=docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]
            (beat if at_beat else beat['notes'][0])[field]=True
            self.assertEqual(compile(docs)['status'],'MISSING',field)
            self.assertEqual(independent(extract_documents(docs),REQUEST,pitch_support='verified_written_ties')['status'],'MISSING',field)

    def test_selected_origin_or_destination_cannot_use_its_own_chain_as_support(self):
        for bar in (1,2,3):
            req=dict(REQUEST,edited_refs=[f'event:77:1:{bar}:0:0:0'])
            result=compile(request=req)
            self.assertEqual(result['status'],'MISSING')
            self.assertIn('EDITED_NOTE_IN_TIE_CHAIN',result['reasons'])

    def test_stale_or_omitted_origin_witness_fails_same_inverse_check(self):
        before=extract_documents(documents());packet=compile()['packet']
        missing=deepcopy(packet);missing['written_tie_support'].pop()
        self.assertEqual(membership.assess(before,missing)['status'],'MISSING')
        wrong=deepcopy(packet);wrong['written_tie_support'][0]['origin_ref']='madeup'
        with self.assertRaises(ValueError):membership.assess(before,wrong)
        extra=deepcopy(packet);extra['written_tie_support'][0]['original_pitch']=48
        with self.assertRaises(ValueError):membership.assess(before,extra)

    def test_missing_unknown_or_wrong_mode_is_not_accepted(self):
        before=extract_documents(documents())
        with self.assertRaises(ValueError):membership.compile_lock(before,REQUEST,pitch_support='guess_ties')
        packet=compile()['packet'];packet.pop('pitch_support')
        with self.assertRaises(ValueError):membership.assess(before,packet)

    def test_changed_source_invalidates_stored_chain_support(self):
        packet=compile()['packet'];docs=documents()
        docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret']=1
        self.assertEqual(membership.assess(extract_documents(docs),packet)['status'],'MISSING')

    def test_actual_isolated_inverse_rechecks_versioned_support(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before=extract_documents(documents());upper=membership.attach(strip_lower(analyze(before)),REQUEST,pitch_support='verified_written_ties')
        self.assertEqual(realize(upper),before)
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as folder:
            result=execute(code,upper,dict(variation=0),before,Path(folder)/'worker',timeout=45)
            self.assertEqual(result['status'],'PASS',result)


if __name__=='__main__':unittest.main()
