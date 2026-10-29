import assert from 'node:assert/strict';
import test from 'node:test';
import { timeSoloChordNumeral } from '../src/data/time-solo.js';

test('Time chord numerals use F# minor tonic and detected chord quality', () => {
  assert.equal(timeSoloChordNumeral(4, 'major'), '♭VII'); // E
  assert.equal(timeSoloChordNumeral(6, 'minor'), 'i'); // F#m
  assert.equal(timeSoloChordNumeral(9, 'major'), '♭III'); // A
  assert.equal(timeSoloChordNumeral(8, 'diminished'), 'ii°'); // G#°
  assert.equal(timeSoloChordNumeral(11, 'minor'), 'iv'); // Bm
  assert.equal(timeSoloChordNumeral(1, 'minor'), 'v'); // C#m
  assert.equal(timeSoloChordNumeral(2, 'major'), '♭VI'); // D
  assert.equal(timeSoloChordNumeral(1, 'major'), 'V'); // C# major
  assert.equal(timeSoloChordNumeral(6, 'major'), 'I'); // borrowed F# major
  assert.equal(timeSoloChordNumeral(4, 'minor'), '♭vii'); // Em
  assert.equal(timeSoloChordNumeral(4, 'unknown'), null);
});
