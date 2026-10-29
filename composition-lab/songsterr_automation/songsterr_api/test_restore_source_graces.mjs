import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {restoreSourceGraces} from './restore_source_graces.mjs';

const types = {None: 0, BeforeBeat: 1, OnBeat: 2};
const sourceNote = (string, fret, ghost = false) => ({string, fret, ghost});
function fixture() {
  const beats = [
    {graceNote: 'onBeat', duration: [1, 32], notes: [sourceNote(0, 2), sourceNote(1, 0, true)]},
    {duration: [1, 1], notes: [sourceNote(0, 5)]}
  ];
  const native = beats.map(b => ({graceType: 0, duration: b.duration[1], dots: 0,
    tupletNumerator: -1, tupletDenominator: -1, isEmpty: false,
    notes: b.notes.map(n => ({string: 2 - n.string, fret: n.fret, isGhost: false, isDead: false}))}));
  return {
    parts: [{partId: 0, instrumentId: 24, tuning: [64, 59], measures: [{voices: [{beats}]}]}],
    score: {tracks: [{index: 0, staves: [{tuning: [64, 59], capo: 0, isPercussion: false, bars: [{voices: [{beats: native}]}]}]}]},
    source: beats, native
  };
}
const run = f => restoreSourceGraces(f.score, f.parts, types);

test('multi-note on-beat group restores only type and ghost, with source untouched', () => {
  const f = fixture(), source = structuredClone(f.parts), before = structuredClone(f.score);
  const r = run(f);
  assert.equal(r.restoredGraceTypes, 1); assert.equal(r.restoredGhostFlags, 1);
  assert.equal(r.graceNotes, 2); assert.equal(r.checkedNotes, 3);
  before.tracks[0].staves[0].bars[0].voices[0].beats[0].graceType = 2;
  before.tracks[0].staves[0].bars[0].voices[0].beats[0].notes[1].isGhost = true;
  assert.deepEqual(f.score, before); assert.deepEqual(f.parts, source);
  assert.equal(run(f).restoredGraceTypes, 0); assert.equal(run(f).restoredGhostFlags, 0);
});

test('consecutive before-beat groups keep order and separate ghost states', () => {
  const f = fixture();
  f.source[0].graceNote = 'beforeBeat'; f.source[0].notes.pop(); f.native[0].notes.pop();
  f.source.splice(1, 0, {graceNote: 'beforeBeat', duration: [1, 16], notes: [sourceNote(1, 4, true)]});
  f.native.splice(1, 0, {...structuredClone(f.native[0]), duration: 16, notes: [{string: 1, fret: 4, isGhost: false}]});
  const r = run(f);
  assert.deepEqual(f.native.map(b => b.graceType), [1, 1, 0]);
  assert.deepEqual(f.native.slice(0, 2).map(b => b.notes[0].isGhost), [false, true]);
  assert.equal(r.witnesses[0].groups[0].host_source_beat, 2);
});

test('normalized grace glyphs are not treated as ordinary metric durations', () => {
  const f = fixture(); f.native[0].graceType = 2; f.native[0].duration = 8;
  f.native[0].notes[1].isGhost = true;
  assert.equal(run(f).restoredGraceTypes, 0);
  assert.equal(f.native[0].duration, 8);
});

test('ordinary duration uses exact rational notation and explicit no-tuplet sentinel', () => {
  const f = fixture(); f.source[1].duration = [1, 3]; f.native[1].duration = 4;
  f.native[1].tupletNumerator = 3; f.native[1].tupletDenominator = 4;
  assert.equal(run(f).restoredGraceTypes, 1);
  for (const pair of [[-2, -2], [-1, 1], [0, 0], [3, 1]]) {
    const g = fixture(); [g.native[1].tupletNumerator, g.native[1].tupletDenominator] = pair;
    assert.throws(() => run(g), /duration mismatch/);
  }
});

test('correspondence and unsupported declarations refuse without partial mutation', () => {
  const mutations = [
    f => f.parts[0].partId = 7,
    f => f.score.tracks[0].index = 1,
    f => f.parts[0].instrumentId = null,
    f => f.score.tracks[0].staves[0].capo = 1,
    f => f.score.tracks[0].staves[0].tuning[0]++,
    f => f.native.pop(),
    f => f.native[0].notes.pop(),
    f => f.native[0].notes[0].fret++,
    f => f.native[0].notes.reverse().forEach(n => n.string = 1),
    f => f.native[0].graceType = 3,
    f => f.native[0].isEmpty = true,
    f => f.native[1].graceType = 1,
    f => f.native[1].duration = 2,
    f => f.source[0].graceNote = 'afterBeat',
    f => f.source[0].notes[1].ghost = 'true',
    f => { f.source.pop(); f.native.pop(); },
    f => { f.source[1].notes = [{rest: true}]; f.native[1].notes = []; },
    f => { const s = structuredClone(f.source[0]), n = structuredClone(f.native[0]); s.graceNote = 'beforeBeat'; f.source.splice(1, 0, s); f.native.splice(1, 0, n); },
    f => { f.source[0].notes[1].string = 0; f.native[0].notes[1].string = 2; }
  ];
  for (const change of mutations) {
    const f = fixture(); change(f); const original = structuredClone(f.score);
    assert.throws(() => run(f)); assert.deepEqual(f.score, original);
  }
});

test('later voice failure leaves earlier verified grace and ghost unchanged', () => {
  const f = fixture();
  f.parts[0].measures[0].voices.push({beats: structuredClone(f.source)});
  const other = structuredClone(f.native); other[1].notes[0].fret++;
  f.score.tracks[0].staves[0].bars[0].voices.push({beats: other});
  const before = structuredClone(f.score);
  assert.throws(() => run(f), /correspondence mismatch/); assert.deepEqual(f.score, before);
});

test('percussion is explicitly unchecked and unchanged', () => {
  const f = fixture(); f.parts[0].instrumentId = 1024;
  f.score.tracks[0].staves[0].isPercussion = true;
  const before = structuredClone(f.score), r = run(f);
  assert.equal(r.uncheckedPercussionGraceBeats, 1); assert.equal(r.graceBeats, 0);
  assert.deepEqual(f.score, before);
});

test('ordinary voices are untouched and never counted as grace verification', () => {
  const f = fixture(); delete f.source[0].graceNote;
  const before = structuredClone(f.score), r = run(f);
  assert.equal(r.checkedNotes, 0); assert.equal(r.witnesses.length, 0);
  assert.deepEqual(f.score, before);
});

const nativeModule = process.env.ALPHATAB_MODULE || '.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
test('exporter cannot hide an extra source track behind the native track count', {skip: !fs.existsSync(nativeModule)}, async () => {
  const at = await import(pathToFileURL(path.resolve(nativeModule)));
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'composition-grace-source-count-'));
  try {
    const folder = path.join(root, 'source'); fs.mkdirSync(folder);
    const score = new at.model.Score(); score.addMasterBar(new at.model.MasterBar());
    const track = new at.model.Track(); score.addTrack(track);
    const staff = new at.model.Staff(); track.addStaff(staff); staff.stringTuning.tunings = [64, 59];
    const bar = new at.model.Bar(); staff.addBar(bar); const voice = new at.model.Voice(); bar.addVoice(voice);
    const beat = new at.model.Beat(); voice.addBeat(beat); beat.duration = 1;
    const note = new at.model.Note(); note.string = 2; note.fret = 2; beat.addNote(note);
    score.finish(new at.Settings());
    // The loader detects the actual file format; the bridge fixture has one native track.
    fs.writeFileSync(path.join(folder, 'bridge.gp5'), new at.exporter.Gp7Exporter().export(score, new at.Settings()));
    const write = (name, data) => fs.writeFileSync(path.join(folder, name), JSON.stringify(data));
    write('bridge-map.json', [{original_track: 0, original_name: 'Synthetic', source_strings: [1, 2], original_string_count: 2, original_tuning: [64, 59], percussion: false}]);
    write('capture.json', {capture_complete: true, song_id: 1});
    write('metadata.json', {songId: 1, title: 'Synthetic count mismatch'});
    for (const partId of [0, 1]) write(`track-${partId}.json`, {partId, instrumentId: 25, tuning: [64, 59], measures: [{voices: [{beats: [{duration: [1, 1], notes: [{string: 0, fret: 2}]}]}]}]});
    const run = spawnSync(process.execPath, [fileURLToPath(new URL('./export_csv_gp7.mjs', import.meta.url)), path.resolve(nativeModule), root, '--restore-pitched-graces'], {encoding: 'utf8', windowsHide: true});
    assert.equal(run.status, 0, run.stderr);
    const report = JSON.parse(fs.readFileSync(path.join(folder, 'gp7-validation.json'), 'utf8'));
    assert.equal(report.roundtripPass, false); assert.match(report.error, /Grace track correspondence mismatch/);
    assert.equal(fs.existsSync(path.join(folder, 'score.gp')), false);
    assert.equal(fs.existsSync(path.join(folder, 'track-1.json')), true);
  } finally {
    const target = path.resolve(root); assert.equal(path.dirname(target), path.resolve(os.tmpdir()));
    fs.rmSync(target, {recursive: true, force: true});
  }
});
test('opt-in export refuses cached or forged grace claims without touching prior files', {skip: !fs.existsSync(nativeModule)}, () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'composition-grace-refusal-'));
  try {
    const folder = path.join(root, 'source'); fs.mkdirSync(folder);
    fs.writeFileSync(path.join(folder, 'capture.json'), JSON.stringify({capture_complete: true, song_id: 1}));
    const prior = {'score.gp': 'old GP bytes', 'score.exact-model-bends.json': '{}',
      'gp7-validation.json': JSON.stringify({roundtripPass: true, exactModelBends: {}, pitchedGraceRestoration: {},
        directPitchedGraces: {status: 'PASS_INDEPENDENT_PITCHED_SOURCE_GRACES', differences: []}})};
    for (const [name, value] of Object.entries(prior)) fs.writeFileSync(path.join(folder, name), value);
    const result = spawnSync(process.execPath, [path.resolve('composition-lab/songsterr_automation/songsterr_api/export_csv_gp7.mjs'),
      path.resolve(nativeModule), root, '--restore-pitched-graces'], {encoding: 'utf8'});
    assert.notEqual(result.status, 0); assert.match(result.stderr, /fresh copied output/);
    for (const [name, value] of Object.entries(prior)) assert.equal(fs.readFileSync(path.join(folder, name), 'utf8'), value);
  } finally {
    const target = path.resolve(root); assert.equal(path.dirname(target), path.resolve(os.tmpdir()));
    fs.rmSync(target, {recursive: true, force: true});
  }
});
