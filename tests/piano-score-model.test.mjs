import test from 'node:test';
import assert from 'node:assert/strict';
import { DOMParser, XMLSerializer } from '@xmldom/xmldom';
import { parseMusicXML, secondsAtBeat, beatAtSeconds, ScoreModelError } from '../public/piano/learning-songs/score-model.js';

/* Focused acceptance checklist for the score/event engine:
 * [x] Preserve notes, rests, exact fractional clocks, part/staff/voice membership.
 * [x] Group simultaneous notes and duplicate pitches without losing source IDs.
 * [x] Tie continuations extend holds without becoming new required attacks.
 * [x] Respect tempo changes and provide inverse clock conversions.
 * [x] Expose written-order repeat behavior; reject unsupported piano pitches.
 * [x] Keep source IDs stable and fail atomically on ambiguous/malformed timing.
 * These are synthetic unit-test scores, not downloaded song demonstrations.
 */

const attrs = (divisions = 1, beats = 4, beatType = 4) => `<attributes><divisions>${divisions}</divisions><time><beats>${beats}</beats><beat-type>${beatType}</beat-type></time></attributes>`;
const note = (step = 'C', octave = 4, duration = 1, extra = '') => `<note>${extra}<pitch><step>${step}</step><octave>${octave}</octave></pitch><duration>${duration}</duration><type>quarter</type></note>`;
const rest = duration => `<note><rest/><duration>${duration}</duration></note>`;
const measure = (content, number = 1) => `<measure number="${number}">${content}</measure>`;
const part = (id, content) => `<part id="${id}">${content}</part>`;
const score = (parts, metadata = '') => `<?xml version="1.0"?><score-partwise version="4.0">${metadata}<part-list><score-part id="P1"><part-name>Piano</part-name></score-part><score-part id="P2"><part-name>Second part</part-name></score-part></part-list>${parts}</score-partwise>`;
const parse = text => parseMusicXML(text, { DOMParser, XMLSerializer });
const oneMeasure = content => score(part('P1', measure(attrs() + content)));
const errorCode = code => error => error instanceof ScoreModelError && error.code === code;

test('backup/forward, independent voices and both staves retain simultaneous pitches', () => {
  const content = attrs()
    + note('C', 4, 2, '<voice>1</voice><staff>1</staff>')
    + note('E', 4, 2, '<chord/><voice>1</voice><staff>1</staff>')
    + note('D', 4, 2, '<voice>1</voice><staff>1</staff>')
    + '<backup><duration>4</duration></backup>'
    + note('G', 3, 4, '<voice>5</voice><staff>2</staff>');
  const model = parse(score(part('P1', measure(content))));
  assert.deepEqual(model.groups.map(group => [group.onset, group.midis]), [[0, [55, 60, 64]], [2, [62]]]);
  assert.equal(model.duration, 4);
  assert.equal(model.notes.find(n => n.midi === 55).voice, '5');
  assert.equal(model.notes.find(n => n.midi === 55).staff, 2);
  assert.equal(model.notes.find(n => n.midi === 62).partIndex, 0);
  const withForward = parse(oneMeasure('<forward><duration>2</duration></forward>' + note()));
  assert.equal(withForward.groups[0].onset, 2);
  assert.equal(withForward.duration, 3);
});

test('duplicate simultaneous pitches need one key attack while retaining all notation IDs', () => {
  const model = parse(score(
    part('P1', measure(attrs() + note('C', 4, 2) + note('E', 4, 2, '<chord/>')))
    + part('P2', measure(attrs() + note('C', 4, 4)))
  ));
  assert.deepEqual(model.groups[0].midis, [60, 64]);
  const c = model.attacks.find(n => n.midi === 60);
  assert.equal(c.duration, 4);
  assert.equal(c.noteIds.length, 2);
  assert.deepEqual(c.partIds, ['P1', 'P2']);
  assert.equal(model.notes.filter(n => n.midi === 60).every(n => n.attackId === c.id), true);
});

test('ties through three measures create one sustained attack and preserve every notehead', () => {
  const start = '<tie type="start"/>';
  const continuation = '<tie type="stop"/><tie type="start"/>';
  const stop = '<tie type="stop"/>';
  const model = parse(score(part('P1',
    measure(attrs(3, 2) + note('C', 4, 6, start), 1)
    + measure(note('C', 4, 6, continuation), 2)
    + measure(note('C', 4, 3, stop) + note('D', 4, 3), 3)
  )));
  assert.deepEqual(model.groups.map(g => [g.onset, g.midis]), [[0, [60]], [5, [62]]]);
  assert.equal(model.attacks[0].duration, 5);
  assert.equal(model.attacks[0].noteIds.length, 3);
  assert.equal(new Set(model.notes.slice(0, 3).map(n => n.attackId)).size, 1);
  assert.equal(model.duration, 6);
});

test('written tied elements work when a producer omits playback tie elements', () => {
  const model = parse(oneMeasure(
    note('C', 4, 1, '<notations><tied type="start" number="2"/></notations>')
    + note('C', 4, 1, '<notations><tied type="stop" number="2"/></notations>')
  ));
  assert.equal(model.attacks.length, 1);
  assert.equal(model.attacks[0].duration, 2);
});

test('rest-only positions do not create quiz groups or lose their elapsed duration', () => {
  const model = parse(score(part('P1', measure(attrs(2) + rest(4) + note('C', 4, 2) + rest(2) + note('D', 4, 2)))));
  assert.deepEqual(model.groups.map(g => g.onset), [2, 4]);
  assert.equal(model.notes.filter(n => n.isRest).length, 2);
  assert.equal(model.notes.filter(n => n.isRest).every(n => n.attackId === null), true);
  assert.equal(model.duration, 5);
});

test('rational triplet onsets from different divisions group exactly without quantization', () => {
  const first = attrs(3) + note('C', 4, 1) + note('D', 4, 1) + note('E', 4, 1) + note('F', 4, 3);
  const second = attrs(6) + rest(4) + note('G', 4, 2);
  const model = parse(score(part('P1', measure(first)) + part('P2', measure(second))));
  assert.deepEqual(model.groups.map(g => g.onsetFraction), ['0', '1/3', '2/3', '1']);
  assert.deepEqual(model.groups[2].midis, [64, 67]);
  assert.equal(model.notes.find(n => n.midi === 67).durationFraction, '1/3');
  assert.equal(model.duration, 2);
});

test('pickup measures align across parts and key/meter changes do not transpose explicit pitches', () => {
  const first = part('P1', measure(attrs() + note('C', 4, 1), 0)
    + measure('<attributes><key><fifths>5</fifths></key><time><beats>3</beats><beat-type>4</beat-type></time></attributes>' + note('E', 4, 3), 1));
  const second = part('P2', measure(attrs() + rest(1), 0) + measure(note('F', 3, 3), 1));
  const model = parse(score(first + second));
  assert.deepEqual(model.measures.map(m => [m.onset, m.duration]), [[0, 1], [1, 3]]);
  assert.deepEqual(model.groups[1].midis, [53, 64]);
  assert.equal(model.duration, 4);
});

test('an entirely empty measure advances by its explicit meter', () => {
  const model = parse(score(part('P1', measure(attrs(1, 3), 1) + measure(note('C', 4, 1), 2))));
  assert.equal(model.groups[0].onset, 3);
  assert.equal(model.duration, 4);
});

test('tempo changes integrate in seconds and invert under speed scaling', () => {
  const model = parse(oneMeasure('<direction><sound tempo="60"/></direction>' + note('C', 4, 2)
    + '<direction><sound tempo="120"/></direction>' + note('D', 4, 2)));
  assert.deepEqual(model.tempos.map(t => [t.onset, t.bpm]), [[0, 60], [2, 120]]);
  assert.equal(secondsAtBeat(model, 4), 3);
  assert.equal(secondsAtBeat(model, 4, 2), 1.5);
  assert.equal(beatAtSeconds(model, 2.5), 3);
  for (const scale of [0.5, 1, 1.75]) for (const beat of [0, 1, 2, 2.5, 4, 5]) {
    assert.ok(Math.abs(beatAtSeconds(model, secondsAtBeat(model, beat, scale), scale) - beat) < 1e-10);
  }
  assert.throws(() => secondsAtBeat(model, 1, 0), errorCode('INVALID_TEMPO_SCALE'));
});

test('metronome beat units and dotted beats convert to quarter-note BPM', () => {
  const model = parse(oneMeasure('<direction><direction-type><metronome><beat-unit>half</beat-unit><per-minute>30</per-minute></metronome></direction-type></direction>' + note()));
  assert.equal(model.tempos[0].bpm, 60);
  const dotted = parse(oneMeasure('<direction><direction-type><metronome><beat-unit>quarter</beat-unit><beat-unit-dot/><per-minute>80</per-minute></metronome></direction-type></direction>' + note()));
  assert.equal(dotted.tempos[0].bpm, 120);
});

test('tempo offsets use the current divisions and source sound tempo takes precedence', () => {
  const model = parse(score(part('P1', measure(attrs(2)
    + '<direction><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>90</per-minute></metronome></direction-type><sound tempo="60"/></direction>'
    + '<direction><offset>2</offset><sound tempo="120"/></direction>' + note('C', 4, 4)))));
  assert.deepEqual(model.tempos.map(t => [t.onset, t.bpm]), [[0, 60], [1, 120]]);
  assert.equal(secondsAtBeat(model, 2), 1.5);
});

test('missing initial tempo is an explicit default and conflicting part tempos reject', () => {
  const model = parse(oneMeasure(note()));
  assert.equal(model.tempos[0].bpm, 120);
  assert.ok(model.warnings.some(w => w.includes('120 BPM')));
  assert.throws(() => parse(score(
    part('P1', measure(attrs() + '<direction><sound tempo="60"/></direction>' + note()))
    + part('P2', measure(attrs() + '<direction><sound tempo="90"/></direction>' + note('G')))
  )), errorCode('CONFLICTING_TEMPO'));
});

test('stable unique note IDs survive serialized XML reload and retain source metadata', () => {
  const input = score(part('P1', measure(attrs() + note().replace('<note>', '<note id="keep-this">')
    + note('D').replace('<note>', '<note id="keep-this">'))), '<work><work-title>A &amp; B</work-title></work><identification><creator type="composer">Example Author</creator></identification>');
  const first = parse(input);
  const second = parseMusicXML(first.xml, { DOMParser });
  assert.equal(first.title, 'A & B');
  assert.equal(first.composer, 'Example Author');
  assert.equal(first.notes[0].id, 'keep-this');
  assert.equal(new Set(first.notes.map(n => n.id)).size, 2);
  assert.deepEqual(second.notes.map(n => n.id), first.notes.map(n => n.id));
  assert.deepEqual(second.groups.map(g => g.id), first.groups.map(g => g.id));
});

test('default XML namespaces are accepted without querySelector assumptions', () => {
  const input = oneMeasure(note()).replace('<score-partwise ', '<score-partwise xmlns="http://www.musicxml.org/ns/musicxml" ');
  assert.equal(parse(input).notes[0].midi, 60);
});

test('repeats and navigation return a prominent written-order warning without extra inferred notes', () => {
  const model = parse(score(part('P1', measure(attrs() + '<barline location="left"><repeat direction="forward"/></barline>' + note(), 1)
    + measure(note('D') + '<barline><ending number="1" type="start"/><repeat direction="backward"/></barline><direction><sound dacapo="yes"/></direction>', 2))));
  assert.equal(model.playbackOrder, 'written');
  assert.equal(model.hasRepeatsOrNavigation, true);
  assert.equal(model.notes.length, 2);
  assert.equal(model.groups.length, 2);
  assert.ok(model.warnings.some(w => /once.*repeat jumps are not performed/i.test(w)));
});

test('grace/cue heads stay in raw notes with explicit exclusions; hidden tie continuation keeps its hold', () => {
  const grace = '<note><grace/><pitch><step>G</step><octave>4</octave></pitch><type>eighth</type></note>';
  const cue = note('D', 4, 1, '<cue/>');
  const hidden = note('E').replace('<note>', '<note print-object="no">');
  const model = parse(oneMeasure(grace + note() + cue + hidden));
  assert.equal(model.notes.length, 4);
  assert.deepEqual(model.groups[0].midis, [60]);
  assert.equal(model.groups.length, 1);
  assert.equal(model.duration, 3);
  assert.ok(model.warnings.some(w => w.includes('Grace notes')));
  assert.ok(model.warnings.some(w => w.includes('Cue notes')));
  assert.ok(model.warnings.some(w => w.includes('hidden')));
  const tied = parse(oneMeasure(note('C', 4, 1, '<tie type="start"/>') + note('C', 4, 1, '<tie type="stop"/>').replace('<note>', '<note print-object="no">')));
  assert.equal(tied.attacks[0].duration, 2);
  assert.equal(tied.attacks[0].noteIds.length, 2);
});

test('microtones, unpitched notes and real instrument transposition fail explicitly', () => {
  assert.throws(() => parse(oneMeasure(note().replace('<step>C</step>', '<step>C</step><alter>0.5</alter>'))), errorCode('MICROTONAL_SCORE'));
  assert.throws(() => parse(oneMeasure('<note><unpitched><display-step>C</display-step><display-octave>4</display-octave></unpitched><duration>1</duration></note>')), errorCode('UNPITCHED_SCORE'));
  assert.throws(() => parse(oneMeasure('<attributes><transpose><diatonic>-1</diatonic><chromatic>-2</chromatic></transpose></attributes>' + note())), errorCode('TRANSPOSED_INSTRUMENT'));
  assert.equal(parse(oneMeasure('<attributes><transpose><diatonic>0</diatonic><chromatic>0</chromatic></transpose></attributes><direction><direction-type><octave-shift type="down" size="8"/></direction-type></direction>' + note('C', 5))).notes[0].midi, 72);
});

test('malformed XML, bad timing, unsupported roots and empty scores fail atomically', () => {
  assert.throws(() => parse('<score-partwise><part></score-partwise>'), errorCode('INVALID_XML'));
  assert.throws(() => parse('<score-timewise/>'), errorCode('UNSUPPORTED_XML'));
  assert.throws(() => parse(score(part('P1', measure(note())))), errorCode('MISSING_DIVISIONS'));
  assert.throws(() => parse(oneMeasure('<backup><duration>1</duration></backup>' + note())), errorCode('INVALID_BACKUP'));
  assert.throws(() => parse(oneMeasure(note('C', 4, 0))), errorCode('INVALID_DURATION'));
  assert.throws(() => parse(oneMeasure(note('C', 4, 1, '<chord/>'))), errorCode('INVALID_CHORD'));
  assert.throws(() => parse(oneMeasure(rest(4))), errorCode('EMPTY_SCORE'));
});

test('orphan, noncontiguous and unfinished ties cannot silently change required attacks', () => {
  assert.throws(() => parse(oneMeasure(note('C', 4, 1, '<tie type="stop"/>'))), errorCode('UNMATCHED_TIE'));
  assert.throws(() => parse(oneMeasure(note('C', 4, 1, '<tie type="start"/>') + rest(1) + note('C', 4, 1, '<tie type="stop"/>'))), errorCode('UNMATCHED_TIE'));
  assert.throws(() => parse(oneMeasure(note('C', 4, 1, '<tie type="start"/>'))), errorCode('UNFINISHED_TIE'));
});

test('a visible tie continuation cannot manufacture a hidden initial attack', () => {
  const hiddenStart = note('C', 4, 1, '<tie type="start"/>').replace('<note>', '<note print-object="no">');
  const model = parse(oneMeasure(hiddenStart + note('C', 4, 1, '<tie type="stop"/>') + note('D')));
  assert.deepEqual(model.groups.map(g => [g.onset, g.midis]), [[2, [62]]]);
  assert.equal(model.notes[0].attackId, null);
  assert.equal(model.notes[1].attackId, null);
  assert.ok(model.warnings.some(w => w.includes('hidden')));
});

test('contradictory note kinds and unrepresentable numeric times reject instead of losing notes', () => {
  assert.throws(() => parse(oneMeasure(note('C', 4, 1, '<rest/>'))), errorCode('INVALID_NOTE'));
  assert.throws(() => parse(oneMeasure(note('C', 4, '9'.repeat(400)))), errorCode('NUMBER_RANGE'));
});
