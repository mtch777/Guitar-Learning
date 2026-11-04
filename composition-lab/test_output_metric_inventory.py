"""Measurement denominators survive ties, percussion and unknown expression."""
from copy import deepcopy
import unittest

from output_metric_inventory import inventory,accent_value,PITCH_FEATURES,SCHEMA
from output_change_targets import freeze_targets,evaluate_targets
from source_fact_tier1 import extract_documents
from test_execution_dependencies import documents,n


class OutputMetricInventoryTests(unittest.TestCase):
    def test_tied_notes_are_one_attack_with_retained_members(self):
        docs=documents([n(0),n(0,tie=True),n(2),n(4)],{0:dict(velocity='f')})
        lower=extract_documents(docs);saved=deepcopy(lower);result=inventory(lower)
        self.assertEqual(result['counts']['written_occurrences'],4)
        self.assertEqual(result['counts']['attack_units'],3)
        self.assertEqual(result['counts']['tied_continuations'],1)
        root='event:86:0:1:0:0:0'
        self.assertEqual(result['attacks'][root]['member_refs'],[root,'event:86:0:1:0:1:0'])
        self.assertEqual(result['features']['attack_written_span_q'][root],'2')
        self.assertEqual(lower,saved)

    def test_percussion_has_timing_and_expression_but_no_melodic_pitch_unit(self):
        docs=documents([n(0),n(2),n(4),n(5)],{0:dict(velocity='f')})
        drum=deepcopy(docs['track-0.json']);drum.update(partId=1,instrumentId=1024,tuning=[])
        for beat in drum['measures'][0]['voices'][0]['beats']:beat['notes']=[dict(fret=38)]
        docs['track-1.json']=drum;docs['metadata.json']['tracks'].append(dict(name='Drums',instrumentId=1024))
        result=inventory(extract_documents(docs))
        self.assertEqual(result['counts']['percussion_attacks'],4)
        self.assertEqual(len(result['features']['attack_onset_q']),8)
        self.assertEqual(len(result['features']['pitched_attack_octave']),4)

    def test_unknown_accent_keeps_its_unit_and_cannot_pass_even_zero(self):
        docs=documents([n(0,accentuated='unknown'),n(2),n(4),n(5)],{0:dict(velocity='mf')})
        result=inventory(extract_documents(docs));values={'accent':result['features']['attack_accent']}
        self.assertEqual(len(values['accent']),4)
        self.assertEqual(result['counts']['unknown_accent_units'],1)
        self.assertFalse(evaluate_targets(freeze_targets(values,{'accent':0}),values)['satisfied'])
        self.assertEqual(accent_value({}),accent_value({'accentuated':False}))
        self.assertEqual(accent_value({}),accent_value({'accentuated':0}))

    def test_complete_coattack_is_one_mute_unit_but_two_pitch_units(self):
        docs=documents([n(0),n(2),n(4),n(5)],{0:dict(velocity='f',palmMute=True)})
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'].append(dict(string=4,fret=0))
        result=inventory(extract_documents(docs))
        self.assertEqual(len(result['features']['pitched_attack_pitch']),5)
        self.assertEqual(len(result['features']['guitar_bass_coattack_mute']),4)
        first=next(row for row in result['coattacks'].values()if row['onset_q']=='0')
        self.assertEqual(len(first['attack_refs']),2)

    def test_unresolved_tie_is_unknown_not_dropped_or_counted_as_clean_attack(self):
        docs=documents([n(0,tie=True),n(2),n(4),n(5)],{0:dict(velocity='f')})
        result=inventory(extract_documents(docs));root='event:86:0:1:0:0:0'
        self.assertEqual(result['counts']['unresolved_ties'],1)
        self.assertEqual(result['counts']['attack_units'],4)
        self.assertIsNone(result['features']['pitched_attack_pitch'][root])
        self.assertIsNone(result['features']['attack_onset_q'][root])

    def test_explicit_dead_member_excludes_only_fundamental_pitch_metrics(self):
        docs=documents([n(0),n(2),n(4),n(5)],{0:dict(velocity='f',palmMute=True)})
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'].append(
            dict(string=4,fret=3,dead=True,accentuated=1))
        lower=extract_documents(docs);before=deepcopy(lower);result=inventory(lower)
        dead='event:86:0:1:0:0:1'
        self.assertEqual(result['schema'],SCHEMA)
        self.assertNotEqual(result['schema'],'actual-output-unit-inventory/1')
        self.assertIsNone(result['notes'][dead]['pitch'])
        for feature in PITCH_FEATURES:
            self.assertEqual(len(result['features'][feature]),4)
            self.assertNotIn(dead,result['features'][feature])
        for feature in ('attack_onset_q','attack_written_span_q','attack_base_dynamic',
                        'attack_accent','guitar_bass_contact'):
            self.assertIn(dead,result['features'][feature])
            self.assertEqual(len(result['features'][feature]),5)
        self.assertEqual(result['features']['guitar_bass_contact'][dead],[[4,3]])
        self.assertEqual(result['features']['attack_accent'][dead],1)
        self.assertTrue(result['notes'][dead]['dead'])
        group=next(row for row in result['coattacks'].values()if row['onset_q']=='0')
        self.assertIn(dead,group['attack_refs'])
        self.assertEqual(result['counts']['explicit_dead_pitch_exclusions'],1)
        self.assertEqual(result['counts']['contact_metric_units'],5)
        classification=result['pitch_unit_classification'][dead]
        self.assertFalse(classification['included'])
        self.assertEqual(classification['reason'],'explicit_dead_note_has_no_fundamental_pitch_unit')
        self.assertEqual(classification['explicit_dead_fact_refs'],[
            'track-0.json#/measures/0/voices/0/beats/0/notes/1/dead'])
        self.assertEqual(lower,before)

    def test_unknown_normal_and_harmonic_pitches_remain_counted(self):
        for additional in ({},{'harmonic':dict(type='natural')},{'dead':False}):
            with self.subTest(additional=additional):
                docs=documents([dict(string=5,**additional),n(2),n(4),n(5)])
                result=inventory(extract_documents(docs));root='event:86:0:1:0:0:0'
                for feature in PITCH_FEATURES:
                    self.assertIn(root,result['features'][feature])
                    self.assertIsNone(result['features'][feature][root])
                    self.assertEqual(len(result['features'][feature]),4)
                self.assertTrue(result['pitch_unit_classification'][root]['included'])
                self.assertEqual(result['pitch_unit_classification'][root]['reason'],
                                 'unknown_fundamental_pitch_remains_a_unit')
                self.assertEqual(result['counts']['unknown_pitched_metric_units'],1)
                self.assertEqual(result['counts']['explicit_dead_pitch_exclusions'],0)

    def test_malformed_dead_declaration_is_not_coerced_to_a_pitch_exclusion(self):
        lower=extract_documents(documents([n(0,dead='true'),n(2),n(4),n(5)]))
        with self.assertRaisesRegex(ValueError,'Unsupported dead declaration'):inventory(lower)

    def test_unresolved_dead_tie_stays_an_unknown_timing_and_contact_unit(self):
        result=inventory(extract_documents(documents([n(0,dead=True,tie=True),n(2),n(4),n(5)])))
        root='event:86:0:1:0:0:0'
        for feature in PITCH_FEATURES:self.assertNotIn(root,result['features'][feature])
        self.assertIn(root,result['features']['attack_onset_q'])
        self.assertIsNone(result['features']['attack_onset_q'][root])
        self.assertIn(root,result['features']['guitar_bass_contact'])
        self.assertIsNone(result['features']['guitar_bass_contact'][root])
        self.assertEqual(result['counts']['attack_units'],4)

    def test_dead_without_fret_preserves_known_string_changes_and_unknown_fret(self):
        result=inventory(extract_documents(documents([dict(string=5,dead=True),n(2),n(4),n(5)])))
        root='event:86:0:1:0:0:0'
        self.assertNotIn(root,result['features']['pitched_attack_pitch'])
        self.assertIn(root,result['features']['guitar_bass_contact'])
        self.assertEqual(result['features']['guitar_bass_contact'][root],[[5,None]])
        self.assertEqual(result['counts']['contact_metric_units'],4)
        changed=inventory(extract_documents(documents([dict(string=4,dead=True),n(2),n(4),n(5)])))
        self.assertEqual(changed['features']['guitar_bass_contact'][root],[[4,None]])
        self.assertEqual(result['features']['guitar_bass_contact'].keys(),changed['features']['guitar_bass_contact'].keys())
        self.assertNotEqual(result['features']['guitar_bass_contact'][root],changed['features']['guitar_bass_contact'][root])

    def test_unknown_pitched_fret_does_not_gain_dead_note_contact_semantics(self):
        result=inventory(extract_documents(documents([dict(string=5),n(2),n(4),n(5)])))
        self.assertIsNone(result['features']['guitar_bass_contact']['event:86:0:1:0:0:0'])


if __name__=='__main__':unittest.main()
