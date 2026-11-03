import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {sourcePassageClock} from './source_passage_clock.mjs';

// Authored clock fixtures, not musical-source evidence.
const bar=(index,start,end)=>({masterBar:{index},start,end});
const input=(shift=0)=>({masterBars:[bar(0,0,3840)],midiTickShift:shift,
 tempoChanges:[{tick:0,tempo:120}],initialTempo:120,
 job:{start_bar:1,end_bar:1,target_bar:1,target_offset_q:'1'}});

test('zero shift retains ordinary source-bar range, cue and duration',()=>{
 const result=sourcePassageClock(input());
 assert.deepEqual(result.playbackRange,{startTick:0,endTick:3840});
 assert.equal(result.targetTick,960);assert.equal(result.targetSeconds,.5);assert.equal(result.requestedSeconds,2);
});
test('native preroll shifts both bounds and target, exactly once',()=>{
 const result=sourcePassageClock(input(120));
 assert.deepEqual(result.playbackRange,{startTick:120,endTick:3960});
 assert.equal(result.targetTick,1080);assert.equal(result.targetSeconds,.5);assert.equal(result.requestedSeconds,2);
});
test('tempo events retain actual MIDI ticks rather than getting a second shift',()=>{
 const source=input(120);source.tempoChanges.push({tick:1920,tempo:60});source.job.target_offset_q='2';
 const result=sourcePassageClock(source);
 assert.equal(result.targetTick,2040);assert.equal(result.targetSeconds,1.0625);assert.equal(result.requestedSeconds,3.0625);
});
test('fractional source offset and a later bar are bound to the chosen traversal',()=>{
 const source=input(120);source.masterBars=[bar(0,0,960),bar(1,960,4800),bar(2,4800,8640)];
 source.job={start_bar:2,end_bar:3,target_bar:3,target_offset_q:'5/2'};
 const result=sourcePassageClock(source);
 assert.deepEqual(result.playbackRange,{startTick:1080,endTick:8760});assert.equal(result.targetTick,7320);
 assert.equal(result.targetSeconds,3.25);assert.equal(result.requestedSeconds,4);
 assert.deepEqual(result.traversal.map(b=>[b.traversal_index,b.source_bar]),[[1,2],[2,3]]);
});
test('repeated source bars retain the existing first-encounter traversal explicitly',()=>{
 const source=input(120);source.masterBars=[bar(0,0,3840),bar(1,3840,7680),bar(0,7680,11520),bar(1,11520,15360)];
 source.job={start_bar:1,end_bar:2,target_bar:2,target_offset_q:0};
 const result=sourcePassageClock(source);
 assert.deepEqual(result.playbackRange,{startTick:120,endTick:7800});assert.equal(result.targetTick,3960);
 assert.deepEqual(result.traversal.map(b=>b.traversal_index),[0,1]);
});
test('missing or invalid native shift is not silently treated as zero',()=>{
 for(const value of[undefined,null,NaN,Infinity,-1,true,'120'])assert.throws(()=>sourcePassageClock({...input(),midiTickShift:value}),/tick shift/);
});
test('unknown tempo or out-of-range target refuses instead of producing a plausible cue',()=>{
 assert.throws(()=>sourcePassageClock({...input(),tempoChanges:[{tick:0,tempo:0}]}),/tempo event/);
 const source=input();source.job.target_offset_q='1/0';assert.throws(()=>sourcePassageClock(source),/offset/);
 source.job.target_offset_q=5;assert.throws(()=>sourcePassageClock(source),/outside/);
});

test('complete score keeps all 155 bars and the actual tempo clock through its ending',()=>{
 const source=input(120);source.sourceBarCount=155;
 source.masterBars=Array.from({length:155},(_,i)=>bar(i,i*3840,(i+1)*3840));
 source.initialTempo=129;
 source.tempoChanges=[{tick:0,tempo:129},{tick:142*3840,tempo:123},{tick:144*3840,tempo:120},{tick:146*3840,tempo:117}];
 source.job={complete_score:true,start_bar:1,end_bar:155,target_bar:147,target_offset_q:0};
 const frozen=JSON.stringify(source),result=sourcePassageClock(source);
 assert.equal(result.traversal.length,155);
 assert.deepEqual(result.playbackRange,{startTick:120,endTick:155*3840+120});
 const expected=(142*3840-120)/960*60/129+8*60/123+8*60/120+(36+120/960)*60/117;
 assert.ok(Math.abs(result.requestedSeconds-expected)<1e-9);
 assert.ok(Math.abs(result.targetSeconds-(expected-36*60/117))<1e-9);
 assert.equal(JSON.stringify(source),frozen);
});

test('complete score includes repeated traversals rather than stopping at the first ending',()=>{
 const source=input(120);source.sourceBarCount=2;
 source.masterBars=[bar(0,0,3840),bar(1,3840,7680),bar(0,7680,11520),bar(1,11520,15360)];
 source.job={complete_score:true,start_bar:1,end_bar:2,target_bar:2,target_offset_q:0};
 const result=sourcePassageClock(source);
 assert.deepEqual(result.playbackRange,{startTick:120,endTick:15480});
 assert.deepEqual(result.traversal.map(b=>b.source_bar),[1,2,1,2]);
 assert.equal(result.targetTick,3960);assert.equal(result.requestedSeconds,8);
});

test('long previews still need explicit complete-score scope and exact source endpoints',()=>{
 const source=input();source.sourceBarCount=25;
 source.masterBars=Array.from({length:25},(_,i)=>bar(i,i*3840,(i+1)*3840));
 source.job={start_bar:1,end_bar:25,target_bar:1};
 assert.throws(()=>sourcePassageClock(source),/passage playback range/);
 assert.throws(()=>sourcePassageClock({...source,job:{...source.job,complete_score:false}}),/passage playback range/);
 for(const complete_score of[1,'true',null])assert.throws(()=>sourcePassageClock({...source,job:{...source.job,complete_score}}),/boolean/);
 source.job.complete_score=true;
 for(const job of[{...source.job,start_bar:2},{...source.job,end_bar:24},{...source.job,end_bar:'25'}])
  assert.throws(()=>sourcePassageClock({...source,job}),/source endpoints/);
 for(const sourceBarCount of[undefined,null,0,24,26,'25'])
  assert.throws(()=>sourcePassageClock({...source,sourceBarCount}),/source endpoints/);
});

test('complete-score claims refuse missing endpoints, discontinuity and malformed traversal',()=>{
 const source=input();source.sourceBarCount=3;
 source.masterBars=[bar(0,0,3840),bar(1,3840,7680),bar(2,7680,11520)];
 source.job={complete_score:true,start_bar:1,end_bar:3,target_bar:1};
 for(const masterBars of[source.masterBars.slice(1),source.masterBars.slice(0,2)])
  assert.throws(()=>sourcePassageClock({...source,masterBars}),/source endpoints/);
 for(const masterBars of[[bar(0,0,3840),bar(2,7680,11520)],
  [bar(0,0,3840),bar(1,3839,7680),bar(2,7680,11520)],
  [bar(0,0,3840),bar(3,3840,7680),bar(2,7680,11520)],
  [bar(0,1,3840),bar(1,3840,7680),bar(2,7680,11520)]])
  assert.throws(()=>sourcePassageClock({...source,masterBars}),/continuous native traversal/);
});

// This stub tests the real CLI's duration/termination contract, not synthesis fidelity.
const exportStub=`
let source;
export const importer={ScoreLoader:{loadScoreFromBytes(data){source=JSON.parse(Buffer.from(data).toString());return source;}}};
export class Settings{constructor(){this.notation={};this.player={vibrato:{}};}}
export const NotationMode={GuitarPro:1};
class MidiFile{constructor(){this.events=[];this.tickShift=0;}}
class TempoChangeEvent{constructor(tick,beatsPerMinute){this.tick=tick;this.beatsPerMinute=beatsPerMinute;}}
class AlphaSynthMidiFileHandler{constructor(midi){this.midi=midi;}}
class MidiFileGenerator{
 constructor(score,settings,handler){this.score=score;this.handler=handler;}
 generate(){this.tickLookup={masterBars:this.score.masterBars.map((_,index)=>({masterBar:{index},start:index*3840,end:(index+1)*3840}))};this.handler.midi.events.push(new TempoChangeEvent(0,this.score.tempo));}
}
export const midi={MidiFile,TempoChangeEvent,AlphaSynthMidiFileHandler,MidiFileGenerator};
class AudioExportOptions{}
class AlphaSynth{
 exportAudio(options){let rendered=0;const seconds=(options.playbackRange.endTick-options.playbackRange.startTick)/960*60/source.tempo;
  return{render(milliseconds){if(milliseconds!==1000)throw Error('Expected one-second render request');if(!source.runaway&&rendered++>=seconds)return null;return{samples:new Float32Array(44100*2).fill(.25)};}};
 }
}
export const synth={AudioExportOptions,AlphaSynth};
`;

function renderFixture(t,runaway){
 const parent=path.resolve(os.tmpdir()),dir=fs.mkdtempSync(path.join(parent,'composition-full-playback-'));
 t.after(()=>{
  assert.equal(path.dirname(path.resolve(dir)),parent);
  assert.ok(path.basename(dir).startsWith('composition-full-playback-'));
  fs.rmSync(dir,{recursive:true,force:true});
 });
 const module=path.join(dir,'export-stub.mjs'),score=path.join(dir,'authored.gp'),font=path.join(dir,'stub.sf2'),jobs=path.join(dir,'jobs.json'),out=path.join(dir,'audio.wav');
 fs.writeFileSync(module,exportStub);fs.writeFileSync(font,Buffer.from([1]));
 fs.writeFileSync(score,JSON.stringify({masterBars:Array.from({length:25},()=>({})),tempo:120,tracks:[{}],runaway}));
 fs.writeFileSync(jobs,JSON.stringify([{file:score,out,mode:'ensemble',complete_score:true,start_bar:1,end_bar:25,target_bar:1}]));
 const script=fileURLToPath(new URL('./render_source_passages.mjs',import.meta.url));
 return{result:spawnSync(process.execPath,[script,module,font,jobs],{encoding:'utf8',timeout:30000}),out,receipt:jobs.replace('.json','.results.json')};
}

test('renderer completes a 50-second full-score job using its verified clock',t=>{
 const {result,out,receipt}=renderFixture(t,false);assert.equal(result.status,0,result.stderr||result.error?.message);
 const report=JSON.parse(fs.readFileSync(receipt,'utf8'))[0];
 assert.equal(report.requested_seconds,50);assert.equal(report.seconds,50);assert.equal(report.source_traversal.length,25);
 assert.equal(report.render_pass_limit,52);assert.equal(report.renderer,'alphaTab internal MIDI / Sonivox GM SF2, fixed .3 gain');
 assert.equal(fs.readFileSync(out).length,44+50*44100*2);
});

test('renderer refuses a never-ending exporter without publishing partial audio',t=>{
 const {result,out,receipt}=renderFixture(t,true);assert.notEqual(result.status,0);assert.match(result.stderr,/over-limit passage/);
 assert.equal(fs.existsSync(out),false);assert.equal(fs.existsSync(receipt),false);
});
