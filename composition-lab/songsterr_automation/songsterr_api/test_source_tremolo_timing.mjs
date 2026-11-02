import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import {pathToFileURL}from'node:url';
import {collectSourceTremoloTiming,prepareSourceTremoloTiming}from'./source_tremolo_timing.mjs';
import {exportWithExactBends,loadWithExactBends}from'./bend_fidelity.mjs';
const modulePath=process.env.ALPHATAB_MODULE||'.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
const available=fs.existsSync(modulePath),at=available?await import(pathToFileURL(path.resolve(modulePath))):null;
const copy=x=>JSON.parse(JSON.stringify(x));
function fixture(value=1,dots=0,{rest=false,tied=false,explicitTie=false,chord=false,twoAttacks=false}={}){
 const score=new at.model.Score(),track=new at.model.Track();score.addTrack(track);const staff=new at.model.Staff();track.addStaff(staff);
 staff.stringTuning.tunings=[64,59,55,50,45,40];track.playbackInfo.program=25;
 const d=dots?[3,value*2]:[1,value],measures=[];
 for(let mi=0;mi<(tied||twoAttacks?2:1);mi++){
  const master=new at.model.MasterBar();master.timeSignatureNumerator=d[0];master.timeSignatureDenominator=d[1];score.addMasterBar(master);
  const bar=new at.model.Bar();staff.addBar(bar);const voice=new at.model.Voice();bar.addVoice(voice);const beat=new at.model.Beat();voice.addBeat(beat);beat.duration=value;beat.dots=dots;
  const source=[];
  if(rest)source.push({rest:true});else for(let ni=0;ni<(chord?2:1);ni++){
   const note=new at.model.Note();note.string=6-ni;note.fret=0;note.isTieDestination=tied&&mi>0;beat.addNote(note);
   const raw={fret:0,string:ni};if(tied&&mi)raw.tie=true;if(!tied||!mi||explicitTie)raw.tremolo=[1,16];source.push(raw);
  }
  if(!rest&&(!tied||!mi||explicitTie)){beat.tremoloPicking=new at.model.TremoloPickingEffect();beat.tremoloPicking.marks=2;}
  measures.push({signature:d,voices:[{beats:[{type:value,duration:d,...(dots?{dots}:{}),notes:source}]}]});
 }
 score.finish(new at.Settings());
 const parts=[{instrumentId:25,tuning:[64,59,55,50,45,40],measures}];return{score,parts};
}
function callbacks(score){const rows=[],file=new at.midi.MidiFile(),handler=new at.midi.AlphaSynthMidiFileHandler(file,false),add=handler.addNote.bind(handler);
 handler.addNote=(track,start,length,key,velocity,channel)=>{rows.push({track,start,length,key,velocity,channel});return add(track,start,length,key,velocity,channel);};
 new at.midi.MidiFileGenerator(score,new at.Settings(),handler).generate();return rows;}
const musical=rows=>rows.map(({start,length,key})=>({start,length,key}));
const json=s=>at.model.JsonConverter.scoreToJson(s);
function expected(f){const duration=f.parts[0].measures.reduce((n,m)=>n+m.voices[0].beats[0].duration[0]*3840/m.voices[0].beats[0].duration[1],0);
 if(f.parts[0].measures[0].voices[0].beats[0].notes[0].rest)return[];
 return Array.from({length:duration/240},(_,i)=>({start:240*i,length:240,key:64}));}

for(const[name,value,dots,opts]of[['whole',1,0,{}],['half',2,0,{}],['quarter',4,0,{}],['eighth',8,0,{}],['dotted-half',2,1,{}],['rest',4,0,{rest:true}],['quarter-tied',4,0,{tied:true}]]){
 test(`explicit source sixteenths survive paired GP reload on ${name}`,{skip:!available},()=>{
  const f=fixture(value,dots,opts),original=json(f.score),raw=copy(f.parts),extension=collectSourceTremoloTiming(f.score,f.parts);
  assert.equal(json(f.score),original);assert.deepEqual(f.parts,raw);
  const pair=exportWithExactBends(at,f.score,new at.Settings(),null,extension);
  assert.equal(pair.sidecar.schema,'composition-lab.exact-model-bends.v2');
  const loaded=loadWithExactBends(at,pair.bytes,copy(pair.sidecar)),native=at.importer.ScoreLoader.loadScoreFromBytes(pair.bytes);
  assert.equal(json(loaded.score),json(native),'playback-only correction must preserve every serialized native field');
  assert.deepEqual(musical(callbacks(loaded.score)),expected(f));
  assert.equal(loaded.restored_tremolo_beats,extension.rates.length);assert.equal(loaded.native_gp_lossless,false);
  assert.deepEqual(f.parts,raw);assert.ok(!Object.hasOwn(at.model.TremoloPickingEffect.prototype,'__sourceRate'));
 });
}
test('v1 remains unchanged and does not silently claim corrected whole-note tremolo',{skip:!available},()=>{
 const f=fixture(),pair=exportWithExactBends(at,f.score);assert.equal(pair.sidecar.schema,'composition-lab.exact-model-bends.v1');
 assert.equal(loadWithExactBends(at,pair.bytes,pair.sidecar).restored_tremolo_beats,0);
 assert.notDeepEqual(musical(callbacks(loadWithExactBends(at,pair.bytes,pair.sidecar).score)),expected(f));
});
test('matching explicitly marked tie destination refuses the native duplicate-attack case',{skip:!available},()=>{
 const f=fixture(4,0,{tied:true,explicitTie:true}),before=json(f.score),raw=copy(f.parts);
 assert.equal(callbacks(f.score).length,12,'retain the native doubled-attack counterexample');
 assert.throws(()=>collectSourceTremoloTiming(f.score,f.parts),/explicit tremolo tie destination unsupported/);
 assert.equal(json(f.score),before);assert.deepEqual(f.parts,raw);
});
test('complete coattack with one agreed rate preserves both notes and multiplicity',{skip:!available},()=>{
 const f=fixture(2,0,{chord:true}),pair=exportWithExactBends(at,f.score,new at.Settings(),null,collectSourceTremoloTiming(f.score,f.parts));
 const rows=callbacks(loadWithExactBends(at,pair.bytes,pair.sidecar).score);assert.equal(rows.length,16);
 for(const key of[64,59])assert.equal(rows.filter(r=>r.key===key&&r.length===240).length,8);
});
test('missing/conflicting coattack declarations refuse without mutating source or model',{skip:!available},()=>{
 for(const change of[n=>delete n.tremolo,n=>n.tremolo=[1,8]]){
  const f=fixture(1,0,{chord:true});change(f.parts[0].measures[0].voices[0].beats[0].notes[1]);
  const before=json(f.score),raw=copy(f.parts);assert.throws(()=>collectSourceTremoloTiming(f.score,f.parts),/coattack/);
  assert.equal(json(f.score),before);assert.deepEqual(f.parts,raw);
 }
});
test('conflicting continuation and corrupted links refuse atomically',{skip:!available},()=>{
 const f=fixture(4,0,{tied:true,explicitTie:true});f.parts[0].measures[1].voices[0].beats[0].notes[0].tremolo=[1,8];f.score.tracks[0].staves[0].bars[1].voices[0].beats[0].tremoloPicking.marks=1;
 const before=json(f.score);assert.throws(()=>collectSourceTremoloTiming(f.score,f.parts),/tie destination unsupported/);assert.equal(json(f.score),before);
 const g=fixture(4,0,{tied:true});g.score.tracks[0].staves[0].bars[1].voices[0].beats[0].notes[0].tieOrigin=null;
 assert.throws(()=>collectSourceTremoloTiming(g.score,g.parts),/tie/);
});
test('invalid hash, source rate, identity, missing coverage and duplicate records refuse',{skip:!available},()=>{
 const f=fixture(4,0,{twoAttacks:true}),ext=collectSourceTremoloTiming(f.score,f.parts),pair=exportWithExactBends(at,f.score,new at.Settings(),null,ext);
 for(const mutate of[
  x=>x.gp_sha256='wrong',x=>x.source_tremolo_timing.rates[0].identity_sha256='wrong',
  x=>x.source_tremolo_timing.rates[0].source_interval_q=[1,2],x=>x.source_tremolo_timing.rates.pop(),
  x=>x.source_tremolo_timing.rates.push(copy(x.source_tremolo_timing.rates[0])),
  x=>x.source_tremolo_timing.rates[0].dependencies.pop(),x=>delete x.source_tremolo_timing,
  x=>x.source_tremolo_timing.rates[0].source_duration_q=[1,2],
 ]){const bad=copy(pair.sidecar);mutate(bad);assert.throws(()=>loadWithExactBends(at,pair.bytes,bad));}
 const bad=copy(ext);bad.rates[1].identity_sha256='wrong';const before=json(f.score);
 assert.throws(()=>prepareSourceTremoloTiming(f.score,bad),/identity/);assert.equal(json(f.score),before);
 for(const bar of f.score.tracks[0].staves[0].bars)assert.ok(!Object.hasOwn(bar.voices[0].beats[0].tremoloPicking,'getDurationAsTicks'));
});
test('wrong source clocks/member identity and unsupported effects refuse',{skip:!available},()=>{
 for(const change of[f=>f.parts[0].measures[0].voices[0].beats[0].duration=[1,2],f=>f.parts[0].measures[0].voices[0].beats[0].notes[0].fret=1,
  f=>f.score.tracks[0].staves[0].bars[0].voices[0].beats[0].notes[0].isDead=true]){
  const f=fixture();change(f);const before=json(f.score);assert.throws(()=>collectSourceTremoloTiming(f.score,f.parts));assert.equal(json(f.score),before);
 }
});
test('old schema cannot ignore a new timing extension',{skip:!available},()=>{
 const f=fixture(),pair=exportWithExactBends(at,f.score,new at.Settings(),null,collectSourceTremoloTiming(f.score,f.parts));pair.sidecar.schema='composition-lab.exact-model-bends.v1';
 assert.throws(()=>loadWithExactBends(at,pair.bytes,pair.sidecar),/requires preview schema v2/);
});
