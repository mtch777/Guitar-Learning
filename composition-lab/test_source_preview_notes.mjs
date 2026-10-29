import {test} from 'node:test';import assert from 'node:assert/strict';
import {address,sourceNote,sharedTargetBeat} from './source_preview_notes.mjs';
test('coattack member follows its own voice/beat/note rather than the first member',()=>{
 const a=address('event:7:0:1:0:0:0'),b=address('event:7:0:1:1:1:0');
 const doc={songId:7,partId:0,measures:[{voices:[{beats:[{notes:[{fret:8}]}]},{beats:[{notes:[{fret:99}]},{notes:[{fret:5}]}]}]}]};
 assert.equal(sourceNote(doc,a).fret,8);assert.equal(sourceNote(doc,b).fret,5);
 const score={tracks:[{staves:[{bars:[{voices:[{beats:[{playbackStart:960,playbackDuration:480}]},{beats:[{}, {playbackStart:960,playbackDuration:480}]}]}]}]}]};
 assert.equal(sharedTargetBeat(score,[a,b]).playbackStart,960);
 score.tracks[0].staves[0].bars[0].voices[1].beats[1].playbackStart=961;
 assert.throws(()=>sharedTargetBeat(score,[a,b]),/shared onset/);
});
test('invalid addresses or different source identities cannot silently display a note',()=>{
 assert.throws(()=>address('event:7:0:0:0:0:0'));assert.throws(()=>address('event:7:0:1:0:0:NaN'));
 assert.throws(()=>sourceNote({songId:8,partId:0},address('event:7:0:1:0:0:0')),/identity/);
 assert.throws(()=>sharedTargetBeat({tracks:[]},[address('event:7:0:1:0:0:0')]),/shared onset/);
});
