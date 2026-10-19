import copy
import tempfile
import unittest
from pathlib import Path

from sequence_palm_method import source_events, fit, predict, apply
from test_performance_opportunities import report
from test_learned_performance import fixture
from gp_author import write_gp
from exact_score import extract_score
from technique_edits import transact, enable_property


def training():
    data = report()
    for row, flag in zip(data['songs'][0]['tracks'][0]['rows'], (True, True, False, False)):
        row['raw_beat_effects']['palmMute'] = flag
    return data


class SequencePalmTests(unittest.TestCase):
    def test_window_preserves_surroundings_and_starts_without_source_state(self):
        score,_,_=fixture();model=fit(source_events(training(),'Artist'),'Artist')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_gp(score,p/'source.gp')
            audit=apply(p/'source.gp',p/'out.gp',model,'Artist',100,window=(0,2,2))
            self.assertTrue(audit['decisions'])
            self.assertTrue(all(int(o.split(':')[1])==2 for d in audit['decisions'] for o in d['members']))
            self.assertIsNone(audit['decisions'][0]['previous'])
            self.assertEqual(extract_score(p/'source.gp')['tracks'][0]['measures'][0],
                             extract_score(p/'out.gp')['tracks'][0]['measures'][0])
            for bad in ((True,1,2),(0,2,1),(5,1,2),(0,1,9)):
                with self.assertRaises(ValueError):apply(p/'source.gp',p/'bad.gp',model,'Artist',100,window=bad)

    def test_continuity_and_section_gap_overlap_exclusion_resets(self):
        data = training()
        self.assertEqual([e['previous'] for e in source_events(data, 'Artist')], [None, True, True, False])
        for kind in ('section', 'gap', 'overlap', 'dead', 'tie', 'mixed', 'grace'):
            changed = training(); track = changed['songs'][0]['tracks'][0]; rows = track['rows']
            if kind == 'section':
                for row in rows[2:]: row['section_start'] = 2
            if kind == 'gap':
                rows[2]['onset_q'] = '3'; rows[3]['onset_q'] = '4'
            if kind == 'overlap':
                rows[2]['onset_q'] = '3/2'; rows[3]['onset_q'] = '5/2'
            if kind == 'dead': rows[1]['raw_note']['dead'] = True
            if kind == 'tie': rows[1]['tie_destination'] = True
            if kind == 'mixed':
                extra = copy.deepcopy(rows[1]); extra.update(occurrence='extra', string=1, midi=45)
                extra['raw_beat_effects']['palmMute'] = False; rows.append(extra)
            if kind == 'grace': track['grace_rows'] = [dict(onset_q='2')]
            events = source_events(changed, 'Artist')
            if kind == 'grace':
                self.assertFalse(any(e['onset_q'] == '2' for e in events))
                self.assertIsNone(next(e for e in events if e['onset_q'] == '3')['previous'])
                continue
            target = next(e for e in events if e['onset_q'] == ('3' if kind == 'gap' else '3/2' if kind == 'overlap' else '2'))
            self.assertIsNone(target['previous'], kind)

    def test_source_coattacking_tie_and_grace_are_not_partial_opportunities(self):
        for kind in ('tie', 'grace'):
            data = training(); track = data['songs'][0]['tracks'][0]
            extra = copy.deepcopy(track['rows'][1]); extra.update(occurrence='extra', string=1, midi=45)
            if kind == 'tie':
                extra['tie_destination'] = True; track['rows'].append(extra)
            else: track['grace_rows'] = [dict(onset_q='1')]
            events = source_events(data, 'Artist')
            self.assertFalse(any(e['onset_q'] == '1' for e in events))
            self.assertIsNone(next(e for e in events if e['onset_q'] == '2')['previous'])

    def test_fit_heldout_is_never_training_and_family_leakage_fails(self):
        events = source_events(training(), 'Artist')
        held = dict(events[0], song_id=2, family='held', partition='held_out')
        model = fit(events + [held], 'Artist')
        self.assertEqual(model, fit(events + [dict(held, label=not held['label'])], 'Artist'))
        with self.assertRaises(ValueError): fit(events + [dict(held, family=events[0]['family'])], 'Artist')
        with self.assertRaises(ValueError): fit(events + [dict(held, song_id=events[0]['song_id'])], 'Artist')
        self.assertEqual(predict(model, 'unseen', None)[1], 'global')

    def test_artist_and_state_configuration_provenance_cannot_be_relabelled(self):
        events = source_events(training(), 'Artist', max_ioi_q='1')
        with self.assertRaisesRegex(ValueError, 'artist/state-reset'): fit(events, 'Other')
        with self.assertRaisesRegex(ValueError, 'artist/state-reset'): fit(events, 'Artist', max_ioi_q='2')
        with self.assertRaises(ValueError): fit(events, 'Artist', max_ioi_q='0')

    def test_zero_byte_identity_and_full_annotation_independence(self):
        model = fit(source_events(training(), 'Artist'), 'Artist')
        score, _, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); original = root / 'base.gp'; write_gp(score, original)
            result = apply(original, root / 'zero.gp', None, 'Artist', 0)
            self.assertTrue(result['byte_identity'])
            actual = extract_score(original)
            keys = {('note', n['note_id'], 'property'): {'PalmMuted'}
                    for t in actual['tracks'] for m in t['measures'] for v in m['voices'] for e in v for n in e['notes']}
            transact(original, root / 'perturbed.gp', {key: [enable_property('PalmMuted')] for key in keys}, keys)
            a = apply(original, root / 'a.gp', model, 'Artist', 100)
            b = apply(root / 'perturbed.gp', root / 'b.gp', model, 'Artist', 100)
            self.assertEqual((root / 'a.gp').read_bytes(), (root / 'b.gp').read_bytes())
            self.assertEqual(a['decisions'], b['decisions'])
            self.assertTrue(a['locked_xml_verified'])

    def test_partial_release_state_uses_actual_output(self):
        model = fit(source_events(training(), 'Artist'), 'Artist')
        score, _, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); write_gp(score, root / 'base.gp')
            audit = apply(root / 'base.gp', root / 'out.gp', model, 'Artist', 50)
            self.assertTrue(any(not e['released'] for e in audit['decisions']))
            for a, b in zip(audit['decisions'], audit['decisions'][1:]):
                self.assertEqual(b['previous'], a['actual_selected'])
                if not a['released']: self.assertFalse(a['actual_selected'])

    def test_section_instance_carries_but_repeated_marker_text_resets(self):
        model = fit(source_events(training(), 'Artist'), 'Artist')
        for repeated_marker in (False, True):
            score, _, _ = fixture()
            score['tracks'][0]['measures'][0]['section'] = 'Intro'
            if repeated_marker: score['tracks'][0]['measures'][1]['section'] = 'Intro'
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory); write_gp(score, root / 'base.gp')
                audit = apply(root / 'base.gp', root / 'out.gp', model, 'Artist', 100)
                prior = next(e for e in audit['decisions'] if e['onset_q'] == '3')
                next_bar = next(e for e in audit['decisions'] if e['onset_q'] == '4')
                if repeated_marker: self.assertIsNone(next_bar['previous'])
                else: self.assertEqual(next_bar['previous'], prior['actual_selected'])

    def test_duplicate_records_preserve_weighted_model_and_invalid_strength_fails(self):
        events = source_events(training(), 'Artist')
        self.assertEqual(fit(events, 'Artist')['tables'], fit(events * 3, 'Artist')['tables'])
        with self.assertRaises(ValueError): apply(None, None, None, 'Artist', True)


if __name__ == '__main__': unittest.main()
