"""Authored ownership/behavior counterexamples, not musical-style evidence."""
from copy import deepcopy
import json
import random
import unittest

import backing_pitch_ownership as backing
import melodic_movement_ownership as movement
from connected_tier2 import analyze, strip_lower
from source_fact_tier1 import extract_documents, project_documents

SONG = 980112
REFERENCE = [f'event:{SONG}:0:1:0:{i}:0' for i in range(3)]
TARGET = [f'event:{SONG}:0:2:0:{i}:0' for i in range(3)]
DEPENDENT = f'event:{SONG}:0:3:0:0:0'
BACKING = f'event:{SONG}:1:3:0:0:0'


def beat(pitch=None, *, duration=(1, 4), string=0, tuning=50, **fields):
    note = dict(rest=True) if pitch is None else dict(string=string, fret=pitch-tuning)
    note.update(fields)
    return dict(duration=list(duration), notes=[note])


def bar(beats):
    return dict(signature=[4, 4], voices=[dict(beats=beats)])


def documents():
    return {
        'metadata.json': dict(songId=SONG, revisionId=1, artist='Authored fixture', title='Signed melodic movement',
            tracks=[dict(name='Guitar', instrumentId=27), dict(name='Bass', instrumentId=34)]),
        'track-0.json': dict(songId=SONG, revisionId=1, partId=0, instrumentId=27,
            tuning=[50,45,40,35,30,25], frets=32,
            measures=[bar([beat(p) for p in (67,74,65)]+[beat()]),
                      bar([beat(p) for p in (60,61,62)]+[beat()]),
                      bar([beat(72),beat(duration=(3,4))])]),
        'track-1.json': dict(songId=SONG, revisionId=1, partId=1, instrumentId=34,
            tuning=[40,35,30,25], frets=32,
            measures=[bar([beat(40,tuning=40,duration=(1,1))]) for _ in range(3)])}


def build(docs=None, *, targets=None, references=None, unrelated=False, bindings=None, rhythm=False):
    docs = documents() if docs is None else docs
    lower = extract_documents(docs)
    links = [dict(occurrence_ref=DEPENDENT,backing_ref=BACKING)] if unrelated else bindings
    options = {} if links is None else dict(backing_bindings=links)
    if rhythm:
        options.update(rhythm_groups=True, rhythm_group_profile='written_time')
    upper = strip_lower(analyze(lower, **options))
    return docs, lower, upper, movement.lift(upper, TARGET if targets is None else targets,
        reference_attack_refs=references)


def controls(level=100, intent='repeat_start', seed=0):
    return dict(context_policy=movement.POLICY, melody=level, intent=intent, seed=seed)


def output(upper):
    return project_documents(movement._realize(upper))


def set_pitches(docs, pitches, *, measure=1, beats=(0,1,2), part=0):
    result = deepcopy(docs)
    track = result[f'track-{part}.json']
    for index, pitch in zip(beats,pitches):
        note = track['measures'][measure]['voices'][0]['beats'][index]['notes'][0]
        note['fret'] = pitch-track['tuning'][note['string']]-track.get('capo',0)
    return result


class MelodicMovementOwnershipTests(unittest.TestCase):
    def test_same_equation_large_negative_steps_and_note_name_octave(self):
        extracted = movement.relation(pitches=['60','67','58'])
        self.assertEqual(extracted,dict(pitch_class='0',octave=4,steps=['7','-9'],pitches=['60','67','58']))
        self.assertEqual(movement.relation(**{k:v for k,v in extracted.items()if k!='pitches'}),extracted)
        self.assertEqual(movement.relation(pitches=['59','60','48'])['octave'],3)
        for args in (dict(pitch_class='12',octave=4,steps=['0']),
                     dict(pitch_class='0',octave=True,steps=['0']),
                     dict(pitch_class='0',octave=4,steps=['1/2']),
                     dict(pitch_class='0',octave=4,steps=[True]),
                     dict(pitch_class='0',octave=4,steps=['reference_step'])):
            with self.subTest(args=args),self.assertRaises(ValueError):movement.relation(**args)

    def test_forward_zero_single_authority_and_exact_all_documents(self):
        docs, lower, plain, owned = build()
        self.assertEqual(movement._realize(owned),lower)
        self.assertEqual(output(owned),docs)
        self.assertNotIn('input',owned)
        model = owned['owned_parameters'][movement.SLOT]
        self.assertEqual(model['parameters'],dict(pitch_class='0',octave=4,steps=['1','1']))
        self.assertEqual(set(model['observations']),{'origin','reference_steps'})
        self.assertIsNone(model['observations']['reference_steps'])
        index = backing._index(movement._body(owned['musical_relationships']))
        for ref in TARGET:self.assertNotIn('bass_register_anchor',index[ref][0])
        for intent in movement.INTENTS:
            zero,report=movement.intervene(owned,controls(0,intent))
            self.assertEqual(zero,owned);self.assertFalse(report['released'])
        self.assertEqual(plain['musical_relationships']['schema'],backing.PLAIN)

    def test_repeat_and_large_non_octave_follow_change_only_selected_frets(self):
        docs,_,_,owned=build(references=REFERENCE)
        snapshot=deepcopy(owned)
        for intent,pitches in [('repeat_start',[60,60,60]),('follow_reference_motion',[60,67,58])]:
            edited,report=movement.intervene(owned,controls(intent=intent))
            self.assertTrue(report['released']);self.assertTrue(report['changed'])
            self.assertEqual(output(edited),set_pitches(docs,pitches))
            restored=deepcopy(edited)
            restored['owned_parameters'][movement.SLOT]['parameters']=deepcopy(owned['owned_parameters'][movement.SLOT]['parameters'])
            self.assertEqual(restored,owned)
            self.assertEqual(owned,snapshot)
        with self.assertRaisesRegex(ValueError,'Existing movement'):
            movement.lift(owned,TARGET)

    def test_saved_current_zero_and_seeded_group_release_and_coincidence(self):
        docs,_,_,owned=build(references=REFERENCE)
        released={seed:random.Random(f'melodic-movement:{seed}').random()<.5 for seed in range(16)}
        seeds=[next(s for s,v in released.items()if not v),next(s for s,v in released.items()if v)]
        for seed in seeds:
            a,ra=movement.intervene(owned,controls(50,'follow_reference_motion',seed))
            b,rb=movement.intervene(owned,controls(50,'follow_reference_motion',seed))
            self.assertEqual((a,ra),(b,rb));self.assertEqual(ra['released'],released[seed])
            self.assertEqual(output(a),set_pitches(docs,[60,67,58])if released[seed]else docs)
        edited,_=movement.intervene(owned,controls())
        saved=json.loads(json.dumps(edited));zero,report=movement.intervene(saved,controls(0))
        self.assertEqual(zero,saved);self.assertFalse(report['released'])
        repeated,report=movement.intervene(saved,controls())
        self.assertEqual(repeated,saved);self.assertTrue(report['released']);self.assertFalse(report['changed'])

    def test_live_reference_changes_after_save_without_new_original_observations(self):
        docs,_,_,owned=build(references=REFERENCE)
        edited,_=movement.intervene(owned,controls(intent='follow_reference_motion'))
        saved=json.loads(json.dumps(edited));observation=deepcopy(saved['owned_parameters'][movement.SLOT]['observations'])
        index=backing._index(movement._body(saved['musical_relationships']))
        index[REFERENCE[1]][0]['bass_register_anchor']='72'
        expected=set_pitches(set_pitches(docs,[67,72,65],measure=0),[60,65,58])
        self.assertEqual(output(saved),expected)
        self.assertEqual(saved['owned_parameters'][movement.SLOT]['observations'],observation)
        zero,_=movement.intervene(saved,controls(0))
        self.assertEqual(zero,saved)

    def test_upper_member_keeps_actual_lower_dead_notes_rests_and_other_voice(self):
        docs=documents()
        for mi in (0,1):
            for b in docs['track-0.json']['measures'][mi]['voices'][0]['beats'][:3]:
                b['notes'] += [dict(string=1,fret=5),dict(string=2,dead=True)]
            docs['track-0.json']['measures'][mi]['voices'].append(dict(
                beats=[beat(64,string=3,tuning=35,duration=(1,1))]))
        _,_,_,owned=build(docs,references=REFERENCE)
        edited,_=movement.intervene(owned,controls(intent='follow_reference_motion'))
        self.assertEqual(output(edited),set_pitches(docs,[60,67,58]))
        body=movement._body(edited['musical_relationships']);index=backing._index(body)
        for ref in TARGET:
            group,member=index[ref]
            self.assertEqual(group['bass_register_anchor'],'50')
            self.assertNotIn('voicing_interval',member)
            self.assertIsNone(group['members'][2]['voicing_interval'])
        lower_refs=[ref[:-1]+'1' for ref in TARGET]
        with self.assertRaisesRegex(ValueError,'lowest|upper member'):
            movement.lift(strip_lower(analyze(extract_documents(docs))),lower_refs)

    def test_one_pitched_member_with_dead_occurrence_needs_no_invented_lower(self):
        docs=documents()
        for measure in docs['track-0.json']['measures'][:2]:
            for b in measure['voices'][0]['beats'][:3]:
                b['notes'].append(dict(string=1,dead=True))
        _,lower,plain,owned=build(docs,references=REFERENCE)
        self.assertEqual(movement._realize(owned),lower)
        index=backing._index(movement._body(owned['musical_relationships']))
        for ref in TARGET:
            group,member=index[ref]
            self.assertNotIn('bass_register_anchor',group)
            self.assertEqual(member['voicing_interval'],'0')
            self.assertIsNone(group['members'][1]['voicing_interval'])
        edited,report=movement.intervene(owned,controls(intent='follow_reference_motion'))
        self.assertEqual(output(edited),set_pitches(docs,[60,67,58]))
        self.assertEqual(report['member_refs'],TARGET)
        # Missing foreign authority is not the same as explicit unknown pitch.
        bad=deepcopy(owned)
        group,_=backing._index(movement._body(bad['musical_relationships']))[TARGET[0]]
        del group['members'][1]['voicing_interval']
        with self.assertRaises(ValueError):movement._realize(bad)
        dead_refs=[ref[:-1]+'1'for ref in TARGET]
        with self.assertRaisesRegex(ValueError,'Known pitched'):
            movement.lift(plain,dead_refs)

    def test_complete_tie_members_share_one_attack_pitch_and_preserve_curves(self):
        docs=documents();beats=docs['track-0.json']['measures'][1]['voices'][0]['beats']
        bend=dict(tone=50,points=[dict(position=0,tone=0),dict(position=15,tone=50),dict(position=60,tone=50)])
        beats[:]=[beat(60),beat(61,duration=(1,8),bend=bend,leftHandVibrato='slight'),
                  beat(61,duration=(1,8),tie=True,leftHandVibrato='slight'),beat(62),beat()]
        roots=[f'event:{SONG}:0:2:0:{i}:0' for i in (0,1,3)]
        _,_,_,owned=build(docs,targets=roots,references=REFERENCE)
        model=owned['owned_parameters'][movement.SLOT]
        self.assertEqual(len(model['attacks']),3)
        self.assertEqual(len(movement._members(model['attacks'])),4)
        edited,_=movement.intervene(owned,controls())
        self.assertEqual(output(edited),set_pitches(docs,[60,60,60,60],beats=(0,1,2,3)))
        bad=deepcopy(owned);bad['owned_parameters'][movement.SLOT]['attacks'][1]['member_refs'].pop()
        with self.assertRaises(ValueError):movement._realize(bad)
        with self.assertRaisesRegex(ValueError,'continuation'):
            movement.lift(strip_lower(analyze(extract_documents(docs))),[roots[0],f'event:{SONG}:0:2:0:2:0',roots[2]])

    def test_unrelated_backing_owner_remains_and_still_propagates_later(self):
        docs,_,_,owned=build(unrelated=True,references=REFERENCE)
        original_links=deepcopy(owned['musical_relationships']['relationships'])
        edited,_=movement.intervene(owned,controls())
        self.assertEqual(edited['musical_relationships']['relationships'],original_links)
        later=json.loads(json.dumps(edited));index=backing._index(movement._body(later['musical_relationships']))
        index[BACKING][0]['bass_register_anchor']='41'
        expected=set_pitches(docs,[60,60,60]);expected=set_pitches(expected,[73],measure=2,beats=(0,))
        expected=set_pitches(expected,[41],measure=2,beats=(0,),part=1)
        self.assertEqual(output(later),expected)
        self.assertEqual(later['musical_relationships']['relationships'],original_links)

    def test_existing_selected_owner_and_indirect_reference_cycle_refuse(self):
        docs=documents()
        bound=dict(occurrence_ref=TARGET[1],backing_ref=f'event:{SONG}:1:2:0:0:0')
        upper=strip_lower(analyze(extract_documents(docs),backing_bindings=[bound]))
        before=deepcopy(upper)
        with self.assertRaisesRegex(ValueError,'conflicting singleton'):
            movement.lift(upper,TARGET)
        self.assertEqual(upper,before)
        refs=[f'event:{SONG}:1:2:0:{i}:0'for i in range(3)]
        docs['track-1.json']['measures'][1]=bar([beat(p,tuning=40)for p in (47,54,45)]+[beat()])
        bindings=[dict(occurrence_ref=a,backing_ref=b)for a,b in zip(refs,TARGET)]
        upper=strip_lower(analyze(extract_documents(docs),backing_bindings=bindings));before=deepcopy(upper)
        with self.assertRaisesRegex(ValueError,'selected|Cyclic'):
            movement.lift(upper,TARGET,reference_attack_refs=refs)
        self.assertEqual(upper,before)

    def test_unselected_dependency_propagation_is_an_atomic_refusal(self):
        docs=documents()
        docs['track-1.json']['measures'][1]=bar([beat(),beat(45,tuning=40,duration=(3,4))])
        dependent=f'event:{SONG}:1:2:0:1:0'
        _,_,_,owned=build(docs,bindings=[dict(occurrence_ref=dependent,backing_ref=TARGET[1])])
        before=deepcopy(owned)
        with self.assertRaisesRegex(ValueError,'outside.*fret scope'):
            movement.intervene(owned,controls())
        self.assertEqual(owned,before)

    def test_duplicate_authorities_unknown_controls_and_illegal_contact_refuse(self):
        _,_,_,owned=build(references=REFERENCE)
        bad=deepcopy(owned);backing._index(movement._body(bad['musical_relationships']))[TARGET[0]][0]['bass_register_anchor']='60'
        with self.assertRaisesRegex(ValueError,'duplicate|Duplicate'):
            movement._realize(bad)
        for key,value in [('melody',None),('melody',True),('melody',50.0),('melody',float('nan')),('seed',True),('intent','guess')]:
            request=controls();request[key]=value;before=deepcopy(owned)
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):movement.intervene(owned,request)
            self.assertEqual(owned,before)
        bad=deepcopy(owned);bad['owned_parameters'][movement.SLOT]['parameters']['steps']=['-50','0']
        with self.assertRaises(ValueError):movement._realize(bad)
        with self.assertRaises(ValueError):movement.intervene(owned,dict(controls(),desired_pitch=70))

    def test_changed_notation_and_unknown_tie_refuse_without_mutation(self):
        docs=documents();docs['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]['tie']=1
        with self.assertRaises(ValueError):build(docs)
        _,_,_,owned=build();bad=deepcopy(owned)
        pointer='track-0.json#/measures/1/voices/0/beats/1/notes/0/string'
        next(r for r in bad['owned_parameters']['source_choices']if r['fact_ref']==pointer)['parameter']['normalized']='1'
        before=deepcopy(bad)
        with self.assertRaises(ValueError):movement.intervene(bad,controls())
        self.assertEqual(bad,before)

    def test_validator_checks_actual_current_pitches_not_only_guard_geometry(self):
        docs,_,_,owned=build()
        wrong=extract_documents(set_pitches(docs,[60,62,62]))
        with self.assertRaisesRegex(ValueError,'movement authority'):
            movement.validate_execution(owned,wrong)

    def test_unrelated_bend_owner_survives_and_keeps_its_future_behavior(self):
        import bend_gesture_ownership as bend_owner
        from test_bend_gesture_ownership import curve
        docs=documents()
        for pitch,tone in ((64,50),(65,100)):
            docs['track-0.json']['measures'].append(bar([
                beat(pitch,duration=(3,8),bend=curve(tone)),
                beat(pitch,duration=(1,8),tie=True,bend=curve(tone,True)),
                beat(duration=(1,2))]))
            docs['track-1.json']['measures'].append(bar([beat(40,tuning=40,duration=(1,1))]))
        upper=strip_lower(analyze(extract_documents(docs)))
        reference=f'event:{SONG}:0:4:0:0:0';target=f'event:{SONG}:0:5:0:0:0'
        bent=bend_owner.lift(upper,reference_ref=reference,target_ref=target)
        owner_before=deepcopy(bent['owned_parameters'][bend_owner.SLOT])
        owned=movement.lift(bent,TARGET,reference_attack_refs=REFERENCE)
        edited,_=movement.intervene(owned,controls(intent='follow_reference_motion'))
        self.assertEqual(output(edited),set_pitches(docs,[60,67,58]))
        self.assertEqual(edited['owned_parameters'][bend_owner.SLOT],owner_before)
        expanded=movement.expand(edited)
        changed,_=bend_owner.intervene(expanded,dict(context_policy=bend_owner.POLICY,
            bend=100,intent='keep_start',seed=0))
        from connected_tier2 import realize
        actual=project_documents(realize(changed))
        expected=set_pitches(docs,[60,67,58])
        for i in (0,1):expected['track-0.json']['measures'][4]['voices'][0]['beats'][i]['notes'][0]['bend']=curve(50,bool(i))
        self.assertEqual(actual,expected)

    def test_written_time_owner_survives_pitch_movement(self):
        docs,_,_,owned=build(rhythm=True,references=REFERENCE)
        prior=deepcopy(owned['musical_relationships']['groups'])
        edited,_=movement.intervene(owned,controls(intent='follow_reference_motion'))
        self.assertEqual(output(edited),set_pitches(docs,[60,67,58]))
        self.assertEqual(edited['musical_relationships']['groups'],prior)


def v2_documents(*, coattack=False, tied=False):
    """Authored six-string geometry; the extra chord witnesses a seven-fret span."""
    docs = documents(); track = docs['track-0.json']
    track.update(tuning=[64,59,55,50,45,40], frets=24)
    for measure in track['measures']:
        for row in measure['voices'][0]['beats']:
            for note in row['notes']:
                if 'string' in note: note['string'] = 3
    if tied:
        track['measures'][1]['voices'][0]['beats'][3] = beat(62, string=3, tie=True)
    if coattack:
        for row in track['measures'][1]['voices'][0]['beats']:
            if 'fret' in row['notes'][0]:
                row['notes'] += [dict(string=5,fret=10),dict(string=2,fret=8),dict(string=4,dead=True)]
    witness = beat(81,string=0,tuning=64)
    witness['notes'].append(dict(string=5,fret=10))
    track['measures'].append(bar([witness,beat(duration=(3,4))]))
    docs['track-1.json']['measures'].append(bar([beat(40,tuning=40,duration=(1,1))]))
    return docs


def build_v2(docs=None, *, references=REFERENCE, unrelated=False, rhythm=False, bindings=None):
    docs = v2_documents() if docs is None else docs
    links = [dict(occurrence_ref=DEPENDENT,backing_ref=BACKING)] if unrelated else bindings
    kwargs = {} if links is None else dict(backing_bindings=links)
    if rhythm: kwargs.update(rhythm_groups=True,rhythm_group_profile='written_time')
    lower = extract_documents(docs); upper = strip_lower(analyze(lower,**kwargs))
    return docs, lower, upper, movement.lift(upper,TARGET,reference_attack_refs=references,register_controls=True)


def v2_controls(melody=0, register=0, *, intent='follow_reference_motion', direction='up', seed=0):
    return dict(context_policy=movement.POLICY,melody=melody,intent=intent,register=register,register_direction=direction,seed=seed)


def selected_pitches(docs, *, tied=False):
    track=docs['track-0.json']; rows=track['measures'][1]['voices'][0]['beats'][:4 if tied else 3]
    return [track['tuning'][r['notes'][0]['string']]+r['notes'][0]['fret'] for r in rows]


class MovementRegisterV2Tests(unittest.TestCase):
    def assert_only_contacts(self, before, after, *, tied=False):
        expected=deepcopy(before)
        for i in range(4 if tied else 3):
            a=expected['track-0.json']['measures'][1]['voices'][0]['beats'][i]['notes'][0]
            b=after['track-0.json']['measures'][1]['voices'][0]['beats'][i]['notes'][0]
            a.update(string=b['string'],fret=b['fret'])
        self.assertEqual(after,expected)

    def test_four_states_on_singleton_and_coattack_use_one_authority(self):
        for coattack in (False,True):
            docs,lower,_,owned=build_v2(v2_documents(coattack=coattack))
            original=deepcopy(owned); obs=deepcopy(owned['owned_parameters'][movement.SLOT]['observations'])
            self.assertEqual(movement._realize(owned),lower)
            self.assertNotIn('input',owned)
            self.assertEqual(owned['owned_parameters'][movement.SLOT]['schema'],movement.SCHEMA_V2)
            self.assertEqual(obs['register_context']['max_simultaneous_span'],'7')
            index=backing._index(movement._body(owned['musical_relationships']))
            for ref in TARGET:
                group,member=index[ref]
                self.assertNotIn('voicing_interval' if coattack else 'bass_register_anchor',member if coattack else group)
            for levels,pitches in [((0,0),[60,61,62]),((100,0),[60,67,58]),((0,100),[72,73,74]),((100,100),[72,79,70])]:
                with self.subTest(coattack=coattack,levels=levels):
                    changed,report=movement.intervene(owned,v2_controls(*levels))
                    actual=output(changed)
                    self.assertEqual(selected_pitches(actual),pitches)
                    self.assert_only_contacts(docs,actual)
                    self.assertEqual(changed['owned_parameters'][movement.SLOT]['observations'],obs)
                    self.assertEqual(changed['owned_parameters'][movement.SLOT]['attacks'],owned['owned_parameters'][movement.SLOT]['attacks'])
                    if levels==(0,0): self.assertEqual(changed,owned)
                    self.assertEqual(movement.expand(changed)['owned_parameters'].get(movement.SLOT),None)
            self.assertEqual(owned,original)

    def test_original_register_counts_are_reports_not_a_literal_pitch_veto(self):
        _,_,_,owned=build_v2()
        observed=owned['owned_parameters'][movement.SLOT]['observations']['register_context']
        pitches={12*(r['octave']+1)+r['pitch_class'] for r in observed['counts']}
        self.assertNotIn(79,pitches)
        changed,report=movement.intervene(owned,v2_controls(100,100))
        self.assertEqual(selected_pitches(output(changed)),[72,79,70])
        choice=report['decisions']['register']['candidates'][1]
        self.assertEqual(choice['original_written_support'][1],0)
        self.assertEqual(changed['owned_parameters'][movement.SLOT]['observations']['register_context'],observed)

    def test_both_orders_reload_current_zero_and_current_relative_direction(self):
        docs,_,_,owned=build_v2(v2_documents(coattack=True))
        moved,_=movement.intervene(owned,v2_controls(100,0))
        mr,_=movement.intervene(json.loads(json.dumps(moved)),v2_controls(0,100))
        raised,_=movement.intervene(owned,v2_controls(0,100))
        rm,_=movement.intervene(json.loads(json.dumps(raised)),v2_controls(100,0))
        for item in (mr,rm):
            self.assertEqual(selected_pitches(output(item)),[72,79,70])
            self.assert_only_contacts(docs,output(item))
            zero,_=movement.intervene(item,v2_controls(0,0,intent='repeat_start',direction='down'))
            self.assertEqual(zero,item)
            self.assertEqual(item['owned_parameters'][movement.SLOT]['observations'],owned['owned_parameters'][movement.SLOT]['observations'])
        self.assertEqual(mr['owned_parameters'][movement.SLOT]['parameters'],rm['owned_parameters'][movement.SLOT]['parameters'])
        down,_=movement.intervene(mr,v2_controls(0,100,direction='down'))
        self.assertEqual(selected_pitches(output(down)),[60,67,58])
        # Placement is recomputed against each current contact state; no assertion
        # that different editing histories must choose identical fingerings.

    def test_independent_release_and_uniform_selection_include_current_at_100(self):
        _,_,_,owned=build_v2(); seen=set()
        for seed in (0,2,3,4,6,7):
            actual,report=movement.intervene(owned,v2_controls(50,50,seed=seed))
            choices=[]
            for axis in ('melody','register'):
                released=random.Random(f'melodic-movement-v2:{axis}:release:{seed}').random()<.5
                self.assertEqual(report['released'][axis],released)
                choice=random.Random(f'melodic-movement-v2:{axis}:selection:{seed}').randrange(2) if released else 0
                if released:self.assertEqual(report['decisions'][axis]['selected_index'],choice)
                choices.append(choice)
            expected=[[60,61,62],[60,67,58]][choices[0]]
            self.assertEqual(selected_pitches(output(actual)),[p+12*choices[1] for p in expected])
            seen.add(tuple(report['released'].values()))
        self.assertEqual(seen,{(False,False),(True,False),(False,True),(True,True)})
        coincident,report=movement.intervene(owned,v2_controls(100,100,seed=2))
        self.assertEqual(coincident,owned)
        self.assertTrue(all(report['released'].values()))
        self.assertTrue(all(d['has_alternative'] for d in report['decisions'].values()))

    def test_live_reference_coincidence_is_not_parameter_deduplicated(self):
        docs=v2_documents()
        for row,pitch in zip(docs['track-0.json']['measures'][0]['voices'][0]['beats'],(67,68,69)):
            row['notes'][0]['fret']=pitch-50
        _,_,_,owned=build_v2(docs)
        choices=movement.options(owned,'follow_reference_motion','up')['movement']
        self.assertEqual(len(choices),2)
        changed,report=movement.intervene(owned,v2_controls(100,0))
        self.assertFalse(report['changed']);self.assertTrue(report['relationships_changed'])
        self.assertEqual(output(changed),docs)
        saved=json.loads(json.dumps(changed));saved_obs=deepcopy(saved['owned_parameters'][movement.SLOT]['observations'])
        backing._index(movement._body(saved['musical_relationships']))[REFERENCE[1]][0]['bass_register_anchor']='70'
        self.assertEqual(selected_pitches(output(saved)),[60,63,62])
        self.assertEqual(saved['owned_parameters'][movement.SLOT]['observations'],saved_obs)

    def test_tied_members_move_together_and_identity_survives_voice_rank_change(self):
        docs,_,_,owned=build_v2(v2_documents(coattack=True,tied=True))
        changed,_=movement.intervene(owned,v2_controls(100,100))
        actual=output(changed)
        self.assertEqual(selected_pitches(actual,tied=True),[72,79,70,70])
        self.assert_only_contacts(docs,actual,tied=True)
        rows=actual['track-0.json']['measures'][1]['voices'][0]['beats']
        self.assertTrue(rows[3]['notes'][0]['tie'])
        self.assertEqual(rows[2]['notes'][0]['string'],rows[3]['notes'][0]['string'])
        self.assertEqual(owned['owned_parameters'][movement.SLOT]['attacks'],changed['owned_parameters'][movement.SLOT]['attacks'])
        self.assertEqual(len(changed['owned_parameters'][movement.SLOT]['attacks']),3)
        down,_=movement.intervene(changed,v2_controls(0,100,direction='down'))
        self.assertEqual(selected_pitches(output(down),tied=True),[60,67,58,58])
        self.assert_only_contacts(docs,output(down),tied=True)

    def test_unrelated_authority_retains_exact_future_propagation(self):
        docs,_,_,owned=build_v2(unrelated=True)
        links=deepcopy(owned['musical_relationships']['relationships'])
        changed,_=movement.intervene(owned,v2_controls(100,100))
        self.assertEqual(changed['musical_relationships']['relationships'],links)
        later=json.loads(json.dumps(changed))
        backing._index(movement._body(later['musical_relationships']))[BACKING][0]['bass_register_anchor']='41'
        actual=output(later);expected=output(changed)
        expected['track-1.json']['measures'][2]['voices'][0]['beats'][0]['notes'][0]['fret']+=1
        expected['track-0.json']['measures'][2]['voices'][0]['beats'][0]['notes'][0]['fret']+=1
        self.assertEqual(actual,expected)

    def test_outside_dependency_is_refused_as_alternative_and_never_partially_mutates(self):
        docs=v2_documents();docs['track-1.json']['measures'][1]=bar([beat(),beat(45,tuning=40,duration=(3,4))])
        dependent=f'event:{SONG}:1:2:0:1:0'
        _,_,_,owned=build_v2(docs,bindings=[dict(occurrence_ref=dependent,backing_ref=TARGET[1])])
        before=deepcopy(owned); choices=movement.options(owned,'follow_reference_motion','up')
        self.assertEqual(len(choices['movement']),1);self.assertEqual(len(choices['register']),1)
        self.assertTrue(all('outside' in r['reason'] for r in choices['movement_refused']+choices['register_refused']))
        with self.assertRaisesRegex(ValueError,'Requested melody alternative unsupported'):
            movement.intervene(owned,v2_controls(100,100))
        self.assertEqual(before,owned)

    def test_declared_geometry_source_span_and_observation_corruption_fail_closed(self):
        _,_,_,owned=build_v2(v2_documents(coattack=True));original=deepcopy(owned)
        bad=deepcopy(owned);bad['owned_parameters'][movement.SLOT]['parameters']['octave']+=1
        # The original strings would put the selected notes too far from held
        # chord contacts; manually changing k cannot bypass the inverse guard.
        with self.assertRaises(ValueError):movement._realize(bad)
        for mutate in ('count','scope','boolean_count'):
            bad=deepcopy(owned);ctx=bad['owned_parameters'][movement.SLOT]['observations']['register_context']
            if mutate=='count':ctx['counts'][0]['count']+=1
            elif mutate=='scope':ctx['excluded_member_refs'].pop()
            else:ctx['counts'][0]['count']=True
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):movement.intervene(bad,v2_controls())
        for value in (None,True,50.0,float('nan')):
            with self.subTest(value=value),self.assertRaises(ValueError):movement.intervene(owned,dict(v2_controls(),register=value))
        with self.assertRaises(ValueError):movement.intervene(owned,dict(v2_controls(),register_direction='best'))
        no_bound=v2_documents();del no_bound['track-0.json']['frets']
        with self.assertRaisesRegex(ValueError,'declared finite'):build_v2(no_bound)
        self.assertEqual(owned,original)

    def test_no_directional_freedom_is_explicit_not_a_creative_pass(self):
        _,_,_,owned=build_v2(v2_documents(coattack=True))
        choices=movement.options(owned,'follow_reference_motion','down')
        self.assertEqual(len(choices['register']),1);self.assertTrue(choices['register_refused'])
        before=deepcopy(owned)
        with self.assertRaisesRegex(ValueError,'Requested register alternative unsupported'):
            movement.intervene(owned,v2_controls(0,100,direction='down'))
        self.assertEqual(owned,before)

    def test_unavailable_combination_cannot_return_a_partial_melody_result(self):
        docs=v2_documents()
        for row,pitch in zip(docs['track-0.json']['measures'][0]['voices'][0]['beats'],(67,87,67)):
            row['notes'][0].update(string=0,fret=pitch-64)
        _,_,_,owned=build_v2(docs);before=deepcopy(owned)
        moved,_=movement.intervene(owned,v2_controls(100,0))
        self.assertEqual(selected_pitches(output(moved)),[60,80,60])
        self.assertEqual(len(movement.options(owned,'follow_reference_motion','up')['register']),2)
        self.assertEqual(len(movement.options(moved,'follow_reference_motion','up')['register']),1)
        with self.assertRaisesRegex(ValueError,'Requested register alternative unsupported'):
            movement.intervene(owned,v2_controls(100,100))
        self.assertEqual(owned,before)

    def test_whole_hold_checks_actual_cells_and_preserves_other_voice_contacts(self):
        docs=v2_documents(); measure=docs['track-0.json']['measures'][1]
        measure['voices'][0]['beats']=[beat(60,string=3,duration=(1,2)),beat(61,string=3),beat(62,string=3)]
        measure['voices'].append(dict(beats=[beat(46,string=5,tuning=40),beat(54,string=5,tuning=40),beat(duration=(1,2))]))
        _,lower,_,owned=build_v2(docs)
        data=movement.closure._data(movement.execution.encoded(lower))
        # Frets6 and14 occur in different halves of this held fret10. Each
        # simultaneous span is4, not the union's fictitious span8.
        self.assertTrue(movement._contact_span_ok(data,TARGET[0],dict(string=3,fret=10),movement.F(4)))
        self.assertFalse(movement._contact_span_ok(data,TARGET[0],dict(string=3,fret=10),movement.F(3)))
        self.assertFalse(movement._contact_span_ok(data,TARGET[0],dict(string=5,fret=20),movement.F(99)))
        before=deepcopy(owned)
        self.assertEqual(output(owned),docs)
        self.assertEqual(owned,before)

    def test_v2_contract_is_opt_in_and_selected_string_forgery_still_validates(self):
        _,_,_,legacy=build(references=REFERENCE)
        with self.assertRaisesRegex(ValueError,'Version2'):movement.intervene(legacy,v2_controls())
        _,_,_,owned=build_v2(v2_documents(coattack=True))
        with self.assertRaisesRegex(ValueError,'Version2'):movement.intervene(owned,controls(0))
        bad=deepcopy(owned);_,ci=movement._string_paths(bad,TARGET)[TARGET[0]]
        bad['owned_parameters']['source_choices'][ci]['parameter']['normalized']='2'
        # The chosen note would occupy an unchanged chord member's string.
        # This must fail inverse validation, even for all-zero controls.
        snapshot=deepcopy(bad)
        with self.assertRaises(ValueError):movement.intervene(bad,v2_controls())
        self.assertEqual(bad,snapshot)


if __name__=='__main__':unittest.main()
