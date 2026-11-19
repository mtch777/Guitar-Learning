import test from 'node:test';
import assert from 'node:assert/strict';
import {DOMParser, XMLSerializer} from '@xmldom/xmldom';
import {parseMusicXML, ScoreModelError} from '../public/piano/learning-songs/score-model.js';
import {transposeScore, transposeLimits} from '../public/piano/learning-songs/score-transpose.js';

const options = {DOMParser, XMLSerializer};
const parse = xml => parseMusicXML(xml, options);
const shift = (model, semitones) => transposeScore(model, semitones, options);
const root = xml => new DOMParser().parseFromString(xml, 'application/xml');
const tags = (xml, tag) => Array.from(root(xml).getElementsByTagName(tag));
const text = (xml, tag) => tags(xml, tag).map(node => node.textContent);
const key = fifths => `<key><fifths>${fifths}</fifths><mode>major</mode></key>`;
const pitch = (step, octave = 4, alter = 0, extra = '') => `<note>${extra}<pitch><step>${step}</step>${alter ? `<alter>${alter}</alter>` : ''}<octave>${octave}</octave></pitch><duration>1</duration><type>quarter</type></note>`;
const measure = (content, number = 1) => `<measure number="${number}">${content}</measure>`;
const score = content => `<score-partwise version="4.0"><work><work-title>Transpose check</work-title></work><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1">${content}</part></score-partwise>`;
const attrs = more => `<attributes><divisions>1</divisions>${more || ''}<time><beats>4</beats><beat-type>4</beat-type></time></attributes>`;
const one = (content, fifths = 0) => parse(score(measure(attrs(fifths === null ? '' : key(fifths)) + '<direction><sound tempo="75"/></direction>' + content)));
const errorCode = code => error => error instanceof ScoreModelError && error.code === code;
const noteIdentity = model => model.notes.map(({midi, step, alter, octave, ...note}) => note);

test('a polyphonic score shifts all notation and practice pitches together with stable IDs and clocks', () => {
  const original = one(pitch('D', 4, -1) + pitch('D', 6, -1, '<chord/>'), -5);
  const originalXML = original.xml;
  for (const [amount, expectedKey, firstChord] of [[1, '2', [62, 86]], [-1, '0', [60, 84]]]) {
    const result = shift(original, amount);
    assert.deepEqual(text(result.xml, 'fifths'), [expectedKey]);
    assert.deepEqual(result.groups[0].midis, firstChord);
    assert.deepEqual(result.notes.map(note => note.midi), original.notes.map(note => note.isRest ? null : note.midi + amount));
    assert.deepEqual(noteIdentity(result), noteIdentity(original));
    assert.deepEqual(result.tempos, original.tempos);
    assert.deepEqual(result.measures, original.measures);
    assert.equal(result.durationFraction, original.durationFraction);
    assert.deepEqual(result.attacks.map(({midi, ...note}) => note), original.attacks.map(({midi, ...note}) => note));
    assert.deepEqual(result.groups.map(({midis, notes, ...group}) => group), original.groups.map(({midis, notes, ...group}) => group));
    assert.equal(result.title, original.title);
    assert.equal(result.composer, original.composer);
    assert.equal(original.xml, originalXML);
  }
  assert.strictEqual(shift(original, 0), original);
  assert.equal(shift(original, 0).xml, originalXML);
});

test('up/down octave crossings have correct written octave and explicit accidental', () => {
  const up = shift(one(pitch('B', 4) + pitch('C', 5, 1, '<accidental cautionary="yes">sharp</accidental>')), 1);
  assert.deepEqual(up.notes.map(note => [note.step, note.alter, note.octave, note.midi]), [['C', 0, 5, 72], ['D', 0, 5, 74]]);
  assert.deepEqual(text(up.xml, 'accidental'), ['natural']);
  assert.equal(tags(up.xml, 'accidental')[0].getAttribute('cautionary'), 'yes');
  const down = shift(one(pitch('C', 4)), -1);
  assert.deepEqual(down.notes.map(note => [note.step, note.alter, note.octave, note.midi]), [['B', 0, 3, 59]]);
  assert.deepEqual(text(down.xml, 'fifths'), ['5']);
});

test('key changes transpose separately and a tied continuation retains its initial spelling', () => {
  const original = parse(score(
    measure(attrs(key(0)) + pitch('C', 4, 1, '<tie type="start"/><accidental>sharp</accidental><notations><tied type="start" number="2"/></notations>'))
    + measure(`<attributes>${key(-5)}</attributes>` + pitch('C', 4, 1, '<tie type="stop"/><accidental>sharp</accidental><notations><tied type="stop" number="2"/></notations>') + pitch('D', 4, -1), 2)
  ));
  const result = shift(original, 1);
  assert.deepEqual(text(result.xml, 'fifths'), ['-5', '2']);
  assert.deepEqual(result.notes.map(note => [note.step, note.alter, note.midi]), [['D', 0, 62], ['D', 0, 62], ['D', 0, 62]]);
  assert.equal(result.attacks[0].duration, 2);
  assert.equal(result.attacks[0].noteIds.length, 2);
  assert.deepEqual(noteIdentity(result), noteIdentity(original));
  assert.deepEqual(text(result.xml, 'accidental'), ['natural', 'natural']);
});

test('staff-specific and mid-measure key contexts follow musical time across backup', () => {
  const original = parse(score(measure(attrs(key(0) + '<key number="2"><fifths>-5</fifths></key>')
    + pitch('C', 4, 0, '<staff>1</staff><voice>1</voice>')
    + `<attributes>${key(-5)}</attributes>`
    + pitch('D', 4, -1, '<staff>1</staff><voice>1</voice>')
    + '<backup><duration>2</duration></backup>'
    + pitch('D', 3, -1, '<staff>2</staff><voice>2</voice>')
    + pitch('D', 3, -1, '<staff>2</staff><voice>2</voice>')
  )));
  const result = shift(original, 1);
  assert.deepEqual(result.notes.map(note => [note.step, note.alter, note.octave]), [['D', -1, 4], ['D', 0, 4], ['D', 0, 3], ['D', 0, 3]]);
  assert.deepEqual(text(result.xml, 'fifths'), ['-5', '2', '2']);
  assert.deepEqual(noteIdentity(result), noteIdentity(original));
});

test('conventional chord roots, slash basses and display labels shift while chord quality survives', () => {
  const harmony = '<harmony placement="above"><root><root-step text="C">C</root-step></root><kind text="maj7" use-symbols="no">major-seventh</kind><bass><bass-step text="G">G</bass-step></bass><degree><degree-value>9</degree-value><degree-alter>1</degree-alter><degree-type>add</degree-type></degree></harmony>';
  const original = one(harmony + '<harmony><function>V7</function><kind>dominant</kind></harmony>' + pitch('C'));
  const result = shift(original, 1);
  assert.deepEqual(text(result.xml, 'root-step'), ['D']);
  assert.deepEqual(text(result.xml, 'root-alter'), ['-1']);
  assert.deepEqual(text(result.xml, 'bass-step'), ['A']);
  assert.deepEqual(text(result.xml, 'bass-alter'), ['-1']);
  assert.equal(tags(result.xml, 'root-step')[0].getAttribute('text'), 'D');
  assert.equal(tags(result.xml, 'bass-step')[0].getAttribute('text'), 'A');
  assert.equal(tags(result.xml, 'kind')[0].getAttribute('text'), 'maj7');
  assert.deepEqual(text(result.xml, 'degree-alter'), ['1']);
  assert.deepEqual(text(result.xml, 'function'), ['V7']);
  assert.equal(tags(result.xml, 'harmony')[0].getAttribute('placement'), 'above');
});

test('every root and bass moves in a stacked chord symbol', () => {
  const harmony = '<harmony><root><root-step>C</root-step></root><kind>major</kind><bass><bass-step>G</bass-step></bass>'
    + '<root><root-step>E</root-step></root><kind>minor</kind><bass><bass-step>B</bass-step></bass></harmony>';
  const result = shift(one(harmony + pitch('C')), 1);
  assert.deepEqual(text(result.xml, 'root-step'), ['D', 'F']);
  assert.deepEqual(text(result.xml, 'root-alter'), ['-1']);
  assert.deepEqual(text(result.xml, 'bass-step'), ['A', 'C']);
  assert.deepEqual(text(result.xml, 'bass-alter'), ['-1']);
  assert.deepEqual(text(result.xml, 'kind'), ['major', 'minor']);
});

test('grace and cue ties cannot replace a playable tie spelling across a key change', () => {
  for (const kind of ['grace', 'cue']) {
    const excluded = kind === 'grace'
      ? '<note><grace/><pitch><step>C</step><alter>1</alter><octave>4</octave></pitch><tie type="start"/><type>eighth</type></note>'
      : pitch('C', 4, 1, '<cue/><tie type="start"/>') + '<backup><duration>1</duration></backup>';
    const original = parse(score(
      measure(attrs(key(0)) + pitch('C', 4, 1, '<tie type="start"/>'))
      + measure(`<attributes>${key(-5)}</attributes>` + excluded + pitch('C', 4, 1, '<tie type="stop"/>'), 2)
    ));
    const result = shift(original, 1);
    assert.deepEqual(result.notes.map(note => [note.step, note.alter]), [['D', 0], ['C', 2], ['D', 0]], kind);
    assert.equal(result.attacks[0].duration, 2);
    assert.deepEqual(noteIdentity(result), noteIdentity(original));
  }
});

test('missing initial key is supplied without altering rhythm, lyrics, rests or dynamics', () => {
  const original = one('<direction><direction-type><dynamics><p/></dynamics></direction-type></direction>'
    + pitch('C', 4, 0, '<lyric number="1"><syllabic>single</syllabic><text>word</text></lyric><notations><articulations><accent/></articulations></notations>')
    + '<note><rest/><duration>2</duration><type>half</type></note>', null);
  const result = shift(original, 1);
  assert.deepEqual(text(result.xml, 'fifths'), ['-5']);
  assert.deepEqual(result.notes.map(note => [note.isRest, note.midi]), [[false, 61], [true, null]]);
  assert.deepEqual(noteIdentity(result), noteIdentity(original));
  for (const tag of ['lyric', 'articulations', 'dynamics', 'rest']) {
    assert.equal(tags(result.xml, tag).length, tags(original.xml, tag).length);
    assert.deepEqual(text(result.xml, tag), text(original.xml, tag));
  }
});

test('arbitrary safe semitone offsets and full octave shifts retain valid pitch/key spelling', () => {
  const original = one(pitch('C'));
  assert.deepEqual(transposeLimits(original), {min: -60, max: 67});
  assert.deepEqual(shift(original, -60).notes.map(note => [note.midi, note.step, note.octave]), [[0, 'C', -1]]);
  assert.deepEqual(shift(original, 67).notes.map(note => [note.midi, note.step, note.octave]), [[127, 'G', 9]]);
  const cSharp = one(pitch('C', 4, 1), 7);
  const octave = shift(cSharp, 12);
  assert.deepEqual(text(octave.xml, 'fifths'), ['7']);
  assert.deepEqual(octave.notes.map(note => [note.step, note.alter, note.octave]), [['C', 1, 5]]);
  assert.throws(() => shift(original, 68), errorCode('TRANSPOSE_RANGE'));
  assert.throws(() => shift(original, 0.5), errorCode('INVALID_TRANSPOSE'));
  assert.throws(() => shift(original, NaN), errorCode('INVALID_TRANSPOSE'));
});

test('safe bounds include excluded grace, cue and hidden pitches', () => {
  const grace = '<note><grace/><pitch><step>C</step><octave>-1</octave></pitch><type>eighth</type></note>';
  const hidden = '<note print-object="no"><pitch><step>C</step><octave>0</octave></pitch><duration>1</duration></note>';
  const original = one(grace + hidden + pitch('G', 9, 0, '<cue/>') + pitch('C'));
  assert.equal(original.attacks.length, 1);
  assert.deepEqual(transposeLimits(original), {min: 0, max: 0});
  assert.throws(() => shift(original, -1), errorCode('TRANSPOSE_RANGE'));
  assert.throws(() => shift(original, 1), errorCode('TRANSPOSE_RANGE'));
  assert.strictEqual(shift(original, 0), original);
});

test('keyless music stays keyless and prefixed XML remains valid', () => {
  const keyless = parse(score(measure(attrs('<key><fifths>0</fifths><mode>none</mode></key>') + pitch('C'))));
  assert.deepEqual(text(shift(keyless, 1).xml, 'fifths'), ['0']);
  const xml = score(measure(attrs('') + pitch('B'))).replace(/<(\/?)([\w-]+)/g, '<$1m:$2').replace('<m:score-partwise ', '<m:score-partwise xmlns:m="urn:musicxml" ');
  const original = parse(xml);
  const result = shift(original, 1);
  assert.equal(result.notes[0].midi, 72);
  assert.match(result.xml, /<m:key><m:fifths>-5<\/m:fifths>/);
  assert.deepEqual(noteIdentity(result), noteIdentity(original));
});

test('unsupported pitch-dependent annotations fail without changing the original', () => {
  const cases = [
    [attrs('<key><key-step>F</key-step><key-alter>1</key-alter></key>') + pitch('C'), 'TRANSPOSE_KEY'],
    [attrs(key(0)) + pitch('C', 4, 0, '<notations><ornaments><trill-mark/><accidental-mark>sharp</accidental-mark></ornaments></notations>'), 'TRANSPOSE_ORNAMENT'],
    [attrs(key(0)) + '<harmony><root><root-step>C</root-step></root><kind>major</kind><frame><frame-strings>6</frame-strings><frame-frets>4</frame-frets></frame></harmony>' + pitch('C'), 'TRANSPOSE_HARMONY'],
    [attrs('<key><fifths>1</fifths><key-octave number="1">5</key-octave></key>') + pitch('C'), 'TRANSPOSE_KEY'],
  ];
  for (const [content, code] of cases) {
    const original = parse(score(measure(content)));
    const snapshot = JSON.stringify(original);
    assert.throws(() => shift(original, 1), errorCode(code));
    assert.equal(JSON.stringify(original), snapshot);
    assert.strictEqual(shift(original, 0), original);
  }
});
