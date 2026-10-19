// Optional alphaTab integration tests; set ALPHATAB_MODULE to another installation.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { exportWithExactBends, loadWithExactBends } from './bend_fidelity.mjs';
import {loadPlaybackScore} from './playback_score.mjs';

const modulePath = process.env.ALPHATAB_MODULE || '.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs';
const available = fs.existsSync(modulePath);
const at = available ? await import(pathToFileURL(path.resolve(modulePath)).href) : null;

test('opt-in exporter refusal preserves existing score, sidecar and validation report', { skip: !available }, () => {
    const root=fs.mkdtempSync(path.join(os.tmpdir(),'composition-bend-refusal-'));
    try {
        const folder=path.join(root,'1');fs.mkdirSync(folder);
        fs.writeFileSync(path.join(folder,'capture.json'),JSON.stringify({capture_complete:true,song_id:1}));
        const baseline={'score.gp':'baseline GP bytes','score.exact-model-bends.json':'{}','gp7-validation.json':'{"roundtripPass":true}'};
        for(const [name,value] of Object.entries(baseline))fs.writeFileSync(path.join(folder,name),value);
        const result=spawnSync(process.execPath,[path.resolve('composition-lab/songsterr_automation/songsterr_api/export_csv_gp7.mjs'),path.resolve(modulePath),root,'--exact-model-bends'],{encoding:'utf8'});
        assert.notEqual(result.status,0);
        assert.match(result.stderr,/validation report preserved/);
        for(const [name,value] of Object.entries(baseline))assert.equal(fs.readFileSync(path.join(folder,name),'utf8'),value);
        const native=spawnSync(process.execPath,[path.resolve('composition-lab/songsterr_automation/songsterr_api/export_csv_gp7.mjs'),path.resolve(modulePath),root,'--recheck','--native-bends-only'],{encoding:'utf8'});
        assert.notEqual(native.status,0);assert.match(native.stderr,/Existing bend companion preserved/);
        for(const [name,value] of Object.entries(baseline))assert.equal(fs.readFileSync(path.join(folder,name),'utf8'),value);
    } finally {fs.rmSync(root,{recursive:true,force:true});}
});

function fixture(points) {
    const score = new at.model.Score();
    score.addMasterBar(new at.model.MasterBar());
    const track = new at.model.Track(); score.addTrack(track);
    const staff = new at.model.Staff(); track.addStaff(staff);
    staff.stringTuning.tunings = [40, 45, 50, 55, 59, 64];
    const bar = new at.model.Bar(); staff.addBar(bar);
    const voice = new at.model.Voice(); bar.addVoice(voice);
    const beat = new at.model.Beat(); voice.addBeat(beat); beat.duration = at.model.Duration.Whole;
    const note = new at.model.Note(); note.fret = 7; note.string = 1; beat.addNote(note);
    score.finish(new at.Settings());
    for (const [offset, value] of points) note.addBendPoint(new at.model.BendPoint(offset, value));
    return score;
}
function midi(score) {
    const file = new at.midi.MidiFile();
    new at.midi.MidiFileGenerator(score, null, new at.midi.AlphaSynthMidiFileHandler(file, false)).generate();
    return file.events.filter(e => e.constructor.name.includes('Bend')).map(e => [e.tick, e.noteKey, e.value]);
}
function points(score) {
    return score.tracks[0].staves[0].bars[0].voices[0].beats[0].notes[0].bendPoints?.map(p => [p.offset, p.value]);
}

test('companion captures original curves before the existing native writer prepares its representation', {skip:!available},()=>{
    const source=fixture([[0,0],[10,2],[45,2],[60,4]]),original=points(source);
    const {bytes,sidecar}=exportWithExactBends(at,source,new at.Settings(),()=>{
        const note=source.tracks[0].staves[0].bars[0].voices[0].beats[0].notes[0],saved=note.bendPoints;
        try{note.bendPoints=[saved[0],saved.at(-1)];return new at.exporter.Gp7Exporter().export(source,new at.Settings());}
        finally{note.bendPoints=saved;}
    });
    assert.deepEqual(points(source),original);
    assert.deepEqual(points(loadWithExactBends(at,bytes,sidecar).score),original);
});

test('routine playback discovers renamed companion, rejects stale data and supports native comparison', { skip: !available }, () => {
    const root=fs.mkdtempSync(path.join(os.tmpdir(),'composition-bend-discovery-'));
    try {
        const source=fixture([[0,0],[10,2],[45,2],[60,4]]);
        const {bytes,sidecar}=exportWithExactBends(at,source);
        const file=path.join(root,'Renamed score.gp'),companion=path.join(root,'Renamed score.exact-model-bends.json');
        fs.writeFileSync(file,bytes);
        assert.equal(loadPlaybackScore(at,file).companion_selection,'absent');
        fs.writeFileSync(companion,JSON.stringify(sidecar));
        const loaded=loadPlaybackScore(at,file);
        assert.equal(loaded.companion_selection,'adjacent');
        assert.deepEqual(midi(loaded.score),midi(source));
        assert.equal(loadPlaybackScore(at,file,{exact_model_bends:false}).companion_selection,'disabled');
        sidecar.gp_sha256='wrong';fs.writeFileSync(companion,JSON.stringify(sidecar));
        assert.throws(()=>loadPlaybackScore(at,file),/hash mismatch/);
        assert.throws(()=>loadPlaybackScore(at,file,{exact_model_bends:path.join(root,'missing.json')}));
    } finally {fs.rmSync(root,{recursive:true,force:true});}
});

for (const [name, curve] of Object.entries({
    hold: [[0, 0], [10, 2], [45, 2], [60, 4]],
    unequal_middle: [[0, 0], [5, 1], [15, 2], [60, 2]],
    release: [[0, 0], [15, 4], [40, 4], [60, 0]],
    many_points: [[0, 0], [5, 1], [15, 2], [30, 2], [40, 1], [60, 0]],
    duplicate_middle: [[0, 0], [30, 4], [30, 4], [60, 0]],
    immediate_release: [[0, 0], [10, 2], [60, 2], [60, 0], [60, 0]]
})) {
    test(`sidecar restores exact model curve and MIDI: ${name}`, { skip: !available }, () => {
        const source = fixture(curve), expectedMidi = midi(source);
        const { bytes, sidecar } = exportWithExactBends(at, source);
        const { score, restored, native_gp_lossless } = loadWithExactBends(at, bytes, sidecar);
        assert.deepEqual(points(score), curve);
        assert.deepEqual(midi(score), expectedMidi);
        assert.equal(restored, 1);
        assert.equal(native_gp_lossless, false);
        assert.match(sidecar.scope, /pre-export alphaTab model/);
    });
}

test('rejects wrong GP, identities, duplicate targets and malformed curves', { skip: !available }, () => {
    const { bytes, sidecar } = exportWithExactBends(at, fixture([[0, 0], [60, 4]]));
    const wrongBytes = new Uint8Array(bytes); wrongBytes[0] ^= 1;
    assert.throws(() => loadWithExactBends(at, wrongBytes, sidecar), /hash mismatch/);
    for (const mutate of [
        s => s.curves[0].identity.fret++,
        s => s.curves[0].address[5] = 99,
        s => s.curves.push(structuredClone(s.curves[0])),
        s => s.curves[0].points = [[60, 4], [0, 0]],
        s => s.curves[0].points = [[0, 0], [61, 2]],
        s => s.curves[0].bend_type = 999
    ]) {
        const bad = structuredClone(sidecar); mutate(bad);
        assert.throws(() => loadWithExactBends(at, bytes, bad));
    }
});

test('never replaces the upstream Note.finish prototype', { skip: !available }, () => {
    const finish = at.model.Note.prototype.finish;
    const { bytes, sidecar } = exportWithExactBends(at, fixture([[0, 0], [10, 2], [45, 2], [60, 4]]));
    loadWithExactBends(at, bytes, sidecar);
    assert.equal(at.model.Note.prototype.finish, finish);
});

test('restores tied bend continuation when native GP omitted a complex origin curve', { skip: !available }, () => {
    const source = fixture([[0, 0], [5, 1], [15, 2], [30, 2], [40, 3], [60, 4]]);
    const voice = source.tracks[0].staves[0].bars[0].voices[0];
    const origin = voice.beats[0].notes[0];
    voice.beats[0].duration = at.model.Duration.Half;
    const beat = new at.model.Beat(); voice.addBeat(beat); beat.duration = at.model.Duration.Half;
    const target = new at.model.Note(); target.string = origin.string; target.fret = origin.fret;
    target.isTieDestination = true; beat.addNote(target);
    source.finish(new at.Settings()); // Six-point custom origin remains custom.
    target.addBendPoint(new at.model.BendPoint(0, 4));
    target.addBendPoint(new at.model.BendPoint(60, 2));
    target.bendOrigin = origin;
    target.isContinuedBend = true;
    const expected = midi(source);
    const { bytes, sidecar } = exportWithExactBends(at, source);
    assert.equal(sidecar.continuations.length, 1);
    const { score } = loadWithExactBends(at, bytes, sidecar);
    assert.deepEqual(midi(score), expected);
    const restoredVoice = score.tracks[0].staves[0].bars[0].voices[0];
    assert.equal(restoredVoice.beats[1].notes[0].bendOrigin, restoredVoice.beats[0].notes[0]);
    assert.equal(restoredVoice.beats[1].notes[0].isContinuedBend, true);
});
