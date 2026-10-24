"""Independent GP checks distinguish fingering changes from pitch changes."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import wave
import zipfile
from check_voicing_artifacts import check


def score(string,fret,midi=64,articulation=0):
    pitches=''.join(f'<Property name="{name}"><Pitch><Step>E</Step><Accidental></Accidental><Octave>4</Octave></Pitch></Property>' for name in ('ConcertPitch','TransposedPitch'))
    return f'''<GPIF><Tracks><Track><Staves><Staff/></Staves></Track></Tracks>
    <MasterBars><MasterBar><Bars>0</Bars></MasterBar></MasterBars>
    <Bars><Bar id="0"><Voices>0</Voices></Bar></Bars><Voices><Voice id="0"><Beats>0</Beats></Voice></Voices>
    <Beats><Beat id="0"><Notes>0</Notes></Beat></Beats><Notes><Note id="0"><Properties>{pitches}
    <Property name="String"><String>{string}</String></Property><Property name="Fret"><Fret>{fret}</Fret></Property>
    <Property name="Midi"><Number>{midi}</Number></Property></Properties><InstrumentArticulation>{articulation}</InstrumentArticulation></Note></Notes></GPIF>'''


class JointGPArtifactTests(unittest.TestCase):
    def fixture(self,root,changed_xml=None):
        for name in ('source','zero','changed'):
            p=root/name;p.mkdir()
            with zipfile.ZipFile(p/'score.gp','w') as z:z.writestr('Content/score.gpif',score(4,5) if name=='changed' and changed_xml is None else changed_xml if name=='changed' else score(5,0))
            for mode in ('focused','ensemble'):
                with wave.open(str(p/(mode+'.wav')),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\0\0'*80)
        qa=root/'qa';qa.mkdir()
        before={'tuning':[64,59,55,50,45,40],'measures':[{'voices':[{'beats':[{'notes':[{'string':0,'fret':0}]}]}]}]}
        after=deepcopy(before);after['measures'][0]['voices'][0]['beats'][0]['notes'][0]={'string':1,'fret':5}
        for name,value in (('zero-capture',before),('changed-capture',after)):
            (qa/name).mkdir();(qa/name/'track-0.json').write_text(json.dumps(value))
        return qa

    def test_physical_only_valid_gp_can_have_identical_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);r=check(root,self.fixture(root))
        self.assertEqual(r['status'],'PASS_NATIVE_GP_AND_RENDER_CHECKS',r)
        self.assertEqual(r['expected_fret_changes']['0']['shift'],0)

    def test_wrong_string_pitch_or_unrelated_field_fails(self):
        for xml in (score(3,5),score(4,5,midi=76),score(4,5,articulation=1)):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);r=check(root,self.fixture(root,xml))
            self.assertEqual(r['status'],'FAIL',r)


if __name__=='__main__':unittest.main()
