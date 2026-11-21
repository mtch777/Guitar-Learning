import test from 'node:test';
import assert from 'node:assert/strict';
import {PianoAudio} from '../public/piano/learning-songs/piano-audio.js';

test('piano tone uses struck, independently decaying string harmonics and stops silently', async () => {
  const original = globalThis.AudioContext;
  const oscillators = [];
  const envelopes = [];
  const param = () => ({value:0, events:[], setValueAtTime(value,time) { this.events.push(['set',value,time]); }, exponentialRampToValueAtTime(value,time) { this.events.push(['ramp',value,time]); }, setTargetAtTime() {}, cancelScheduledValues() {}});
  class MockContext {
    constructor() { this.state='running'; this.currentTime=1; this.destination={}; }
    createGain() { const gain={gain:param(),connect() {},disconnect() {}}; envelopes.push(gain); return gain; }
    createDynamicsCompressor() { return {connect() {}}; }
    createOscillator() { const oscillator={frequency:param(),type:'',connect() {},disconnect() {},start(time) {this.started=time;},stop(time) {this.stopped=time ?? true;}}; oscillators.push(oscillator); return oscillator; }
  }
  globalThis.AudioContext=MockContext;
  try {
    const audio = new PianoAudio();
    await audio.unlock();
    audio.note(69, .5, audio.time, .7);
    assert.equal(oscillators.length, 4);
    assert.ok(oscillators.every(oscillator => oscillator.type === 'sine' && oscillator.started >= 1));
    assert.equal(oscillators[0].frequency.value, 440);
    assert.ok(oscillators[3].frequency.value > oscillators[2].frequency.value);
    const noteEnvelopes=envelopes.slice(-4).map(gain=>gain.gain.events);
    assert.ok(noteEnvelopes.every(events => events.length === 4));
    assert.ok(noteEnvelopes[3][2][1] < noteEnvelopes[0][2][1], 'Upper partials decay faster.');
    audio.stopAll();
    assert.equal(audio.voices.size, 0);
    assert.ok(oscillators.every(oscillator => oscillator.stopped));
  } finally { globalThis.AudioContext=original; }
});

test('long sustain becomes 60% volume after the threshold, without changing ordinary notes', async () => {
  const original = globalThis.AudioContext;
  const gains = [];
  const param = () => ({
    value: 0, events: [],
    setValueAtTime(value, time) { this.events.push(['set', value, time]); },
    linearRampToValueAtTime(value, time) { this.events.push(['linear', value, time]); },
    exponentialRampToValueAtTime(value, time) { this.events.push(['exponential', value, time]); },
    setTargetAtTime() {}, cancelScheduledValues() {},
  });
  class MockContext {
    constructor() { this.state = 'running'; this.currentTime = 1; this.destination = {}; }
    createGain() {
      const output = {gain:param(), connect(target) {this.target = target;}, disconnect() {}};
      gains.push(output);
      return output;
    }
    createDynamicsCompressor() { return {connect() {}}; }
    createOscillator() {
      return {frequency:param(), type:'', connect() {}, disconnect() {}, start() {}, stop() {}};
    }
  }
  globalThis.AudioContext = MockContext;
  try {
    const audio = new PianoAudio();
    await audio.unlock();
    audio.note(60, 5, audio.time, .65, 3.4);
    const softening = audio.voices.values().next().value.sustainGain;
    assert.ok(softening, 'A note held beyond the threshold gets its own gain stage.');
    assert.deepEqual(softening.gain.events.map(e => [e[0], e[1]]),
      [['set', 1], ['set', 1], ['linear', .6]]);
    const events = softening.gain.events;
    assert.ok(Math.abs(events[1][2] - events[0][2] - 3.4) < 0.001);
    assert.ok(Math.abs(events[2][2] - events[1][2] - .025) < 0.001);
    assert.ok(gains.slice(2, 6).every(gain => gain.target === softening),
      'Only the long note is routed through the 60% volume stage.');

    const before = gains.length;
    audio.note(60, 3, audio.time, .65, null);
    assert.equal(gains.length - before, 4, 'Other notes use the unmodified four-partial voice.');
    const ordinary = [...audio.voices].at(-1);
    assert.equal(ordinary.sustainGain, null);

    audio.note(60, 1, audio.time, .65, 0);
    const resumed = [...audio.voices].at(-1).sustainGain;
    assert.ok(resumed);
    assert.deepEqual(resumed.gain.events.map(e => [e[0], e[1]]),
      [['set', .6]], 'Resuming a note beyond four beats starts at 60%.');

    audio.stopAll();
    assert.equal(audio.voices.size, 0);
  } finally {
    globalThis.AudioContext = original;
  }
});
