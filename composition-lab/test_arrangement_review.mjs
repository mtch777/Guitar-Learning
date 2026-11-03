import test from 'node:test';
import assert from 'node:assert/strict';
import {difference,partRange,pitchedLaneGeometry,barAt,formatTime,comparisonView,changeScrollLeft,playbackSwitchState} from './arrangement-review.mjs';
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

test('a full MIDI range fits without cropping or overlapping adjacent pitched notes',()=>{
 const versions=[{notes:[note(0,0),note(0,127)]},{notes:[note(0,60)]}],before=JSON.stringify(versions);
 const geometry=pitchedLaneGeometry(partRange(versions,0));
 assert.equal(geometry.height,280);assert.equal(geometry.rowCount,130);
 const extent=(geometry.noteHeight+geometry.outlineWidth)/2;
 for(let pitch=0;pitch<=127;pitch++){
  assert(geometry.mapY(pitch)-extent>=34);assert(geometry.mapY(pitch)+extent<=geometry.height);
  if(pitch<127){
   assert(geometry.mapY(pitch+1)+extent<geometry.mapY(pitch)-extent);
   assert(Math.abs(geometry.mapY(pitch)-geometry.mapY(pitch+1)-geometry.rowSize)<1e-10);
  }
 }
 assert.equal(JSON.stringify(versions),before);
});

test('wide all-version bounds keep removed extremes and equal pitch distances',()=>{
 const versions=[{notes:[note(0,27),note(0,90)]},{notes:[note(0,15),note(0,60)]}];
 const geometry=pitchedLaneGeometry(partRange(versions,0));
 assert.equal(geometry.height,280);assert.equal(geometry.rowCount,78);
 assert(Math.abs((geometry.mapY(15)-geometry.mapY(27))-(geometry.mapY(60)-geometry.mapY(72)))<1e-10);
 assert(geometry.mapY(90)>34);assert(geometry.mapY(15)<280);
});

test('single-pitch and short ranges retain their original lane and glyph sizes',()=>{
 const single=pitchedLaneGeometry(partRange([{notes:[note(0,42)]}],0));
 assert.deepEqual([single.rowCount,single.rowSize,single.height,single.noteHeight,single.outlineWidth,single.mapY(42)],[3,9,90,7,1.7,47.5]);
 const short=pitchedLaneGeometry(partRange([{notes:[note(0,48),note(0,60)]}],0));
 assert.deepEqual([short.rowCount,short.rowSize,short.height,short.noteHeight,short.outlineWidth],[15,9,169,7,1.7]);
});
test('different bar numbers and unequal bar durations use the supplied clock',()=>{
 const data={bars:[21,23],bar_times:[{bar:21,time:0},{bar:22,time:1.5},{bar:23,time:3},{bar:24,time:5}]};
 assert.equal(barAt(data,0),21);assert.equal(barAt(data,1.5-1e-6),22);assert.equal(barAt(data,4.8),23);assert.equal(barAt(data,5),23);
 assert.equal(formatTime(65.8),'1:05');
});
test('filter without a distinct comparison cannot erase the original',()=>{
 const current={id:'source',notes:[{part:1,pitch:60,start:0,end:1}]};
 for(const base of [undefined,current,{id:'same-notes',notes:current.notes}]){
  const view=comparisonView(current,base,true);
  assert.equal(view.canFilter,false);assert.equal(view.filterActive,false);assert.equal(view.shown.length,1);assert.equal(view.removed.length,0);
 }
});
test('changed-part filter keeps context notes and reveals offscreen changes without moving audio',()=>{
 const common={part:1,voice:0,pitch:60,start:0,end:1};
 const current={id:'edit',notes:[common,{...common,pitch:65,start:15,end:16},{...common,part:2}]};
 const baseline={id:'source',notes:[common,{...common,pitch:64,start:15,end:16},{...common,part:2}]};
 const view=comparisonView(current,baseline,true);
 assert.equal(view.filterActive,true);assert.deepEqual([...view.changedParts],[1]);assert.equal(view.shown.filter(n=>view.changedParts.has(n.part)).length,2);
 assert.equal(changeScrollLeft(view.changes,0,400,100),1480);
 assert.equal(changeScrollLeft(view.changes,2200,400,100),1480);
 assert.equal(changeScrollLeft(view.changes,1400,400,100),1400);
 assert.equal(current.notes[1].start,15);
});

test('rapid A/B/C switches preserve position and playback through every load completion order',()=>{
 for(const order of [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]){
  const state=playbackSwitchState(),tokens=[state.begin(219,true),state.begin(0,false),state.begin(0,false)];
  assert.equal(state.position(0),219);
  let actualPosition=0,applied=[];
  for(const index of order){
   const target=state.complete(tokens[index],290.55);
   if(target){applied.push(target);actualPosition=target.position;}
   assert.equal(state.position(actualPosition),219);
  }
  assert.deepEqual(applied,[{position:219,playing:true}]);
  assert.equal(state.isCurrent(tokens[0]),false);assert.equal(state.isCurrent(tokens[2]),true);
 }
});

test('explicit seeks while loading survive later version clicks and retain paused intent',()=>{
 const state=playbackSwitchState(),a=state.begin(219,false);
 assert.equal(state.seek(88),true);assert.equal(state.position(0),88);
 const b=state.begin(0,false);assert.equal(state.seek(112),true);
 const c=state.begin(0,false);
 assert.equal(state.complete(a,290.55),null);assert.equal(state.complete(b,290.55),null);
 assert.deepEqual(state.complete(c,290.55),{position:112,playing:false});
 assert.equal(state.seek(45),false);assert.equal(state.position(45),45);
});

test('incomplete metadata cannot consume the pending target and a settled switch captures the new position',()=>{
 const state=playbackSwitchState(),a=state.begin(219,true);
 assert.equal(state.complete(a,NaN),null);assert.equal(state.position(0),219);
 assert.deepEqual(state.complete(a,220),{position:219,playing:true});
 const b=state.begin(250,false);
 assert.deepEqual(state.complete(b,240),{position:240,playing:false});
});
