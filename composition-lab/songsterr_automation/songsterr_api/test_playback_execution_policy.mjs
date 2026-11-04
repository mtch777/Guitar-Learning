import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {loadPlaybackScore} from './playback_score.mjs';
import {exportWithExactBends} from './bend_fidelity.mjs';
const modulePath=process.env.ALPHATAB_MODULE||'.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
assert.ok(fs.existsSync(modulePath),'Native alphaTab is required');
const at=await import(pathToFileURL(path.resolve(modulePath))),sha=x=>createHash('sha256').update(x).digest('hex');
const write=(p,x)=>fs.writeFileSync(p,JSON.stringify(x));
function fixture(t,{bend=false,mixed=false}={}){
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'composition-execution-policy-'));
 t.after(()=>{const target=path.resolve(folder),base=path.resolve(os.tmpdir())+path.sep;
  assert.ok(target.startsWith(base)&&path.basename(target).startsWith('composition-execution-policy-'));
  fs.rmSync(target,{recursive:true,force:true});});
 const score=new at.model.Score(),master=new at.model.MasterBar();master.timeSignatureNumerator=3;score.addMasterBar(master);
 const track=new at.model.Track();score.addTrack(track);const staff=new at.model.Staff();track.addStaff(staff);
 staff.stringTuning.tunings=[64,59,55,50,45,40];const bar=new at.model.Bar();staff.addBar(bar);
 const voice=new at.model.Voice();bar.addVoice(voice);const notes=[];
 for(let i=0;i<3;i++){
  const beat=new at.model.Beat();beat.duration=at.model.Duration.Quarter;voice.addBeat(beat);
  const n=new at.model.Note();n.string=6;n.fret=0;n.isPalmMute=!(mixed&&i===1);n.isTieDestination=i===1;
  beat.addNote(n);notes.push(n);
 }
 const settings=new at.Settings();settings.notation.notationMode=at.NotationMode.GuitarPro;score.finish(settings);
 if(bend){notes[2].addBendPoint(new at.model.BendPoint(0,0));notes[2].addBendPoint(new at.model.BendPoint(60,4));notes[2].bendType=at.model.BendType.Custom;}
 const file=path.join(folder,'score.gp'),sidecar=path.join(folder,'score.exact-model-bends.json'),policy=path.join(folder,'score.execution-policy.json');
 if(bend){const pair=exportWithExactBends(at,score,settings);fs.writeFileSync(file,pair.bytes);write(sidecar,pair.sidecar);}
 else fs.writeFileSync(file,new at.exporter.Gp7Exporter().export(score,settings));
 const receipt={schema:'composition-lab.execution-policy/1',policy:'composition-lab.continuous-mute-terminal-release/1',
  gp_sha256:sha(fs.readFileSync(file)),exact_model_bends_sha256:bend?sha(fs.readFileSync(sidecar)):null};
 return{folder,file,sidecar,policy,receipt};
}
function native(score){
 const midi=new at.midi.MidiFile(),handler=new at.midi.AlphaSynthMidiFileHandler(midi,false),calls=[],add=handler.addNote.bind(handler);
 handler.addNote=(track,start,length,key,velocity,channel)=>{calls.push({track,start,length,key,velocity,channel});return add(track,start,length,key,velocity,channel);};
 const settings=new at.Settings();settings.notation.notationMode=at.NotationMode.GuitarPro;
 new at.midi.MidiFileGenerator(score,settings,handler).generate();return{calls,events:JSON.parse(JSON.stringify(midi.events))};
}

test('no execution receipt preserves ordinary native loading and exact MIDI behavior',t=>{
 const f=fixture(t),raw=at.importer.ScoreLoader.loadScoreFromBytes(fs.readFileSync(f.file));
 const loaded=loadPlaybackScore(at,f.file);assert.equal(loaded.execution_policy_selection,'absent');
 assert.equal(loaded.execution_policy_registration,null);assert.equal(loaded.execution_policy_receipt,null);
 assert.deepEqual(native(loaded.score),native(raw));assert.equal(native(loaded.score).calls[0].length,160);
});

test('adjacent hash-bound receipt corrects only scoped continuous duration after actual GP reload',t=>{
 const f=fixture(t);write(f.policy,f.receipt);
 const loaded=loadPlaybackScore(at,f.file),before=at.model.JsonConverter.scoreToJson(loaded.score);
 assert.equal(loaded.execution_policy_selection,'adjacent');assert.deepEqual(loaded.execution_policy_receipt,f.receipt);
 assert.equal(loaded.execution_policy_registration.continuous_gestures,1);
 const result=native(loaded.score);assert.equal(result.calls.length,2);assert.equal(result.calls[0].length,1120);
 assert.equal(result.calls[1].length,160);assert.equal(at.model.JsonConverter.scoreToJson(loaded.score),before);
 const unpaired=at.importer.ScoreLoader.loadScoreFromBytes(fs.readFileSync(f.file));assert.equal(native(unpaired).calls[0].length,160,'Standalone GP has no new-policy claim');
});

test('explicit receipt path overrides adjacent discovery while false disables even malformed adjacent data',t=>{
 const f=fixture(t),explicit=path.join(f.folder,'verified.json');write(explicit,f.receipt);fs.writeFileSync(f.policy,'not json');
 const loaded=loadPlaybackScore(at,f.file,{execution_policy:explicit});assert.equal(loaded.execution_policy_selection,'explicit');
 assert.equal(native(loaded.score).calls[0].length,1120);
 const disabled=loadPlaybackScore(at,f.file,{execution_policy:false});assert.equal(disabled.execution_policy_selection,'disabled');
 assert.equal(native(disabled.score).calls[0].length,160);assert.equal(disabled.execution_policy_receipt,null);
});

test('both GP and exact-bend bytes are verified before the score can be registered',t=>{
 const f=fixture(t,{bend:true});write(f.policy,f.receipt);
 assert.equal(loadPlaybackScore(at,f.file).execution_policy_selection,'adjacent');
 const bad={...f.receipt,gp_sha256:'0'.repeat(64)};write(f.policy,bad);
 assert.throws(()=>loadPlaybackScore(at,f.file),/GP hash mismatch/);
 write(f.policy,f.receipt);fs.appendFileSync(f.sidecar,' ');
 assert.throws(()=>loadPlaybackScore(at,f.file),/bend companion hash mismatch/);
 const plain=loadPlaybackScore(at,f.file,{execution_policy:false});assert.equal(native(plain.score).calls[0].length,160);
});

test('a required missing or disabled bend companion refuses, rather than changing the bound score',t=>{
 const f=fixture(t,{bend:true});write(f.policy,f.receipt);
 assert.throws(()=>loadPlaybackScore(at,f.file,{exact_model_bends:false}),/bend companion hash mismatch/);
 const detached=path.join(f.folder,'detached.gp');fs.copyFileSync(f.file,detached);
 write(path.join(f.folder,'detached.execution-policy.json'),f.receipt);
 assert.throws(()=>loadPlaybackScore(at,detached),/bend companion hash mismatch/);
 assert.throws(()=>loadPlaybackScore(at,f.file,{exact_model_bends:path.join(f.folder,'missing.json')}),/ENOENT/);
});

test('a receipt claiming no bend companion cannot silently load an adjacent one',t=>{
 const f=fixture(t,{bend:true});write(f.policy,{...f.receipt,exact_model_bends_sha256:null});
 assert.throws(()=>loadPlaybackScore(at,f.file),/bend companion hash mismatch/);
});

test('closed schema rejects unknown policy, version, hidden musical payload and missing fields',t=>{
 const f=fixture(t);const gp=fs.readFileSync(f.file);
 for(const change of[
  r=>r.schema='composition-lab.execution-policy/2',r=>r.policy='some-other-policy',
  r=>r.notes=[{pitch:99}],r=>delete r.exact_model_bends_sha256,r=>r.gp_sha256=null,
 ]){
  const receipt=structuredClone(f.receipt);change(receipt);write(f.policy,receipt);
  assert.throws(()=>loadPlaybackScore(at,f.file),/policy|hash/);assert.deepEqual(fs.readFileSync(f.file),gp);
 }
 for(const value of[null,[],false,'policy']){write(f.policy,value);assert.throws(()=>loadPlaybackScore(at,f.file),/receipt/);}
});

test('unsupported request types and missing explicit receipts cannot enable a fallback policy',t=>{
 const f=fixture(t);
 for(const value of[null,true,0,[],{},''])assert.throws(()=>loadPlaybackScore(at,f.file,{execution_policy:value}),/execution policy|execution_policy/);
 assert.throws(()=>loadPlaybackScore(at,f.file,{execution_policy:path.join(f.folder,'missing.json')}),/ENOENT/);
 assert.equal(native(loadPlaybackScore(at,f.file).score).calls[0].length,160);
});

test('native registration refuses mixed gestures without changing GP or companion bytes',t=>{
 const f=fixture(t,{mixed:true});write(f.policy,f.receipt);const before=fs.readFileSync(f.file),receipt=fs.readFileSync(f.policy);
 assert.throws(()=>loadPlaybackScore(at,f.file),/mixed mute/);
 assert.deepEqual(fs.readFileSync(f.file),before);assert.deepEqual(fs.readFileSync(f.policy),receipt);
 assert.equal(loadPlaybackScore(at,f.file,{execution_policy:false}).execution_policy_selection,'disabled');
});

test('isolated exact bends remain loaded and unchanged under a correctly bound policy',t=>{
 const f=fixture(t,{bend:true});write(f.policy,f.receipt);
 const loaded=loadPlaybackScore(at,f.file),isolated=loaded.score.tracks[0].staves[0].bars[0].voices[0].beats[2].notes[0];
 const before=isolated.bendPoints.map(p=>[p.offset,p.value]);const output=native(loaded.score);
 assert.equal(loaded.companion_selection,'adjacent');assert.deepEqual(isolated.bendPoints.map(p=>[p.offset,p.value]),before);
 assert.equal(output.calls.length,2);assert.equal(output.calls[0].length,1120);assert.equal(output.calls[1].length,160);
});
