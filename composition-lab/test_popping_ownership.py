"""Popping is preserved notation, not a reconstructed attack or a new lever."""
from copy import deepcopy
import itertools
from pathlib import Path
import tempfile
import unittest

from test_execution_dependencies import documents, n
from source_fact_tier1 import extract_documents, project_documents
from connected_tier2 import analyze, strip_lower, realize
from execution_dependencies import build
from check_execution_dependencies import expected, check
from voicing_register import effect_reasons


REF = 'event:86:0:1:0:0:0'
FIELD = 'track-0.json#/measures/0/voices/0/beats/0/popping'


def fixture(**flags):
    docs = documents([n(0), n(2), n(2), n(5)], {0: dict(velocity='f', **flags)})
    beats = docs['track-0.json']['measures'][0]['voices'][0]['beats']
    for beat in beats:
        beat['type'] = 4
    return docs


class PoppingOwnershipTests(unittest.TestCase):
    def test_absent_false_true_have_distinct_exact_owners(self):
        for present, value in ((False, None), (True, False), (True, True)):
            with self.subTest(present=present, value=value):
                docs = fixture(**({'popping': value} if present else {}))
                beat = docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]
                beat['notes'].append(dict(string=4, fret=2))
                lower = extract_documents(docs)
                # Tier1 already preserves this field before connected ownership.
                self.assertEqual(project_documents(lower), docs)
                saved = deepcopy(lower)
                upper = strip_lower(analyze(lower))
                self.assertEqual(lower, saved)
                self.assertFalse(upper['unsupported'])
                self.assertEqual(realize(upper), lower)
                self.assertEqual(project_documents(realize(upper)), docs)
                owners = [r for r in upper['owned_parameters']['source_choices'] if r['fact_ref'] == FIELD]
                self.assertEqual(len(owners), int(present))
                if owners:
                    self.assertEqual(owners[0]['owner'], 'source_beat_execution_declaration')
                    restored = next(r for r in realize(upper)['facts'] if r['id'] == FIELD)
                    self.assertEqual(restored['type'], 'boolean')
                    self.assertIs(restored['value'], value)
                graph = build(lower)
                self.assertEqual(graph, expected(lower))
                self.assertEqual(graph['pinned_members'], [REF, 'event:86:0:1:0:0:1'] if value is True else [])
                self.assertEqual('BEAT_DEPENDENCY:popping' in effect_reasons(beat, beat['notes'][0]), value is True)
                if value is True:
                    self.assertEqual(graph['edges'][0]['status'], 'declaration_only_unknown_attack_execution')
                    self.assertIsNone(graph['edges'][0]['semantics']['performed_attack'])

    def test_nonboolean_popping_remains_unowned_and_refused(self):
        for value in (None, 0, 1, 1.0, 'true', [], {}):
            with self.subTest(value=value):
                docs = fixture(popping=value)
                lower = extract_documents(docs)
                self.assertEqual(project_documents(lower), docs)
                upper = strip_lower(analyze(lower))
                self.assertTrue(upper['unsupported'])
                saved = deepcopy(upper)
                with self.assertRaises(ValueError):
                    realize(upper)
                self.assertEqual(upper, saved)

    def test_missing_duplicate_or_wrong_type_owner_cannot_reconstruct(self):
        upper = strip_lower(analyze(extract_documents(fixture(popping=True))))
        for damage in ('missing', 'duplicate', 'integer'):
            with self.subTest(damage=damage):
                bad = deepcopy(upper)
                choices = bad['owned_parameters']['source_choices']
                row = next(r for r in choices if r['fact_ref'] == FIELD)
                if damage == 'missing':
                    choices.remove(row)
                elif damage == 'duplicate':
                    choices.append(deepcopy(row))
                else:
                    row['parameter'] = {'symbol': 1}
                saved = deepcopy(bad)
                with self.assertRaises(ValueError):
                    realize(bad)
                self.assertEqual(bad, saved)

    def test_all_mixed_attack_flags_are_exact_and_priority_is_unknown(self):
        for values in itertools.product((False, True), repeat=3):
            flags = dict(zip(('slapping', 'tapping', 'popping'), values))
            with self.subTest(flags=flags):
                docs = fixture(**flags)
                docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'].append(dict(string=4, fret=2))
                lower = extract_documents(docs)
                self.assertEqual(realize(strip_lower(analyze(lower))), lower)
                graph = build(lower)
                self.assertEqual(graph, expected(lower))
                active = {key for key, value in flags.items() if value}
                ambiguous = [e for e in graph['edges'] if e['status'] == 'ambiguous_attack_execution']
                self.assertEqual(bool(ambiguous), len(active) > 1)
                for edge in ambiguous:
                    self.assertEqual(set(edge['member_refs']), {REF, 'event:86:0:1:0:0:1'})
                    semantics = edge['semantics']
                    self.assertIsNone(semantics['performed_attack'])
                    self.assertIsNone(semantics['performed_priority'])
                    self.assertEqual(set(semantics['active_attack_declarations']), active)
                    for key, source in semantics['active_attack_declarations'].items():
                        self.assertIs(next(r for r in lower['facts'] if r['id'] == source)['value'], True)
                if ambiguous:
                    corrupted = deepcopy(graph)
                    next(e for e in corrupted['edges'] if e['status'] == 'ambiguous_attack_execution')['semantics']['performed_priority'] = 'slapping'
                    self.assertEqual(check(lower, corrupted)['status'], 'FAIL_INDEPENDENT_EXECUTION_DEPENDENCIES')

    def test_full_beat_scope_refuses_owned_notes_but_not_whole_part(self):
        from backing_execution_constraints import build as execution_scope
        docs = fixture(popping=True)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'].append(dict(string=4, fret=2))
        lower = extract_documents(docs)
        for ref in (REF, 'event:86:0:1:0:0:1'):
            with self.assertRaisesRegex(ValueError, 'UNRESOLVED_AFFECTED_EXECUTION: popping'):
                execution_scope(lower, [ref])
        scope = execution_scope(lower, ['event:86:0:1:0:2:0'])
        self.assertEqual(len(scope['unresolved_outside_neighborhood']), 1)

    def test_neighbor_only_popping_excludes_melody_and_rhythm_edits(self):
        from melodic_contour_choices import inventory as melodies
        from source_rhythm_groups import inventory as rhythms
        docs = fixture(popping=True)
        beats = docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[1]['beamStart'] = True
        beats[2]['beamStop'] = True
        lower = extract_documents(docs)
        row = next(r for r in melodies(lower)['neighborhoods'] if r['target_ref'] == 'event:86:0:1:0:2:0')
        self.assertNotIn('BEAT_EXECUTION_DECLARATION', row['reasons'])
        self.assertIn('NEIGHBOR_BEAT_EXECUTION', row['reasons'])
        self.assertIsNone(row['context_key'])
        group = rhythms(lower)['groups'][0]
        self.assertIn('BOUNDARY_EXECUTION', group['reasons'])
        self.assertNotIn('ACTIVE_BEAT_EXECUTION', group['reasons'])
        # The same effect on a member is a direct execution restriction.
        del beats[0]['popping']
        beats[1]['popping'] = True
        lower = extract_documents(docs)
        row = melodies(lower)['neighborhoods'][0]
        self.assertIn('BEAT_EXECUTION_DECLARATION', row['reasons'])
        self.assertIn('ACTIVE_BEAT_EXECUTION', rhythms(lower)['groups'][0]['reasons'])

    def test_voicing_producer_and_independent_context_refuse_popping(self):
        from check_voicing_policy import _source_units
        from check_voicing_context import _nodes
        from voicing_register import inventory
        docs = fixture(popping=True)
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'].append(dict(string=4, fret=2))
        lower = extract_documents(docs)
        producer = next(u for u in inventory(lower)['units'] if REF in u['member_refs'])
        self.assertIn('BEAT_DEPENDENCY:popping', producer['refusal_reasons'])
        oracle = next(u for u in _source_units(docs)[0] if REF in u['member_refs'])
        self.assertIn('BEAT_DEPENDENCY:popping', oracle['refusal_reasons'])
        nodes = _nodes(lower)[2]
        self.assertIn('BEAT_DEPENDENCY:popping', nodes[REF]['reasons'])

    def test_existing_muted_register_scope_does_not_expand(self):
        from test_muted_figure_register import documents as muted_documents, fixture as muted_fixture
        docs = muted_documents()
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['popping'] = True
        saved = deepcopy(docs)
        with self.assertRaisesRegex(ValueError, 'UNRESOLVED_AFFECTED_EXECUTION'):
            muted_fixture(docs)
        self.assertEqual(docs, saved)

    def test_actual_source_denied_zero_preserves_mixed_declarations(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower = extract_documents(fixture(popping=True, slapping=True, tapping=True))
        upper = strip_lower(analyze(lower, rhythm_groups=True, rhythm_group_profile='written_time'))
        code, _ = bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as temporary:
            result = execute(code, upper, dict(variation=0), lower, Path(temporary) / 'zero', timeout=60)
            self.assertEqual(result['status'], 'PASS', result)


if __name__ == '__main__':
    unittest.main()
