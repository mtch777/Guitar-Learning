// Read-only supplement to the existing actual GP/MIDI snapshot. No selection.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {loadPlaybackScore} from './songsterr_automation/songsterr_api/playback_score.mjs';

const [moduleArg, rootArg] = process.argv.slice(2);
if (!rootArg) throw Error('alphaTab module and native output folder required');
const root = path.resolve(rootArg), modulePath = path.resolve(moduleArg);
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const sha = p => hash(fs.readFileSync(p));
const sharedPath = path.join(root, 'dynamic-native-snapshot.json');
const shared = JSON.parse(fs.readFileSync(sharedPath, 'utf8'));
if (shared.module_sha256 !== sha(modulePath) ||
    shared.core_sha256 !== sha(path.join(path.dirname(modulePath), 'alphaTab.core.mjs')))
    throw Error('Shared snapshot runtime differs');
const at = await import(pathToFileURL(modulePath));
const quarter = new at.model.MasterBar();
quarter.timeSignatureNumerator = 1;
quarter.timeSignatureDenominator = 4;
const timing = {
    quarter_ticks: quarter.calculateDuration(),
    palm_mute_constant: at.midi.MidiFileGenerator._defaultDurationPalmMute,
    position_scale: at.model.BendPoint.MaxPosition
};
if (Object.values(timing).some(v => !Number.isInteger(v) || v <= 0))
    throw Error('Pinned native mute duration parameters unavailable');
const cases = {};
for (const method of ['source', 'zero', 'changed']) {
    const file = path.join(root, method, 'score.gp');
    if (sha(file) !== shared.cases[method].gp_sha256) throw Error('Actual GP changed');
    const {score} = loadPlaybackScore(at, file, {});
    const notes = [];
    for (const [part, track] of score.tracks.entries()) {
        if (track.staves.length !== 1) throw Error('Single staff correspondence required');
        for (const [mi, bar] of track.staves[0].bars.entries())
            for (const [vi, voice] of bar.voices.entries())
                for (const beat of voice.beats)
                    for (const note of beat.notes)
                        notes.push({native_ref: `native:${part}:${mi + 1}:${vi}:${beat.index}:${note.index}`,
                            is_palm_muted: note.isPalmMute, beat_duration_ticks: beat.playbackDuration});
    }
    if (JSON.stringify(notes.map(n => n.native_ref)) !==
        JSON.stringify(shared.cases[method].notes.map(n => n.native_ref)))
        throw Error('Native note correspondence changed');
    cases[method] = {gp_sha256: sha(file), notes};
}
const result = {schema: 'native-palm-mute-supplement/1',
    shared_snapshot: {file: 'dynamic-native-snapshot.json', sha256: sha(sharedPath)},
    adapter_sha256: sha(fileURLToPath(import.meta.url)), timing, cases};
const output = path.join(root, 'palm-mute-native-supplement.json');
if (fs.existsSync(output)) throw Error('Refusing to overwrite native supplement');
fs.writeFileSync(output, JSON.stringify(result, null, 2));
console.log(JSON.stringify({status: 'NATIVE_MUTE_SUPPLEMENT_WRITTEN_NOT_ACCEPTANCE', timing,
    notes: Object.fromEntries(Object.entries(cases).map(([name, value]) => [name, value.notes.length]))}));
