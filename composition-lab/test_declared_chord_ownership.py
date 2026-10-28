from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,reconstruct,validate
from chord_symbol_lexicon import parse


def documents(label='C',pitches=(52,55,60)):
    beat=dict(duration=[1,1],notes=[dict(string=i,fret=p-40) for i,p in enumerate(pitches)],chord=dict(text=label))
    return {'metadata.json':dict(songId=11,revisionId=1,title='Authored degree fixture',artist='Fixture',tracks=[dict(instrumentId=25)]),
        'track-0.json':dict(songId=11,revisionId=1,partId=0,instrumentId=25,tuning=[40]*len(pitches),measures=[dict(signature=[4,4],voices=[dict(beats=[beat])])])}


def owner(upper):return upper['musical_relationships']['core']['coattacks'][0]


class DeclaredChordTests(unittest.TestCase):
    def test_source_degrees_own_notes_not_bass_and_reconstruct_exactly(self):
        lower=extract_documents(documents('C/E'));upper=analyze(lower,declared_chords=True);g=owner(upper)
        self.assertNotIn('bass_register_anchor',g)
        self.assertTrue(all('voicing_interval' not in m for m in g['members']))
        self.assertEqual([m['degree_token'] for m in g['members']],['3','5','1'])
        self.assertEqual(validate(upper),lower)
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)

    def test_no_implicit_root_position_and_same_degree_equation(self):
        lower=extract_documents(documents());upper=strip_lower(analyze(lower,declared_chords=True))
        self.assertIn('declared_chord_ref',owner(upper))
        owner(upper)['members'][0]['relative_octaves']+=1
        changed=project_documents(reconstruct(upper,{'variation':0}))
        notes=changed['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes']
        self.assertEqual([n['fret'] for n in notes],[24,15,20])
        self.assertEqual(changed['track-0.json']['measures'][0]['voices'][0]['beats'][0]['chord']['text'],'C')
        with self.assertRaises(ValueError):reconstruct(upper,dict(context_policy='exact_context',voicing=100,register=0,target_ref='event:11:0:1:0:0:0',seed=1))

    def test_slash_bass_unknown_and_incomplete_are_not_promoted(self):
        for label,pitches in [('C/G',(52,55,60)),('unrecognized',(52,55,60)),('C',(52,55)),('C',(52,55,60,61))]:
            lower=extract_documents(documents(label,pitches));upper=analyze(lower,declared_chords=True)
            self.assertNotIn('declared_chord_ref',owner(upper));self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)
        upper=strip_lower(analyze(extract_documents(documents('C/E')),declared_chords=True))
        owner(upper)['members'][0]['relative_octaves']+=1
        with self.assertRaises(ValueError):reconstruct(upper,{'variation':0})

    def test_degree9_is_compound_and_not_a_modulo12_alias(self):
        upper=analyze(extract_documents(documents('C9',(48,52,55,58,62))),declared_chords=True)
        m=owner(upper)['members'][-1]
        self.assertEqual((m['degree_token'],m['relative_octaves']),('9',4))

    def test_capo_grace_mixed_voice_and_multiple_labels_keep_old_owner(self):
        cases=[]
        docs=documents();docs['track-0.json']['capo']=12;cases.append(docs)
        docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['graceNote']='beforeBeat';cases.append(docs)
        docs=documents();voice=docs['track-0.json']['measures'][0]['voices'][0]
        other=deepcopy(voice);other['beats'][0].pop('chord');docs['track-0.json']['measures'][0]['voices'].append(other);cases.append(docs)
        docs=documents();docs['track-0.json']['measures'][0]['voices'].append(deepcopy(docs['track-0.json']['measures'][0]['voices'][0]));cases.append(docs)
        for docs in cases:
            lower=extract_documents(docs);upper=analyze(lower,declared_chords=True)
            self.assertTrue(all('declared_chord_ref' not in g for g in upper['musical_relationships']['core']['coattacks']))
            self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)

    def test_declaration_does_not_extend_to_following_beat(self):
        docs=documents();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats'];beats[0]['duration']=[1,2]
        beats.append(deepcopy(beats[0]));beats[1].pop('chord')
        upper=analyze(extract_documents(docs),declared_chords=True)
        self.assertEqual(['declared_chord_ref' in g for g in upper['musical_relationships']['core']['coattacks']],[True,False])

    def test_no_duplicate_pitch_owner_or_forged_parameter(self):
        original=strip_lower(analyze(extract_documents(documents()),declared_chords=True))
        for name,value in [('bass_register_anchor','52'),('root_pc',0)]:
            bad=deepcopy(original);owner(bad)[name]=value
            with self.assertRaises(ValueError):reconstruct(bad,{'variation':0})
        for name,value in [('relative_octaves',True),('degree_token','9'),('voicing_interval','0')]:
            bad=deepcopy(original);owner(bad)['members'][0][name]=value
            with self.assertRaises(ValueError):reconstruct(bad,{'variation':0})
        bad=deepcopy(original);owner(bad)['declared_chord_ref']=owner(bad)['declared_chord_ref'].replace('/beats/0/','/beats/1/')
        with self.assertRaises(ValueError):reconstruct(bad,{'variation':0})

    def test_exact_isolated_complete_capture_reversal_and_techniques(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        from check_technique_connections import check
        docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['vibrato']=True
        lower=extract_documents(docs);upper=analyze(lower,declared_chords=True)
        self.assertEqual(check(docs,upper)['status'],'PASS_SOURCE_BACKED_RELATIONSHIPS')
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            report=execute(code,strip_lower(upper),{'variation':0},lower,Path(folder)/'zero')
            self.assertEqual(report['status'],'PASS',report)

    def test_lexical_standard_flats_and_no_quality_guessing(self):
        for text,pc in [('A\u266d',8),('C\u266d',11),('D\u266d',1),('F\u266fm',6),('B-',10)]:
            self.assertEqual(parse(text)['interpretations'][0]['root_pc'],pc)
        for text in ('F#m3','Bb','nonsense','C6/9'):
            self.assertNotEqual(parse(text)['status'],'UNIQUE_LIBRARY_SYMBOL')

    def test_numeric_power_syntax_and_slash_bass_have_separate_meaning(self):
        for label,pitches,selected in [('C5',(48,55,60),True),('C5/G',(43,48,55),True),
                                     ('C5/E',(52,55,60),False),('C1',(48,60),False),('C3',(48,52),False)]:
            lower=extract_documents(documents(label,pitches));upper=analyze(lower,declared_chords=True)
            self.assertEqual('declared_chord_ref' in owner(upper),selected,label)
            self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)
        self.assertEqual(parse('C5/E')['interpretations'],[dict(root_pc=0,kind='power',explicit_bass_pc=4)])

    def test_numeric_compilation_records_entire_native_domain(self):
        from chord_symbol_lexicon import NUMERIC_QUALITY_AUDIT,QUALITY_ALIASES
        self.assertEqual({r['suffix'] for r in NUMERIC_QUALITY_AUDIT},{'1','2','3','4','5','6','7','9','11','13'})
        self.assertEqual(QUALITY_ALIASES['5'],['power'])
        for row in NUMERIC_QUALITY_AUDIT:
            self.assertEqual(len(row['roots']),12)
            if row['status'].startswith('ACCEPTED'):
                self.assertTrue(all(len(r['matches'])==1 for r in row['roots']))
                self.assertEqual(len({(tuple(r['intervals']),tuple(r['matches'])) for r in row['roots']}),1)
            else:self.assertNotIn(row['suffix'],QUALITY_ALIASES)

    def test_admission_version_preserves_old_fallbacks_without_new_inverse(self):
        from chord_symbol_lexicon import LEGACY_PROFILE,CURRENT_PROFILE
        lower=extract_documents(documents('C5',(48,55,60)))
        old=analyze(lower,declared_chords=True,declared_chord_profile=LEGACY_PROFILE)
        self.assertNotIn('admission_profile',old['musical_relationships'])
        self.assertNotIn('declared_chord_ref',owner(old))
        self.assertEqual(validate(old),lower)
        self.assertEqual(reconstruct(strip_lower(old),{'variation':0}),lower)
        new=analyze(lower,declared_chords=True)
        self.assertEqual(new['musical_relationships']['admission_profile'],CURRENT_PROFILE)
        self.assertIn('declared_chord_ref',owner(new));self.assertEqual(validate(new),lower)
        for profile in ('unknown',LEGACY_PROFILE,None):
            bad=strip_lower(new);bad['musical_relationships']['admission_profile']=profile
            with self.assertRaises(ValueError):reconstruct(bad,{'variation':0})
        bad=strip_lower(new);bad['musical_relationships'].pop('admission_profile')
        with self.assertRaises(ValueError):reconstruct(bad,{'variation':0})


if __name__=='__main__':unittest.main()
