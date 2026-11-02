"""Authored relation/ownership tests; these fixtures are not artist evidence."""
from copy import deepcopy
import json
import random
import unittest

import musical_cell_development as cell
import melodic_movement_ownership as movement
import backing_pitch_ownership as backing
from connected_tier2 import analyze, strip_lower
from source_fact_tier1 import extract_documents, project_documents
from source_observation_evidence import digest


def instances():
    shapes = [(67,60,55,69),(64,60,53,63)]
    return [dict(pitches=list(map(str,[high,center,low]*3+[developed,center,low]*2+[center])),
                 timing=[dict(onset_q=str(i+start),duration_q='1') for i in range(16)])
            for start,(high,center,low,developed) in zip((0,16),shapes)]


class MusicalCellDevelopmentRelationTests(unittest.TestCase):
    def test_fit_is_one_shared_role_relation_without_note_vector(self):
        source = instances(); model = cell.fit(source)
        self.assertEqual(cell.realize(model),source)
        self.assertEqual(model['center_pitch'],'60')
        self.assertEqual(model['structure'],dict(period=3,cell_count=5,development_start=3,
            role_order=['OUTER','CENTER','LOW'],ending_role='CENTER'))
        self.assertEqual(model['instances'][0]['outer_interval'],'7')
        self.assertEqual(model['instances'][1]['outer_interval'],'4')
        self.assertNotIn('pitches',json.dumps(model))
        self.assertNotIn('residual',json.dumps(model))

    def test_phase_changes_cells_not_development_or_ending(self):
        model = cell.fit(instances()); changed = cell.phase_relation(model,1,1)
        result = cell.realize(changed)
        self.assertEqual(result[0],instances()[0])
        self.assertEqual(result[1]['pitches'],list(map(str,[60,53,64]*3+[60,53,63]*2+[60])))
        self.assertEqual(result[1]['timing'],instances()[1]['timing'])
        self.assertEqual(changed['structure'],model['structure'])
        self.assertEqual(model,cell.fit(instances()))

    def test_live_shared_center_reaches_all_cells_and_both_endings(self):
        model = cell.phase_relation(cell.fit(instances()),1,1)
        before = cell.realize(model); model['center_pitch']='62'
        after = cell.realize(json.loads(json.dumps(model)))
        for original,current in zip(before,after):
            self.assertEqual([int(p)+2 for p in original['pitches']],list(map(int,current['pitches'])))
            self.assertEqual(current['pitches'][-1],'62')
            self.assertEqual(current['timing'],original['timing'])

    def test_development_is_only_outer_in_final_cells(self):
        model = cell.phase_relation(cell.fit(instances()),1,1)
        before = cell.realize(model); model['instances'][1]['development_interval']='2'
        after = cell.realize(model)
        changed = [i for i,(a,b) in enumerate(zip(before[1]['pitches'],after[1]['pitches']))if a!=b]
        self.assertEqual(changed,[11,14])
        self.assertEqual(after[1]['pitches'][-1],'60')
        self.assertEqual(before[0],after[0])

    def test_outlier_shared_center_ending_and_timing_mismatches_refuse(self):
        for kind in ('pitch','center','ending','duration','onset'):
            source = instances()
            if kind=='pitch':source[0]['pitches'][6]='68'
            if kind=='center':source[1]['pitches']=[str(int(p)+1)for p in source[1]['pitches']]
            if kind=='ending':source[1]['pitches'][-1]='53'
            if kind=='duration':source[1]['timing'][4]['duration_q']='1/2'
            if kind=='onset':source[1]['timing'][4]['onset_q']='41/2'
            snapshot=deepcopy(source)
            with self.subTest(kind=kind),self.assertRaises(ValueError):cell.fit(source)
            self.assertEqual(source,snapshot)

    def test_constant_outer_does_not_invent_a_development_boundary(self):
        source=instances()
        for row in source:
            for i in (9,12):row['pitches'][i]=row['pitches'][0]
        with self.assertRaisesRegex(ValueError,'found 4'):cell.fit(source)

    def test_types_extra_payload_and_invalid_role_coordinates_refuse(self):
        model=cell.fit(instances())
        for change in (lambda m:m.update(pitches=['60']*32),
                       lambda m:m['instances'][0].update(phase=True),
                       lambda m:m['instances'][0].update(low_interval='0'),
                       lambda m:m['instances'][0].update(development_interval='-7'),
                       lambda m:m['rhythm'].update(span_q='3.0'),
                       lambda m:m['structure'].update(development_start=True)):
            bad=deepcopy(model);change(bad)
            with self.assertRaises(ValueError):cell.realize(bad)
        for phase in (-1,3,True,None):
            with self.assertRaises(ValueError):cell.phase_relation(model,1,phase)


SONG=980213
ROOTS=[f'event:{SONG}:0:{bar}:0:{beat}:0'for bar in range(1,9)for beat in range(4)]
PEERS=[ref.replace(f':{SONG}:0:',f':{SONG}:1:')for ref in ROOTS]
FOREIGN=f'event:{SONG}:2:9:0:0:0'
FOREIGN_BACKING=f'event:{SONG}:3:9:0:0:0'


def authored_score():
    pitches=[int(p)for row in instances()for p in row['pitches']]
    def rest():return dict(duration=[1,1],notes=[dict(rest=True)])
    def bar(beats):return dict(signature=[4,4],voices=[dict(beats=beats)])
    def beat(pitch,tuning,duration=(1,4)):
        string=next(i for i,base in enumerate(tuning)if 0<=pitch-base<=30)
        return dict(duration=list(duration),notes=[dict(string=string,fret=pitch-tuning[string])])
    metadata=dict(songId=SONG,revisionId=1,artist='Authored fixture',title='Cell development',
                  tracks=[dict(name=f'Part {i}',instrumentId=34 if i==3 else 27)for i in range(4)])
    docs={'metadata.json':metadata}
    for part,tuning in enumerate(([50,45,40,35,30,25],[45,40,35,30,25,20],[50,45,40,35,30,25],[40,35,30,25])):
        if part<2:
            values=[p-12*part for p in pitches]
            bars=[bar([beat(p,tuning)for p in values[i:i+4]])for i in range(0,32,4)]+[bar([rest()])]
        else:
            bars=[bar([rest()])for _ in range(8)]+[bar([beat(65 if part==2 else 40,tuning,duration=(1,1))])]
        docs[f'track-{part}.json']=dict(songId=SONG,revisionId=1,partId=part,
            instrumentId=34 if part==3 else 27,tuning=list(tuning),frets=30,measures=bars)
    return docs


def build(*, admit_peers=True, docs=None, legacy=False):
    docs=authored_score() if docs is None else docs;lower=extract_documents(docs)
    links=[dict(occurrence_ref=peer,backing_ref=root)for peer,root in zip(PEERS,ROOTS)]
    links.append(dict(occurrence_ref=FOREIGN,backing_ref=FOREIGN_BACKING))
    ordinary=strip_lower(analyze(lower,backing_bindings=links))
    t2=movement.lift(ordinary,ROOTS,register_controls=True)
    if legacy:
        # Persisted /1 format predates peer execution contracts. This authored
        # fixture retains its original facts, not a migration through /2.
        groups=[ROOTS[:16],ROOTS[16:]];relationship=cell.fit(instances())
        contexts=[movement._original_register_context(lower,t2['source_origin'],PEERS)] if admit_peers else []
        obs=dict(origin=deepcopy(t2['source_origin']),original_relation_sha256=digest(relationship),
                 bindings_sha256=digest(groups),dependent_contexts=contexts)
        obs['evidence_sha256']=digest(obs)
        child=deepcopy(t2);del child['owned_parameters'][movement.SLOT]['parameters']
        t3=dict(tier=3,schema=cell.LEGACY_TIER3_SCHEMA,lower_tier=child,relationship=relationship,
                instance_attack_refs=groups,observations=obs)
    else:
        t3=cell.lift(t2,[ROOTS[:16],ROOTS[16:]],dependent_refs=PEERS if admit_peers else ())
    return docs,lower,t2,t3


def controls(level=100,seed=0,phase=1):
    return dict(context_policy=cell.POLICY,variation=level,instance=1,phase=phase,seed=seed)


def changed_seed(level=100):
    # Authored fixture chooses by public RNG streams, before inspecting output.
    return next(seed for seed in range(32)
                if random.Random(f'musical-cell-phase:release:{seed}').random()<level/100
                and random.Random(f'musical-cell-phase:selection:{seed}').randrange(2)==1)


class MusicalCellDevelopmentOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.docs,cls.lower,cls.t2,cls.t3=build()

    def test_real_tier_boundary_exact_whole_score_and_single_authority(self):
        t3=deepcopy(self.t3)
        self.assertEqual(t3['tier'],3)
        self.assertEqual(t3['schema'],cell.TIER3_SCHEMA)
        self.assertNotIn('parameters',t3['lower_tier']['owned_parameters'][movement.SLOT])
        self.assertEqual(cell.expand(t3),self.t2)
        self.assertEqual(cell.reconstruct(t3,{'variation':0}),self.lower)
        self.assertEqual(project_documents(cell.reconstruct(t3,controls(0))),self.docs)
        self.assertNotIn('lower_tier_cache',t3['lower_tier'])
        self.assertNotIn('pitches',json.dumps(t3['relationship']))

    def test_phase_changes_only_second_instance_and_explicit_direct_peers(self):
        source=deepcopy(self.t3);edited,report=cell.intervene(source,controls(seed=changed_seed()))
        self.assertTrue(report['changed']);self.assertTrue(report['released'])
        self.assertEqual(report['chosen_phase'],1)
        lower=cell.reconstruct(edited,{'variation':0});docs=project_documents(lower)
        expected=[60,53,64]*3+[60,53,63]*2+[60]
        for part,shift in ((0,0),(1,-12)):
            track=docs[f'track-{part}.json'];actual=[]
            for measure in track['measures'][4:8]:
                for b in measure['voices'][0]['beats']:
                    n=b['notes'][0];actual.append(track['tuning'][n['string']]+n['fret'])
            self.assertEqual(actual,[p+shift for p in expected])
        self.assertEqual(docs['track-0.json']['measures'][:4],self.docs['track-0.json']['measures'][:4])
        self.assertEqual(docs['track-1.json']['measures'][:4],self.docs['track-1.json']['measures'][:4])
        self.assertEqual(docs['track-2.json'],self.docs['track-2.json'])
        self.assertEqual(docs['track-3.json'],self.docs['track-3.json'])
        allowed=set()
        for ref in ROOTS[16:]+PEERS[16:]:
            _,_,part,bar,voice,beat,note=ref.split(':')
            pointer=f'track-{part}.json#/measures/{int(bar)-1}/voices/{voice}/beats/{beat}/notes/{note}'
            allowed.update(pointer+'/'+field for field in ('string','fret'))
        for old,new in zip(self.lower['facts'],lower['facts']):
            if old==new:continue
            self.assertIn(old['id'],allowed)
            self.assertIn(old['id'].rsplit('/',1)[-1],('fret','string'))
            self.assertEqual({k:v for k,v in old.items()if k!='value'},{k:v for k,v in new.items()if k!='value'})
        self.assertTrue(any(self.docs['track-1.json']['measures'][b]['voices'][0]['beats'][n]['notes'][0]['string']!=
                            docs['track-1.json']['measures'][b]['voices'][0]['beats'][n]['notes'][0]['string']
                            for b in range(4,8)for n in range(4)))
        self.assertEqual(edited['observations'],self.t3['observations'])
        self.assertEqual(edited['lower_tier']['musical_relationships']['relationships'],self.t2['musical_relationships']['relationships'])
        self.assertEqual(source,self.t3)

    def test_zero_half_full_and_saved_current_state(self):
        zero,report=cell.intervene(self.t3,controls(0,changed_seed()))
        self.assertEqual(zero,self.t3);self.assertFalse(report['released'])
        half,report=cell.intervene(self.t3,controls(50,changed_seed(50)))
        self.assertTrue(report['changed'])
        saved=json.loads(json.dumps(half));current,report=cell.intervene(saved,controls(0,phase=0))
        self.assertEqual(current,saved);self.assertFalse(report['released'])
        same,report=cell.intervene(saved,controls(100,phase=1))
        self.assertEqual(same,saved);self.assertTrue(report['released']);self.assertEqual(report['candidate_count'],1)
        restored,report=cell.intervene(saved,controls(100,changed_seed(),phase=0))
        # Returning the musical phase does not promise the original fingering:
        # the shared contact proposal prefers the CURRENT feasible string.
        self.assertEqual(cell.realize(restored['relationship']),cell.realize(self.t3['relationship']))
        restored_lower=cell.reconstruct(restored,{'variation':0})
        self.assertEqual(len(restored_lower['facts']),len(self.lower['facts']))
        self.assertEqual(cell.expand(restored)['owned_parameters'][movement.SLOT],self.t2['owned_parameters'][movement.SLOT])
        self.assertEqual(restored['observations'],self.t3['observations'])
        coincidence=next(seed for seed in range(32)if random.Random(f'musical-cell-phase:selection:{seed}').randrange(2)==0)
        current,report=cell.intervene(self.t3,controls(100,coincidence))
        self.assertEqual(current,self.t3);self.assertTrue(report['released']);self.assertFalse(report['changed'])

    def test_unrelated_owner_survives_and_still_propagates(self):
        edited,_=cell.intervene(self.t3,controls(seed=changed_seed()))
        model=json.loads(json.dumps(edited))
        index=backing._index(movement._body(model['lower_tier']['musical_relationships']))
        index[FOREIGN_BACKING][0]['bass_register_anchor']='41'
        output=project_documents(cell.reconstruct(model,{'variation':0}))
        self.assertEqual(output['track-2.json']['measures'][8]['voices'][0]['beats'][0]['notes'][0]['fret'],16)
        self.assertEqual(output['track-3.json']['measures'][8]['voices'][0]['beats'][0]['notes'][0]['fret'],1)
        self.assertEqual(model['observations'],edited['observations'])
        self.assertEqual(model['lower_tier']['musical_relationships']['relationships'],edited['lower_tier']['musical_relationships']['relationships'])

    def test_shared_center_and_live_ending_propagate_after_reload(self):
        model=json.loads(json.dumps(self.t3));model['relationship']['center_pitch']='61'
        lower=cell.reconstruct(model,{'variation':0});docs=project_documents(lower)
        for part in (0,1):
            for bar in (3,7):
                n=docs[f'track-{part}.json']['measures'][bar]['voices'][0]['beats'][3]['notes'][0]
                self.assertEqual(docs[f'track-{part}.json']['tuning'][n['string']]+n['fret'],61-12*part)
        self.assertEqual(model['observations'],self.t3['observations'])

    def test_missing_peer_permission_refuses_atomically(self):
        _,_,_,model=build(admit_peers=False);snapshot=deepcopy(model)
        with self.assertRaises(ValueError):cell.intervene(model,controls(seed=changed_seed()))
        self.assertEqual(model,snapshot)

    def test_peer_pull_off_cannot_be_broken_by_phase_placement(self):
        docs=authored_score()
        docs['track-1.json']['measures'][4]['voices'][0]['beats'][0]['notes'][0]['hp']=True
        _,lower,t2,model=build(docs=docs);snapshot=deepcopy(model)
        scope=movement.execution.build(lower,PEERS)
        self.assertTrue(scope['obligations'])
        self.assertEqual(cell.reconstruct(model,{'variation':0}),lower)
        wanted=cell.expand(cell.phase_candidate(model,1,1))['owned_parameters'][movement.SLOT]['parameters']
        with self.assertRaisesRegex(ValueError,'EXECUTION'):
            movement._placed_candidate(t2,wanted,lower,dependent_contexts=model['observations']['dependent_contexts'])
        with self.assertRaisesRegex(ValueError,'EXECUTION'):
            cell.intervene(model,controls(seed=4))
        self.assertEqual(model,snapshot)

    def test_saved_peer_contact_corruption_refuses_even_when_pitch_is_exact(self):
        docs=authored_score()
        docs['track-1.json']['measures'][4]['voices'][0]['beats'][0]['notes'][0]['hp']=True
        _,lower,_,model=build(docs=docs)
        pi,ci=movement._string_paths(cell.expand(model),[PEERS[16]])[PEERS[16]]
        model['lower_tier']['owned_parameters']['source_choices'][ci]['parameter'].update(normalized='1',negative_zero=False)
        model=json.loads(json.dumps(model));snapshot=deepcopy(model)
        # Existing pitch ownership accepts the same pitch on another string.
        current=project_documents(movement._realize(cell.expand(model)))['track-1.json']
        note=current['measures'][4]['voices'][0]['beats'][0]['notes'][0]
        self.assertEqual(current['tuning'][note['string']]+note['fret'],52)
        with self.assertRaisesRegex(ValueError,'EXECUTION'):cell.reconstruct(model,{'variation':0})
        self.assertEqual(model,snapshot)

    def test_untouched_peer_pull_off_survives_edit_reload_and_next_edit(self):
        docs=authored_score()
        docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['hp']=True
        _,lower,_,model=build(docs=docs)
        scope=movement.execution.build(lower,PEERS)
        edited,report=cell.intervene(model,controls(seed=changed_seed()))
        self.assertTrue(report['changed'])
        saved=json.loads(json.dumps(edited));after=cell.reconstruct(saved,{'variation':0})
        movement.execution.validate(scope,after,PEERS)
        again,_=cell.intervene(saved,controls(seed=changed_seed(),phase=0))
        movement.execution.validate(scope,cell.reconstruct(again,{'variation':0}),PEERS)
        self.assertEqual(again['observations'],model['observations'])

    def test_new_peer_execution_contract_cannot_be_omitted(self):
        model=deepcopy(self.t3)
        del model['observations']['dependent_execution']
        model['observations']['evidence_sha256']=digest({k:v for k,v in model['observations'].items()if k!='evidence_sha256'})
        with self.assertRaisesRegex(ValueError,'provenance'):cell.reconstruct(model,{'variation':0})

    def test_legacy_original_unresolved_exit_slide_remains_exact_at_zero(self):
        docs=authored_score()
        docs['track-1.json']['measures'][4]['voices'][0]['beats'][0]['notes'][0]['slide']='downwards'
        _,lower,_,old=build(docs=docs,legacy=True);snapshot=deepcopy(old)
        self.assertEqual(cell.reconstruct(old,{'variation':0}),lower)
        zero,report=cell.intervene(old,controls(0,seed=4))
        self.assertEqual(zero,old);self.assertFalse(report['changed'])
        with self.assertRaisesRegex(ValueError,'EXECUTION'):
            cell.intervene(old,controls(seed=4))
        self.assertEqual(old,snapshot)

    def test_legacy_plain_saves_work_but_techniques_require_original_contract(self):
        def legacy(model):
            result=deepcopy(model);result['schema']=cell.LEGACY_TIER3_SCHEMA
            del result['observations']['dependent_execution']
            result['observations']['evidence_sha256']=digest({k:v for k,v in result['observations'].items()if k!='evidence_sha256'})
            return result
        old=legacy(self.t3)
        edited,_=cell.intervene(old,controls(seed=changed_seed()))
        self.assertEqual(cell.reconstruct(json.loads(json.dumps(edited)),{'variation':0}),
                         cell.reconstruct(cell.intervene(self.t3,controls(seed=changed_seed()))[0],{'variation':0}))
        docs=authored_score()
        docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['hp']=True
        _,lower,_,model=build(docs=docs);old=legacy(model);snapshot=deepcopy(old)
        self.assertEqual(cell.reconstruct(old,{'variation':0}),lower)
        with self.assertRaisesRegex(ValueError,'LEGACY_PEER_EXECUTION'):
            cell.intervene(old,controls(seed=changed_seed()))
        self.assertEqual(old,snapshot)
        edited,_=cell.intervene(model,controls(seed=changed_seed()))
        with self.assertRaisesRegex(ValueError,'LEGACY_PEER_EXECUTION'):
            cell.reconstruct(legacy(edited),{'variation':0})

    def test_duplicate_old_parameters_bindings_origin_and_timing_corruption_refuse(self):
        changes=(lambda m:m['lower_tier']['owned_parameters'][movement.SLOT].update(parameters=deepcopy(self.t2['owned_parameters'][movement.SLOT]['parameters'])),
                 lambda m:m['instance_attack_refs'][1].reverse(),
                 lambda m:m['observations']['origin'].update(facts_sha256='a'*64),
                 lambda m:m['relationship']['instances'][1].update(onset_q='17'))
        for change in changes:
            model=deepcopy(self.t3);change(model);snapshot=deepcopy(model)
            with self.assertRaises(ValueError):cell.reconstruct(model,{'variation':0})
            self.assertEqual(model,snapshot)
        wrong=deepcopy(self.lower)
        changed=next(row for row in wrong['facts']if row['id'].endswith('/measures/0/voices/0/beats/0/notes/0/fret'))
        changed['value']+=1
        with self.assertRaises(ValueError):cell.validate_execution(self.t3,wrong)

    def test_individual_boundary_refuses_lower_payload_and_wrong_tier(self):
        for key,value in [('input',self.lower),('derived_views',{}),('lower_tier_cache',{}),('tier',3),('tier',2.0)]:
            model=deepcopy(self.t3);model['lower_tier'][key]=deepcopy(value)
            with self.subTest(key=key),self.assertRaises(ValueError):cell.expand(model)
        self.assertEqual(self.t3['lower_tier'],strip_lower(self.t3['lower_tier']))

    def test_saved_peer_span_obligation_is_checked_by_inverse(self):
        docs=authored_score()
        docs['track-1.json']['measures'][0]['voices'].append(dict(beats=[
            dict(duration=[1,8],notes=[dict(rest=True)]),
            dict(duration=[3,4],notes=[dict(string=5,fret=5)]),
            dict(duration=[1,8],notes=[dict(rest=True)])]))
        # The existing experiment envelope comes from source coattacks. Supply
        # an actual unselected coattack witnessing span5; a held overlap alone
        # does not establish that envelope in the existing inventory.
        docs['track-1.json']['measures'][8]['voices'][0]['beats']=[
            dict(duration=[1,1],notes=[dict(string=0,fret=10),dict(string=5,fret=5)])]
        _,_,_,model=build(docs=docs)
        peer=PEERS[1]
        pi,ci=movement._string_paths(cell.expand(model),[peer])[peer]
        model['lower_tier']['owned_parameters']['source_choices'][ci]['parameter'].update(normalized='4',negative_zero=False)
        # Pitch48 on string4/fret23 is legal in isolation and preserves its
        # backing link, but widens the held-note span beyond original5.
        self.assertEqual(model['observations']['dependent_contexts'][0]['max_simultaneous_span'],'5')
        movement._realize(cell.expand(model))
        snapshot=deepcopy(model)
        with self.assertRaisesRegex(ValueError,'Dependent contact exceeds'):cell.reconstruct(model,{'variation':0})
        self.assertEqual(model,snapshot)

    def test_invalid_controls_and_reference_replacement_refuse(self):
        for key,value in [('variation',True),('variation',None),('variation',101),('seed',True),('instance',0),('instance',True),('phase',3)]:
            c=controls();c[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):cell.intervene(self.t3,c)
        with self.assertRaises(ValueError):cell.lift(self.t3,[ROOTS[:16],ROOTS[16:]])
        with self.assertRaises(ValueError):cell.lift(self.t2,[ROOTS[:16],ROOTS[16:]],dependent_refs=[FOREIGN])


if __name__=='__main__':unittest.main()
