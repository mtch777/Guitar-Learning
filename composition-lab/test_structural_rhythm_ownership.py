"""Written timing can be known while a rhythm change remains inadmissible."""
from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize,validate
from test_group_rhythm_relations import documents
from test_local_lever_combinations import documents as combination_documents,changed_seed,control,INSIDE
from group_rhythm_relations import SCHEMA,STRUCTURAL_SCHEMA
from source_rhythm_groups import timing_owner_reasons
import local_accents as accents
import local_group_rhythm as rhythm


class StructuralTimingTests(unittest.TestCase):
    def test_markings_and_different_pitches_have_time_without_change_permission(self):
        for kind in ('accent','palm','different_pitch','dynamic_boundary'):
            with self.subTest(kind=kind):
                docs=documents();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
                if kind=='accent':beats[0]['notes'][0]['accentuated']=1
                elif kind=='palm':beats[0]['palmMute']=True
                elif kind=='different_pitch':beats[1]['notes'][0]['fret']+=2
                else:beats[1]['velocity']='mf'
                before=extract_documents(docs)
                legacy=strip_lower(analyze(before,rhythm_groups=True))
                current=strip_lower(analyze(before,rhythm_groups=True,rhythm_group_profile='written_time'))
                self.assertEqual(legacy['musical_relationships']['schema'],SCHEMA)
                self.assertEqual(current['musical_relationships']['schema'],STRUCTURAL_SCHEMA)
                group=current['musical_relationships']['groups'][0]
                self.assertEqual(group['bar'],1)
                self.assertNotIn(group['id'],[g['id']for g in legacy['musical_relationships']['groups']])
                self.assertEqual(validate(current),before)
                self.assertEqual(validate(legacy),before)
                evidence=rhythm.options(before,group['id'])
                self.assertEqual(evidence['status'],'UNSUPPORTED_GROUP')
                self.assertEqual(evidence['options'],[])

    def test_actual_accent_preserves_time_owner_but_later_rhythm_stays_refused(self):
        before=extract_documents(combination_documents())
        upper=strip_lower(analyze(before,note_accent_slots=True,rhythm_groups=True,rhythm_group_profile='written_time'))
        evidence=accents.options(before,INSIDE)
        seed=changed_seed(accents,evidence,'accents',INSIDE,predicate=lambda c:c['sound_level']==1)
        changed,decision=accents.intervene(upper,control(accents,'accents',INSIDE,seed=seed))
        self.assertTrue(decision['changed'])
        self.assertEqual(changed['musical_relationships'],upper['musical_relationships'])
        actual=validate(changed);expected=deepcopy(combination_documents())
        expected['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['accentuated']=1
        self.assertEqual(project_documents(actual),expected)
        group=upper['musical_relationships']['groups'][0]
        refused,reason=rhythm.intervene(changed,control(rhythm,'rhythm',group['id']))
        self.assertFalse(reason['changed'])
        self.assertEqual(reason['evidence']['status'],'UNSUPPORTED_GROUP')
        self.assertEqual(refused,changed)

    def test_unknown_or_invalid_clock_is_never_reclassified_as_safe(self):
        self.assertEqual(timing_owner_reasons({'reasons':['ACCENT_DECLARATION','NEW_CLOCK_FAILURE']}),['NEW_CLOCK_FAILURE'])
        docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['dots']=1
        before=extract_documents(docs)
        model=strip_lower(analyze(before,rhythm_groups=True,rhythm_group_profile='written_time'))
        self.assertFalse(any(g['bar']==1 for g in model['musical_relationships']['groups']))
        bad=deepcopy(model);bad['musical_relationships']['schema']='source-group-rhythm/999'
        with self.assertRaises((ValueError,KeyError)):realize(bad)

    def test_profiles_are_explicit_and_legacy_is_default(self):
        before=extract_documents(documents())
        with self.assertRaises(ValueError):analyze(before,rhythm_group_profile='written_time')
        with self.assertRaises(ValueError):analyze(before,rhythm_groups=True,rhythm_group_profile='invented')
        self.assertEqual(strip_lower(analyze(before,rhythm_groups=True))['musical_relationships']['schema'],SCHEMA)


if __name__=='__main__':unittest.main()
