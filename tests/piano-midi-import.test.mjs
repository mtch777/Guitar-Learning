import test from 'node:test';
import assert from 'node:assert/strict';
import {dispatchMidiImport, validateMidiUrl} from '../public/piano/learning-songs/github-midi-import.js';

const SAMPLE = 'https://s3w.musescore.com/musescore.scoredata/g/example/score.mid';

test('validates direct MIDI sources without accepting arbitrary hosts or credentials', () => {
  assert.equal(validateMidiUrl(SAMPLE), SAMPLE);
  for (const url of [
    'https://musescore.com/user/19750166/scores/6109206',
    'https://localhost/score.mid',
    'http://s3w.musescore.com/score.mid',
    'https://user:pass@s3w.musescore.com/score.mid',
  ]) assert.throws(() => validateMidiUrl(url));
});

test('dispatches authorized GitHub Actions workflow without exposing token in input', async () => {
  let request;
  const result = await dispatchMidiImport(SAMPLE, 'test-token', {
    fetchImpl:async (url, options) => { request = {url, options}; return {status:204}; },
  });
  assert.deepEqual(result, {queued:true});
  assert.match(request.url, /actions\/workflows\/piano-import-midi\.yml\/dispatches$/);
  assert.equal(request.options.headers.Authorization, 'Bearer test-token');
  assert.deepEqual(JSON.parse(request.options.body), {ref:'main', inputs:{midi_url:SAMPLE}});
  assert.ok(!request.options.body.includes('test-token'));
});

test('permission failures are actionable', async () => {
  await assert.rejects(() => dispatchMidiImport(SAMPLE, 'test-token', {
    fetchImpl:async () => ({status:403}),
  }), /Actions: write/);
});
