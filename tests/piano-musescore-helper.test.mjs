import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile, mkdtemp, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import vm from 'node:vm';
import {writeImportReceipt} from '../scripts/piano/write-midi-import-receipt.mjs';

const ID = 'gl-0123456789abcdef0123456789abcdef';
const SOURCE_FILENAME = `midi-${'a'.repeat(64)}.musicxml`;
const SONG_ID = `upload-${'b'.repeat(64)}`;
const SIGNED = 'https://s3w.musescore.com/musescore.scoredata/g/abc/score.mid?X-Amz-Signature=sig';
const script = await readFile(new URL('../public/piano/learning-songs/musescore-auto-import.user.js', import.meta.url), 'utf8');

function runHelper(url, {resources = [], responseUrl, xhr = false} = {}) {
  const source = new URL(url), session = new Map(), intervals = [], redirects = [];
  const document = {
    title:'Fiona Apple — Piano score | MuseScore',
    documentElement:{dataset:{}},
    addEventListener() {},
    querySelector(selector) { return selector === 'h1' ? {textContent:'I Want You To Love Me'} : null; },
    querySelectorAll() { return []; },
  };
  const location = {
    hostname:source.hostname,
    hash:source.hash,
    replace(value) { redirects.push(value); },
  };
  const window = {
    dispatchEvent() {},
    document,
    performance:{getEntriesByType() { return resources.map(name => ({name})); }},
    fetch() { return Promise.resolve({clone:() => ({json:async () => ({info:{url:responseUrl}})})}); },
  };
  if (xhr) {
    window.XMLHttpRequest = class {
      open() {}
      addEventListener(_event, fn) { this.onLoad = fn; }
      send() { this.status = 200; this.responseText = JSON.stringify({info:{url:responseUrl}}); this.onLoad?.(); }
    };
  }
  const context = {location, window, document, URL, URLSearchParams, Event:class {},
    PerformanceObserver:undefined,
    sessionStorage:{getItem:key => session.get(key) || null, setItem:(key,value) => session.set(key,value), removeItem:key => session.delete(key)},
    setInterval(fn) { intervals.push(fn); return intervals.length; },
    clearInterval() {},
  };
  vm.runInNewContext(script, context);
  return {window, document, session, intervals, redirects};
}

test('helper advertises readiness on the piano lesson without navigating away', () => {
  const state = runHelper('https://mtch777.github.io/Guitar-Learning/piano/learning-songs/');
  assert.equal(state.document.documentElement.dataset.musescoreHelper, 'ready');
  assert.deepEqual(state.redirects, []);
});

test('helper returns the MIDI URL from MuseScore resource timing without another click', () => {
  const state = runHelper(`https://musescore.com/user/19750166/scores/6109206/piano-tutorial#guitar-learning-import=${ID}`, {resources:[SIGNED]});
  assert.equal(state.redirects.length, 1);
  const target = new URL(state.redirects[0]);
  assert.equal(target.origin, 'https://mtch777.github.io');
  const params = new URLSearchParams(target.hash.slice(1));
  assert.equal(params.get('musescore-request'), ID);
  assert.equal(params.get('musescore-midi'), SIGNED);
  assert.equal(params.get('musescore-title'), 'I Want You To Love Me');
});

test('helper ignores unrelated or forged MIDI sources', () => {
  const state = runHelper(`https://musescore.com/user/19750166/scores/6109206/piano-tutorial#guitar-learning-import=${ID}`, {resources:['https://bad.example/score.mid']});
  assert.deepEqual(state.redirects, []);
  assert.equal(state.intervals.length, 1);
});

test('helper can read the authorized jmuse JSON response if observed before MIDI fetch', async () => {
  const state = runHelper(`https://musescore.com/user/19750166/scores/6109206/piano-tutorial#guitar-learning-import=${ID}`, {responseUrl:SIGNED});
  await state.window.fetch('https://musescore.com/api/jmuse?id=6109206&index=0&type=midi');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(state.redirects.length, 1);
});

test('helper can read authorized MIDI responses from XMLHttpRequest', () => {
  const state = runHelper(`https://musescore.com/user/19750166/scores/6109206/piano-tutorial#guitar-learning-import=${ID}`, {responseUrl:SIGNED, xhr:true});
  const request = new state.window.XMLHttpRequest();
  request.open('GET', '/api/jmuse?id=6109206&index=0&type=midi');
  request.send();
  assert.equal(state.redirects.length, 1);
});

test('import receipt maps the converted MIDI file to the exact published song', async () => {
  const root = await mkdtemp(join(tmpdir(), 'midi-receipt-test-'));
  try {
    await writeFile(join(root, 'song-library.json'), JSON.stringify({songs:[{id:SONG_ID, sourceFilename:SOURCE_FILENAME}]}));
    const result = await writeImportReceipt(ID, SOURCE_FILENAME, {root});
    assert.deepEqual(result, {version:1, requestId:ID, songId:SONG_ID, sourceFilename:SOURCE_FILENAME});
    const saved = JSON.parse(await readFile(join(root, 'imports', `${ID}.json`)));
    assert.deepEqual(saved, result);
    await assert.rejects(() => writeImportReceipt('INVALID/../', SOURCE_FILENAME, {root}), /Invalid/);
    await assert.rejects(() => writeImportReceipt(ID, `midi-${'c'.repeat(64)}.musicxml`, {root}), /missing/);
  } finally { await rm(root, {recursive:true, force:true}); }
});
