import json
import unittest
from copy import deepcopy

from connected_tier2 import analyze, strip_lower
from source_fact_tier1 import extract_documents, project_documents
import musical_tier2 as music
import note_rest_timing as timing


def ref(part, beat, measure=0):
    return f'track-{part}.json#/measures/{measure}/voices/0/beats/{beat}'


def binding():
    return dict(note_beat_ref=ref(0, 1), rest_beat_ref=ref(0, 2),
                donor_note_beat_ref=ref(1, 1), donor_rest_beat_ref=ref(1, 2))


def documents():
    def note(typ, fret=0, string=0, dots=0):
        b = dict(type=typ, duration=[3 if dots else 1, typ * (2 if dots else 1)],
                 notes=[dict(string=string, fret=fret)])
        if dots:
            b['dots'] = dots
        return b
    def rest(typ):
        return dict(type=typ, duration=[1, typ], rest=True, notes=[dict(rest=True)])
    beats = [[note(2, 2, dots=1), note(4, 2, 1, dots=1), rest(8), note(8, 2), note(8, 3)],
             [note(1), note(8), rest(8), note(4)]]
    docs = {'metadata.json': dict(songId=77, revisionId=3, artist='Fixture', title='Space',
                                 tracks=[dict(name='Bass', instrumentId=35), dict(name='Voice', instrumentId=66)])}
    for pid, sequence in enumerate(beats):
        docs[f'track-{pid}.json'] = dict(songId=77, revisionId=3, partId=pid,
            name='Bass' if pid == 0 else 'Voice', instrumentId=35 if pid == 0 else 66,
            tuning=[33, 38], measures=[dict(signature=[6, 4], voices=[dict(beats=sequence)])])
    return docs


def model_for(docs=None, mode=None):
    lower = extract_documents(documents() if docs is None else docs)
    upper = strip_lower(analyze(lower, **(mode or {})))
    return lower, timing.lift(lower, upper['musical_relationships'], [binding()], upper['source_origin'])


def realized_facts(before, model):
    """Checker projection, independent of the connected integration under test."""
    core, values = timing.expand(model)
    after = deepcopy(before)
    for row in after['facts']:
        if row['id'] in values:
            row['value'] = values[row['id']]
    # Compare actual source parsing with the shared musical inverse.
    from run_reversible_tier_qa import extract_documents as source_events
    actual = source_events(project_documents(after))
    if core['schema'] == 'musical-context-relations/2':
        assert actual == music.reconstruct(core, {'variation': 0})
    timing.validate_source(model, after)
    return after


class NoteRestTimingTests(unittest.TestCase):
    def test_exact_original_and_changed_complete_facts(self):
        before, model = model_for()
        self.assertEqual(realized_facts(before, model), before)
        changed = timing.apply(model, model['pairs'][0]['id'])
        after = realized_facts(before, changed)
        report = timing.verify_effect(before, after, changed, changed['pairs'][0]['id'])
        self.assertEqual((report['note_duration_q'], report['rest_duration_q'], report['fixed_next_attack_q']), ('1', '1', '5'))
        self.assertTrue(report['cross_part_donor'])
        self.assertEqual(len(report['changed_fact_refs']), 5)
        self.assertEqual(model['pairs'][0]['shares'], ['3/4', '1/4'])
        self.assertEqual(changed['pairs'][0]['shares'], ['1/2', '1/2'])
        self.assertEqual(changed['pairs'][0]['observations'], model['pairs'][0]['observations'])

    def test_saved_edit_and_current_source_guards(self):
        before, model = model_for()
        edited = timing.apply(model, model['pairs'][0]['id'])
        saved = json.loads(json.dumps(edited))
        after = realized_facts(before, saved)
        self.assertEqual(timing.apply(saved, saved['pairs'][0]['id']), saved)
        for base in (before, after):
            for effect in ('tie', 'bend', 'letRing', 'sustainPedal'):
                docs = project_documents(base); beat = docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]
                if effect in ('tie', 'bend'):
                    beat['notes'][0][effect] = True if effect == 'tie' else {'points': []}
                else:
                    beat[effect] = True
                current = model if base is before else saved
                with self.subTest(effect=effect, changed=base is after), self.assertRaises(ValueError):
                    timing.validate_source(current, extract_documents(docs))

    def test_plain_source_admission_rejects_tie_curve_ring_and_incomplete_pause(self):
        for kind in ('tie', 'bend', 'slide', 'letRing', 'sustainPedal', 'other_voice', 'rest_donor', 'following_tie', 'unknown_clock'):
            docs = documents(); target = docs['track-0.json']['measures'][0]['voices'][0]['beats']
            donor = docs['track-1.json']['measures'][0]['voices'][0]['beats']
            if kind in ('tie', 'bend', 'slide'):
                target[1]['notes'][0][kind] = True if kind == 'tie' else {'tone': 100} if kind == 'bend' else 'downwards'
            elif kind in ('letRing', 'sustainPedal'):
                target[0][kind] = True
            elif kind == 'other_voice':
                docs['track-0.json']['measures'][0]['voices'].append(deepcopy(docs['track-0.json']['measures'][0]['voices'][0]))
            elif kind == 'rest_donor':
                donor[3].update(rest=True, notes=[dict(rest=True)])
            elif kind == 'following_tie':
                target[3]['notes'][0]['tie'] = True
            else:
                target[0]['duration'] = [1, 2]
            frozen = deepcopy(docs)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                model_for(docs)
            self.assertEqual(docs, frozen)

    def test_observation_tampering_duplicate_owners_and_unobserved_values(self):
        _, model = model_for()
        for kind in ('donor', 'origin', 'shares', 'old_duration', 'old_onset', 'unknown_payload', 'duplicate', 'wrong_ref', 'slot_scale'):
            bad = deepcopy(model); pair = bad['pairs'][0]; body = bad['pitch_relationships']
            group = next(g for g in body['coattacks'] if g['id'] == pair['coattack_ref'])
            if kind == 'donor': pair['observations']['donor']['shares'] = ['1/4', '3/4']
            elif kind == 'origin': bad['source_origin']['facts_sha256'] = '0' * 64
            elif kind == 'shares': pair['shares'] = ['5/8', '3/8']
            elif kind == 'old_duration': group['members'][0]['duration_q'] = '3/2'
            elif kind == 'old_onset': group['onset_q'] = '3'
            elif kind == 'unknown_payload': pair['raw_score'] = {}
            elif kind == 'duplicate': bad['pairs'].append(deepcopy(pair))
            elif kind == 'wrong_ref': pair['coattack_ref'] = 'coattack:999'
            else: pair['slots'][0]['fraction_scale'] = 0
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                timing.expand(bad)

    def test_original_provenance_cannot_be_rebased_after_an_edit(self):
        before, model = model_for()
        changed = timing.apply(model, model['pairs'][0]['id'])
        after = realized_facts(before, changed)
        with self.assertRaisesRegex(ValueError, 'relabel'):
            timing.lift(after, timing.expand(changed)[0], [binding()], model['source_origin'])

    def test_target_and_donor_require_known_pitched_instrument_domains(self):
        for part in (0, 1):
            for program in (None, True, '35', -1, 128, 1024):
                docs = documents(); docs[f'track-{part}.json']['instrumentId'] = program
                with self.subTest(part=part, program=program), self.assertRaises(ValueError):
                    model_for(docs)

    def test_all_members_of_one_coattack_share_release(self):
        docs = documents(); beat = docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]
        beat['notes'].append(dict(string=0, fret=7))
        before, model = model_for(docs)
        edited = timing.apply(model, model['pairs'][0]['id'])
        after = realized_facts(before, edited)
        report = timing.verify_effect(before, after, edited, edited['pairs'][0]['id'])
        self.assertEqual(len(report['occurrence_refs']), 2)

    def test_source_fraction_gauge_and_existing_dot_slots_preserved(self):
        docs = documents(); beats = docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[1]['duration'] = [6, 16]; beats[2]['duration'] = [2, 16]
        before, model = model_for(docs)
        self.assertEqual(realized_facts(before, model), before)
        after = project_documents(realized_facts(before, timing.apply(model, model['pairs'][0]['id'])))
        selected = after['track-0.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual(selected[1]['duration'], [2, 8]); self.assertEqual(selected[2]['duration'], [2, 8])
        self.assertEqual(selected[1]['dots'], 0); self.assertNotIn('dots', selected[2])

    def test_no_new_notation_slots_or_unadmitted_held_extension(self):
        for mode in ('unrepresentable', 'extension'):
            docs = documents(); donor = docs['track-1.json']['measures'][0]['voices'][0]['beats']
            if mode == 'unrepresentable':
                donor[1].update(type=16, duration=[1, 16]); donor[2].update(type=8, duration=[3, 16], dots=1)
            else:
                donor[1].update(type=4, duration=[3, 8], dots=1); donor[2].update(type=16, duration=[1, 16])
                donor[3].update(type=16, duration=[1, 16])
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                model_for(docs)

    def test_only_allowed_source_facts_may_change(self):
        before, model = model_for(); edited = timing.apply(model, model['pairs'][0]['id'])
        after = realized_facts(before, edited)
        for row in after['facts']:
            if row['id'] == ref(1, 1) + '/notes/0/fret': row['value'] += 1
        with self.assertRaisesRegex(ValueError, 'locked source fact'):
            timing.verify_effect(before, after, edited, edited['pairs'][0]['id'])


if __name__ == '__main__':
    unittest.main()
