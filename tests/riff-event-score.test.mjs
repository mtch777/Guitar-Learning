import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {DROP_E, normalizeEvents, toEventScore} from '../src/riff-event-score.js';
const nativePath=resolve('.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs');
const at=existsSync(nativePath)?await import(pathToFileURL(nativePath).href):null;
const skip=at?false:'Native alphaTab not installed';
const note=(string_number,fret,duration_q,extra={})=>({string_number,fret,pitch:DROP_E[string_number-1]+fret,duration_q,...extra});
const fixture={tempo:142,tuning:DROP_E,duration_q:'8',events:[
  {onset_q:'0',members:[note(8,0,'1/2'),note(5,7,'2')]},
  {onset_q:'1/2',members:[note(8,3,'1/2')]},
  {onset_q:'1',members:[note(8,5,'1/2',{hp:true})]},
  {onset_q:'3/2',members:[note(8,7,'1/2')]},
  {onset_q:'3',members:[note(3,2,'2')]},
  {onset_q:'6',members:[note(7,0,'1/3')]},
  {onset_q:'19/3',members:[note(7,2,'1/3')]},
  {onset_q:'20/3',members:[note(7,3,'1/3')]},
]};
function played(score){const out=[];const handler=new Proxy({},{get:(_,method)=>(...args)=>{if(method==='addNote')out.push(args);}});new at.midi.MidiFileGenerator(score,new at.Settings(),handler).generate();return out;}
function canonical(rows){return rows.sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));}
test('reject incompatible contact and occupied string without modifying input',()=>{
  for(const mutate of [x=>x.events[0].members[0].pitch++,x=>x.events[1].members[0].duration_q='2']){
    const x=structuredClone(fixture);mutate(x);const before=JSON.stringify(x);assert.throws(()=>normalizeEvents(x));assert.equal(JSON.stringify(x),before);
  }
});
test('native clock preserves polyphonic member lengths, triplets, rests and ties across bars',{skip},()=>{
  const source=normalizeEvents(fixture),native=toEventScore(at,fixture),audio=played(native);
  assert.equal(audio.length,source.notes.length,'Tied subdivisions must not reattack');
  assert.deepEqual(canonical(audio.map(n=>[n[1],n[2],n[3]])),canonical(source.notes.map(n=>[Math.round(n.start*960),Math.round((n.end-n.start)*960),n.pitch])));
  const notes=native.tracks[0].staves[0].bars.flatMap(b=>b.voices[0].beats.flatMap(b=>b.notes));
  assert.ok(notes.filter(n=>n.isTieDestination).length>=3);
  const hp=notes.find(n=>n.isHammerPullOrigin);assert.ok(hp?.hammerPullDestination);assert.equal(hp.hammerPullDestination.realValue,35);
  assert.equal(native.tempo,142);
});
test('non-dotted composite holds and rests split without adding attacks',{skip},()=>{
  const x={tempo:142,tuning:DROP_E,duration_q:'4',events:[{onset_q:'0',members:[note(8,3,'5/4')]},{onset_q:'5/2',members:[note(8,5,'5/4')]}]};
  assert.deepEqual(played(toEventScore(at,x)).map(n=>[n[1],n[2],n[3]]),[[0,1200,31],[2400,1200,33]]);
});
test('source-derived partial-bar lengths preserve exact native clocks without padding',{skip},()=>{
  for (const duration of ['1/2','7','17/2']) {
    const length=duration==='1/2'?.5:duration==='7'?7:8.5;
    const x={tempo:142,tuning:DROP_E,duration_q:duration,
      events:[{onset_q:'0',members:[note(8,3,duration)]}]};
    const native=toEventScore(at,x), audio=played(native);
    assert.equal(audio.length,1,'Written subdivisions must remain one held attack');
    assert.deepEqual(audio.map(n=>[n[1],n[2],n[3]]),[[0,length*960,31]]);
    assert.equal(native.masterBars.reduce((total,b)=>total+b.calculateDuration(),0),length*960);
    assert.equal(native.masterBars.at(-1).calculateDuration(),(length%4||4)*960);
  }
});

test('unsupported native clocks never silently round an attack or final duration',{skip},()=>{
  const x={tempo:142,tuning:DROP_E,duration_q:'1/7',
    events:[{onset_q:'0',members:[note(8,3,'1/7')]}]};
  assert.throws(()=>toEventScore(at,x),/native tick grid/);
});

test('source-derived triple and odd meters retain bar phases and final holds',{skip},()=>{
  for (const meter of [[3,4],[7,8]]) {
    const x={tempo:142,tuning:DROP_E,duration_q:'12',meter,
      events:[{onset_q:'0',members:[note(8,3,'12')]}]};
    const native=toEventScore(at,x), barLength=meter[0]*4/meter[1];
    assert.deepEqual(normalizeEvents(x).meter,meter);
    assert.deepEqual(native.masterBars.map(b=>[b.timeSignatureNumerator,b.timeSignatureDenominator]),
      Array.from({length:Math.ceil(12/barLength)},()=>meter));
    assert.deepEqual(native.masterBars.map(b=>b.start),
      Array.from({length:Math.ceil(12/barLength)},(_,i)=>i*barLength*960));
    assert.deepEqual(played(native).map(n=>[n[1],n[2],n[3]]),[[0,11520,31]]);
    assert.equal(native.masterBars.reduce((sum,b)=>sum+b.calculateDuration(),0),11520);
  }
});

test('invalid declared meter is rejected instead of being silently rewritten',()=>{
  for (const meter of [[0,4],[4,3],[3.5,4],[],null]) {
    const x={...fixture,meter};
    assert.throws(()=>normalizeEvents(x),/invalid meter/);
  }
});

test('source bar map preserves a clipped opening and changing meter without moving notes',{skip},()=>{
  const x={tempo:130,tuning:DROP_E,duration_q:'8',meter:[3,4],bar_map:[
    {onset_q:'0',span_q:'1/2',meter:[3,4]},
    {onset_q:'1/2',span_q:'7/2',meter:[7,8]},
    {onset_q:'4',span_q:'4',meter:[4,4]}],events:[
    {onset_q:'0',members:[note(8,3,'8')]},
    {onset_q:'3/4',members:[note(5,7,'1/2')]}]};
  const native=toEventScore(at,x);
  assert.deepEqual(native.masterBars.map(b=>[b.start,b.calculateDuration(),b.timeSignatureNumerator,b.timeSignatureDenominator]),
    [[0,480,3,4],[480,3360,7,8],[3840,3840,4,4]]);
  assert.deepEqual(canonical(played(native).map(n=>[n[1],n[2],n[3]])),canonical([[0,7680,31],[720,480,52]]));
});

test('bar map cannot add silence, overlap, extend beyond meter or omit a tail',()=>{
  for (const bar_map of [[],[{onset_q:'1',span_q:'7',meter:[4,4]}],
    [{onset_q:'0',span_q:'8',meter:[4,4]}],
    [{onset_q:'0',span_q:'4',meter:[4,4]}],
    [{onset_q:'0',span_q:'4',meter:[4,4]},{onset_q:'3',span_q:'4',meter:[4,4]}]]) {
    assert.throws(()=>normalizeEvents({...fixture,bar_map}),/bar|bars/);
  }
});

test('bend pitch trajectory survives an unrelated attack, tied subdivisions and a bar seam',{skip},()=>{
  const bend={points:[{offset_fraction:'0',semitones:'0'},
    {offset_fraction:'1/4',semitones:'1/2'},{offset_fraction:'1',semitones:'1'}]};
  for(const middle of [false,true]) {
    const x={tempo:120,tuning:DROP_E,duration_q:'8',events:[
      {onset_q:'3',members:[note(8,3,'4',{marks:{bend}})]}]};
    if(middle)x.events.push({onset_q:'7/2',members:[note(5,7,'1/4')]});
    const native=toEventScore(at,x),all=[];
    new at.midi.MidiFileGenerator(native,new at.Settings(),new Proxy({},{get:(_,method)=>(...args)=>all.push({method,args})})).generate();
    assert.deepEqual(all.filter(e=>e.method==='addNote'&&e.args[3]===31).map(e=>e.args.slice(1,4)),[[2880,3840,31]],'Bend subdivisions must not reattack');
    const events=all.filter(e=>e.method==='addNoteBend'&&e.args[3]===31).map(e=>e.args);
    assert.ok(events.length>5,'Native MIDI must actually contain the bend');
    for(const e of events) {
      const position=(e[1]-2880)/3840;
      const semitones=position<=.25?position*2:.5+(position-.25)*2/3;
      assert.ok(Math.abs(e[4]-(8192+semitones*512))<=1,`Bend at tick ${e[1]} changed trajectory`);
    }
    assert.equal(events.at(-1)[1],6720);
    assert.equal(events.at(-1)[4],8704);
  }
});

test('successive bends reset to their own attack without carrying the previous excursion',{skip},()=>{
  const bend={points:[{offset_fraction:'0',semitones:'0'},{offset_fraction:'1',semitones:'2'}]};
  const x={tempo:120,tuning:DROP_E,duration_q:'4',events:[
    {onset_q:'0',members:[note(8,3,'1',{marks:{bend}})]},
    {onset_q:'2',members:[note(8,3,'1',{marks:{bend}})]}]};
  const native=toEventScore(at,x),events=[];
  new at.midi.MidiFileGenerator(native,new at.Settings(),new Proxy({},{get:(_,method)=>(...args)=>{if(method==='addNoteBend')events.push(args);}})).generate();
  assert.ok(events.some(e=>e[1]===1920&&e[4]===8192));
  assert.deepEqual(played(native).map(e=>e.slice(1,4)),[[0,960,31],[1920,960,31]]);
});

test('wrong tuning and incomplete or impossible bend declarations are not silently played plain',()=>{
  const wrong=structuredClone(fixture);wrong.tuning=[...DROP_E];wrong.tuning[7]=30;
  assert.throws(()=>normalizeEvents(wrong),/Drop E/);
  for(const points of [[],[{offset_fraction:'0',semitones:'0'}],
    [{offset_fraction:'0',semitones:'0'},{offset_fraction:'1/2',semitones:'1'}],
    [{offset_fraction:'0',semitones:'0'},{offset_fraction:'1',semitones:'7'}]]) {
    const x={tempo:120,tuning:DROP_E,duration_q:'1',events:[{onset_q:'0',members:[note(8,3,'1',{marks:{bend:{points}}})]}]};
    assert.throws(()=>normalizeEvents(x),/bend/);
  }
});

test('connected legato slides bend the original sounding voice while retaining exact tablature',{skip},()=>{
  for(const frets of [[7,9,7],[9,7,10]])for(const start of [0,3.75]){
    const events=frets.map((fret,i)=>({onset_q:String(start+i/4),members:[note(5,fret,'1/4',{marks:{slide:i<2?'legato':null}})]}));
    events.push({onset_q:String(start+.75),members:[note(5,frets[0],'1/4')]});
    const input={tempo:120,tuning:DROP_E,duration_q:'8',events},before=structuredClone(input),native=toEventScore(at,input),calls=[];
    new at.midi.MidiFileGenerator(native,new at.Settings(),new Proxy({},{get:(_,method)=>(...args)=>calls.push({method,args})})).generate();
    const pitches=frets.map(f=>DROP_E[4]+f),base=pitches[0];
    const written=native.tracks[0].staves[0].bars.flatMap(b=>b.voices[0].beats.flatMap(b=>b.notes)).filter(n=>!n.isTieDestination);
    assert.deepEqual(written.map(n=>n.fret),[...frets,frets[0]]);
    assert.deepEqual(calls.filter(e=>e.method==='addNote').map(e=>e.args.slice(1,4)),[[start*960,720,base],[(start+.75)*960,240,base]]);
    for(const i of [1,2])assert.ok(calls.some(e=>e.method==='addNoteBend'&&e.args[1]===(start+i/4)*960&&e.args[3]===base&&e.args[4]===8192+(pitches[i]-base)*512));
    assert.ok(calls.some(e=>e.method==='addNoteBend'&&e.args[1]===(start+.75)*960&&e.args[3]===base&&e.args[4]===8192));
    assert.deepEqual(input,before);
  }
});

test('ordinary shift slides retain their reattacks and independent voice',{skip},()=>{
  const input={tempo:120,tuning:DROP_E,duration_q:'2',events:[
    {onset_q:'0',members:[note(5,7,'1/2',{marks:{slide:'shift'}})]},
    {onset_q:'1/2',members:[note(5,9,'1/2',{marks:{slide:'shift'}})]},
    {onset_q:'1',members:[note(5,7,'1/2')]}]};
  assert.deepEqual(played(toEventScore(at,input)).map(e=>e.slice(1,4)),[[0,480,52],[480,480,54],[960,480,52]]);
});
// Frozen actual engine examples are generated by the private corpus validation run.
const examplesPath=resolve('composition-lab/local-artifacts/fretboard-study-2026-11-04/riff-engine-001/EXAMPLES.json');
if(existsSync(examplesPath)) {
  const examples=JSON.parse(readFileSync(examplesPath,'utf8'));
  for(const {case:label,result} of examples.cases)if(result.status==='generated')test(`actual ${label}: native pitches/attacks/holds agree with generated events`,{skip},()=>{
    const source=normalizeEvents(result),audio=played(toEventScore(at,result));
    assert.equal(audio.length,source.notes.length);
    const expected=canonical(source.notes.map(n=>[Math.round(n.start*960),n.pitch]));
    assert.deepEqual(canonical(audio.map(n=>[Math.round(n[1]),n[3]])),expected);
    for(const n of audio){const original=source.notes.find(x=>Math.abs(x.start*960-n[1])<1e-5&&x.pitch===n[3]);assert.ok(original);assert.ok(n[2]>0);const marks=original.marks||{};if(!marks.let_ring&&marks.slide!=='legato')assert.ok(n[2]<=(original.end-original.start)*960+1e-5);if(!original.palm_mute&&!marks.staccato&&!marks.let_ring&&marks.slide!=='legato')assert.ok(Math.abs(n[2]-(original.end-original.start)*960)<1e-5);}
  });
}
