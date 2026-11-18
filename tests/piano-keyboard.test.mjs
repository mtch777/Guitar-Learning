import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {DOMParser, XMLSerializer} from '@xmldom/xmldom';
import {keyboardLayout, playingPitchesAt} from '../public/piano/learning-songs/keyboard-model.js';
import {parseMusicXML, secondsAtBeat} from '../public/piano/learning-songs/score-model.js';

const sorted = pitches => [...pitches].sort((a, b) => a - b);
const phoebe = parseMusicXML(readFileSync(new URL('../public/piano/learning-songs/scores/phoebe-bridgers-i-know-the-end.musicxml', import.meta.url), 'utf8'), {DOMParser, XMLSerializer});

test('actual Phoebe keyboard spans every pitch from its black low endpoint through its black high endpoint', () => {
  const layout = keyboardLayout(phoebe.attacks);
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

test('actual Phoebe sustains its first lower note while its upper note changes, using speed-adjusted score time', () => {
  for (const speed of [1, .5, 1.5]) {
    const notes = phoebe.attacks.map(note => ({midi:note.midi,
      time:secondsAtBeat(phoebe, note.onset, speed),
      endTime:secondsAtBeat(phoebe, note.onset + note.duration, speed)}));
    assert.deepEqual(sorted(playingPitchesAt(notes, 0)), [61, 85]);
    assert.deepEqual(sorted(playingPitchesAt(notes, .21 / speed)), [61, 80]);
    assert.deepEqual(sorted(playingPitchesAt(notes, -.01)), []);
  }
});
