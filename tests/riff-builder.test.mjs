import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { toNativeScore } from '../src/riff-builder.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const localPython = resolve(root, '.local/songsterr-venv/Scripts/python.exe');
const python = existsSync(localPython) ? localPython : (process.env.PYTHON || 'python3');
const fixtureText = execFileSync(python, ['-B', '-c', [
  'import sys,json',
  "sys.path.insert(0,'public/riff-builder')",
  'import composer',
  "print(json.dumps({r:composer.generate(r) for r in composer.RECIPES}))",
].join(';')], { cwd: root, encoding: 'utf8', maxBuffer: 4 * 1024 * 1024 });
const fixtures = JSON.parse(fixtureText);
const nativePath = resolve(root, '.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs');
const at = existsSync(nativePath) ? await import(pathToFileURL(nativePath).href) : null;
const nativeSkip = at ? false : 'Native alphaTab 1.8.4 is not installed in this checkout';
const q = value => { const [n, d = 1] = String(value).split('/').map(Number); return n / d; };
const canonical = rows => rows.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
const PPQ = 960;

function midiEvents(score) {
  const events = [];
  const handler = new Proxy({}, { get: (_, method) => (...args) => events.push({method, args}) });
  new at.midi.MidiFileGenerator(score, new at.Settings(), handler).generate();
  return events;
}

test('deployed Python API supplies three complete original/developed pairs', () => {
  assert.deepEqual(Object.keys(fixtures), ['conversation', 'flow', 'chords']);
  for (const [recipe, pair] of Object.entries(fixtures)) {
    assert.equal(pair.recipe, recipe);
    assert.deepEqual(pair.tuning, [64, 59, 55, 50, 45, 40, 35, 28]);
    assert.ok(pair.changes.changed.pitch.length > 0);
    assert.notDeepEqual(pair.baseline.notes, pair.variation.notes);
    for (const score of [pair.baseline, pair.variation]) {
      assert.equal(score.bars.length, 8);
      assert.equal(score.tempo, pair.tempo);
      assert.ok(score.notes.length > 50);
      assert.ok(score.notes.some(n => q(n.duration_q) < 1));
      for (const bar of score.bars) {
        assert.equal(bar.reduce((sum, b) => sum + b.duration[0] / b.duration[1], 0), 1);
      }
    }
  }
});

for (const [recipe, pair] of Object.entries(fixtures)) {
  for (const version of ['baseline', 'variation']) {
    test(`${recipe}/${version}: native notes, rests, HP, dynamics and MIDI clock match`, {skip: nativeSkip}, () => {
      const source = pair[version];
      const native = toNativeScore(at, source, pair.title);
      const staff = native.tracks[0].staves[0];
      assert.equal(native.tempo, source.tempo);
      assert.deepEqual(staff.stringTuning.tunings, source.tuning_high_to_low);
      assert.equal(native.tracks[0].playbackInfo.program, 30);
      const notes = [];
      const rests = [];
      for (const [barIndex, bar] of staff.bars.entries()) {
        let expectedStart = barIndex * 4;
        assert.equal(bar.voices[0].beats.length, source.bars[barIndex].length);
        for (const [beatIndex, beat] of bar.voices[0].beats.entries()) {
          const original = source.bars[barIndex][beatIndex];
          const duration = 4 * original.duration[0] / original.duration[1];
          assert.equal(beat.absolutePlaybackStart, expectedStart * PPQ);
          assert.equal(beat.playbackDuration, duration * PPQ);
          assert.equal(beat.isRest, original.notes.length === 0);
          if (beat.isRest) rests.push(expectedStart * PPQ);
          for (const n of beat.notes) {
            const written = source.notes.find(x => x.bar === barIndex + 1 && x.beat === beatIndex && x.string === 8 - n.string);
            assert.ok(written, 'Native note must bind to its original authored attack');
            assert.equal(n.realValue, written.pitch);
            assert.equal(n.fret, written.fret);
            assert.equal(n.isPalmMute, written.palm_mute);
            assert.equal(n.isHammerPullOrigin, written.hp);
            assert.equal(n.accentuated, written.accent ? 1 : 0);
            assert.equal(n.dynamics, written.velocity === 'f' ? 5 : 4);
            if (written.hp) {
              const destination = n.hammerPullDestination;
              assert.ok(destination, 'HP must resolve to an actual destination');
              const expected = source.notes.find(x => x.string === written.string && q(x.onset_q) === q(written.onset_q) + q(written.duration_q));
              assert.ok(expected, 'Source HP has a directly connected same-string target');
              assert.equal(destination.realValue, expected.pitch);
              assert.equal(destination.fret, expected.fret);
              assert.equal(destination.beat.absolutePlaybackStart, q(expected.onset_q) * PPQ);
            }
            notes.push([beat.absolutePlaybackStart, n.realValue, n.string, n.fret, beat.playbackDuration]);
          }
          expectedStart += duration;
        }
        assert.equal(expectedStart, (barIndex + 1) * 4);
      }
      assert.deepEqual(canonical(notes), canonical(source.notes.map(n => [q(n.onset_q) * PPQ, n.pitch, 8 - n.string, n.fret, q(n.duration_q) * PPQ])));
      const events = midiEvents(native);
      const played = events.filter(e => e.method === 'addNote').map(e => ({start:e.args[1], duration:e.args[2], pitch:e.args[3], velocity:e.args[4]}));
      assert.deepEqual(canonical(played.map(n => [n.start, n.pitch])), canonical(source.notes.map(n => [q(n.onset_q) * PPQ, n.pitch])));
      for (const n of played) {
        const original = source.notes.find(x => x.pitch === n.pitch && q(x.onset_q) * PPQ === n.start);
        assert.ok(n.duration > 0 && n.duration <= q(original.duration_q) * PPQ);
        // Palm muting deliberately shortens sound; unmuted written holds remain exact.
        if (!original.palm_mute) assert.equal(n.duration, q(original.duration_q) * PPQ);
        assert.ok(n.velocity > 0 && n.velocity <= 127);
      }
      assert.deepEqual(events.filter(e => e.method === 'addTempo').map(e => e.args), [[0, source.tempo]]);
      assert.deepEqual(events.filter(e => e.method === 'addRest').map(e => e.args[1]), rests);
      assert.ok(events.some(e => e.method === 'finishTrack' && e.args[1] === 32 * PPQ));
    });
  }
}

test('tempo override reaches the native playback clock without changing pitches or attacks', {skip: nativeSkip}, () => {
  const source = structuredClone(fixtures.conversation.baseline);
  source.tempo = 175;
  const native = toNativeScore(at, source);
  const events = midiEvents(native);
  assert.equal(native.tempo, 175);
  assert.deepEqual(events.filter(e => e.method === 'addTempo').map(e => e.args), [[0, 175]]);
  assert.deepEqual(canonical(events.filter(e => e.method === 'addNote').map(e => [e.args[1], e.args[3]])), canonical(source.notes.map(n => [q(n.onset_q) * PPQ, n.pitch])));
});
