import test from 'node:test';
import assert from 'node:assert/strict';
import { isTimeFile, timeNotePosition, applySongPitch, timeCagedShapeForBar } from '../src/song-profile.js';
const dropE = [28,35,40,45,50,55,59,64];
const tuning = [64,59,55,50,45,40];
const note = (string, fret) => ({string, fret, beat: {voice: {bar: {staff: {stringTuning: {tunings: tuning}, capo: 0}}}}});
test('only time.gp enables the profile', () => {
  assert.ok(isTimeFile('time.gp'));
  assert.ok(isTimeFile('Time.GP'));
  for (const name of ['overtime.gp','time.gp5','another.gp']) assert.equal(isTimeFile(name),false);
});
test('Time source notes preserve original F# minor pitches', () => {
  assert.deepEqual(timeNotePosition(note(3,4)),{string:5,fret:4});
  for (let string=1;string<=6;string++) for (let fret=0;fret<=24;fret++) {
    const result=timeNotePosition(note(string,fret));
    assert.ok(result);
    assert.equal(dropE[result.string-1]+result.fret,tuning[6-string]+fret);
    assert.ok(result.fret >= 0 && result.fret <= 24);
  }
});
test('Time playback retains source key and every track remains untransposed', () => {
  const tracks=[{staves:[{isPercussion:false}]},{staves:[{isPercussion:false}]},{staves:[{isPercussion:true}]}];
  const calls=[];
  const api={changeTrackTranspositionPitch:(tracks,shift)=>calls.push(shift)};
  applySongPitch(api,{tracks},true);
  assert.deepEqual(calls,[0,0,0]);
  calls.length=0;
  applySongPitch(api,{tracks},false);
  assert.deepEqual(calls,[0,0,0]);
});

test('CAGED sections follow source-score measure indices', () => {
  assert.equal(timeCagedShapeForBar(93),'low-e');
  assert.equal(timeCagedShapeForBar(104),'a');
  assert.equal(timeCagedShapeForBar(110),'high-e');
  assert.equal(timeCagedShapeForBar(126),'low-e');
});
