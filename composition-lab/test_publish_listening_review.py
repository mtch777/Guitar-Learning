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
    def different_clocks(self):
        for b in self.data['bar_times'][:-1]:b['beat_times']=[b['time']+.05]
        for i,v in enumerate(self.data['versions']):
            factor=1 if i==0 else .5;v['seconds']=self.data['seconds']*factor
            v['bar_times']=[dict(bar=b['bar'],time=b['time']*factor,**({'beat_times':[t*factor for t in b['beat_times']]}if 'beat_times'in b else{}))for b in self.data['bar_times']]
            for n in v['notes']:
                n.update(start=n['start']*factor,end=n['end']*factor,comparison_identity='source:attack:0',score_start_tick=0,score_end_tick=960)
            if i:
                with wave.open(str(self.root/v['audio']),'wb')as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes((200).to_bytes(2,'little',signed=True)*4410)
                v['audio_sha256']=hashlib.sha256((self.root/v['audio']).read_bytes()).hexdigest()
        self.write()
    def test_per_version_clocks_reuse_distinct_verified_audio_without_rescaling(self):
        self.different_clocks();result=publish(self.manifest,self.root,self.out)
        actual=json.loads((self.out/'comparison.json').read_bytes())
        self.assertEqual(result['audio_rendered'],0)
        self.assertEqual([v['seconds']for v in actual['versions']],[.2,.1])
        self.assertEqual(actual['bar_times'],self.data['bar_times'])
        for a,b in zip(actual['versions'],self.data['versions']):
            self.assertEqual(a['notes'],b['notes']);self.assertEqual(a['bar_times'],b['bar_times'])
            self.assertEqual((self.out/a['audio']).read_bytes(),(self.root/b['audio']).read_bytes())
    def test_invalid_version_clock_or_written_identity_preserves_existing_review(self):
        self.different_clocks();publish(self.manifest,self.root,self.out);before=self.snapshot();original=copy.deepcopy(self.data)
        for change in('missing_clock','wrong_duration','missing_beat','reordered_beat','wrong_original','missing_tick','boolean_tick','missing_identity'):
            self.data=copy.deepcopy(original);v=self.data['versions'][1]
            if change=='missing_clock':v.pop('seconds')
            elif change=='wrong_duration':v['seconds']=.12
            elif change=='missing_beat':v['bar_times'][0].pop('beat_times')
            elif change=='reordered_beat':v['bar_times'][0]['beat_times']=[.03,.02]
            elif change=='wrong_original':self.data['versions'][0]['bar_times'][0]['beat_times']=[.04]
            elif change=='missing_tick':v['notes'][0].pop('score_end_tick')
            elif change=='boolean_tick':v['notes'][0]['score_end_tick']=True
            else:v['notes'][0].pop('comparison_identity')
            self.write()
            with self.assertRaises(ValueError,msg=change):publish(self.manifest,self.root,self.out)
            self.assertEqual(before,self.snapshot(),change)
    def test_distinct_duration_without_explicit_clock_refuses(self):
        self.different_clocks()
        for v in self.data['versions']:v.pop('seconds');v.pop('bar_times')
        self.write()
        with self.assertRaisesRegex(ValueError,'Audio duration'):publish(self.manifest,self.root,self.out)
    def test_version_clock_still_requires_matched_sample_format(self):
        self.different_clocks();v=self.data['versions'][1]
        with wave.open(str(self.root/v['audio']),'wb')as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(22050);w.writeframes((200).to_bytes(2,'little',signed=True)*2205)
        v['audio_sha256']=hashlib.sha256((self.root/v['audio']).read_bytes()).hexdigest();self.write()
        with self.assertRaisesRegex(ValueError,'matched audio formats'):publish(self.manifest,self.root,self.out)

if __name__=='__main__':unittest.main()
