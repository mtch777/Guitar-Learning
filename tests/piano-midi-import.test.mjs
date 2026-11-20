import test from 'node:test';
import assert from 'node:assert/strict';
import {dispatchMidiImport, validateMidiUrl, scorePageUrl, beginMuseScoreImport, consumeMidiHandoff, newImportId, readMidiImportReceipt} from '../public/piano/learning-songs/github-midi-import.js';

const SAMPLE = 'https://s3w.musescore.com/musescore.scoredata/g/example/score.mid';
const ID = 'gl-0123456789abcdef0123456789abcdef';
const session = () => {
  const entries = new Map();
  return {getItem:key => entries.get(key) ?? null, setItem:(key,value) => entries.set(key,value), removeItem:key => entries.delete(key)};
};

test('validates direct MIDI sources without accepting arbitrary hosts or credentials', () => {
  assert.equal(validateMidiUrl(SAMPLE), SAMPLE);
  for (const url of [
    'https://musescore.com/user/19750166/scores/6109206',
    'https://localhost/score.mid',
    'http://s3w.musescore.com/score.mid',
    'https://user:pass@s3w.musescore.com/score.mid',
    'https://s3w.musescore.com/not-midi.xml',
  ]) assert.throws(() => validateMidiUrl(url));
});

test('dispatches Contents: write repository event without exposing token in payload', async () => {
  let request;
  const result = await dispatchMidiImport(SAMPLE, 'test-token', {
    id:ID, title:'   Fiona Apple — Test Score  ',
    fetchImpl:async (url, options) => { request = {url, options}; return {status:204}; },
  });
  assert.deepEqual(result, {queued:true, id:ID});
  assert.match(request.url, /repos\/mtch777\/Guitar-Learning\/dispatches$/);
  assert.equal(request.options.headers.Authorization, 'Bearer test-token');
  assert.deepEqual(JSON.parse(request.options.body), {event_type:'piano-midi-import', client_payload:{midi_url:SAMPLE, request_id:ID, title:'Fiona Apple — Test Score'}});
  assert.ok(!request.options.body.includes('test-token'));
});

test('permission failures are actionable', async () => {
  await assert.rejects(() => dispatchMidiImport(SAMPLE, 'test-token', {
    id:ID, fetchImpl:async () => ({status:403}),
  }), /Contents: write/);
});

test('MuseScore URLs open the normal score page, leaving piano tutorial in its hidden frame', () => {
  assert.equal(scorePageUrl('https://musescore.com/user/19750166/scores/6109206'),
    'https://musescore.com/user/19750166/scores/6109206');
  assert.equal(scorePageUrl('6109206'), 'https://musescore.com/user/0/scores/6109206');
  assert.equal(beginMuseScoreImport('6109206', {id:ID, storage:session()}),
    'https://musescore.com/user/0/scores/6109206#guitar-learning-import=' + ID);
  assert.equal(scorePageUrl('https://musescore.com/user/19750166/scores/6109206/piano-tutorial'),
    'https://musescore.com/user/19750166/scores/6109206');
  assert.equal(scorePageUrl('https://www.musescore.com/pianouser/scores/6109206'),
    'https://musescore.com/pianouser/scores/6109206');
  assert.throws(() => scorePageUrl('https://musescore.com/other/path'));
  assert.throws(() => scorePageUrl('https://evil.test/user/19750166/scores/6109206'));
});

test('automatic MuseScore redirect and authorized MIDI return share a tab-bound request', () => {
  const signed = 'https://s3w.musescore.com/musescore.scoredata/g/test/score.mid?X-Amz-Signature=abc';
  const storage = session();
  const target = beginMuseScoreImport('https://musescore.com/user/19750166/scores/6109206', {id:ID, storage});
  assert.equal(target, `https://musescore.com/user/19750166/scores/6109206#guitar-learning-import=${ID}`);
  const location = {pathname:'/Guitar-Learning/piano/learning-songs/', search:'?v=test', hash:'#'+new URLSearchParams({'musescore-midi':signed, 'musescore-request':ID, 'musescore-title':'Fiona Apple'})};
  let replacement;
  assert.deepEqual(consumeMidiHandoff(location, {replaceState:(_a,_b,url) => replacement = url}, {storage}), {id:ID, url:signed, title:'Fiona Apple'});
  assert.equal(replacement, '/Guitar-Learning/piano/learning-songs/?v=test');
  assert.equal(consumeMidiHandoff({...location, hash:'#nothing=here'}, {replaceState() {throw Error('unexpected');}}, {storage}), null);
  assert.throws(() => consumeMidiHandoff(location, {replaceState() {}}, {storage}), /not started/);
  assert.equal(newImportId({randomUUID:() => '01234567-89ab-cdef-0123-456789abcdef'}), ID);
});

test('a MuseScore error returns to the lesson with a useful message', () => {
  const storage = session();
  beginMuseScoreImport('https://musescore.com/user/19750166/scores/6109206', {id:ID, storage});
  const location = {pathname:'/Guitar-Learning/piano/learning-songs/', search:'', hash:'#'+new URLSearchParams({'musescore-error':'MIDI never loaded', 'musescore-request':ID})};
  assert.deepEqual(consumeMidiHandoff(location, {replaceState() {}}, {storage}), {id:ID, error:'MIDI never loaded'});
});

test('a timed-out MuseScore import returns an actionable, bounded diagnostic trace', () => {
  const storage = session();
  beginMuseScoreImport('https://musescore.com/user/19750166/scores/6109206', {id:ID, storage});
  const hash = '#'+new URLSearchParams({
    'musescore-request':ID,
    'musescore-error':'MuseScore did not provide MIDI within 90 seconds.',
    'musescore-debug':'Score page opened → Tutorial frame loaded → MIDI API HTTP 404',
  });
  assert.deepEqual(consumeMidiHandoff({pathname:'/Guitar-Learning/piano/learning-songs/', search:'', hash}, {replaceState() {}}, {storage}), {
    id:ID, error:'MuseScore did not provide MIDI within 90 seconds.',
    debug:'Score page opened → Tutorial frame loaded → MIDI API HTTP 404',
  });
});

test('old manually supplied MIDI links remain available but require an explicit Import click', () => {
  const url = SAMPLE + '?X-Amz-Signature=example';
  const result = consumeMidiHandoff({pathname:'/Guitar-Learning/piano/learning-songs/', search:'', hash:'#'+new URLSearchParams({'musescore-midi':url})}, {replaceState() {}}, {storage:session()});
  assert.equal(result.legacy, true);
  assert.equal(result.url, url);
  assert.match(result.id, /^gl-[a-f0-9]{32}$/);
});

test('published MIDI success and failed-import receipts have request-bound, actionable outcomes', () => {
  const songId = 'upload-' + 'a'.repeat(64);
  assert.deepEqual(readMidiImportReceipt({version:1, requestId:ID, songId}, ID), {failed:false, songId});
  assert.deepEqual(readMidiImportReceipt({version:1, requestId:ID, status:'failed',
    error:'A tie into measure 22 has no matching start.'}, ID),
    {failed:true, error:'A tie into measure 22 has no matching start.'});
  assert.throws(() => readMidiImportReceipt({version:1, requestId:'gl-' + 'b'.repeat(32),
    status:'failed', error:'failure'}, ID), /invalid/);
  assert.throws(() => readMidiImportReceipt({version:1, requestId:ID,
    status:'garbage', songId}, ID), /invalid/);
  assert.throws(() => readMidiImportReceipt({version:1, requestId:ID,
    status:'failed', error:''}, ID), /invalid/);
});
