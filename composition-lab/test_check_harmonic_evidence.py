from copy import deepcopy
import unittest
from test_connected_tier2 import documents
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower
from harmonic_evidence import context,from_context
from check_harmonic_evidence import check,native_forms


class NativeEvidenceTests(unittest.TestCase):
    def test_native_compound_degrees_keep_their_octave(self):
        definitions=next(d for k,_,d in native_forms()if k=='Tristan')
        self.assertEqual(next(d['theoretical_semitones']for d in definitions if d['token']=='#9'),15)
        from chord_degree_definitions import degree_definitions
        for kind,_,defs in native_forms():self.assertEqual(defs,list(degree_definitions(kind)),kind)

    def fixture(self):
        docs=documents();p=docs['track-0.json'];p['tuning']=[60,64,67]
        b=p['measures'][0]['voices'][0]['beats'][0];b['notes']=[dict(string=s,fret=0)for s in range(3)];b['chord']=dict(text='C')
        lower=extract_documents(docs);c=context(strip_lower(analyze(lower,declared_chords=True)))
        return lower,from_context(c)

    def test_source_and_native_theory_match(self):
        lower,view=self.fixture();self.assertEqual(check(lower,view)['status'],'PASS_NATIVE_HARMONIC_EVIDENCE')

    def test_forged_declaration_claims_and_provenance_fail(self):
        lower,view=self.fixture();bad=[]
        for field in ('parse_status','declared_admission_status'):
            x=deepcopy(view)
            if field=='parse_status':x['groups'][0]['declarations'][0][field]='UNSUPPORTED_SYMBOL'
            else:x['groups'][0][field]='NO_DECLARATION'
            bad.append(x)
        x=deepcopy(view);x['theory']['forms_sha256']='invented';bad.append(x)
        x=deepcopy(view);x['schema']='actual_harmonic_truth';bad.append(x)
        for x in bad:self.assertEqual(check(lower,x)['status'],'FAIL')


if __name__=='__main__':unittest.main()
