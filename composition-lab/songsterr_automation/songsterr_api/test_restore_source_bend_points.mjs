// Authored fixtures only. Optional native tests use the same AlphaTab build as export.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
import {restoreSourceBendPoints} from './restore_source_bend_points.mjs';
import {exportWithExactBends, loadWithExactBends} from './bend_fidelity.mjs';

const modulePath = process.env.ALPHATAB_MODULE || '.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
const available = fs.existsSync(modulePath);
const at = available ? await import(pathToFileURL(path.resolve(modulePath)).href) : null;
const options = {skip: !available};
const rawCurve = (middle = 30) => [{position: 0, tone: 0}, {position: middle, tone: 100}, {position: 60, tone: 100}];
const noteAt = (score, i = 0) => score.tracks[0].staves[0].bars[0].voices[0].beats[i].notes[0];
const curve = n => n.bendPoints.map(p => [p.offset, p.value]);
function settings() {
  const value = new at.Settings(); value.notation.notationMode = at.NotationMode.GuitarPro; return value;
}
function fixture(curves = [rawCurve()]) {
  const score = new at.model.Score();
  score.addMasterBar(new at.model.MasterBar());
  const track = new at.model.Track(); score.addTrack(track); track.playbackInfo.program = 30;
  track.playbackInfo.secondaryChannel = 1;
  const staff = new at.model.Staff(); track.addStaff(staff); staff.stringTuning.tunings = [64, 59, 55, 50, 45, 40];
  const bar = new at.model.Bar(); staff.addBar(bar);
  const voice = new at.model.Voice(); bar.addVoice(voice);
  const beats = [];
  for (const points of curves) {
    const beat = new at.model.Beat(); voice.addBeat(beat); beat.duration = at.model.Duration.Eighth;
    const note = new at.model.Note(); note.fret = 16; note.string = 4; beat.addNote(note);
    for (const p of points) note.addBendPoint(new at.model.BendPoint(p.position ?? p.precisePosition * .6, p.tone / 25));
    beats.push({duration: [1, 8], notes: [{string: 2, fret: 16, bend: {tone: 100, points: structuredClone(points)}}]});
  }
  score.finish(settings()); // Actual upstream classification removes early-arrival points.
  const parts = [{partId: 0, instrumentId: 30, tuning: [...staff.tuning], measures: [{signature: [4, 4], voices: [{beats}]}]}];
  return {score, parts};
}
function snapshot(score, ignored = new Set()) {
  const seen = new WeakSet();
  return JSON.stringify(score, function(key, value) {
    if (ignored.has(this) && ['bendPoints', 'maxBendPoint'].includes(key)) return 'owned curve';
    if (value && typeof value === 'object') {
      if (seen.has(value)) return '[reference]';
      seen.add(value);
      if (value instanceof Map) return [...value.entries()];
    }
    return value;
  });
}
function midi(score) {
  const file = new at.midi.MidiFile();
  new at.midi.MidiFileGenerator(score, settings(), new at.midi.AlphaSynthMidiFileHandler(file, false)).generate();
  return file.events;
}
function assertHalfwayHold(score, arrivalTicks = 240) {
  const events = midi(score), attack = events.find(e => e.constructor.name === 'NoteOnEvent');
  const release = events.find(e => e.constructor.name === 'NoteOffEvent');
  const bends = events.filter(e => e.constructor.name === 'NoteBendEvent');
  assert.ok(attack && release && bends.length > 2);
  assert.equal(release.tick - attack.tick, 480);
  // Pinned renderer range is sixteen semitones; a two-semitone bend is +1/8 of
  // its signed 32-bit half-range. This checks pitch magnitude, not only equality.
  const peak = 2147483648 + 2147483648 / 8;
  assert.equal(Math.max(...bends.map(e => e.value)), peak);
  assert.equal(Math.min(...bends.filter(e => e.value === peak).map(e => e.tick)) - attack.tick, arrivalTicks);
  assert.ok(bends.filter(e => e.tick >= attack.tick + arrivalTicks).every(e => e.value === peak));
  assert.ok(bends.some(e => e.tick >= attack.tick + 470));
}

test('restores early arrival after finish, preserving all non-curve model fields and raw input', options, () => {
  const {score, parts} = fixture(), note = noteAt(score), raw = JSON.stringify(parts);
  assert.deepEqual(curve(note), [[0, 0], [60, 4]]);
  const before = snapshot(score, new Set([note])), type = note.bendType, style = note.bendStyle;
  const report = restoreSourceBendPoints(score, parts, at.model);
  assert.equal(report.restoredCurves, 1); assert.equal(report.checkedCurves, 1);
  assert.deepEqual(report.excluded, []);
  assert.deepEqual(curve(note), [[0, 0], [30, 4], [60, 4]]);
  assert.equal(note.bendType, type); assert.equal(note.bendStyle, style);
  assert.equal(snapshot(score, new Set([note])), before); assert.equal(JSON.stringify(parts), raw);
  assert.equal(restoreSourceBendPoints(score, parts, at.model).unchangedCurves, 1);
});

test('paired GP reader retains actual 240/480 arrival and held tail', options, () => {
  const {score, parts} = fixture(); restoreSourceBendPoints(score, parts, at.model);
  assertHalfwayHold(score);
  const result = exportWithExactBends(at, score, settings());
  const loaded = loadWithExactBends(at, result.bytes, result.sidecar, settings()).score;
  assert.deepEqual(curve(noteAt(loaded)), [[0, 0], [30, 4], [60, 4]]);
  assertHalfwayHold(loaded);
  assert.deepEqual(midi(loaded), midi(score));
});

test('another source arrival and precise-percent precedence change native arrival time', options, () => {
  for (const points of [rawCurve(15), [{position: 0, precisePosition: 0, tone: 0},
    {position: 30, precisePosition: 25, tone: 100}, {position: 60, precisePosition: 100, tone: 100}]]) {
    const {score, parts} = fixture([points]);
    const report = restoreSourceBendPoints(score, parts, at.model);
    assert.deepEqual(curve(noteAt(score)), [[0, 0], [15, 4], [60, 4]]);
    assert.equal(report.witnesses[0].position_basis[1], points[1].precisePosition == null ? 'coarse_sixtieths' : 'precise_percent');
    const result = exportWithExactBends(at, score, settings());
    assertHalfwayHold(loadWithExactBends(at, result.bytes, result.sidecar, settings()).score, 120);
  }
});

test('preserves arbitrary ordered curves, fractional precise coordinates and duplicate offsets', options, () => {
  const points = [{position: 0, tone: 0}, {position: 20, precisePosition: 33, tone: 75},
    {position: 40, tone: 50}, {position: 40, tone: 25}, {position: 60, tone: 0}];
  const {score, parts} = fixture([points]); restoreSourceBendPoints(score, parts, at.model);
  assert.deepEqual(curve(noteAt(score)), [[0, 0], [19.8, 3], [40, 2], [40, 1], [60, 0]]);
  const result = exportWithExactBends(at, score, settings());
  assert.deepEqual(curve(noteAt(loadWithExactBends(at, result.bytes, result.sidecar, settings()).score)), curve(noteAt(score)));
});

test('later malformed source curves fail atomically without silently choosing defaults', options, () => {
  const edits = [p => p.tone = true, p => p.tone = '100', p => p.tone = Infinity,
    p => p.position = -1, p => p.precisePosition = 101, p => p.precisePosition = '50'];
  for (const edit of edits) {
    const {score, parts} = fixture([rawCurve(), rawCurve()]), before = snapshot(score);
    edit(parts[0].measures[0].voices[0].beats[1].notes[0].bend.points[1]);
    assert.throws(() => restoreSourceBendPoints(score, parts, at.model), /Source bend/);
    assert.equal(snapshot(score), before);
  }
  for (const replacement of [{tone: 100}, {points: []}, {points: [{position: 30, tone: 100}, {position: 0, tone: 0}]}]) {
    const {score, parts} = fixture([rawCurve(), rawCurve()]), before = snapshot(score);
    parts[0].measures[0].voices[0].beats[1].notes[0].bend = replacement;
    assert.throws(() => restoreSourceBendPoints(score, parts, at.model)); assert.equal(snapshot(score), before);
  }
});

test('identity, preceding duration, meter and duplicate-member mismatches fail before mutation', options, () => {
  for (const edit of [
    p => p[0].partId = 1, p => p[0].instrumentId = 29, p => p[0].tuning[0]++, p => p[0].capo = 1,
    p => p[0].measures[0].signature = [3, 4],
    p => p[0].measures[0].voices[0].beats[0].duration = [1, 4],
    p => p[0].measures[0].voices[0].beats[1].notes[0].fret++,
    p => p[0].measures[0].voices[0].beats[1].notes[0].string++,
    p => p[0].measures[0].voices[0].beats[1].notes.push(structuredClone(p[0].measures[0].voices[0].beats[1].notes[0]))
  ]) {
    const {score, parts} = fixture([rawCurve(), rawCurve()]), before = snapshot(score); edit(parts);
    assert.throws(() => restoreSourceBendPoints(score, parts, at.model)); assert.equal(snapshot(score), before);
  }
});

test('unsupported point execution and non-default bend timing are explicitly unchanged', options, () => {
  const {score, parts} = fixture([rawCurve(), rawCurve()]);
  parts[0].measures[0].voices[0].beats[0].notes[0].bend.points[1].vibrato = true;
  noteAt(score, 1).bendStyle = at.model.BendStyle.Fast;
  const before = snapshot(score), report = restoreSourceBendPoints(score, parts, at.model);
  assert.equal(report.sourceDeclarations, 2); assert.equal(report.checkedCurves, 0);
  assert.deepEqual(report.excluded.map(x => x.reason), ['unsupported_point_fields:vibrato', 'nondefault_native_bend_timing_style']);
  assert.equal(snapshot(score), before);
});

test('tie identity mismatch refuses atomically instead of attaching a curve to a new attack', options, () => {
  for (const sourceTie of [true, false]) {
    const {score, parts} = fixture([rawCurve(), rawCurve()]);
    parts[0].measures[0].voices[0].beats[1].notes[0].tie = sourceTie;
    noteAt(score, 1).isTieDestination = !sourceTie;
    const before = snapshot(score);
    assert.throws(() => restoreSourceBendPoints(score, parts, at.model), /member mismatch/);
    assert.equal(snapshot(score), before);
  }
});

test('continuation topology is excluded explicitly without rewriting native links', options, () => {
  for (const field of ['tieOrigin', 'tieDestination', 'bendOrigin', 'isContinuedBend']) {
    const {score, parts} = fixture([rawCurve(), rawCurve()]);
    const target = noteAt(score, 1);
    target[field] = field === 'isContinuedBend' ? true : noteAt(score);
    const before = snapshot(score, new Set([noteAt(score)]));
    const report = restoreSourceBendPoints(score, parts, at.model);
    assert.equal(report.restoredCurves, 1);
    assert.deepEqual(report.excluded.map(x => x.reason), ['tie_or_continued_bend_topology_unchecked']);
    assert.equal(snapshot(score, new Set([noteAt(score)])), before);
  }
});

test('a preceding dead-note placeholder has string/dead identity, not a fabricated pitch', options, () => {
  const {score, parts} = fixture([rawCurve(), rawCurve()]);
  const rawDead = parts[0].measures[0].voices[0].beats[0].notes[0], nativeDead = noteAt(score);
  delete rawDead.bend; rawDead.dead = true; rawDead.fret = -1;
  nativeDead.isDead = true; nativeDead.fret = 0; nativeDead.bendPoints = null;
  nativeDead.maxBendPoint = null; nativeDead.bendType = at.model.BendType.None;
  const before = snapshot(score, new Set([noteAt(score, 1)]));
  assert.equal(restoreSourceBendPoints(score, parts, at.model).restoredCurves, 1);
  assert.equal(snapshot(score, new Set([noteAt(score, 1)])), before);
  nativeDead.isDead = false;
  assert.throws(() => restoreSourceBendPoints(score, parts, at.model), /member mismatch/);
});

const python = process.env.SONGSTERR_PYTHON || (process.platform === 'win32'
  ? '.local/songsterr-venv/Scripts/python.exe' : 'python3');
const pythonAvailable = fs.existsSync(python) || (!/[\\/]/.test(python) &&
  spawnSync(python, ['-c', 'import guitarpro'], {encoding: 'utf8'}).status === 0);

const tiedOptions = {restoreSimpleTiedHolds: true};
function tiedFixture(explicit = false) {
  const {score, parts} = fixture([rawCurve(15), rawCurve()]);
  const origin = noteAt(score), hold = noteAt(score, 1);
  origin.beat.duration = at.model.Duration.Quarter; origin.beat.dots = 1;
  parts[0].measures[0].voices[0].beats[0].duration = [3, 8];
  hold.isTieDestination = true; hold.bendPoints = null; hold.maxBendPoint = null; hold.bendType = at.model.BendType.None;
  const rawHold = parts[0].measures[0].voices[0].beats[1].notes[0]; rawHold.tie = true; delete rawHold.bend;
  origin.vibrato = hold.vibrato = at.model.VibratoType.Slight;
  if (explicit) {
    rawHold.bend = {tone: 100, points: [0, 30, 60].map(position => ({position, tone: 100}))};
    for (const p of rawHold.bend.points) hold.addBendPoint(new at.model.BendPoint(p.position, 4));
  }
  score.finish(settings());
  return {score, parts, origin, hold};
}
function ownedMidi(score) {
  const file = new at.midi.MidiFile(), generator = new at.midi.MidiFileGenerator(score, settings(), new at.midi.AlphaSynthMidiFileHandler(file, false));
  let current = null;
  const owners = new WeakMap(), add = file.addEvent.bind(file), generate = generator._generateNote;
  file.addEvent = e => {owners.set(e, current ? `${current.beat.voice.index}:${current.beat.index}:${current.index}` : null); return add(e);};
  generator._generateNote = function(n, ...args) {const prior = current; current = n; try {return generate.call(this, n, ...args);} finally {current = prior;}};
  generator.generate();
  return file.events.map(e => ({kind: e.constructor.name, owner: owners.get(e), event: JSON.parse(JSON.stringify(e))}));
}
test('opt-in checked simple tied hold restores source quarter-arrival, never a tied reattack or a manufactured curve', options, () => {
  for (const explicit of [false, true]) {
    const {score, parts, origin, hold} = tiedFixture(explicit), raw = JSON.stringify(parts);
    const before = snapshot(score, new Set([origin])), oldMidi = ownedMidi(score), heldCurve = JSON.stringify(hold.bendPoints);
    const report = restoreSourceBendPoints(score, parts, at.model, tiedOptions);
    assert.equal(report.restoredCurves, 1); assert.equal(report.checkedCurves, 1);
    assert.equal(report.witnesses[0].simple_tied_hold.origin_ticks, 1440);
    assert.equal(report.witnesses[0].simple_tied_hold.continuation_ticks, 480);
    assert.equal(JSON.stringify(parts), raw); assert.equal(JSON.stringify(hold.bendPoints), heldCurve);
    assert.equal(snapshot(score, new Set([origin])), before);
    const events = ownedMidi(score), outside = e => e.kind !== 'NoteBendEvent' || e.owner !== '0:0:0';
    assert.deepEqual(events.filter(outside), oldMidi.filter(outside));
    const attacks = events.filter(e => e.kind === 'NoteOnEvent'), releases = events.filter(e => e.kind === 'NoteOffEvent');
    assert.equal(attacks.length, 1); assert.equal(releases.length, 1);
    assert.equal(releases[0].event.tick - attacks[0].event.tick, 1920);
    const bends = events.filter(e => e.kind === 'NoteBendEvent' && e.owner === '0:0:0');
    const peak = 2147483648 + 2 * 134217728, arrival = attacks[0].event.tick + 360;
    assert.equal(Math.min(...bends.filter(e => e.event.value === peak).map(e => e.event.tick)), arrival);
    assert.ok(bends.filter(e => e.event.tick >= arrival).every(e => e.event.value === peak));
    assert.ok(bends.some(e => e.event.tick === attacks[0].event.tick + 1440));
    const result = exportWithExactBends(at, score, settings()), loaded = loadWithExactBends(at, result.bytes, result.sidecar, settings()).score;
    assert.deepEqual(ownedMidi(loaded), events);
    assert.equal(restoreSourceBendPoints(score, parts, at.model, tiedOptions).unchangedCurves, 1);
  }
});
test('simple tied holds remain unchanged without explicit opt-in', options, () => {
  const {score, parts} = tiedFixture(true), before = snapshot(score);
  assert.equal(restoreSourceBendPoints(score, parts, at.model).restoredCurves, 0);
  assert.equal(snapshot(score), before);
});
test('unresolved, retriggered, released, nonlocal or conflicting simple-tie candidates remain intact', options, () => {
  const cases = [
    ({origin}) => {origin.tieDestination = null;},
    ({hold}) => {hold.tieOrigin = null;},
    ({hold, origin}) => {hold.tieDestination = origin;},
    ({hold, parts}) => {hold.fret++; parts[0].measures[0].voices[0].beats[1].notes[0].fret++;},
    ({hold, parts}) => {hold.isTieDestination = false; parts[0].measures[0].voices[0].beats[1].notes[0].tie = false;},
    ({parts}) => {parts[0].measures[0].voices[0].beats[1].notes[0].bend.points.at(-1).tone = 0;},
    ({hold}) => {hold.bendPoints.at(-1).value = 0;},
    ({hold}) => {hold.beat.playbackDuration--;},
    ({hold}) => {hold.beat.playbackStart--;},
    ({origin}) => {origin.bendPoints.at(-1).value = 3;},
    ({parts}) => {parts[0].measures[0].voices[0].beats[0].notes[0].bend.points.at(-1).tone = 0;},
    ({origin, hold}) => {const other = new at.model.Note(); other.string = hold.string; other.fret = hold.fret; other.beat = hold.beat; other.isTieDestination = true; other.tieOrigin = origin; origin.tieDestination = other;}
  ];
  for (const edit of cases) {
    const data = tiedFixture(true); edit(data); const before = snapshot(data.score);
    const report = restoreSourceBendPoints(data.score, data.parts, at.model, tiedOptions);
    assert.equal(report.restoredCurves, 0, String(edit)); assert.ok(report.excluded.length);
    assert.equal(snapshot(data.score), before);
  }
});
test('simple-tie source mismatch refuses atomically and unrelated same-pitch voice is preserved', options, () => {
  const data = tiedFixture(true), {score, parts, origin} = data;
  const voice = new at.model.Voice(); origin.beat.voice.bar.addVoice(voice);
  const beat = new at.model.Beat(); voice.addBeat(beat); beat.duration = at.model.Duration.Half;
  const other = new at.model.Note(); other.string = origin.string; other.fret = origin.fret; beat.addNote(other);
  parts[0].measures[0].voices.push({beats: [{duration: [1, 2], notes: [{string: 2, fret: 16}]}]});
  score.finish(settings());
  const before = snapshot(score, new Set([origin]));
  const untouched = ownedMidi(score).filter(e => e.owner === '1:0:0');
  assert.equal(restoreSourceBendPoints(score, parts, at.model, tiedOptions).restoredCurves, 1);
  assert.equal(snapshot(score, new Set([origin])), before);
  assert.deepEqual(ownedMidi(score).filter(e => e.owner === '1:0:0'), untouched);
  parts[0].measures[0].voices[0].beats[1].notes[0].fret++;
  const invalidBefore = snapshot(score);
  assert.throws(() => restoreSourceBendPoints(score, parts, at.model, tiedOptions), /member mismatch/);
  assert.equal(snapshot(score), invalidBefore);
});
test('actual authored GP5 import loses midpoint and source adapter plus paired reader restores it', {skip: !available || !pythonAvailable}, () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'source-bend-gp5-'));
  try {
    const file = path.join(temporary, 'authored.gp5');
    const code = `import guitarpro as gp, sys
m=gp.models
s=m.Song(); s.tempo=120
t=s.tracks[0];t.channel.instrument=30
t.strings=[m.GuitarString(i+1,p) for i,p in enumerate([64,59,55,50,45,40])]
v=t.measures[0].voices[0]
b=m.Beat(v); b.status=m.BeatStatus.normal; b.duration=m.Duration(8); v.beats.append(b)
n=m.Note(b);n.string=3;n.value=16;n.type=m.NoteType.normal;b.notes.append(n)
n.effect.bend=m.BendEffect(type=m.BendType.bend,value=4,points=[m.BendPoint(0,0),m.BendPoint(6,4),m.BendPoint(12,4)])
gp.write(s,sys.argv[1],version=(5,1,0))`;
    const built = spawnSync(python, ['-c', code, file], {encoding: 'utf8'});
    assert.equal(built.status, 0, built.stderr);
    const score = at.importer.ScoreLoader.loadScoreFromBytes(fs.readFileSync(file), settings());
    const parts = fixture().parts;
    assert.deepEqual(curve(noteAt(score)), [[0, 0], [60, 4]]);
    restoreSourceBendPoints(score, parts, at.model);
    const result = exportWithExactBends(at, score, settings());
    assertHalfwayHold(loadWithExactBends(at, result.bytes, result.sidecar, settings()).score);
  } finally {
    const actual = path.resolve(temporary), parent = path.resolve(os.tmpdir());
    assert.equal(path.dirname(actual), parent);
    assert.ok(path.basename(actual).startsWith('source-bend-gp5-'));
    fs.rmSync(actual, {recursive: true, force: true});
  }
});
