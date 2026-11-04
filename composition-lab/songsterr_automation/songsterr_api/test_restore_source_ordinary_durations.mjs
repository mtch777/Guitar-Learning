import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {restoreSourceOrdinaryDurations} from './restore_source_ordinary_durations.mjs';
import {restoreSourcePercussion} from './restore_source_percussion.mjs';
const modulePath = process.env.ALPHATAB_MODULE || '.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
const at = fs.existsSync(modulePath) ? await import(pathToFileURL(path.resolve(modulePath))) : null;
const json = score => at.model.JsonConverter.scoreToJson(score);
function fixture({kind = 'pitched', dots = 0, enters = 1, times = 1, count = 1} = {}) {
  const score = new at.model.Score(), track = new at.model.Track(), staff = new at.model.Staff();
  score.addMasterBar(new at.model.MasterBar()); score.addTrack(track); track.addStaff(staff);
  staff.stringTuning.tunings = [64,59,55,50,45,40]; staff.isPercussion = kind === 'percussion';
  if (staff.isPercussion) {track.playbackInfo.primaryChannel = 9; track.playbackInfo.secondaryChannel = 9;}
  const bar = new at.model.Bar(), voice = new at.model.Voice(); staff.addBar(bar); bar.addVoice(voice);
  const rows = [], notation = [];
  for (let i = 0; i < count; i++) {
    const beat = new at.model.Beat(); voice.addBeat(beat); beat.duration = 4; beat.dots = dots ? 1 : 0;
    beat.tupletNumerator = enters; beat.tupletDenominator = times;
    const row = {type:128, dots, duration:[(2 ** (dots + 1) - 1) * times, 128 * 2 ** dots * enters], notes:[]};
    if (kind === 'rest') row.notes.push({rest:true});
    else {
      const note = new at.model.Note(); beat.addNote(note);
      if (kind === 'percussion') {note.percussionArticulation = 38 + i; row.notes.push({fret:38+i, string:1.5});}
      else {note.string = 6; note.fret = 3 + i; row.notes.push({string:0, fret:3+i});}
    }
    rows.push(row); notation.push({value:128, dots, enters, times});
  }
  const parts = [{partId:0, instrumentId:staff.isPercussion ? 1024 : 25, tuning:[...staff.tuning], measures:[{voices:[{beats:rows}]}]}];
  const bridge = [[ [notation] ]], settings = new at.Settings(); score.finish(settings);
  return {score, track, staff, voice, rows, parts, bridge, settings};
}

for (const kind of ['pitched','rest','percussion']) for (const dots of [0,1]) for (const triplet of [false,true]) {
  test(`authenticated 128th ${kind}, dots ${dots}, ${triplet?'triplet':'ordinary'} survives GP7`, {skip:!at}, () => {
    const f = fixture({kind,dots,enters:triplet?3:1,times:triplet?2:1});
    const source = structuredClone(f.parts), bridge = structuredClone(f.bridge), beat = f.voice.beats[0], notes = [...beat.notes];
    const beforeClocks = [beat.displayStart,beat.displayDuration,beat.playbackStart,beat.playbackDuration];
    const report = restoreSourceOrdinaryDurations(f.score,f.parts,f.bridge,at);
    assert.equal(report.restored128thBeats,1); assert.equal(beat.duration,128); assert.equal(beat.dots,dots);
    assert.deepEqual(beat.notes,notes); assert.deepEqual(f.parts,source); assert.deepEqual(f.bridge,bridge);
    assert.deepEqual([beat.displayStart,beat.displayDuration,beat.playbackStart,beat.playbackDuration],beforeClocks,'No direct clock edits');
    if (kind === 'percussion') restoreSourcePercussion(f.score,f.parts,at);
    f.score.finish(f.settings);
    const bytes = new at.exporter.Gp7Exporter().export(f.score,f.settings);
    const out = at.importer.ScoreLoader.loadScoreFromBytes(bytes,f.settings).tracks[0].staves[0].bars[0].voices[0].beats[0];
    assert.equal(out.duration,128); assert.equal(out.dots,dots);
    const [n,d] = f.rows[0].duration;
    assert.equal(out.displayDuration,Math.floor(3840*n/d));
    assert.equal(out.notes.length,beat.notes.length); assert.equal(out.isRest,kind==='rest');
    const after = json(f.score); assert.equal(restoreSourceOrdinaryDurations(f.score,f.parts,null,at).restored128thBeats,0); assert.equal(json(f.score),after);
  });
}

test('double-dotted 128th repair refuses because native playback loses duration', {skip:!at}, () => {
  for (const kind of ['pitched','rest','percussion']) for (const triplet of [false,true]) {
    const f = fixture({kind,dots:2,enters:triplet?3:1,times:triplet?2:1});
    const before = json(f.score); assert.throws(()=>restoreSourceOrdinaryDurations(f.score,f.parts,f.bridge,at),/Unsupported double-dotted/);
    assert.equal(json(f.score),before);
    // Retain the independent counterexample, rather than changing its oracle
    // to the incorrect renderer duration and calling it faithful playback.
    const beat=f.voice.beats[0];beat.duration=128;beat.dots=2;f.score.finish(f.settings);
    const [n,d]=f.rows[0].duration; assert.notEqual(beat.displayDuration,3840*n/d);
  }
});

test('a later mismatch refuses every queued repair and preserves all inputs', {skip:!at}, () => {
  const mutations = [
    f => f.rows[1].duration = [1,64],
    f => f.bridge[0][0][0][1].value = 64,
    f => f.bridge[0][0][0][1].dots = 1,
    f => f.bridge[0][0][0].pop(),
    f => f.voice.beats[1].duration = 8,
    f => f.voice.beats[1].dots = 1,
    f => f.voice.beats[1].tupletNumerator = 3,
    f => f.voice.beats[1].notes[0].fret++,
    f => f.voice.beats[1].notes[0].string--,
    f => f.voice.beats[1].notes = [],
    f => f.voice.beats[1].graceType = at.model.GraceType.BeforeBeat,
    f => f.parts[0].tuning[0]++,
    f => f.parts[0].instrumentId = 1024,
    f => f.bridge = null,
  ];
  for (const mutate of mutations) {
    const f = fixture({count:2}); mutate(f);
    const before = json(f.score), source = structuredClone(f.parts), bridge = structuredClone(f.bridge);
    assert.throws(()=>restoreSourceOrdinaryDurations(f.score,f.parts,f.bridge,at),/128th/);
    assert.equal(json(f.score),before); assert.deepEqual(f.parts,source); assert.deepEqual(f.bridge,bridge);
  }
});

test('grace durations and unrelated ordinary mismatches remain with their existing owners', {skip:!at}, () => {
  const f = fixture({count:2}); f.rows[0].graceNote = 'beforeBeat'; f.voice.beats[0].graceType = at.model.GraceType.BeforeBeat;
  f.rows[1].type = 64; f.rows[1].duration = [1,64];
  const before = json(f.score); assert.equal(restoreSourceOrdinaryDurations(f.score,f.parts,null,at).restored128thBeats,0); assert.equal(json(f.score),before);
});

test('rest/pitched and wrong percussion member substitutions refuse atomically', {skip:!at}, () => {
  for (const kind of ['rest','percussion']) {
    const f = fixture({kind,count:2});
    if (kind === 'rest') {const n = new at.model.Note();n.string=6;n.fret=0;f.voice.beats[1].addNote(n);}
    else f.voice.beats[1].notes[0].percussionArticulation++;
    const before = json(f.score); assert.throws(()=>restoreSourceOrdinaryDurations(f.score,f.parts,f.bridge,at),/identity mismatch/);assert.equal(json(f.score),before);
  }
});
