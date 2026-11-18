import test from 'node:test';
import assert from 'node:assert/strict';
import {File} from 'node:buffer';
import {webcrypto} from 'node:crypto';
import {uploadScoreToGitHub} from '../public/piano/learning-songs/github-song-upload.js';

const options = {cryptoImpl:webcrypto, encodeBase64:input => Buffer.from(input, 'binary').toString('base64')};

test('direct upload sends original bytes to the GitHub source directory', async () => {
  const bytes = Buffer.from([0, 1, 2, 3, 127, 128, 254, 255]);
  const file = new File([bytes], 'My score.musicxml');
  let request;
  const result = await uploadScoreToGitHub(file, 'temporary-test-token', {
    ...options,
    fetchImpl:async (url, init) => { request = {url, init}; return {status:201}; },
  });
  assert.match(result.path, /^public\/piano\/learning-songs\/uploads\/My score--[a-f0-9]{64}\.musicxml$/);
  assert.equal(request.init.method, 'PUT');
  assert.equal(request.init.credentials, 'omit');
  assert.equal(request.init.headers.Authorization, 'Bearer temporary-test-token');
  assert.equal(request.init.cache, 'no-store');
  assert.equal(new URL(request.url).pathname.endsWith(encodeURIComponent(result.filename)), true);
  const body = JSON.parse(request.init.body);
  assert.equal(body.branch, 'main');
  assert.deepEqual(Buffer.from(body.content, 'base64'), bytes);
  assert.doesNotMatch(JSON.stringify(result), /temporary-test-token/);
});

test('invalid file and missing token never call GitHub', async () => {
  let called = false;
  const fetchImpl = async () => { called = true; return {status:201}; };
  await assert.rejects(uploadScoreToGitHub(new File(['x'], 'score.gp'), 'token', {...options, fetchImpl}), /MusicXML/i);
  await assert.rejects(uploadScoreToGitHub(new File(['x'], 'score.xml'), '', {...options, fetchImpl}), /token/i);
  assert.equal(called, false);
});

test('authentication failure provides a useful error without echoing the token', async () => {
  await assert.rejects(uploadScoreToGitHub(new File(['score'], 'score.xml'), 'sensitive-token', {
    ...options, fetchImpl:async () => ({status:403}),
  }), error => /Contents: read and write/.test(error.message) && !error.message.includes('sensitive-token'));
});
