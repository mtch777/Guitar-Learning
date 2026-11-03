import copy, hashlib, json, tempfile, unittest, wave
from pathlib import Path
from publish_listening_review import publish

class PublishReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.out=self.root/'public'
        for name,value in [('raw',100),('variation',200)]:
            with wave.open(str(self.root/f'{name}.wav'),'wb')as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(value.to_bytes(2,'little',signed=True)*8820)
        self.data=dict(schema='listening-review/1',title='Authored fixture',artist='Test',playback_note='Matched test audio',bars=[7,8],seconds=.2,
            questions=['Does the ending work?'],original_version='raw',default_version='variation',all_parts=1,tracks=[dict(id=2,name='Guitar',percussion=False)],silent_tracks=[],
            sections=[dict(first=7,last=8,label='Compare')],bar_times=[dict(bar=7,time=0),dict(bar=8,time=.1),dict(bar=9,time=.2)],versions=[])
        for name,pitch in [('raw',60),('variation',64)]:
            self.data['versions'].append(dict(id=name,label=name,description='Unedited source'if name=='raw'else'Changed pitch',compare_to=None if name=='raw'else'raw',
                audio=name+'.wav',audio_sha256=hashlib.sha256((self.root/f'{name}.wav').read_bytes()).hexdigest(),
                notes=[dict(part=2,voice=0,bar=7,pitch=pitch,start=0,end=.1,velocity=80,fret=0,string=1,dead=False,ghost=False)]))
        self.manifest=self.root/'review.json';self.write()
    def write(self):self.manifest.write_text(json.dumps(self.data))
    def snapshot(self):return {p.name:p.read_bytes()for p in self.out.iterdir()}
    def test_repopulation_reuses_page_and_audio_and_retains_notes(self):
        first=publish(self.manifest,self.root,self.out);before=self.snapshot();second=publish(self.manifest,self.root,self.out)
        self.assertEqual(first['ui_files_refreshed'],3);self.assertEqual(second['ui_files_refreshed'],0);self.assertEqual(second['audio_rendered'],0);self.assertEqual(before,self.snapshot())
        actual=json.loads((self.out/'comparison.json').read_bytes());self.assertEqual([v['notes']for v in actual['versions']],[v['notes']for v in self.data['versions']])
        self.data['questions']=['Which ending do you prefer?'];self.write();third=publish(self.manifest,self.root,self.out)
        self.assertEqual(third['ui_files_refreshed'],0);self.assertEqual(json.loads((self.out/'comparison.json').read_bytes())['questions'],self.data['questions'])
    def test_bad_inputs_do_not_change_live_review(self):
        publish(self.manifest,self.root,self.out);before=self.snapshot();original=copy.deepcopy(self.data)
        for change in('questions','hash','path','baseline','clock'):
            self.data=copy.deepcopy(original)
            if change=='questions':self.data['questions']=[]
            elif change=='hash':self.data['versions'][1]['audio_sha256']='0'*64
            elif change=='path':self.data['versions'][1]['audio']='../raw.wav'
            elif change=='baseline':self.data['versions'][1]['compare_to']='missing'
            else:self.data['seconds']=.3
            self.write()
            with self.assertRaises(ValueError):publish(self.manifest,self.root,self.out)
            self.assertEqual(before,self.snapshot(),change)
    def test_incomplete_note_or_hidden_low_part_refuses(self):
        self.data['versions'][1]['notes'][0]['part']=9;self.write()
        with self.assertRaises(ValueError):publish(self.manifest,self.root,self.out)
        self.assertFalse(self.out.exists())
    def test_comparison_identity_is_preserved_and_bad_identity_does_not_replace_page(self):
        for v in self.data['versions']:v['notes'][0]['comparison_identity']='source:note:attack:0'
        self.write();publish(self.manifest,self.root,self.out);before=self.snapshot();valid=copy.deepcopy(self.data)
        stored=json.loads((self.out/'comparison.json').read_bytes())
        self.assertEqual(stored['versions'][0]['notes'],self.data['versions'][0]['notes'])
        for change in('missing','duplicate','empty'):
            self.data=copy.deepcopy(valid);notes=self.data['versions'][1]['notes']
            if change=='missing':notes[0].pop('comparison_identity')
            elif change=='duplicate':notes.append(copy.deepcopy(notes[0]))
            else:notes[0]['comparison_identity']=''
            self.write()
            with self.assertRaisesRegex(ValueError,'Comparison identities'):publish(self.manifest,self.root,self.out)
            self.assertEqual(before,self.snapshot())

if __name__=='__main__':unittest.main()
