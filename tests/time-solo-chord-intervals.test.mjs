import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source=readFileSync(new URL('../src/trainer.js',import.meta.url),'utf8');
const start=source.indexOf('function applyContinuousBendPitch(');
const end=source.indexOf('function getPhysicalBendOffset(',start);
assert.ok(start>=0 && end>start);
test('Time solo note and bend rendering use active chord, not global base key',()=>{
  assert.match(source,/root: Number\(section\.root\)/);
  assert.match(source,/revealCell\(cell, interval\)/);
  assert.match(source,/applyContinuousBendPitch\(\s*cell,\s*bendSemitones,\s*chord/);
  const calls=[];
  const cell={dataset:{absolutePitch:'55'},style:{setProperty(){}},appendChild(){},innerHTML:''};
  const ctx=vm.createContext({
    document:{getElementById(id){return {value:id==='rootSelect'?'4':'aeolian'};},createElement(){return {className:'',appendChild(){},append(){}};}},
    getIntervalForPitch(pitch,root,mode){calls.push({pitch,root,mode});return 'R';},
    intervalStyles:{R:{background:'#34A853',color:'#000'}},
    midiToPitchClass:p=>((p%12)+12)%12,
    midiToOctave:p=>Math.floor(p/12)-1,
    createBendIntervalLabel:()=>({}),
    mixHexColors:()=> '#34A853'
  });
  vm.runInContext(source.slice(start,end),ctx);
  ctx.applyContinuousBendPitch(cell,1,{root:7,quality:'major'});
  assert.deepEqual(calls.map(x=>x.root),[7,7]);
  assert.deepEqual(calls.map(x=>x.mode),['ionian','ionian']);
  calls.length=0;
  ctx.applyContinuousBendPitch(cell,1,{root:4,quality:'minor'});
  assert.deepEqual(calls.map(x=>x.root),[4,4]);
  assert.deepEqual(calls.map(x=>x.mode),['aeolian','aeolian']);
  calls.length=0;
  ctx.applyContinuousBendPitch(cell,1,null);
  assert.deepEqual(calls.map(x=>x.root),[4,4],'MVP retains selected base-key behavior');
});
