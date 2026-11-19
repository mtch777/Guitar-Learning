import assert from 'node:assert/strict';
import test from 'node:test';
import {keyboardLayout, playingPitchesAt} from '../public/piano/learning-songs/keyboard-model.js';
import {secondsAtBeat} from '../public/piano/learning-songs/score-model.js';

const sorted = pitches => [...pitches].sort((a, b) => a - b);
// A deterministic phrase, independent of songs the user may delete.
const phrase = {tempos:[{onset:0,bpm:75}], attacks:[
  {midi:61,onset:0,duration:1},
  {midi:85,onset:0,duration:.25},
  {midi:80,onset:.25,duration:.75},
  {midi:46,onset:2,duration:.5},
  {midi:97,onset:3,duration:.5},
]};

test('full-range keyboard spans every pitch between black low and high endpoints', () => {
  const layout = keyboardLayout(phrase.attacks);
  assert.equal(layout.min, 46);
  assert.equal(layout.max, 97);
  assert.equal(layout.keys.length, 52);
  assert.deepEqual(layout.keys.map(key => key.midi), Array.from({length:52}, (_, i) => i + 46));
  assert.equal(layout.keys[0].black, true);
  assert.equal(layout.keys.at(-1).black, true);
  assert.equal(layout.keys[0].left, 0);
  assert.ok(Math.abs(layout.keys.at(-1).left + layout.keys.at(-1).width - 1) < 1e-12);
  for (const key of layout.keys) {
    assert.ok(key.left >= 0 && key.width > 0 && key.left + key.width <= 1 + 1e-12);
  }
  const c4 = layout.keys.find(key => key.midi === 60);
  const cs4 = layout.keys.find(key => key.midi === 61);
  const d4 = layout.keys.find(key => key.midi === 62);
  assert.ok(Math.abs(c4.left + c4.width - d4.left) < 1e-12);
  assert.ok(cs4.left < d4.left && cs4.left + cs4.width > d4.left, 'Black key straddles the white-key boundary.');
});

test('single-note and short black-edge ranges remain complete without invented adjacent keys', () => {
  for (const midi of [60, 61, 0, 127]) {
    const layout = keyboardLayout([{midi}]);
    assert.equal(layout.keys.length, 1);
    assert.equal(layout.keys[0].midi, midi);
    assert.equal(layout.keys[0].left, 0);
    assert.ok(Math.abs(layout.keys[0].width - 1) < 1e-12);
  }
  const edge = keyboardLayout([{midi:61}, {midi:62}]);
  assert.deepEqual(edge.keys.map(key => key.midi), [61, 62]);
  assert.ok(edge.keys.every(key => key.left >= 0 && key.left + key.width <= 1 + 1e-12));
  assert.deepEqual(keyboardLayout([{midi:null}, {midi:-1}, {midi:128}]).keys, []);
});

test('playback highlights release between onsets and retain overlapping same-pitch voices through their final release', () => {
  const notes = [
    {midi:60, time:0, endTime:2},
    {midi:64, time:.5, endTime:1},
    {midi:60, time:1.5, endTime:3},
    {midi:67, time:4, endTime:4.25},
  ];
  for (const [time, pitches] of [[-.1, []], [0, [60]], [.5, [60,64]], [1, [60]], [1.5, [60]], [2.5, [60]], [3, []], [4, [67]], [4.25, []]]) {
    assert.deepEqual(sorted(playingPitchesAt(notes, time)), pitches, `At ${time} seconds`);
  }
});

test('a sustained lower note remains lit while the upper note changes, at every playback speed', () => {
  for (const speed of [1, .5, 1.5]) {
    const notes = phrase.attacks.map(note => ({midi:note.midi,
      time:secondsAtBeat(phrase, note.onset, speed),
      endTime:secondsAtBeat(phrase, note.onset + note.duration, speed)}));
    assert.deepEqual(sorted(playingPitchesAt(notes, 0)), [61, 85]);
    assert.deepEqual(sorted(playingPitchesAt(notes, .21 / speed)), [61, 80]);
    assert.deepEqual(sorted(playingPitchesAt(notes, -.01)), []);
  }
});
