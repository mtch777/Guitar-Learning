"""Independent time-link audit across existing ownership wrappers; synthetic data."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import backing_pitch_ownership as backing
from check_technique_connections import check
from connected_tier2 import analyze
from source_fact_tier1 import extract_documents
from test_group_rhythm_relations import documents as rhythm_documents


def documents():
    docs = rhythm_documents()
    docs['track-0.json']['tuning'] = [40, 45, 50]
    for measure in docs['track-0.json']['measures']:
        beat = measure['voices'][0]['beats'][3]
        beat['notes'] = [dict(string=0, fret=8), dict(string=1, fret=7), dict(string=2, fret=5)]
        beat['chord'] = dict(text='C')
    docs['metadata.json']['tracks'].append(dict(name='Backing', instrumentId=25))
    docs['track-1.json'] = dict(songId=77, revisionId=3, partId=1, name='Backing', instrumentId=25,
        tuning=[36], measures=[dict(signature=[4, 4], voices=[dict(beats=[dict(duration=[1, 1],
            notes=[dict(string=0, fret=0)])])]) for _ in range(3)])
    return docs


def case(*, rhythm=False, profile='plain_repeat', mode=None, backing_version=None):
    docs = documents()
    lower = extract_documents(docs)
    flags = {mode: True} if mode else {}
    upper = analyze(lower, rhythm_groups=rhythm,
                    rhythm_group_profile=profile if rhythm else 'plain_repeat', **flags)
    upper.pop('input')
    if backing_version is not None:
        upper['musical_relationships'] = backing.lift(upper['musical_relationships'],
            [dict(occurrence_ref='event:77:0:1:0:0:0', backing_ref='event:77:1:1:0:0:0')],
            tier1=lower, preserve_execution=backing_version == 3)
        if backing_version == 1:
            upper['musical_relationships']['schema'] = backing.LEGACY_SCHEMA
            del upper['musical_relationships']['written_tie_constraints']
    return docs, upper


class TechniqueWrapperTests(unittest.TestCase):
    def test_muted_figure_reads_time_owners_without_solving_pitch(self):
        from test_muted_figure_register import fixture
        docs, _, _, full = fixture()
        with patch('figure_register_ownership.expand', side_effect=AssertionError('Producer figure inverse called')):
            self.assert_pass_without_inverse(docs, full)
            changed = deepcopy(full)
            # The register wrapper owns no time; its original time owner must
            # still be audited against source rather than trusted through it.
            rhythm = changed['musical_relationships']['core']['core']
            self.assertEqual(rhythm['schema'], 'source-group-rhythm/2')
            self.assertEqual(rhythm['groups'], [])
            rhythm['pitch_relationships']['coattacks'][0]['onset_q'] = '1/4'
            self.assertEqual(check(docs, changed)['status'], 'FAIL')

    def assert_pass_without_inverse(self, docs, upper):
        original = deepcopy(upper)
        with patch('group_rhythm_relations.expand', side_effect=AssertionError('Producer rhythm inverse called')), \
             patch('voicing_families.realize', side_effect=AssertionError('Producer family inverse called')), \
             patch('backing_pitch_ownership.expand', side_effect=AssertionError('Producer backing inverse called')):
            result = check(docs, upper)
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['status'], 'PASS_SOURCE_BACKED_RELATIONSHIPS')
        self.assertEqual(upper, original)

    def test_plain_and_nonempty_family_and_degree_owners(self):
        for mode in (None, 'families', 'declared_chords'):
            with self.subTest(mode=mode):
                docs, upper = case(mode=mode)
                if mode:
                    groups = upper['musical_relationships']['core']['coattacks']
                    key = 'spacing_ref' if mode == 'families' else 'declared_chord_ref'
                    self.assertTrue(any(key in row for row in groups))
                self.assert_pass_without_inverse(docs, upper)

    def test_both_rhythm_versions_with_existing_pitch_wrappers(self):
        for profile in ('plain_repeat', 'written_time'):
            for mode in (None, 'families', 'declared_chords'):
                with self.subTest(profile=profile, mode=mode):
                    docs, upper = case(rhythm=True, profile=profile, mode=mode)
                    self.assertEqual(len(upper['musical_relationships']['groups']), 3)
                    self.assert_pass_without_inverse(docs, upper)

    def test_backing_versions_over_plain_and_structural_rhythm(self):
        for version in (1, 2, 3):
            for owned_time in (False, True):
                with self.subTest(version=version, owned_time=owned_time):
                    docs, upper = case(rhythm=owned_time, profile='written_time', backing_version=version)
                    self.assert_pass_without_inverse(docs, upper)

    def test_changed_start_span_or_valid_share_permutation_fails_source_time_check(self):
        docs, original = case(rhythm=True, profile='written_time')
        for field, value in (('start_q', '1/4'), ('span_q', '2'), ('shares', ['1/4', '1/4', '1/2'])):
            with self.subTest(field=field):
                upper = deepcopy(original)
                upper['musical_relationships']['groups'][0][field] = value
                result = check(docs, upper)
                self.assertEqual(result['status'], 'FAIL')
                self.assertTrue(any('source/time link differs' in x for x in result['issues']))

    def test_invalid_shares_and_missing_or_duplicate_owners_fail(self):
        docs, original = case(rhythm=True, profile='written_time', backing_version=3)
        for kind in ('sum', 'zero', 'typed', 'missing', 'duplicate', 'short', 'wrong_ref', 'wrong_coattack'):
            with self.subTest(kind=kind):
                upper = deepcopy(original); model = upper['musical_relationships']['core']; group = model['groups'][0]
                if kind == 'sum': group['shares'] = ['1/3', '1/3', '1/4']
                elif kind == 'zero': group['shares'] = ['0', '1/2', '1/2']
                elif kind == 'typed': group['start_q'] = 0
                elif kind == 'missing': model['groups'].pop(0)
                elif kind == 'duplicate': model['groups'].append(deepcopy(group))
                elif kind == 'short': group['members'].pop()
                elif kind == 'wrong_ref': group['members'][0]['occurrence_ref'] = 'absent'
                else: group['members'][0]['coattack_ref'] = 'wrong'
                self.assertEqual(check(docs, upper)['status'], 'FAIL')

    def test_duplicate_original_time_cannot_override_group_parameters(self):
        docs, upper = case(rhythm=True, profile='written_time')
        model = upper['musical_relationships']; member = model['groups'][0]['members'][0]
        group = next(x for x in model['pitch_relationships']['coattacks'] if x['id'] == member['coattack_ref'])
        group['onset_q'] = '0'; group['members'][0]['duration_q'] = '1/2'
        self.assertEqual(check(docs, upper)['status'], 'FAIL')

    def test_unknown_wrapper_returns_failed_audit(self):
        docs, upper = case()
        upper['musical_relationships'] = dict(schema='unknown-owner/1', core=upper['musical_relationships'])
        self.assertEqual(check(docs, upper)['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
