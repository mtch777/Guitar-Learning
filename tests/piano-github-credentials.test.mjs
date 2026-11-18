import test from 'node:test';
import assert from 'node:assert/strict';
import {githubCredentials} from '../public/piano/learning-songs/github-credentials.js';

test('credentials persist only on explicit save and can be forgotten', () => {
  const previous = globalThis.localStorage;
  const items = new Map();
  globalThis.localStorage = {
    getItem: key => items.get(key) ?? null,
    setItem: (key,value) => items.set(key,String(value)),
    removeItem: key => items.delete(key),
  };
  try {
    assert.equal(githubCredentials.get(), '');
    assert.equal(githubCredentials.save('   '), false);
    assert.equal(items.size, 0);
    assert.equal(githubCredentials.save(' temporary-credential '), true);
    assert.equal(githubCredentials.get(), 'temporary-credential');
    assert.equal(items.size, 1);
    githubCredentials.forget();
    assert.equal(githubCredentials.get(), '');
    assert.equal(items.size, 0);
  } finally { globalThis.localStorage = previous; }
});

test('blocked browser storage fails safely without leaking a credential', () => {
  const previous = globalThis.localStorage;
  globalThis.localStorage = {getItem() {throw Error('blocked');},setItem() {throw Error('blocked');},removeItem() {throw Error('blocked');}};
  try {
    assert.equal(githubCredentials.get(), '');
    assert.equal(githubCredentials.save('temporary-credential'), false);
    assert.doesNotThrow(() => githubCredentials.forget());
  } finally { globalThis.localStorage = previous; }
});
