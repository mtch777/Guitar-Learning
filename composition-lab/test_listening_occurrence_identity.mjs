import test from 'node:test';
import assert from 'node:assert/strict';
import {difference} from './arrangement-review.mjs';

const note=(identity,start)=>({comparison_identity:identity,part:2,voice:0,pitch:60,start,end:start+1,velocity:80,string:1,fret:0,dead:false,ghost:false});

test('moving repeated notes into another occurrence position remains a visible change',()=>{
 const original=[note('source:a',1),note('source:b',2),note('source:c',3)];
 const shifted=[note('source:a',0),note('source:b',1),note('source:c',2)];
 const result=difference(shifted,original);
 assert.deepEqual(result.shown.map(n=>n.change),['new','new','new']);
 assert.equal(result.removed.length,3);
 assert.equal(difference(original,original).removed.length,0);
 assert.deepEqual(difference([...original].reverse(),original).shown.map(n=>n.change),['same','same','same']);
});

test('mixed or duplicated asserted identities fail instead of hiding uncertainty',()=>{
 const original=[note('a',1),note('b',2)];
 assert.throws(()=>difference([note('a',1),note('a',2)],original),/complete and unique/);
 assert.throws(()=>difference([note('a',1),note(undefined,2)],original),/complete and unique/);
 assert.throws(()=>difference([note('',1)],original),/complete and unique/);
});

test('legacy payloads retain their measured multiset comparison',()=>{
 const original=[note(undefined,1),note(undefined,2),note(undefined,2)];
 const current=[note(undefined,1),note(undefined,2)];
 const result=difference(current,original);
 assert.deepEqual(result.shown.map(n=>n.change),['same','same']);
 assert.equal(result.removed.length,1);
});
