import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {planSourceGraceChordJoins, joinSourceGraceChords} from './join_source_grace_chords.mjs';
import {restoreSourceGraces} from './restore_source_graces.mjs';
import {checkSourceGraces} from './check_source_graces.mjs';

function fixture() {
  const n = (string, fret, id) => ({string, fret, id, isghost: false});
  const b = (notes, id, gracetype = 0) => ({id, notes, gracetype, isempty: false, duration: gracetype ? 16 : 1,
    dots: 0, tupletdenominator: -1, tupletnumerator: -1, displaystart: 0, displayduration: gracetype ? 0 : 3840,
    playbackstart: id * 60, playbackduration: gracetype ? 60 : 3720, dynamics: 5, automations: [], text: null});
  const source = [{graceNote: 'onBeat', type: 32, duration: [1, 32], notes: [{string: 1, fret: 3}, {string: 0, fret: 2}]},
    {type: 1, duration: [1, 1], notes: [{string: 0, fret: 4}, {string: 1, fret: 5}]}];
  const beats = [b([n(2, 2, 10)], 0, 1), b([n(1, 3, 11)], 1, 1), b([n(2, 4, 12), n(1, 5, 13)], 2)];
  const parts = [{partId: 0, instrumentId: 25, tuning: [64, 59], measures: [{voices: [{beats: source}]}]}];
  const native = {tracks: [{staves: [{stringtuning: {tunings: [64, 59]}, capo: 0, ispercussion: false, bars: [{voices: [{beats}]}]}]}]};
  return {parts, native, source, beats};
}

test('source chord membership supplies grouping and source note order', () => {
  const f = fixture(), before = structuredClone(f), r = planSourceGraceChordJoins(f.native, f.parts);
  assert.equal(r.joinedSourceChords, 1); assert.equal(r.removedFragmentBeats, 1);
  assert.deepEqual(r.joins[0].source_member_keys, ['1:3', '2:2']);
  assert.deepEqual(r.joins[0].members_in_source_order, [{native_beat: 1, native_note: 0}, {native_beat: 0, native_note: 0}]);
  assert.deepEqual(f, before);
});

test('member collision, metadata conflict and ordinary boundary corruption refuse', () => {
  const changes = [
    f => f.beats[1].notes[0].fret++, f => f.beats[1].notes[0] = structuredClone(f.beats[0].notes[0]),
    f => f.beats[1].dynamics++, f => f.beats[1].text = 'Do not discard me',
    f => f.beats[1].automations.push({type: 1, value: 90}), f => f.beats[1].gracetype = 2,
    f => f.beats[1].duration = 8, f => f.beats[1].displaystart++, f => f.beats[1].displayduration = 1,
    f => f.beats[2].notes[0].fret++, f => f.beats.pop(), f => f.beats.push(structuredClone(f.beats[1])),
    f => f.source[0].notes[0].string = 0, f => f.parts[0].tuning[0]++, f => f.parts[0].partId = 1,
    f => f.source[0].graceNote = 'afterBeat', f => f.beats[1].id = f.beats[0].id,
    f => f.beats[1].notes[0].id = f.beats[0].notes[0].id,
    f => f.beats[1].notes[0].slidetargetnoteid = 999
  ];
  for (const change of changes) {
    const f = fixture(); change(f); const before = structuredClone(f);
    assert.throws(() => planSourceGraceChordJoins(f.native, f.parts)); assert.deepEqual(f, before);
  }
});

test('later invalid voice does not mutate an earlier verified chord', () => {
  const f = fixture(); f.parts[0].measures[0].voices.push({beats: structuredClone(f.source)});
  const later = structuredClone(f.beats); later[2].notes[0].fret++;
  f.native.tracks[0].staves[0].bars[0].voices.push({beats: later}); const before = structuredClone(f);
  assert.throws(() => planSourceGraceChordJoins(f.native, f.parts)); assert.deepEqual(f, before);
});

test('percussion and already one-to-one voices stay outside joining', () => {
  const f = fixture(); f.parts[0].instrumentId = 1024;
  assert.equal(planSourceGraceChordJoins(f.native, f.parts).joinedSourceChords, 0);
  const g = fixture(); g.beats[0].notes.push(...g.beats[1].notes); g.beats.splice(1, 1);
  assert.equal(planSourceGraceChordJoins(g.native, g.parts).joinedSourceChords, 0);
});

const modulePath = process.env.ALPHATAB_MODULE || '.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
const at = fs.existsSync(modulePath) ? await import(pathToFileURL(path.resolve(modulePath))) : null;
function nativeFixture({mode = 'onBeat', transition = 'slide'} = {}) {
  const f = fixture(), settings = new at.Settings(), score = new at.model.Score(); score.addMasterBar(new at.model.MasterBar());
  const track = new at.model.Track(); score.addTrack(track); track.playbackInfo.program = 25;
  const staff = new at.model.Staff(); track.addStaff(staff); staff.stringTuning.tunings = [64, 59];
  const bar = new at.model.Bar(); staff.addBar(bar); const voice = new at.model.Voice(); bar.addVoice(voice);
  // A preceding regular beat carries native track initialization; grace fragments
  // with conflicting automation must remain a refusal, not a positive fixture.
  const rest = new at.model.Beat(); rest.duration = 4; voice.addBeat(rest);
  for (const [i, row] of f.beats.entries()) {
    const beat = new at.model.Beat(); voice.addBeat(beat); beat.duration = row.duration;
    beat.graceType = i < 2 ? mode === 'onBeat' ? 1 : 2 : 0;
    for (const raw of row.notes) {const note = new at.model.Note(); note.string = raw.string; note.fret = raw.fret; beat.addNote(note);}
  }
  for (const i of [0, 1]) {
    const note = voice.beats[i + 1].notes[0];
    if (transition === 'slide') note.slideOutType = at.model.SlideOutType.Legato;
    if (transition === 'hammer') note.isHammerPullOrigin = true;
  }
  f.source[0].graceNote = mode;
  f.source[1].type = 2; f.source[1].dots = 1; f.source[1].duration = [3, 4];
  voice.beats[3].duration = 2; voice.beats[3].dots = 1;
  f.source.unshift({type: 4, duration: [1, 4], notes: [{rest: true}]});
  score.finish(settings);
  return {...f, score, settings, voice};
}

test('native GP7 preserves simultaneous members, note effects, links and ordinary time', {skip: !at}, () => {
  for (const mode of ['onBeat', 'beforeBeat']) for (const transition of ['slide', 'hammer']) {
    const f = nativeFixture({mode, transition}), before = at.model.JsonConverter.scoreToJson(f.score);
    const r = joinSourceGraceChords(f.score, f.parts, at, f.settings);
    assert.equal(at.model.JsonConverter.scoreToJson(f.score), before);
    assert.notEqual(r.score, f.score); assert.equal(r.report.joinedSourceChords, 1);
    restoreSourceGraces(r.score, f.parts, at.model.GraceType); r.score.finish(f.settings);
    const voice = r.score.tracks[0].staves[0].bars[0].voices[0], grace = voice.beats[1], host = voice.beats[2];
    assert.deepEqual(grace.notes.map(n => [2 - n.string, n.fret]), f.source[1].notes.map(n => [n.string, n.fret]));
    assert.equal(host.displayStart, 960); assert.equal(host.displayDuration, 2880);
    for (const note of grace.notes) {
      assert.equal(note.beat, grace); assert.equal(grace.notes[note.index], note);
      const target = transition === 'slide' ? note.slideTarget : note.hammerPullDestination;
      assert.equal(target?.beat, host); assert.equal(target?.string, note.string);
    }
    const bytes = new at.exporter.Gp7Exporter().export(r.score, f.settings);
    const actual = at.importer.ScoreLoader.loadScoreFromBytes(bytes, f.settings);
    assert.equal(checkSourceGraces(actual, f.parts).status, 'PASS_INDEPENDENT_PITCHED_SOURCE_GRACES');
    const imported = actual.tracks[0].staves[0].bars[0].voices[0];
    assert.deepEqual(imported.beats[1].notes.map(n => [2 - n.string, n.fret]), f.source[1].notes.map(n => [n.string, n.fret]));
    const again = joinSourceGraceChords(actual, f.parts, at, f.settings);
    assert.equal(again.report.joinedSourceChords, 0); assert.equal(again.score, actual);
    for (const note of imported.beats[1].notes) {
      const target = transition === 'slide' ? note.slideTarget : note.hammerPullDestination;
      assert.equal(target?.beat, imported.beats[2]); assert.equal(target?.string, note.string);
    }
  }
});

test('native candidate refuses source corruption without altering original score', {skip: !at}, () => {
  const f = nativeFixture(); f.parts[0].measures[0].voices[0].beats[1].notes[0].fret++;
  const before = at.model.JsonConverter.scoreToJson(f.score);
  assert.throws(() => joinSourceGraceChords(f.score, f.parts, at, f.settings));
  assert.equal(at.model.JsonConverter.scoreToJson(f.score), before);
});
