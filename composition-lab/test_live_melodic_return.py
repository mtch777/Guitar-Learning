"""Authored live relative direction through actual material/T4/T5 inverses."""
from copy import deepcopy
import json
import unittest

import test_musical_cell_development as fixture
import musical_support_material as material
import support_material_uses as uses
import support_arrangement as single
import section_arrangements as sections
import thematic_return as theme
import melodic_return_relation as relation
import material_rhythm_control as rhythm
from source_fact_tier1 import project_documents

SOURCE='material-use:2'
RETURN='material-use:3'
RHYTHM_RETURN='material-use:1'
CORRESPONDENCE=dict(source_section=dict(first_bar=1,last_bar=4,label='Chorus'),
                    return_section=dict(first_bar=5,last_bar=8,label='Chorus'))


def build_live(*, tremolo=False, return_tremolo=None):
    """Real small model: paired support, separate approach and retained cell."""
    docs=fixture.authored_score()
    for part in (2,3):
        track=docs[f'track-{part}.json']
        for bar in (1,5):
            track['measures'][bar-1]['voices'][0]['beats']=[dict(type=4,duration=[1,4],velocity='f',
                notes=[dict(string=0,fret=p-track['tuning'][0]),dict(string=1,fret=p+7-track['tuning'][1])])
                for p in (50,52,50,53)]
    docs['metadata.json']['tracks'].extend([dict(name='Pulse',instrumentId=128),dict(name='Approach',instrumentId=27)])
    docs['track-4.json']=dict(songId=fixture.SONG,revisionId=1,partId=4,instrumentId=128,tuning=[],
        measures=[dict(signature=[4,4],voices=[dict(beats=[dict(type=8,duration=[1,8],notes=[dict(string=0,fret=36)])
            for _ in range(8)])])for _ in range(9)])
    docs['track-5.json']=dict(songId=fixture.SONG,revisionId=1,partId=5,instrumentId=27,tuning=[60],frets=24,
        measures=[dict(signature=[4,4],voices=[dict(beats=[dict(type=1,duration=[1,1],notes=[dict(rest=True)])])])for _ in range(9)])
    for bar in (2,6):
        docs['track-5.json']['measures'][bar-1]['voices'][0]['beats']=[dict(type=kind,duration=length,
            notes=[dict(string=0,fret=fret)])for kind,length,fret in ((4,[1,4],0),(4,[1,4],2),(2,[1,2],4))]
        if tremolo:
            for beat in docs['track-5.json']['measures'][bar-1]['voices'][0]['beats']:
                beat['notes'][0]['tremolo']=deepcopy(return_tremolo if bar==6 and return_tremolo is not None else [1,16])
    for name,track in docs.items():
        if not name.startswith('track-'):continue
        for bar,label in ((1,'Chorus'),(5,'Chorus'),(9,'Ending')):track['measures'][bar-1]['marker']=dict(text=label)
    _,lower,_,cell=fixture.build(docs=docs)
    t3=uses.lift(material.lift_t3(cell,[dict(parts=[2,3],first_bar=b,last_bar=b)for b in(1,5)]+
        [dict(parts=[5],first_bar=b,last_bar=b)for b in(2,6)]))
    contexts=[dict(id='authored:C-major',tonic_pc=0,intervals=[0,2,4,5,7,9,11])]
    for uid,bar in((SOURCE,2),(RETURN,6)):
        refs=[f'event:{fixture.SONG}:5:{bar}:0:{beat}:0'for beat in range(3)]
        t3=uses.lift_approach(t3,uid,refs,contexts,'authored-fixture-explicit-collection')
    t4=single.lift(t3,'material-use:0',[0,1])
    t4=sections.extend(t4,[],[dict(use_id=RHYTHM_RETURN,eligible_materials=[0,1])],
        equivalent_uses=[(RHYTHM_RETURN,0)])
    old=theme.candidate(theme.fit(t4,'material-use:0',RHYTHM_RETURN),'recall')
    old=rhythm.lift_composed(old,RHYTHM_RETURN)
    return old,theme.fit_approach(old,SOURCE,RETURN,CORRESPONDENCE)


def pitches(model,bar):
    docs=project_documents(theme.reconstruct(model,{'variation':0}));track=docs['track-5.json']
    return [track['tuning'][n['string']]+n['fret']for b in track['measures'][bar-1]['voices'][0]['beats']for n in b['notes']]


class DirectionEquationTests(unittest.TestCase):
    def test_technique_address_normalization_preserves_unknown_payload(self):
        note='track-8.json#/measures/12/voices/1/beats/3/notes/0';beat=note.rsplit('/notes/',1)[0]
        pointer=note.split('#',1)[1]+'/tremolo'
        declaration=dict(owner_ref=note,structure=[dict(id=note+'/tremolo',pointer=pointer,
            future=dict(literal_pointer=pointer))],parameters=[dict(fact_ref=note+'/tremolo/1',
                parameter=dict(normalized='16',negative_zero=False))],future=dict(literal_pointer=pointer))
        frozen=deepcopy(declaration);result=relation._technique_signature(declaration,note,beat)
        self.assertEqual(result['structure'][0]['pointer'],'NOTE/tremolo')
        self.assertEqual(result['structure'][0]['future'],declaration['structure'][0]['future'])
        self.assertEqual(result['future'],declaration['future'])
        self.assertEqual(result['parameters'][0]['parameter'],declaration['parameters'][0]['parameter'])
        self.assertEqual(declaration,frozen)

    def test_effective_direction_not_equal_mode_strings(self):
        for source_original in(-1,1):
            for target_original in(-1,1):
                for source_mode in('original','flip'):
                    sd=source_original*(1 if source_mode=='original'else-1)
                    for intention,factor in(('same',1),('opposite',-1)):
                        mode=relation.direction_relation(source_original_direction=source_original,source_mode=source_mode,
                            return_original_direction=target_original,independent_mode='flip',mode=intention)
                        self.assertEqual(target_original*(1 if mode=='original'else-1),sd*factor)
                    self.assertEqual(relation.direction_relation(source_original_direction=source_original,source_mode=source_mode,
                        return_original_direction=target_original,independent_mode='flip',mode='independent'),'flip')


class LiveMelodicReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old,cls.live=build_live()

    def test_exact_zero_and_one_return_direction_owner(self):
        self.assertEqual(theme.expand(self.live),theme.expand(self.old))
        self.assertEqual(theme.reconstruct(self.live,{'variation':0}),theme.reconstruct(self.old,{'variation':0}))
        self.assertEqual(self.live['relationship'],self.old['relationship'])
        target=next(u for u in self.live['lower_tier']['lower_tier']['uses']if u['id']==RETURN)
        self.assertNotIn('approach_mode',target)
        self.assertEqual(self.live['approach_relationship']['independent_mode'],'original')

    def test_matching_tremolo_at_different_bars_keeps_values_and_rejects_mismatch(self):
        old,live=build_live(tremolo=True)
        self.assertEqual(theme.expand(live),theme.expand(old))
        changed=theme.change_approach_source(theme.approach_candidate(live,'opposite'),'flip')
        before=project_documents(theme.reconstruct(old,{'variation':0}))
        after=project_documents(theme.reconstruct(changed,{'variation':0}))
        for bar in (2,6):
            a=before['track-5.json']['measures'][bar-1]['voices'][0]['beats']
            b=after['track-5.json']['measures'][bar-1]['voices'][0]['beats']
            self.assertEqual([beat['notes'][0]['tremolo']for beat in a],[[1,16]]*3)
            self.assertEqual([beat['notes'][0]['tremolo']for beat in b],[[1,16]]*3)
        frozen=deepcopy(live)
        with self.assertRaisesRegex(ValueError,'musical structure'):
            build_live(tremolo=True,return_tremolo=[1,8])
        self.assertEqual(live,frozen)

    def test_opposite_survives_reload_and_follows_later_source_flip(self):
        linked=theme.approach_candidate(self.live,'opposite')
        self.assertEqual(pitches(linked,2),[60,62,64]);self.assertEqual(pitches(linked,6),[67,65,64])
        changed=theme.change_approach_source(json.loads(json.dumps(linked)),'flip')
        self.assertEqual(pitches(changed,2),[67,65,64]);self.assertEqual(pitches(changed,6),[60,62,64])
        self.assertEqual(changed['relationship'],self.live['relationship'])
        self.assertEqual(changed['lower_tier']['choices'],self.live['lower_tier']['choices'])
        self.assertEqual(changed['lower_tier']['lower_tier']['materials'],self.live['lower_tier']['lower_tier']['materials'])
        self.assertEqual(changed['lower_tier']['lower_tier']['observations'],self.live['lower_tier']['lower_tier']['observations'])

    def test_independent_return_stays_fixed_after_source_flip(self):
        changed=theme.change_approach_source(json.loads(json.dumps(self.live)),'flip')
        self.assertEqual(pitches(changed,2),[67,65,64]);self.assertEqual(pitches(changed,6),[60,62,64])
        same=theme.approach_candidate(changed,'same')
        self.assertEqual(pitches(same,6),[67,65,64])

    def test_packing_preserves_rhythm_and_refuses_competing_authority(self):
        linked=theme.approach_candidate(self.live,'opposite')
        t3=sections.expand(theme.expand(linked))
        selected=next(u for u in t3['uses']if u['id']==RHYTHM_RETURN);selected['rhythm_offset_q']='1/2'
        changed=theme.pack_uses(linked,t3)
        self.assertEqual(sections.expand(theme.expand(changed)),t3)
        theme.reconstruct(changed,{'variation':0})
        bad=deepcopy(t3);next(u for u in bad['uses']if u['id']==RETURN)['approach_mode']='original'
        with self.assertRaisesRegex(ValueError,'live return'):theme.pack_uses(linked,bad)
        bad=deepcopy(t3);next(u for u in bad['uses']if u['id']=='material-use:0')['material_ref']=1
        with self.assertRaisesRegex(ValueError,'higher-owned'):theme.pack_uses(linked,bad)

    def test_correspondence_and_existing_owners_cannot_be_rewritten(self):
        frozen=deepcopy(self.live)
        for kind in('competing-mode','definition','annotation','unknown-payload','section-label','section-boundary','section-clock'):
            bad=deepcopy(self.live);t3=bad['lower_tier']['lower_tier']
            if kind=='competing-mode':next(u for u in t3['uses']if u['id']==RETURN)['approach_mode']='original'
            elif kind=='definition':t3['materials'][2]['approach']['relation']['arrival_pitch']='65'
            elif kind=='annotation':bad['approach_relationship']['correspondence']['annotation_sha256']='wrong'
            elif kind.startswith('section-'):
                field={'section-label':'label','section-boundary':'first_bar','section-clock':'start_q'}[kind]
                bad['approach_relationship']['correspondence']['source_section'][field]='Invented'if field=='label'else 2
            else:bad['approach_relationship']['notes']=[60,62,64]
            with self.subTest(kind=kind),self.assertRaises(ValueError):theme.expand(bad)
        wrong=deepcopy(CORRESPONDENCE);wrong['source_section']['label']='Invented'
        with self.assertRaisesRegex(ValueError,'annotations'):theme.fit_approach(self.old,SOURCE,RETURN,wrong)
        self.assertEqual(self.live,frozen)

    def test_zero_fifty_hundred_release_semantics_and_atomic_failure(self):
        flags=set();choices=set()
        for release in(0,50,100):
            for seed in range(4):
                out,report=theme.intervene_approach(self.live,dict(release=release,mode='opposite',seed=seed))
                if release==0:self.assertEqual(out,self.live)
                if release==100:self.assertTrue(report['released'])
                if release==50:flags.add(report['released'])
                choices.add(report['chosen']);self.assertEqual(report['changed'],out!=self.live)
        self.assertEqual(flags,{False,True});self.assertEqual(choices,{'independent','opposite'})
        frozen=deepcopy(self.live)
        with self.assertRaises(ValueError):theme.intervene_approach(self.live,dict(release=100,mode='invent',seed=0))
        self.assertEqual(self.live,frozen)

    def test_existing_guitar_recall_changes_keep_melodic_relationship(self):
        linked=theme.approach_candidate(self.live,'opposite')
        changed=theme.change_source(linked,1)
        self.assertEqual(changed['approach_relationship'],linked['approach_relationship'])
        self.assertEqual(pitches(changed,6),[67,65,64])
        independent=theme.candidate(changed,'independent')
        self.assertEqual(independent['approach_relationship'],linked['approach_relationship'])


if __name__=='__main__':unittest.main()
