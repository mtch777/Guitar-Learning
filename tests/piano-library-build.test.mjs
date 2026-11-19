import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {buildSongLibrary} from '../scripts/piano/build-song-library.mjs';
import {validateSongCatalog} from '../public/piano/learning-songs/github-song-storage.js';

const fixtureXML = await fs.readFile(new URL('../public/piano/learning-songs/scores/conversion-test.musicxml', import.meta.url), 'utf8');
const fixtureOriginal = await fs.readFile(new URL('../public/piano/learning-songs/scores/conversion-test-source.nwctxt', import.meta.url));
const moduleObject = {exports:{}};
vm.runInNewContext(await fs.readFile(new URL('../public/piano/learning-songs/vendor/fflate-0.8.3.min.js', import.meta.url), 'utf8'), {
  module:moduleObject, exports:moduleObject.exports, require:createRequire(import.meta.url),
  Uint8Array, Uint16Array, Uint32Array, Int32Array, ArrayBuffer, TextEncoder, TextDecoder,
});
const {zipSync} = moduleObject.exports;
const bytes = value => new TextEncoder().encode(value);
const digest = value => createHash('sha256').update(value).digest('hex');
const titled = title => fixtureXML.replaceAll('Cuthbert NWC Test', title);
const normalized = xml => xml.replace(/(<\?xml\b[^?]*\bencoding\s*=\s*["'])[^"']+(["'])/i, '$1UTF-8$2');

async function temporaryLibrary(t) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'piano-song-library-'));
  t.after(() => fs.rm(root, {recursive:true, force:true}));
  await fs.mkdir(path.join(root, 'scores'));
  await fs.mkdir(path.join(root, 'uploads'));
  await fs.writeFile(path.join(root, 'scores/seed.musicxml'), fixtureXML);
  await fs.writeFile(path.join(root, 'scores/seed-source.nwctxt'), fixtureOriginal);
  const seed = {version:1, defaultSongId:'fixture', songs:[{
    id:'fixture', title:'Bundled fixture', composer:'Michael Cuthbert',
    scorePath:'scores/seed.musicxml', sourcePath:'scores/seed-source.nwctxt', testScore:true,
  }]};
  await fs.writeFile(path.join(root, 'song-library.seed.json'), JSON.stringify(seed));
  return {root, seed, put:async (filename, contents) => {
    const target = path.join(root, 'uploads', filename);
    await fs.mkdir(path.dirname(target), {recursive:true});
    await fs.writeFile(target, contents);
    return target;
  }};
}

test('native MusicXML becomes a shared song while the exact uploaded bytes remain untouched', async t => {
  const {root, put} = await temporaryLibrary(t);
  const original = Buffer.from(titled('Uploaded MusicXML'));
  const uploadedPath = await put('piano.musicxml', original);
  const parserBefore = globalThis.DOMParser;
  const catalog = await buildSongLibrary({root});
  assert.equal(globalThis.DOMParser, parserBefore);
  assert.equal(catalog.songs.length, 2);
  const song = catalog.songs[1];
  assert.equal(song.title, 'Uploaded MusicXML');
  assert.equal(song.sourcePath, 'uploads/piano.musicxml');
  assert.equal(song.noteCount, 20);
  assert.equal(song.attackCount, 19);
  assert.equal(song.sourceSha256, digest(original));
  assert.deepEqual(await fs.readFile(uploadedPath), original);
  const output = await fs.readFile(path.join(root, song.scorePath), 'utf8');
  assert.equal(output, normalized(original.toString('utf8')));
  assert.equal(song.sha256, digest(output));
  assert.equal(song.id, `upload-${song.sha256}`);
  assert.equal(validateSongCatalog(catalog).songs.length, 2);
});

test('saved MIDI keeps its display name and import receipt when the converter changes its score ID', async t => {
  const {root, seed, put} = await temporaryLibrary(t);
  const filename = `midi-${'e'.repeat(64)}.musicxml`;
  const scoreXML = titled('Music21 Fragment');
  const originalPath = await put(filename, scoreXML);
  seed.uploadedLabels = {[filename]: {title:'I Want You To Love Me', composer:'Fiona Apple'}};
  await fs.writeFile(path.join(root, 'song-library.seed.json'), JSON.stringify(seed));
  await fs.mkdir(path.join(root, 'imports'));
  const requestId = `gl-${'b'.repeat(32)}`;
  const receiptPath = path.join(root, 'imports', `${requestId}.json`);
  await fs.writeFile(receiptPath, JSON.stringify({version:1, requestId, sourceFilename:filename, songId:`upload-${'0'.repeat(64)}`}) + '\n');
  const catalog = await buildSongLibrary({root});
  const song = catalog.songs.find(song => song.sourceFilename === filename);
  assert.equal(song.title, 'I Want You To Love Me');
  assert.equal(song.composer, 'Fiona Apple');
  assert.equal(JSON.parse(await fs.readFile(receiptPath, 'utf8')).songId, song.id);
  assert.equal(await fs.readFile(originalPath, 'utf8'), scoreXML, 'The stored MusicXML is never changed to rename a song.');
  const previousReceipt = await fs.readFile(receiptPath, 'utf8');
  await buildSongLibrary({root});
  assert.equal(await fs.readFile(receiptPath, 'utf8'), previousReceipt, 'A second build does not rewrite the receipt.');
});

test('legacy XML encoding normalizes to UTF-8 without changing accents or source bytes', async t => {
  const {root, put} = await temporaryLibrary(t);
  const originalText = titled('Béla Bartók étude').replace(/encoding="[^"]+"/, 'encoding="ISO-8859-1"');
  const original = Buffer.from(originalText, 'latin1');
  const source = await put('Béla Bartók (piano).xml', original);
  const catalog = await buildSongLibrary({root});
  const song = catalog.songs[1];
  assert.equal(song.title, 'Béla Bartók étude');
  assert.equal(song.sourceFilename, 'Béla Bartók (piano).xml');
  assert.equal(song.sourceSha256, digest(original));
  assert.deepEqual(await fs.readFile(source), original);
  const output = await fs.readFile(path.join(root, song.scorePath), 'utf8');
  assert.match(output, /encoding="UTF-8"/);
  assert.match(output, /Béla Bartók étude/);
  assert.equal(validateSongCatalog(catalog).songs[1].sourceFilename, song.sourceFilename);
});

test('UTF-16 source normalizes declared encoding and preserves the uploaded original including BOM', async t => {
  const {root, put} = await temporaryLibrary(t);
  const xml = titled('UTF-16 étude').replace(/encoding="[^"]+"/, 'encoding="UTF-16"');
  const original = Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(xml, 'utf16le')]);
  const source = await put('wide characters.xml', original);
  const catalog = await buildSongLibrary({root});
  const song = catalog.songs[1];
  const output = await fs.readFile(path.join(root, song.scorePath), 'utf8');
  assert.equal(output, normalized(xml));
  assert.deepEqual(await fs.readFile(source), original);
  assert.equal(song.sourceSha256, digest(original));
});

test('actual MXL ZIP uses its namespaced container and preserves Unicode title and original binary', async t => {
  const {root, put} = await temporaryLibrary(t);
  const xml = titled('Été — 曲 № 1');
  const original = Buffer.from(zipSync({
    'wrong.xml': bytes(titled('Wrong first file')),
    'META-INF/container.xml': bytes('<?xml version="1.0"?><c:container xmlns:c="urn:oasis:names:tc:opendocument:xmlns:container"><c:rootfiles><c:rootfile full-path="scores/actual.musicxml" media-type="application/vnd.recordare.musicxml+xml"/></c:rootfiles></c:container>'),
    'scores/actual.musicxml': bytes(xml),
  }));
  const source = await put('Été (piano) № 1.mxl', original);
  const catalog = await buildSongLibrary({root});
  const song = catalog.songs[1];
  assert.equal(song.title, 'Été — 曲 № 1');
  assert.equal(song.sourceFilename, 'Été (piano) № 1.mxl');
  assert.equal(await fs.readFile(path.join(root, song.scorePath), 'utf8'), normalized(xml));
  assert.deepEqual(await fs.readFile(source), original);
  assert.equal(song.sourceSha256, digest(original));
  assert.equal(validateSongCatalog(catalog).songs.length, 2);
});

test('invalid XML and MXL are isolated diagnostics while valid uploads remain playable', async t => {
  const {root, put} = await temporaryLibrary(t);
  await put('valid.musicxml', titled('Valid survivor'));
  const brokenXML = Buffer.from('<score-partwise><part></score-partwise>');
  const brokenMXL = Buffer.from('not a ZIP');
  const sourceXML = await put('broken.xml', brokenXML);
  const sourceMXL = await put('broken.mxl', brokenMXL);
  const catalog = await buildSongLibrary({root});
  assert.equal(catalog.songs.length, 2);
  assert.equal(catalog.songs[1].title, 'Valid survivor');
  assert.equal(catalog.importErrors.length, 2);
  assert.deepEqual(new Set(catalog.importErrors.map(item => item.sourceFilename)), new Set(['broken.xml', 'broken.mxl']));
  assert.ok(catalog.importErrors.every(item => item.message.length > 0));
  assert.deepEqual(await fs.readFile(sourceXML), brokenXML);
  assert.deepEqual(await fs.readFile(sourceMXL), brokenMXL);
  assert.equal(validateSongCatalog(catalog).importErrors.length, 2);
});

test('duplicate uploads share one score and leave every original intact', async t => {
  const {root, put} = await temporaryLibrary(t);
  const xml = titled('Duplicate upload');
  const first = await put('a.musicxml', xml);
  const second = await put('b.xml', xml);
  const catalog = await buildSongLibrary({root});
  assert.equal(catalog.songs.length, 2);
  assert.equal(catalog.songs[1].sourcePath, 'uploads/a.musicxml');
  assert.equal(await fs.readFile(first, 'utf8'), xml);
  assert.equal(await fs.readFile(second, 'utf8'), xml);
  assert.equal((await fs.readdir(path.join(root, 'scores'))).filter(name => name.startsWith('upload-')).length, 1);
});

test('re-uploading an existing seed score does not create a declaration-case duplicate', async t => {
  const {root, put} = await temporaryLibrary(t);
  await put('existing.musicxml', fixtureXML);
  const catalog = await buildSongLibrary({root});
  assert.equal(catalog.songs.length, 1);
  assert.equal(catalog.songs[0].id, 'fixture');
  assert.equal(catalog.songs[0].sha256, digest(fixtureXML));
});

test('removing an upload removes only its derived score, preserving originals and unrelated scores', async t => {
  const {root, put} = await temporaryLibrary(t);
  const first = await put('remove-me.musicxml', titled('Remove me'));
  const remainingBytes = Buffer.from(titled('Keep me'));
  const second = await put('upload-' + 'f'.repeat(64) + '.musicxml', remainingBytes);
  await fs.writeFile(path.join(root, 'scores/handwritten.musicxml'), 'hand-authored untouched');
  const before = await buildSongLibrary({root});
  const removedSong = before.songs.find(song => song.title === 'Remove me');
  const remainingSong = before.songs.find(song => song.title === 'Keep me');
  await fs.unlink(first);
  const after = await buildSongLibrary({root});
  assert.equal(after.songs.length, 2);
  await assert.rejects(fs.access(path.join(root, removedSong.scorePath)), {code:'ENOENT'});
  await fs.access(path.join(root, remainingSong.scorePath));
  assert.deepEqual(await fs.readFile(second), remainingBytes);
  assert.equal(await fs.readFile(path.join(root, 'scores/handwritten.musicxml'), 'utf8'), 'hand-authored untouched');
  assert.equal(await fs.readFile(path.join(root, 'scores/seed.musicxml'), 'utf8'), fixtureXML);
});

test('explicit seed files remain protected even when their names match generated-score naming', async t => {
  const {root, seed} = await temporaryLibrary(t);
  seed.songs[0].scorePath = `scores/upload-${'a'.repeat(64)}.musicxml`;
  await fs.writeFile(path.join(root, seed.songs[0].scorePath), fixtureXML);
  await fs.writeFile(path.join(root, 'song-library.seed.json'), JSON.stringify(seed));
  await buildSongLibrary({root});
  assert.equal(await fs.readFile(path.join(root, seed.songs[0].scorePath), 'utf8'), fixtureXML);
});

test('repeated builds produce an identical catalog and scores without source modification', async t => {
  const {root, put} = await temporaryLibrary(t);
  const a = await put('nested/Piece A (piano).musicxml', titled('A score'));
  const b = await put('Piece B.xml', titled('B score'));
  const sourceBytes = await Promise.all([fs.readFile(a), fs.readFile(b)]);
  const first = await buildSongLibrary({root});
  const manifestBytes = await fs.readFile(path.join(root, 'song-library.json'));
  const firstScores = await Promise.all(first.songs.map(song => fs.readFile(path.join(root, song.scorePath))));
  const second = await buildSongLibrary({root});
  assert.deepEqual(second, first);
  assert.deepEqual(await fs.readFile(path.join(root, 'song-library.json')), manifestBytes);
  assert.deepEqual(await Promise.all(second.songs.map(song => fs.readFile(path.join(root, song.scorePath)))), firstScores);
  assert.deepEqual(await Promise.all([fs.readFile(a), fs.readFile(b)]), sourceBytes);
});

test('symbolic links outside uploads are excluded from repository song imports', async t => {
  const {root} = await temporaryLibrary(t);
  await fs.writeFile(path.join(root, 'outside.musicxml'), titled('Outside file'));
  await fs.symlink('../outside.musicxml', path.join(root, 'uploads/linked.musicxml'));
  const catalog = await buildSongLibrary({root});
  assert.equal(catalog.songs.length, 1);
  assert.equal(catalog.importErrors.length, 0);
});

test('unsupported uploaded formats get diagnostics while upload-folder housekeeping stays quiet', async t => {
  const {root, put} = await temporaryLibrary(t);
  const unsupported = Buffer.from('unchanged original MIDI bytes');
  const source = await put('piano.mid', unsupported);
  await put('README.md', 'How to upload scores.');
  await put('.gitkeep', '');
  const catalog = await buildSongLibrary({root});
  assert.equal(catalog.songs.length, 1);
  assert.equal(catalog.importErrors.length, 1);
  assert.equal(catalog.importErrors[0].sourcePath, 'uploads/piano.mid');
  assert.match(catalog.importErrors[0].message, /musicxml|supported|convert/i);
  assert.deepEqual(await fs.readFile(source), unsupported);
  assert.equal(validateSongCatalog(catalog).importErrors.length, 1);
});

test('only explicitly fingerprinted uploads are marked as tests, preserving same-title user scores', async t => {
  const {root, seed, put} = await temporaryLibrary(t);
  const testXML = titled('MusicXML-upload-test');
  const userXML = testXML.replace('</score-partwise>', '<!-- User copy -->\n</score-partwise>');
  seed.testSourceSha256 = [digest(testXML)];
  await fs.writeFile(path.join(root, 'song-library.seed.json'), JSON.stringify(seed));
  const testPath = await put('renamed-fixture.xml', testXML);
  const userPath = await put('MusicXML-upload-test.xml', userXML);
  const catalog = await buildSongLibrary({root});
  const uploaded = catalog.songs.filter(song => song.id !== 'fixture');
  assert.equal(uploaded.length, 2);
  assert.equal(uploaded.find(song => song.sourceFilename === 'renamed-fixture.xml').testScore, true);
  assert.equal(uploaded.find(song => song.sourceFilename === 'MusicXML-upload-test.xml').testScore, undefined);
  assert.equal(await fs.readFile(testPath, 'utf8'), testXML);
  assert.equal(await fs.readFile(userPath, 'utf8'), userXML);
});
