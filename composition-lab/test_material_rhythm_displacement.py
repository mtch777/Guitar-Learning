"""Authored clock/notation tests; no artist or listening-quality claim."""
from copy import deepcopy
from fractions import Fraction as F
import json
import unittest

import connected_tier2 as connected
import material_rhythm_displacement as displacement
import musical_support_material as material
import test_musical_support_material as fixture
import test_musical_cell_development as cell_fixture
from source_fact_tier1 import extract_documents, project_documents
from source_observation_evidence import digest
from technique_observation_relations import scalar_relation


def build(docs=None, *, first=1,last=1):
    docs=deepcopy(docs if docs is not None else fixture.authored()[0])
    for part in (2,3):
        for m in docs[f'track-{part}.json']['measures'][first-1:last]:
            for beat in m['voices'][0]['beats']:
                beat.setdefault('type',beat['duration'][1])
    _,lower,t2,_=cell_fixture.build(docs=docs)
    definition=material.fit(t2,parts=[2,3],first_bar=first,last_bar=last,lower=lower)
    return docs,lower,t2,definition


def clocks(definition):
    expanded=material.expand(definition)
    rows={r['fact_ref']:r for r in expanded['source_choices']}
    return {s['beat_ref']:dict(duration=[scalar_relation('integer',parameter=rows[s['beat_ref']+f'/duration/{i}']['parameter'])for i in (0,1)],
        type=scalar_relation('integer',parameter=rows[s['beat_ref']+'/type']['parameter']),
        dots=scalar_relation('integer',parameter=rows[s['beat_ref']+'/dots']['parameter'])if s['beat_ref']+'/dots'in rows else None)
        for s in definition['slots']}


class DisplacementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs,cls.lower,cls.t2,cls.base=build()

    def test_same_clock_positive_offset_and_exact_zero_restore(self):
        original=deepcopy(self.base);changed,report=displacement.solve(self.base,'1/2')
        self.assertEqual(self.base,original)
        self.assertEqual(changed['pulse_shares'],['3/8','1/4','1/4','1/8'])
        self.assertEqual(len(report['shifted_pulses']),3)
        self.assertEqual(len(report['shifted_attacks']),6)
        self.assertEqual(len(report['added_notation_refs']),2)
        self.assertEqual(displacement.solve(json.loads(json.dumps(self.base)),'0')[0],self.base)
        self.assertEqual(displacement.solve(self.base,'0')[0],original)
        for key in('pitch_paths','voicings','bindings','slots','provenance','observed_execution'):
            self.assertEqual(changed[key],self.base[key])
        for part in(2,3):
            values=[clocks(changed)[f'track-{part}.json#/measures/0/voices/0/beats/{i}']for i in range(4)]
            self.assertEqual(values,[dict(duration=[3,8],type=4,dots=1),dict(duration=[1,4],type=4,dots=None),
                                     dict(duration=[1,4],type=4,dots=None),dict(duration=[1,8],type=8,dots=None)])

    def test_complete_existing_inverse_includes_new_dots_authority(self):
        changed,_=displacement.solve(self.base,'1/2')
        skeleton=material._remove(self.t2,[self.base['scope']])
        result=material.restore_fragments(skeleton,[material.expand(changed)])
        actual=connected.realize(connected.strip_lower(result));expected=deepcopy(self.docs)
        for part in(2,3):
            beats=expected[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
            beats[0].update(duration=[3,8],dots=1);beats[-1].update(duration=[1,8],type=8)
        self.assertEqual(actual,extract_documents(expected))
        self.assertEqual(result['source_origin'],self.t2['source_origin'])
        restored=material.restore_fragments(skeleton,[material.expand(displacement.solve(self.base,'0')[0])])
        self.assertEqual(connected.realize(connected.strip_lower(restored)),self.lower)

    def test_negative_offset_uses_same_equation(self):
        changed,report=displacement.solve(self.base,'-1/2')
        self.assertEqual(changed['pulse_shares'],['1/8','1/4','1/4','3/8'])
        self.assertTrue(report['changed'])
        self.assertTrue(all(r['after_q']==str(F(r['before_q'])-F(1,2))for r in report['shifted_pulses']))

    def test_coattacks_rests_and_later_release_are_preserved(self):
        docs=deepcopy(self.docs)
        for part in(2,3):
            track=docs[f'track-{part}.json'];beats=track['measures'][0]['voices'][0]['beats']
            for index in(0,2):beats[index]['notes'].append(dict(string=1,fret=62-track['tuning'][1]))
            for index in(1,3):beats[index]=dict(duration=[1,4],type=4,rest=True,notes=[dict(rest=True)])
            for b in beats:b['palmMute']=True
        _,_,_,base=build(docs);frozen=deepcopy(base)
        changed,report=displacement.solve(base,'1/2')
        self.assertEqual(changed['pulse_shares'],['3/8','1/4','1/8','1/4'])
        self.assertEqual(len(report['shifted_pulses']),2)
        self.assertEqual(len(report['shifted_attacks']),2)
        self.assertEqual(base,frozen)
        self.assertEqual(changed['lower_tier']['coattacks'],base['lower_tier']['coattacks'])
        self.assertEqual(changed['lower_tier']['technique_declarations'],base['lower_tier']['technique_declarations'])
        before=clocks(base);after=clocks(changed)
        for part in(2,3):
            tail=f'track-{part}.json#/measures/0/voices/0/beats/3'
            self.assertEqual(after[tail],before[tail])

    def test_source_fraction_scale_and_original_explicit_dots_presence(self):
        docs=deepcopy(self.docs)
        for part in(2,3):
            beats=docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
            beats[0]['duration']=[2,8]
        docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['dots']=0
        _,_,_,base=build(docs);changed,report=displacement.solve(base,'1/2')
        self.assertEqual([s['fraction_scale']for s in changed['slots']],[s['fraction_scale']for s in base['slots']])
        for part in(2,3):self.assertEqual(clocks(changed)[f'track-{part}.json#/measures/0/voices/0/beats/0']['duration'],[6,16])
        self.assertEqual(len(report['added_notation_refs']),1)
        self.assertEqual(displacement.solve(base,'0')[0],base)

    def test_existing_dotted_source_is_validated_and_resolved(self):
        docs=deepcopy(self.docs)
        for part in(2,3):
            beats=docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
            beats[0].update(duration=[3,8],type=4,dots=1)
            beats[1].update(duration=[1,8],type=8)
        _,_,_,base=build(docs);changed,_=displacement.solve(base,'1/2')
        self.assertEqual(clocks(changed)['track-2.json#/measures/0/voices/0/beats/0'],dict(duration=[1,2],type=2,dots=0))
        self.assertEqual(displacement.solve(base,'0')[0],base)

    def test_double_dotted_notation_and_fixed_later_bar(self):
        docs=deepcopy(self.docs)
        for part in(2,3):
            beats=docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
            beats[0].update(duration=[7,16],type=4,dots=2)
            beats[1].update(duration=[1,16],type=16)
        _,_,_,base=build(docs);changed,_=displacement.solve(base,'1/4')
        self.assertEqual(clocks(changed)['track-2.json#/measures/0/voices/0/beats/0'],dict(duration=[1,2],type=2,dots=0))
        self.assertEqual(clocks(changed)['track-2.json#/measures/0/voices/0/beats/3'],dict(duration=[3,16],type=8,dots=1))
        docs=deepcopy(self.docs)
        for part in(2,3):
            start=deepcopy(docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats'][0])
            docs[f'track-{part}.json']['measures'][1]['voices'][0]['beats']=[start,
                dict(duration=[3,4],type=2,dots=1,rest=True,notes=[dict(rest=True)])]
        _,_,_,base=build(docs,last=2);changed,report=displacement.solve(base,'1/2')
        self.assertEqual(changed['bar_spans_q'],['4','4'])
        self.assertTrue(all(F(r['before_q'])<4 for r in report['shifted_pulses']))
        self.assertEqual({k:v for k,v in clocks(base).items()if '/measures/1/'in k},
                         {k:v for k,v in clocks(changed).items()if '/measures/1/'in k})

    def test_active_grace_or_tuplet_notation_cannot_be_hidden_in_lower_choices(self):
        for field in('graceNote','tuplet'):
            bad=deepcopy(self.base);fragment=bad['lower_tier'];beat=bad['slots'][0]['beat_ref'];ref=beat+'/'+field
            old=next(r for r in fragment['source_structure']if r['id']==beat+'/type')
            row=deepcopy(old);row.update(id=ref,pointer=old['pointer'][:-len('/type')]+'/'+field,slot=field,type='boolean')
            fragment['source_structure'].append(row)
            next(r for r in fragment['source_structure']if r['id']==beat)['children'].append(ref)
            fragment['source_choices'].append(dict(fact_ref=ref,owner='source_notation_choice',parameter=scalar_relation('boolean',source=True)))
            fragment['coverage'].append(dict(fact_ref=ref,owner='source_notation_choice'))
            before=deepcopy(bad)
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'Unsupported active notation'):
                displacement.solve(bad,'1/2')
            self.assertEqual(bad,before)

    def test_nonzero_without_movable_attack_refuses_instead_of_false_creative_pass(self):
        for all_rest in(False,True):
            docs=deepcopy(self.docs)
            for part in(2,3):
                beats=docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
                for index in range(0 if all_rest else 1,len(beats)):
                    beats[index]=dict(duration=[1,4],type=4,rest=True,notes=[dict(rest=True)])
            _,_,_,base=build(docs);before=deepcopy(base)
            zero,report=displacement.solve(base,'0')
            self.assertEqual(zero,base);self.assertFalse(report['changed'])
            for offset in('1/2','-1/2'):
                with self.subTest(all_rest=all_rest,offset=offset),self.assertRaisesRegex(ValueError,'No internal pitched attack'):
                    displacement.solve(base,offset)
                self.assertEqual(base,before)

    def test_invalid_notation_is_rejected_even_at_zero(self):
        for kind in('type','dots','missing','duplicate'):
            bad=deepcopy(self.base);ref=bad['slots'][0]['beat_ref']+'/type'
            choice=next(r for r in bad['lower_tier']['source_choices']if r['fact_ref']==ref)
            if kind=='type':choice['parameter']['normalized']='8'
            elif kind=='dots':displacement._add_dots(bad['lower_tier'],bad['slots'][0]['beat_ref'],3)
            elif kind=='missing':bad['lower_tier']['source_choices'].remove(choice)
            else:bad['lower_tier']['source_choices'].append(deepcopy(choice))
            saved=deepcopy(bad)
            with self.subTest(kind=kind),self.assertRaises(ValueError):displacement.solve(bad,'0')
            self.assertEqual(bad,saved)

    def test_nonpositive_unnotatable_and_noncanonical_offsets_refuse_atomically(self):
        for offset in('1','-1','1/3','0.5','2/4',.5,True):
            before=digest(self.base)
            with self.subTest(offset=offset),self.assertRaises(ValueError):displacement.solve(self.base,offset)
            self.assertEqual(digest(self.base),before)

    def test_misaligned_clock_and_different_rest_pattern_refuse(self):
        for kind in('clock','pattern'):
            docs=deepcopy(self.docs);beats=docs['track-3.json']['measures'][0]['voices'][0]['beats']
            if kind=='clock':beats[0].update(duration=[1,8],type=8);beats[1].update(duration=[3,8],type=4,dots=1)
            else:beats[1].update(rest=True,notes=[dict(rest=True)])
            _,_,_,base=build(docs);before=deepcopy(base)
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'Coordinated parts'):displacement.solve(base,'1/2')
            self.assertEqual(base,before)

    def test_ties_and_dead_notes_preserve_zero_but_nonzero_refuses(self):
        for kind in('tie','dead'):
            docs=deepcopy(self.docs)
            for part in(2,3):
                beats=docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
                if kind=='tie':beats[1]['notes'][0].update(fret=beats[0]['notes'][0]['fret'],tie=True)
                else:beats[1]['notes'][0]['dead']=True
            _,_,_,base=build(docs);before=deepcopy(base)
            self.assertEqual(displacement.solve(base,'0')[0],base)
            with self.subTest(kind=kind),self.assertRaises(ValueError):displacement.solve(base,'1/2')
            self.assertEqual(base,before)


if __name__=='__main__':unittest.main()
