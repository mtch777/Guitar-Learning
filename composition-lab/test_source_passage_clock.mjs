import test from 'node:test';
import assert from 'node:assert/strict';
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
