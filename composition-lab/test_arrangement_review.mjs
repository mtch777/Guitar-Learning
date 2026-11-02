import test from 'node:test';
import assert from 'node:assert/strict';
import {difference,partRange,barAt,formatTime} from './arrangement-review.mjs';
const note=(part,pitch,start=0,extra={})=>({part,pitch,start,end:start+1,voice:0,velocity:80,fret:0,string:1,dead:false,ghost:false,...extra});
test('coattacks and repeated identical notes are counted, never collapsed',()=>{
 const base=[note(0,40),note(0,47),note(0,47),note(1,40)];
 const current=[note(1,40),note(0,47),note(0,52)];
 const d=difference(current,base);assert.deepEqual(d.shown.map(n=>n.change),['same','same','new']);
 assert.deepEqual(d.removed.map(n=>n.pitch),[40,47]);assert.equal(base.length,4);
});
test('reordered addresses cannot disguise a changed pitch, duration, or voice',()=>{
 const base=[note(0,40,0,{ref:'old:0'}),note(0,43,1,{ref:'old:1'}),note(0,47,2)];
 const current=[note(0,45,1,{ref:'old:1'}),note(0,40,0,{ref:'new:99'}),note(0,47,2,{end:4}),note(0,47,2,{voice:1})];
 const d=difference(current,base);assert.equal(d.shown.filter(n=>n.change==='same').length,1);assert.equal(d.removed.length,2);
});
test('pitch bounds include all versions, low notes and high removed notes',()=>{
 const versions=[{notes:[note(0,27),note(0,90),note(1,10)]},{notes:[note(0,15),note(0,60)]}];
 assert.deepEqual(partRange(versions,0),{low:14,high:91});
});
test('different bar numbers and unequal bar durations use the supplied clock',()=>{
 const data={bars:[21,23],bar_times:[{bar:21,time:0},{bar:22,time:1.5},{bar:23,time:3},{bar:24,time:5}]};
 assert.equal(barAt(data,0),21);assert.equal(barAt(data,1.5-1e-6),22);assert.equal(barAt(data,4.8),23);assert.equal(barAt(data,5),23);
 assert.equal(formatTime(65.8),'1:05');
});
