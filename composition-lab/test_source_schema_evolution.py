"""Observed source declaration evolution: ownership, not musical inference."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from test_connected_tier2 import documents
from source_fact_tier1 import extract_documents, project_documents
from connected_tier2 import analyze, strip_lower, reconstruct


def fixture():
    docs=documents()
    docs['metadata.json'].update(nextAudio='provider-a',nextAudioGenerated='provider-b',nextMidi='provider-c',nextAudioMeta=dict(hasQuickMix=False,hasMixLayout=True),audios=dict(next=dict(hash='provider-d',meta=dict(hasQuickMix=True,hasMixLayout=False))))
    track=docs['track-0.json'];track['grandStaffGroup']=1
    bar=track['measures'][0]
    bar.update(clef='treble',keySignature=dict(accidentalCount=1,mode='minor',transposeAs='b'))
    note=bar['voices'][0]['beats'][0]['notes'][0]
    note.update(spn=[1,4,0],courtesyAccidental=False)
    return docs


class SourceSchemaEvolutionTests(unittest.TestCase):
    def exact(self,docs):
        lower=extract_documents(docs);upper=analyze(lower)
        self.assertEqual(upper['unsupported'],[])
        actual=reconstruct(strip_lower(upper),dict(variation=0))
        self.assertEqual(actual,lower)
        self.assertEqual(project_documents(actual),docs)
        return upper

    def rejected(self,docs):
        try:upper=analyze(extract_documents(docs))
        except ValueError:return
        self.assertTrue(upper['unsupported'])
        with self.assertRaises(ValueError):reconstruct(strip_lower(upper),dict(variation=0))

    def test_all_new_declarations_exact_and_other_signature_variant(self):
        self.exact(fixture())
        docs=fixture();docs['track-0.json']['measures'][0]['keySignature']=dict(accidentalCount=2,mode='major',transposeAs='#')
        self.exact(docs)

    def test_display_and_provider_choices_do_not_become_pitch_authority(self):
        base=self.exact(documents())['musical_relationships']
        docs=fixture();docs['track-0.json']['measures'][0].pop('keySignature')
        self.assertEqual(self.exact(docs)['musical_relationships'],base)

    def test_absence_and_valid_empty_new_containers(self):
        self.exact(documents())
        docs=fixture();docs['metadata.json']['nextAudioMeta']={}
        docs['metadata.json']['audios']['next']={}
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['spn']=[]
        self.exact(docs)

    def test_strict_scalar_types(self):
        cases=[('metadata','nextAudio',True),('metadata','nextMidi',1),('flag','hasQuickMix',1),('signature','accidentalCount',True),('signature','mode',1),('signature','transposeAs',False),('note','spn',[True]),('note','spn',[1.5]),('note','courtesyAccidental',1),('bar','clef',1),('track','grandStaffGroup',True)]
        for scope,key,value in cases:
            with self.subTest(scope=scope,key=key,value=value):
                docs=fixture();bar=docs['track-0.json']['measures'][0]
                owner={'metadata':docs['metadata.json'],'flag':docs['metadata.json']['nextAudioMeta'],'signature':bar['keySignature'],'note':bar['voices'][0]['beats'][0]['notes'][0],'bar':bar,'track':docs['track-0.json']}[scope]
                owner[key]=value;self.rejected(docs)

    def test_wrong_container_kinds_and_scalar_impostors(self):
        for field,value in [('nextAudio',{}),('nextAudioMeta',[]),('audios',dict(next=[]))]:
            docs=fixture();docs['metadata.json'][field]=value
            with self.subTest(field=field):self.rejected(docs)
        for value in ({},[[]],[{}]):
            docs=fixture();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['spn']=value
            with self.subTest(spn=value):self.rejected(docs)
        docs=fixture();docs['track-0.json']['measures'][0]['keySignature']=[];self.rejected(docs)
        docs=fixture();docs['metadata.json']['nextAudioMeta']['hiddenNotes']=[60,64];self.rejected(docs)

    def test_actual_isolated_complete_inverse(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(fixture());upper=analyze(lower);code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            result=execute(code,strip_lower(upper),dict(variation=0),lower,Path(folder)/'isolated',timeout=30)
        self.assertEqual(result['status'],'PASS',result)


if __name__=='__main__':unittest.main()
