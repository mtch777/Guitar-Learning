"""Pinned source theory preservation; no assigned artist/function preferences."""
import ast
from copy import deepcopy
import hashlib
from importlib.util import find_spec
import json
from pathlib import Path
import subprocess
import sys
import unittest
from chord_degree_definitions import CHORD_DEGREE_DEFINITIONS,CHORD_DEGREE_PROVENANCE,degree_definitions


def slots(kind):return {r['token']:r for r in degree_definitions(kind)}


class ChordDegreeTests(unittest.TestCase):
    def test_all_definitions_exactly_cover_existing_forms_and_digest(self):
        path=Path(__file__).with_name('musical_tier2.py')
        node=next(n for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='THEORY_FORMS' for t in n.targets))
        forms=ast.literal_eval(node.value)
        self.assertEqual([(k,tuple(sorted({r[4]for r in rows})))for k,f,rows in CHORD_DEGREE_DEFINITIONS],list(forms))
        self.assertEqual(len(CHORD_DEGREE_DEFINITIONS),50)
        self.assertEqual(CHORD_DEGREE_PROVENANCE['definitions_sha256'],hashlib.sha256(json.dumps(CHORD_DEGREE_DEFINITIONS,ensure_ascii=False,separators=(',',':')).encode()).hexdigest())

    def test_enharmonic_slots_compounds_suspensions_and_augmented_sixth(self):
        diminished=slots('diminished-seventh')['--7'];sixth=slots('major-sixth')['6']
        self.assertEqual((diminished['degree'],diminished['alteration'],diminished['theoretical_semitones']),(7,-2,9))
        self.assertEqual((sixth['degree'],sixth['alteration'],sixth['theoretical_semitones']),(6,0,9))
        self.assertNotEqual(diminished,sixth)
        extended=slots('major-13th')
        self.assertEqual([(extended[t]['degree'],extended[t]['theoretical_semitones'])for t in ('9','11','13')],[(9,14),(11,17),(13,21)])
        self.assertEqual(set(slots('suspended-fourth')),{'1','4','5'})
        self.assertEqual(set(slots('power')),{'1','5'})
        self.assertEqual((slots('Italian')['#4']['degree'],slots('Italian')['#4']['alteration'],slots('Italian')['#4']['theoretical_semitones']),(4,1,6))

    def test_runtime_no_music21_and_returned_values_do_not_alias(self):
        before=deepcopy(CHORD_DEGREE_DEFINITIONS);returned=degree_definitions('major');returned[0]['degree']=99
        self.assertEqual(CHORD_DEGREE_DEFINITIONS,before)
        for wrong in ('not-a-kind',None,True,3):
            with self.assertRaises(ValueError):degree_definitions(wrong)
        path=Path(__file__).with_name('chord_degree_definitions.py')
        code="import runpy,sys;d=runpy.run_path(sys.argv[1]);assert len(d['degree_definitions']('major'))==3;assert not any(k.startswith('music21') for k in sys.modules)"
        result=subprocess.run([sys.executable,'-I','-S','-c',code,str(path)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(find_spec('music21'),'Optional pinned theory-build dependency')
    def test_pinned_reproduction_and_library_all_root_pitch_classes(self):
        import music21
        if music21.__version__!='9.9.2':self.skipTest('Reproduction specifically pins music21 9.9.2')
        from build_chord_degree_definitions import definitions
        from music21 import harmony,pitch
        records,provenance=definitions()
        self.assertEqual(records,CHORD_DEGREE_DEFINITIONS);self.assertEqual(provenance,CHORD_DEGREE_PROVENANCE)
        for kind,formula,rows in records:
            self.assertEqual(formula,harmony.CHORD_TYPES[kind][0])
            for root in range(12):
                source_pcs={p.pitchClass for p in harmony.ChordSymbol(root=pitch.Pitch(root),kind=kind).pitches}
                self.assertEqual({(root+r[3])%12 for r in rows},source_pcs,(kind,root))


if __name__=='__main__':unittest.main()
