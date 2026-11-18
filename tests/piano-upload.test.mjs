import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { File } from 'node:buffer';
import { DOMParser } from '@xmldom/xmldom';
import { readScoreFile } from '../public/piano/learning-songs/score-upload.js';
import { parseMusicXML } from '../public/piano/learning-songs/score-model.js';

// Exercise the actual browser-vendored ZIP implementation, not an unzip mock.
const moduleObject = { exports: {} };
vm.runInNewContext(fs.readFileSync(new URL('../public/piano/learning-songs/vendor/fflate-0.8.3.min.js', import.meta.url), 'utf8'), {
  module: moduleObject, exports: moduleObject.exports, require: createRequire(import.meta.url),
  Uint8Array, Uint16Array, Uint32Array, Int32Array, ArrayBuffer, TextEncoder, TextDecoder,
});
const { zipSync, unzipSync } = moduleObject.exports;
globalThis.DOMParser = DOMParser;

// Real public-domain Cuthbert score already shipped with the lesson.
const xml = fs.readFileSync(new URL('../public/piano/learning-songs/scores/conversion-test.musicxml', import.meta.url), 'utf8');
const bytes = text => new TextEncoder().encode(text);
const file = (name, contents) => new File([contents], name);
const archive = entries => file('score.mxl', zipSync(entries));
const read = input => readScoreFile(input, { unzip: unzipSync });
const container = path => `<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="${path}" media-type="application/vnd.recordare.musicxml+xml"/></rootfiles></container>`;

test('plain real MusicXML stays byte-equivalent and retains its 20 source notes', async () => {
  const loaded = await read(file('real-score.musicxml', bytes(xml)));
  assert.equal(loaded, xml);
  assert.equal(parseMusicXML(loaded, { DOMParser }).notes.filter(note => !note.isRest).length, 20);
});

test('real compressed MXL follows its declared nested MusicXML path', async () => {
  const loaded = await read(archive({
    'META-INF/container.xml': bytes(container('scores/actual.musicxml')),
    'irrelevant.xml': bytes('<unrelated/>'),
    'scores/actual.musicxml': bytes(xml),
  }));
  assert.equal(loaded, xml);
});

test('namespace-prefixed MXL container cannot silently select a different score', async () => {
  const prefixed = '<?xml version="1.0"?><c:container xmlns:c="urn:oasis:names:tc:opendocument:xmlns:container"><c:rootfiles><c:rootfile full-path="actual.musicxml" media-type="application/vnd.recordare.musicxml+xml"/></c:rootfiles></c:container>';
  const loaded = await read(archive({
    'wrong.xml': bytes('<score-partwise version="4.0"><work><work-title>Wrong score</work-title></work></score-partwise>'),
    'META-INF/container.xml': bytes(prefixed),
    'actual.musicxml': bytes(xml),
  }));
  assert.equal(loaded, xml);
});

test('a missing declared MXL score is rejected instead of substituting another file', async () => {
  await assert.rejects(read(archive({
    'META-INF/container.xml': bytes(container('missing.musicxml')),
    'other.musicxml': bytes(xml),
  })), /missing its declared score/i);
});

test('UTF-16 BOM and declared legacy XML encoding preserve valid source text', async () => {
  const utf16 = Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(xml.replace(/encoding="[^"]+"/, 'encoding="UTF-16"'), 'utf16le')]);
  assert.match(await read(file('utf16.musicxml', utf16)), /score-partwise/);
  const latinText = xml.replace(/encoding="[^"]+"/, 'encoding="ISO-8859-1"').replace('Cuthbert NWC Test', 'Béla Bartók');
  const decoded = await read(file('legacy.xml', Buffer.from(latinText, 'latin1')));
  assert.equal(decoded, latinText);
  assert.match(decoded, /Béla Bartók/);
});

test('empty, oversized, wrong-extension and non-ZIP files fail with actionable messages', async () => {
  await assert.rejects(read(file('empty.xml', new Uint8Array())), /nonempty/i);
  await assert.rejects(read(file('large.xml', new Uint8Array(20 * 1024 * 1024 + 1))), /20 MB/i);
  await assert.rejects(read(file('song.pdf', bytes(xml))), /Export other formats to MusicXML/i);
  await assert.rejects(read(file('not-a-zip.mxl', bytes(xml))), /not a compressed MusicXML archive/i);
});

test('actual compressed XML payloads exceeding the expanded limit reject before use', async () => {
  const huge = new Uint8Array(20 * 1024 * 1024 + 1).fill(32);
  await assert.rejects(read(archive({
    'META-INF/container.xml': bytes(container('too-large.xml')),
    'too-large.xml': huge,
  })), /expanded score exceeds the 20 MB limit/i);
});

test('malformed ordinary XML is rejected by the real parser before an import can be committed', async () => {
  const loaded = await read(file('broken.musicxml', bytes('<score-partwise><part></score-partwise>')));
  assert.throws(() => parseMusicXML(loaded, { DOMParser }), error => error.code === 'INVALID_XML');
});
