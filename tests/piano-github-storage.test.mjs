import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import {SONG_LIBRARY, validateSongCatalog, loadSongLibrary, loadSongScore, visibleSongChoices} from '../public/piano/learning-songs/github-song-storage.js';

const deployedUrl = 'https://mtch777.github.io/Guitar-Learning/piano/learning-songs/song-library.json';
const scoreXml = '<?xml version="1.0"?><score-partwise version="4.0"/>';
const scoreSha = createHash('sha256').update(scoreXml).digest('hex');
const fixture = () => ({
  version: 1,
  defaultSongId: 'phoebe-bridgers-i-know-the-end',
  songs: [{
    id: 'phoebe-bridgers-i-know-the-end', title: 'I Know the End', composer: 'Phoebe Bridgers',
    scorePath: 'scores/phoebe-bridgers-i-know-the-end.musicxml',
    sourcePath: 'scores/phoebe-bridgers-i-know-the-end.mid',
    sourceFilename: 'Phoebe Bridgers — I Know the End.mid', sha256: scoreSha,
  }],
});
const response = (body, status = 200) => ({ok: status < 400, status, text: async () => body, headers: new Headers()});

test('published catalog loads across devices with repository URLs and no credentials', async () => {
  const requests = [];
  const fetchImpl = async (url, options) => {
    requests.push({url, options});
    return response(JSON.stringify(fixture()));
  };
  const result = await loadSongLibrary({fetchImpl, deployedCatalogUrl: deployedUrl, cacheKey: 'test'});
  assert.equal(result.source, 'deployed');
  assert.equal(result.warning, '');
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, `${deployedUrl}?library-refresh=test`);
  assert.equal(requests[0].options.credentials, 'omit');
  assert.equal(requests[0].options.cache, 'no-store');
  assert.equal(result.songs[0].url, 'https://mtch777.github.io/Guitar-Learning/piano/learning-songs/scores/phoebe-bridgers-i-know-the-end.musicxml');
  assert.match(result.songs[0].fallbackUrl, /\/gh-pages\/piano\/learning-songs\/scores\//);
  assert.equal(result.songs[0].repositorySaved, true);
  assert.match(result.songs[0].originalUrl, /\/blob\/main\/public\/piano\/learning-songs\//);
  assert.equal(SONG_LIBRARY.uploadUrl, 'https://github.com/mtch777/Guitar-Learning/upload/main/public/piano/learning-songs/uploads');
});

test('deployed failure falls back silently to the published gh-pages branch', async () => {
  const requests = [];
  const result = await loadSongLibrary({deployedCatalogUrl: deployedUrl, fetchImpl: async url => {
    requests.push(url);
    return requests.length === 1 ? response('unavailable', 503) : response(JSON.stringify(fixture()));
  }});
  assert.equal(result.source, 'github');
  assert.equal(result.warning, '');
  assert.match(requests[1], /raw\.githubusercontent\.com\/mtch777\/Guitar-Learning\/gh-pages\/piano\/learning-songs\/song-library\.json/);
  assert.doesNotMatch(requests[1], /\/main\//);
  assert.match(result.songs[0].url, /\/gh-pages\//);
});

test('unavailable repository library throws instead of claiming a local save or returning an empty list', async () => {
  await assert.rejects(loadSongLibrary({deployedCatalogUrl: deployedUrl, fetchImpl: async () => response('missing', 404)}), error => {
    assert.match(error.message, /Song list unavailable/);
    assert.match(error.cause.join('; '), /HTTP 404/);
    return true;
  });
});

test('malformed catalog gets one alternate-source attempt, then fails honestly', async () => {
  let calls = 0;
  await assert.rejects(loadSongLibrary({deployedCatalogUrl: deployedUrl, fetchImpl: async () => {
    calls++;
    return response('{broken');
  }}), /Song list unavailable/);
  assert.equal(calls, 2);
});

test('catalog rejects traversal, remote score targets, duplicated IDs and missing default', () => {
  for (const scorePath of ['../private.musicxml', 'scores/../private.musicxml', 'scores/%2e%2e/private.musicxml', 'https://example.org/music.xml', 'scores\\private.xml', '/scores/private.xml', 'uploads/raw.mxl']) {
    const catalog = fixture(); catalog.songs[0].scorePath = scorePath;
    assert.throws(() => validateSongCatalog(catalog), /unsafe score path/);
  }
  const duplicated = fixture(); duplicated.songs.push({...duplicated.songs[0]});
  assert.throws(() => validateSongCatalog(duplicated), /duplicate song ID/);
  const missingDefault = fixture(); missingDefault.defaultSongId = 'not-uploaded';
  assert.throws(() => validateSongCatalog(missingDefault), /default song/);
});

test('manifest cannot inject a local XML score, fake saved flag or arbitrary fetch URL', () => {
  const catalog = fixture();
  Object.assign(catalog.songs[0], {url: 'https://attacker.invalid/', xml: 'fake', needsScore: true, repositorySaved: false});
  const song = validateSongCatalog(catalog).songs[0];
  assert.equal(song.url, undefined);
  assert.equal(song.xml, undefined);
  assert.equal(song.needsScore, undefined);
  assert.equal(song.repositorySaved, undefined);
});

test('upload validation errors remain available without hiding valid songs', () => {
  const catalog = fixture();
  catalog.importErrors = [{sourcePath: 'uploads/broken.xml', sourceFilename: 'broken.xml', message: 'No playable notes.'}];
  const result = validateSongCatalog(catalog);
  assert.equal(result.songs.length, 1);
  assert.deepEqual(result.importErrors, catalog.importErrors);
});

test('published score digest is checked, then alternate endpoint recovers from stale content', async () => {
  const song = {...fixture().songs[0], url: 'https://mtch777.github.io/score.musicxml', fallbackUrl: 'https://raw.githubusercontent.com/mtch777/Guitar-Learning/gh-pages/score.musicxml'};
  let calls = 0;
  const result = await loadSongScore(song, {fetchImpl: async () => response(++calls === 1 ? '<stale/>' : scoreXml)});
  assert.equal(result.xml, scoreXml);
  assert.equal(result.warning, '');
  assert.equal(calls, 2);
});

test('bad score bytes are never accepted against the catalog checksum', async () => {
  const song = {...fixture().songs[0], url: 'https://mtch777.github.io/score.musicxml'};
  await assert.rejects(loadSongScore(song, {fetchImpl: async () => response('<wrong/>')}), error => {
    assert.match(error.message, /Score unavailable/);
    assert.match(error.cause.join('; '), /does not yet match/);
    return true;
  });
});

test('source filenames are metadata; binary and Unicode originals keep their original identity', () => {
  const catalog = fixture();
  Object.assign(catalog.songs[0], {sourcePath: 'uploads/Piano étude № 1 (original).mxl', sourceFilename: 'Piano étude № 1 (original).mxl', sourceSha256: 'b'.repeat(64)});
  const song = validateSongCatalog(catalog).songs[0];
  assert.equal(song.sourceFilename, 'Piano étude № 1 (original).mxl');
  assert.equal(song.sourceSha256, 'b'.repeat(64));
  assert.equal(song.sourcePath, 'uploads/Piano étude № 1 (original).mxl');
});

test('GitHub original links encode filename fragments and query characters instead of navigating elsewhere', async () => {
  const catalog = fixture(); catalog.songs[0].sourcePath = 'uploads/Bach étude #1?100%.mxl';
  const result = await loadSongLibrary({deployedCatalogUrl: deployedUrl, fetchImpl: async () => response(JSON.stringify(catalog))});
  assert.match(result.songs[0].originalUrl, /uploads\/Bach%20%C3%A9tude%20%231%3F100%25\.mxl$/);
  const url = new URL(result.songs[0].originalUrl);
  assert.equal(url.hash, '');
  assert.equal(url.search, '');
});

test('an aborted request releases its timer and reports timeout without falling back to local data', async () => {
  const fetchImpl = async (_url, {signal}) => new Promise((resolve, reject) => {
    signal.addEventListener('abort', () => reject(Object.assign(new Error('aborted'), {name: 'AbortError'})), {once: true});
  });
  await assert.rejects(loadSongLibrary({deployedCatalogUrl: deployedUrl, fetchImpl, timeoutMs: 1}), error => {
    assert.match(error.message, /Song list unavailable/);
    assert.match(error.cause.join('; '), /request timed out/);
    return true;
  });
});

test('display choices hide exact test copies and alias shared copies without trusting titles or IDs', async () => {
  const digest = xml => createHash('sha256').update(xml).digest('hex');
  const testXML = '<?xml version="1.0" encoding="utf-8"?><score-partwise>fixture</score-partwise>';
  const normalizedTestXML = testXML.replace('utf-8', 'UTF-8');
  const uniqueXML = '<score-partwise>user score with the same title</score-partwise>';
  const entries = [
    {id:'shared', title:'Song', repositorySaved:true, sha256:scoreSha},
    {id:'test', title:'Conversion test', repositorySaved:true, testScore:true, sha256:digest(normalizedTestXML)},
    {id:'local-copy', title:'Renamed local copy', localOnly:true, xml:scoreXml},
    {id:'local-test', title:'Unrelated display title', localOnly:true, xml:testXML},
    {id:'local-shared', legacyId:'shared', title:'Conversion test', localOnly:true, xml:uniqueXML},
  ];
  const before = structuredClone(entries);
  const result = await visibleSongChoices(entries);
  assert.deepEqual(result.songs.map(song => song.id), ['shared', 'local-shared']);
  assert.deepEqual([...result.aliases], [['local-copy', 'shared']]);
  assert.deepEqual(entries, before);
});

test('offline catalog fallback hides only the three exact legacy fixtures and keeps same-title user data', async () => {
  const paths = [
    'conversion-test.musicxml',
    'upload-3bd940f45a28e83f4a8065bb0d4e6c4634f5a51afc3874eb22d129ee9ea84c61.musicxml',
    'upload-734aa2f1e2baa21664a3c34e542730c48bd9c444087544e9b02df32d60a55a72.musicxml',
  ];
  const copies = await Promise.all(paths.map(async (path, index) => ({
    id:`local-old-${index}`, title:'Renamed device score', localOnly:true,
    xml:await fs.readFile(new URL(`../public/piano/learning-songs/scores/${path}`, import.meta.url), 'utf8'),
  })));
  const original = structuredClone(copies);
  const builtIn = {id:'phoebe-bridgers-i-know-the-end', title:'I Know the End', repositorySaved:true};
  const genuine = {id:'local-user', title:'Conversion test · 20 notes', localOnly:true,
    xml:copies[0].xml.replace('</score-partwise>', '<!-- Different user copy -->\n</score-partwise>')};
  const result = await visibleSongChoices([builtIn, ...copies, genuine]);
  assert.deepEqual(result.songs, [builtIn, genuine]);
  assert.equal(result.aliases.size, 0);
  assert.deepEqual(copies, original);
});
