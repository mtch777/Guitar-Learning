import test from 'node:test';import assert from 'node:assert/strict';
import {restoreDeadTies} from './restore_dead_ties.mjs';
function fixture(){
 const note={string:1,fret:0,isDead:false,isTieDestination:true};
 const beat={graceType:0,isEmpty:false,notes:[note]};
 return {note,track:{staves:[{tuning:[40],bars:[{voices:[{beats:[beat]}]}]}]},raw:{instrumentId:24,measures:[{voices:[{beats:[{notes:[{string:0,fret:0,dead:true,tie:true}]}]}]}]}};
}
test('restores both flags without changing identity or tie',()=>{const f=fixture();assert.deepEqual(restoreDeadTies(f.track,f.raw),{checked:1,restored:1,skippedGrace:0});assert.deepEqual(f.note,{string:1,fret:0,isDead:true,isTieDestination:true});assert.equal(restoreDeadTies(f.track,f.raw).restored,0);});
test('rejects mismatched fret, string, tie, beat count and ambiguous string',()=>{for(const change of [f=>f.note.fret=2,f=>f.note.string=2,f=>f.note.isTieDestination=false,f=>f.track.staves[0].bars[0].voices[0].beats=[],f=>f.track.staves[0].bars[0].voices[0].beats[0].notes.push({...f.note})]){const f=fixture();change(f);assert.throws(()=>restoreDeadTies(f.track,f.raw),/mismatch/);assert.equal(f.note.isDead,false);}});
test('leaves pitched ties unchanged and discloses skipped grace',()=>{const f=fixture();f.raw.measures[0].voices[0].beats[0].notes[0].dead=false;f.raw.measures[0].voices[0].beats.push({graceNote:true,notes:[{dead:true,tie:true}]});assert.deepEqual(restoreDeadTies(f.track,f.raw),{checked:0,restored:0,skippedGrace:1});assert.equal(f.note.isDead,false);});
