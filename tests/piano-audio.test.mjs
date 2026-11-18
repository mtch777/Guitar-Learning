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
