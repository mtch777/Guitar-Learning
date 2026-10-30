"""Authored musical contrasts; not real-song or listening acceptance."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize
import melodic_contour_choices as choice
import melodic_contour_intervention as edit

TARGET='event:77:0:2:0:1:0'


def documents():
    def note(fret,duration):
        return dict(type=4 if duration==[1,4]else 2,duration=duration,notes=[dict(string=0,fret=fret)])
    melody=[];harmony=[]
    for i in range(9):
        middle=7 if i==4 else 4
        beats=[note(0,[1,4]),note(middle,[1,2]),note(12,[1,4])]
        beats[0]['velocity']='f'
        melody.append(dict(signature=[4,4],voices=[dict(beats=beats)]))
        harmony.append(dict(signature=[4,4],voices=[dict(beats=[dict(type=1,duration=[1,1],velocity='f',notes=[dict(string=s,fret=0)for s in range(3)])])]))
    parts=[dict(songId=77,revisionId=3,partId=0,name='Single string',instrumentId=25,tuning=[60],measures=melody),
        dict(songId=77,revisionId=3,partId=1,name='Written chords',instrumentId=25,tuning=[48,52,55],measures=harmony)]
    return {'metadata.json':dict(songId=77,revisionId=3,artist='Authored contrast',title='Middle note',tracks=[dict(name=p['name'],instrumentId=p['instrumentId'])for p in parts]),
        **{f'track-{p["partId"]}.json':p for p in parts}}


def model(docs=None,**kwargs):
    before=extract_documents(documents()if docs is None else docs)
    return before,strip_lower(analyze(before,**kwargs))


class MelodicContourTests(unittest.TestCase):
    def test_both_directions_include_repeated_notes(self):
        self.assertEqual(choice.contour(['60','64','72']),[1,1])
        self.assertEqual(choice.contour(['60','64','60']),[1,-1])
        self.assertEqual(choice.contour(['60','60','60']),[0,0])
        self.assertEqual(choice.contour(['60','60','59']),[0,-1])

    def test_complete_neighborhoods_and_disjoint_source_witnesses(self):
        before,_=model();view=choice.inventory(before)
        self.assertEqual(len(view['neighborhoods']),32)  # 27 melody +9 chord beats, minus two ends each
        evidence=choice.source_options(view,TARGET)
        self.assertEqual(evidence['status'],'INDEPENDENT_MELODIC_ALTERNATIVES')
        self.assertEqual({r['pitch']for r in evidence['options']},{'64','67'})
        byid={r['target_ref']:r for r in view['neighborhoods']}
        for ref in evidence['witness_pair']:
            self.assertFalse(set(byid[ref]['closure_refs'])&set(evidence['target']['closure_refs']))
        a,b=map(byid.get,evidence['witness_pair'])
        self.assertFalse(set(a['closure_refs'])&set(b['closure_refs']))

    def test_real_operation_uses_existing_owner_and_preserves_whole_source(self):
        before,upper=model();c=edit.prepare(upper);evidence=edit.options(upper,TARGET,c)
        self.assertEqual(evidence['status'],'SOURCE_SUPPORTED_MELODIC_CHOICES',evidence)
        selected=next(o for o in evidence['options']if o['changed'])
        after=realize(edit.apply_pitch(upper,TARGET,selected['pitch']))
        diffs=[(a['id'],a.get('value'),b.get('value'))for a,b in zip(before['facts'],after['facts'])if a!=b]
        self.assertEqual(diffs,[('track-0.json#/measures/1/voices/0/beats/1/notes/0/fret',4,7)])
        self.assertNotIn('original_pitch',str(upper))
        from check_melodic_contour_change import check
        verdict=check(before,after,evidence['target'],selected,edit.packet(c,TARGET)['packet'])
        self.assertEqual(verdict['status'],'PASS_INDEPENDENT_MIDDLE_NOTE_CHANGE',verdict)
        corrupted=deepcopy(after)
        next(r for r in corrupted['facts']if r['id']=='track-0.json#/measures/1/voices/0/beats/1/notes/0/fret')['value']=8
        self.assertEqual(check(before,corrupted,evidence['target'],selected,edit.packet(c,TARGET)['packet'])['status'],'FAIL')

    def test_zero_is_exact_and_release_is_not_forced_difference(self):
        before,upper=model();changed,report=edit.intervene(upper,dict(context_policy=choice.POLICY,melody=0,target_ref=TARGET,seed=1))
        self.assertEqual(changed,upper);self.assertEqual(realize(changed),before)
        evidence=dict(options=[dict(pitch='64',donor_refs=['a'],changed=False),dict(pitch='67',donor_refs=['b'],changed=True)])
        for amount in (0,50,100):
            reports=[choice.sample(evidence,dict(context_policy=choice.POLICY,melody=amount,target_ref=TARGET,seed=s))[1]for s in range(512)]
            if amount==0:self.assertFalse(any(r['released']or r['changed']for r in reports))
            elif amount==100:
                self.assertTrue(all(r['released']for r in reports));self.assertTrue(any(not r['changed']for r in reports))
            else:self.assertTrue(200<sum(r['released']for r in reports)<312)

    def test_changed_chord_membership_cannot_be_called_same_role(self):
        docs=documents()
        # D is not a C-major chord member; E and G are. No scale-fitting escape.
        docs['track-0.json']['measures'][4]['voices'][0]['beats'][1]['notes'][0]['fret']=2
        _,upper=model(docs);result=edit.options(upper,TARGET)
        self.assertEqual(result['status'],'NO_INDEPENDENT_MATCHED_HARMONY_CHOICES')
        self.assertTrue(any(r['reason']=='DONOR_HARMONIC_RELATIONSHIP_DIFFERS'for r in result['rejected']))

    def test_missing_harmony_is_not_permission(self):
        docs=documents();docs.pop('track-1.json');docs['metadata.json']['tracks'].pop()
        _,upper=model(docs);result=edit.options(upper,TARGET)
        self.assertEqual(result['status'],'MISSING_SURROUNDING_HARMONY')

    def test_full_duration_includes_later_chord_changes(self):
        docs=documents();part=docs['track-1.json'];part['tuning']=[48,52,55,59,62]
        part['measures'][1]['voices'][0]['beats']=[
            dict(duration=[1,2],type=2,velocity='f',notes=[dict(string=s,fret=0)for s in (0,1,2)]),
            dict(duration=[1,2],type=2,notes=[dict(string=s,fret=0)for s in (2,3,4)])]
        _,upper=model(docs);c=edit.prepare(upper);bound=edit.packet(c,TARGET)
        self.assertEqual(bound['status'],'SUPPORTED')
        self.assertGreater(len(bound['packet']['contexts']),1)
        self.assertEqual(edit.options(upper,TARGET,c)['status'],'NO_INDEPENDENT_MATCHED_HARMONY_CHOICES')

    def test_unknown_and_linked_execution_refused(self):
        for extra in ({'bend':{}},{'harmonicFret':0},{'slide':[]},{'newEffect':True},{'hp':True}):
            docs=documents();docs['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0].update(extra)
            view=choice.inventory(extract_documents(docs));row=next(r for r in view['neighborhoods']if r['target_ref']==TARGET)
            self.assertTrue(row['reasons'],extra);self.assertIsNone(row['context_key'])

    def test_changing_contour_or_timing_removes_donor(self):
        for change in ('direction','duration','string'):
            docs=documents();b=docs['track-0.json']['measures'][4]['voices'][0]['beats'][1]
            if change=='direction':b['notes'][0]['fret']=15
            elif change=='duration':b['duration']=[1,4]
            else:b['notes'][0]['string']=1;docs['track-0.json']['tuning'].append(60)
            row=choice.source_options(choice.inventory(extract_documents(docs)),TARGET)
            self.assertEqual(row['options'],[],change)

    def test_effect_or_outside_fret_change_fails_complete_output_guard(self):
        before,upper=model();c=edit.prepare(upper);evidence=edit.options(upper,TARGET,c)
        donor=next(r for r in c['inventory']['neighborhoods']if r['target_ref']=='event:77:0:5:0:1:0')
        after=realize(edit.apply_pitch(upper,TARGET,'67'))
        corrupt=deepcopy(after)
        next(r for r in corrupt['facts']if r['id']=='track-0.json#/measures/0/voices/0/beats/0/notes/0/fret')['value']=1
        with self.assertRaisesRegex(ValueError,'Locked source fact changed'):
            edit.verify(before,corrupt,evidence['target'],donor,edit.packet(c,TARGET)['packet'])

    def test_degree_and_family_wrappers_keep_their_original_validation(self):
        for kwargs in ({'families':True},{'declared_chords':True},{'note_accent_slots':True}):
            before,upper=model(**kwargs);out=edit.apply_pitch(upper,TARGET,'67')
            self.assertEqual(project_documents(realize(out))['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]['fret'],7)
            self.assertEqual(realize(upper),before)

    def test_unknown_wrapper_is_not_silently_bypassed(self):
        _,upper=model();upper['musical_relationships']=dict(schema='unregistered',core=upper['musical_relationships'])
        with self.assertRaisesRegex(ValueError,'Unsupported musical owner'):edit.apply_pitch(upper,TARGET,'67')

    def test_rhythm_owner_composes_without_storing_a_second_timing_answer(self):
        from test_group_rhythm_relations import documents as rhythm_documents
        before,upper=model(rhythm_documents(),rhythm_groups=True)
        original=deepcopy(upper['musical_relationships']['groups'])
        edited=edit.apply_pitch(upper,'event:77:0:1:0:3:0','47')
        self.assertEqual(edited['musical_relationships']['groups'],original)
        actual=project_documents(realize(edited))
        self.assertEqual(actual['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['fret'],7)
        for schema in ({'families':True},{'declared_chords':True}):
            _,upper=model(rhythm_documents(),rhythm_groups=True,**schema)
            self.assertEqual(project_documents(realize(edit.apply_pitch(upper,'event:77:0:1:0:3:0','47'))),actual)
        # A proposed pitch edit cannot secretly invalidate a locked repeated-note group.
        with self.assertRaises(ValueError):realize(edit.apply_pitch(upper,'event:77:0:1:0:1:0','47'))
        # Structural time ownership remains valid when an independent pitch
        # relationship changes; admission of any rhythm edit is still separate.
        _,upper=model(rhythm_documents(),rhythm_groups=True,rhythm_group_profile='written_time')
        original=deepcopy(upper['musical_relationships']['groups'])
        changed=edit.apply_pitch(upper,'event:77:0:1:0:1:0','47')
        self.assertEqual(changed['musical_relationships']['schema'],'source-group-rhythm/2')
        self.assertEqual(changed['musical_relationships']['groups'],original)
        self.assertEqual(project_documents(realize(changed))['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['fret'],7)

    def test_actual_isolated_zero_and_changed_inverse(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before,upper=model();code,_=bundle(Path(__file__).parent)
        expected=realize(edit.apply_pitch(upper,TARGET,'67'))
        with tempfile.TemporaryDirectory()as folder:
            for name,value,answer in [('zero',upper,before),('changed',edit.apply_pitch(upper,TARGET,'67'),expected)]:
                receipt=execute(code,value,dict(variation=0),answer,Path(folder)/name,timeout=45)
                self.assertEqual(receipt['status'],'PASS',receipt)

    def test_isolated_actual_percentage_policy_selects_from_source(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before,upper=model();code,_=bundle(Path(__file__).parent)
        changed_docs=documents();changed_docs['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]['fret']=7
        expected=extract_documents(changed_docs)
        with tempfile.TemporaryDirectory()as folder:
            for amount in(0,50,100):
                control=dict(context_policy=choice.POLICY,melody=amount,target_ref=TARGET,seed=5)
                result=execute(code,upper,control,expected if amount==100 else before,Path(folder)/str(amount),timeout=45,purpose='local_melodic_contour_intervention')
                self.assertEqual(result['status'],'PASS',result)


if __name__=='__main__':unittest.main()
