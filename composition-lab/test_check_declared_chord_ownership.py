import unittest
from copy import deepcopy
try:
    import music21
except ImportError:music21=None

@unittest.skipUnless(music21,'Native music21 evaluation dependency absent')
class IndependentDeclaredTests(unittest.TestCase):
    def test_native_glyph_flat_regressions(self):
        from check_declared_chord_ownership import native_interpretations
        from chord_symbol_lexicon import parse
        for text,pc in [('A♭',8),('C♭',11),('D♭',1),('C/E',0),('C/G',0)]:
            self.assertEqual(native_interpretations(text)[0]['root_pc'],pc)
            self.assertEqual(parse(text)['interpretations'][0]['root_pc'],pc)
    def test_actual_owner_and_corruptions(self):
        from test_declared_chord_ownership import documents
        from source_fact_tier1 import extract_documents
        from connected_tier2 import analyze
        from check_declared_chord_ownership import check
        docs=documents('C/E');upper=analyze(extract_documents(docs),declared_chords=True)
        self.assertEqual(check(docs,upper)['issues'],[])
        for change in ('octave','duplicate','owner'):
            bad=deepcopy(upper);g=bad['musical_relationships']['core']['coattacks'][0]
            if change=='octave':g['members'][0]['relative_octaves']=True
            elif change=='duplicate':g['members'].append(deepcopy(g['members'][0]))
            else:g['bass_register_anchor']='52'
            self.assertEqual(check(docs,bad)['status'],'FAIL')
    def test_fallback_inventory_and_no_implied_bass(self):
        from test_declared_chord_ownership import documents
        from source_fact_tier1 import extract_documents
        from connected_tier2 import analyze
        from check_declared_chord_ownership import check
        for symbol in ('C','C/G','unknown','F#m3'):
            docs=documents(symbol);upper=analyze(extract_documents(docs),declared_chords=True)
            self.assertEqual(check(docs,upper)['issues'],[])
        bad=deepcopy(upper);bad['musical_relationships']['core']['coattacks']=[]
        self.assertEqual(check(docs,bad)['status'],'FAIL')

    def test_all_finite_roots_and_aliases_match_native(self):
        from music21 import harmony,pitch
        from chord_symbol_lexicon import parse,ROOT_SPELLINGS
        from experiment_chord_glyph_adapter import normalize_roots
        for spelling,pc in ROOT_SPELLINGS.items():
            normalized,_=normalize_roots(spelling)
            self.assertEqual(pitch.Pitch(normalized).pitchClass,pc,spelling)
        for kind,(_,aliases) in harmony.CHORD_TYPES.items():
            for alias in aliases:
                result=parse('C'+alias)
                self.assertTrue(any(h['kind']==kind and h['root_pc']==0 for h in result['interpretations']),alias)
        self.assertEqual(parse('C♭♭♭')['status'],'UNSUPPORTED_SYMBOL')

    def test_scope_fallbacks_and_complete_reconstruction(self):
        from test_declared_chord_ownership import documents
        from source_fact_tier1 import extract_documents
        from connected_tier2 import analyze,reconstruct,strip_lower
        from check_declared_chord_ownership import check
        cases=[]
        d=documents();d['track-0.json']['capo']=12;cases.append(d)
        d=documents();d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['graceNote']='beforeBeat';cases.append(d)
        d=documents();v=d['track-0.json']['measures'][0]['voices'][0];v2=deepcopy(v);v2['beats'][0].pop('chord');d['track-0.json']['measures'][0]['voices'].append(v2);cases.append(d)
        for d in cases:
            lower=extract_documents(d);u=analyze(lower,declared_chords=True)
            result=check(d,u,reconstruct(strip_lower(u),{'variation':0}))
            self.assertEqual(result['issues'],[])
            self.assertEqual(result['counts'].get('selected',0),0)


    def test_complete_native_text_parser_standard_symbols(self):
        from music21 import harmony
        from chord_symbol_lexicon import parse
        from experiment_chord_glyph_adapter import normalize_roots
        for text in ('C','C/E','C/G','A♭m','C♭','D♭','C7','C9','Cdim7','Csus4','Cm7'):
            normalized,_=normalize_roots(text);native=harmony.ChordSymbol(normalized)
            h=parse(text)['interpretations'][0]
            self.assertEqual((h['root_pc'],h['kind']),(native.root().pitchClass,native.chordKind),text)

    def test_source_partition_scope_and_label_corruptions(self):
        from test_declared_chord_ownership import documents
        from source_fact_tier1 import extract_documents
        from connected_tier2 import analyze
        from check_declared_chord_ownership import check
        d=documents();u=analyze(extract_documents(d),declared_chords=True)
        for field,value in [('id','forged'),('scope_type','sounding_harmony'),('part_id',True)]:
            bad=deepcopy(u);bad['musical_relationships']['core']['coattacks'][0][field]=value
            self.assertEqual(check(d,bad)['status'],'FAIL')
        bad=deepcopy(u)
        next(c for c in bad['owned_parameters']['source_choices'] if '/chord/text' in c['fact_ref'])['parameter']['symbol']='D'
        self.assertEqual(check(d,bad)['status'],'FAIL')

    def test_numeric_native_domain_and_all_root_parity(self):
        from check_declared_chord_ownership import native_numeric_aliases,native_interpretations
        from chord_symbol_lexicon import parse
        from music21 import harmony
        mappings=native_numeric_aliases()
        self.assertEqual(mappings['5'],'power')
        self.assertFalse(any(x in mappings for x in ('2','3','4')))
        for root in ('C','C#','D','E-','E','F','F#','G','A-','A','B-','B'):
            for suffix,kind in mappings.items():
                symbol=root+suffix;native=harmony.ChordSymbol(symbol)
                result=parse(symbol)
                self.assertTrue(any(h['kind']==kind for h in result['interpretations']),symbol)
                interpretation=next(h for h in native_interpretations(symbol) if h['kind']==kind)
                self.assertEqual(set(interpretation['pcs']),{p.pitchClass for p in native.pitches})

    def test_slash_never_adds_formula_tones_and_singleton_fallback(self):
        from test_declared_chord_ownership import documents
        from source_fact_tier1 import extract_documents
        from connected_tier2 import analyze
        from check_declared_chord_ownership import check,native_interpretations
        h=native_interpretations('C5/E')[0]
        self.assertEqual((h['kind'],h['pcs'],h['slash_bass_pc']),('power',[0,7],4))
        for label,pitches,selected in [('C5',(48,55,60),True),('C5/E',(52,55,60),False),('C5/G',(55,60,67),True),('C1',(48,60),False),('C3',(48,52),False)]:
            docs=documents(label,pitches);upper=analyze(extract_documents(docs),declared_chords=True)
            result=check(docs,upper)
            self.assertEqual(result['issues'],[],label)
            self.assertEqual(result['counts'].get('selected',0),int(selected),label)

    def test_immutable_legacy_and_current_admission_profiles(self):
        from test_declared_chord_ownership import documents
        from source_fact_tier1 import extract_documents
        from connected_tier2 import analyze
        from check_declared_chord_ownership import check,native_interpretations,LEGACY_PROFILE,CURRENT_PROFILE
        self.assertEqual(native_interpretations('C5',LEGACY_PROFILE),[])
        self.assertEqual(native_interpretations('C5',CURRENT_PROFILE)[0]['kind'],'power')
        docs=documents('C5',(48,55,60));upper=analyze(extract_documents(docs),declared_chords=True)
        self.assertFalse(check(docs,upper)['issues'])
        wrong=deepcopy(upper);wrong['musical_relationships'].pop('admission_profile')
        self.assertEqual(check(docs,wrong)['status'],'FAIL')
        wrong=deepcopy(upper);wrong['musical_relationships']['admission_profile']='future-unknown'
        self.assertEqual(check(docs,wrong)['status'],'FAIL')
