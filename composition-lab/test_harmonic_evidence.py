from copy import deepcopy
import unittest
import musical_tier2 as music
from harmonic_evidence import build,validate,source_patterns
from test_musical_tier2 import facts


def core_for(pitches,duration=1,uncertain=False):
    lower=facts([(0,p,0,duration) for p in pitches])
    for i,e in enumerate(lower['events']):e['beat']=0;e['note']=i
    if uncertain:lower['source_coverage']['layout_warnings']=[dict(bar=1,reason='conflicting_track_meter')]
    return music.strip_lower(music.analyze(lower))


def evidence(pitches,**kwargs):return build(core_for(pitches),{}, {},{'0':25},**kwargs)


class HarmonicEvidenceTests(unittest.TestCase):
    def test_sixth_seventh_and_symmetric_roots_stay_ambiguous(self):
        h=evidence([60,64,67,69])['groups'][0]['hypotheses'];labels={(r['root_pc'],r['kind']) for r in h}
        self.assertTrue({(0,'major-sixth'),(9,'minor-seventh')}<=labels)
        h=evidence([60,63,66,69])['groups'][0]['hypotheses']
        self.assertEqual({r['root_pc'] for r in h if r['kind']=='diminished-seventh'},{0,3,6,9})
        self.assertTrue(all('preferred' not in r for r in h))

    def test_power_dyad_and_insufficient_evidence(self):
        self.assertTrue(any(h['root_pc']==4 and h['kind']=='power' for h in evidence([40,47])['groups'][0]['hypotheses']))
        self.assertEqual(evidence([60,61])['groups'][0]['status'],'NO_EXACT_FIT_IN_VOCABULARY')
        self.assertIn('INSUFFICIENT_DISTINCT_PITCH_CLASSES',evidence([60,60])['groups'][0]['reasons'])

    def test_unknown_percussion_and_timing_are_not_complete_fits(self):
        for core,program,reason in [(core_for([60,64,None]),25,'UNKNOWN_WRITTEN_PITCH'),(core_for([60,64,67]),128,'NONPITCHED_OR_UNKNOWN_INSTRUMENT'),(core_for([60,64,67]),True,'NONPITCHED_OR_UNKNOWN_INSTRUMENT'),(core_for([60,64,67],duration=0),25,'GRACE_OR_NONPOSITIVE_DURATION'),(core_for([60,64,67],uncertain=True),25,'UNCERTAIN_SOURCE_CLOCK')]:
            row=build(core,{}, {},{'0':program})['groups'][0]
            self.assertIn(reason,row['reasons']);self.assertFalse(row['hypotheses'])

    def test_compound_ninth_is_not_second(self):
        row=next(h for h in evidence([48,52,55,58,62])['groups'][0]['hypotheses'] if h['root_pc']==0 and h['kind']=='dominant-ninth')
        self.assertEqual(row['member_roles'][-1]['degree_relationships'][0]['token'],'9')
        self.assertEqual(row['member_roles'][-1]['degree_relationships'][0]['theoretical_semitones'],14)

    def test_source_labels_do_not_create_or_replace_observed_fits(self):
        core=core_for([60,64,67]);ref='track-0.json#/measures/0/voices/0/beats/0/chord/text'
        def observed(view):
            return [{k:v for k,v in h.items() if k!='matching_declared_root_kind_refs'} for h in view['groups'][0]['hypotheses']]
        empty=build(core,{}, {},{'0':25});right=build(core,{ref:'C'}, {},{'0':25});wrong=build(core,{ref:'F#'}, {},{'0':25})
        self.assertEqual(observed(empty),observed(right));self.assertEqual(observed(empty),observed(wrong))
        self.assertEqual(right['groups'][0]['declared_admission_status'],'SUPPORTED_DECLARED_WRITTEN_CHORD')
        self.assertEqual(wrong['groups'][0]['declared_admission_status'],'SYMBOL_PITCH_SET_MISMATCH')

    def test_global_transposition_preserves_every_alternative(self):
        source=[60,64,67,69]
        labels=lambda v:{(h['root_pc'],h['kind']) for h in v['groups'][0]['hypotheses']}
        old=labels(evidence(source))
        for shift in range(-13,14):self.assertEqual(labels(evidence([p+shift for p in source])),{((r+shift)%12,k) for r,k in old})

    def test_member_serialization_does_not_select_a_root(self):
        lower=facts([(0,p,0,1) for p in [60,64,67,69]])
        a=build(music.strip_lower(music.analyze(lower)),{}, {},{'0':25})
        lower['events'].reverse();b=build(music.strip_lower(music.analyze(lower)),{}, {},{'0':25})
        convert=lambda view:{h['id']:{m['member_ref']:m['degree_relationships'] for m in h['member_roles']} for h in view['groups'][0]['hypotheses']}
        self.assertEqual(convert(a),convert(b))

    def test_stale_coordinates_members_roots_and_provenance_rejected(self):
        core=core_for([60,64,67]);good=build(core,{}, {},{'0':25});bad=[]
        x=deepcopy(good);x['groups'][0]['hypotheses']=[];bad.append(x)
        x=deepcopy(good);x['groups'][0]['hypotheses'][0]['root_pc']=True;bad.append(x)
        x=deepcopy(good);x['groups'][0]['hypotheses'][0]['member_roles'].pop();bad.append(x)
        x=deepcopy(good);x['groups'][0]['hypotheses'][0]['member_roles'][0]['degree_relationships'][0]['relative_octaves']+=1;bad.append(x)
        x=deepcopy(good);x['groups'][0]['hypotheses'][0]['matching_declared_root_kind_refs']=['invented'];bad.append(x)
        for x in bad:
            with self.assertRaises(ValueError):validate(core,{}, {},{'0':25},x)
        self.assertEqual(validate(core,{}, {},{'0':25},good),good)

    def test_unlabeled_groups_reach_existing_pattern_guards_without_source_edits(self):
        from test_inner_voicing import fixture,analyzed
        from connected_tier2 import realize
        docs,_,_=fixture()
        for part in [v for k,v in docs.items() if k.startswith('track-')]:
            for m in part['measures']:
                for v in m['voices']:
                    for beat in v['beats']:beat.pop('chord',None)
        lower,upper,old=analyzed(docs);self.assertFalse(old['units'])
        new=source_patterns(upper);self.assertTrue(new['units']);self.assertEqual(realize(upper),lower)
        self.assertTrue(all(not r['declarations'] for r in new['harmonic_evidence']['groups']))
        self.assertTrue(all(u['evidence_class']=='exact_observed_pc_fit' for u in new['units']))


if __name__=='__main__':unittest.main()
