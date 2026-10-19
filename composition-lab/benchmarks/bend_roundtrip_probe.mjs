/**
 * Optional, source-free alphaTab bend-fidelity diagnostic.
 * Usage: node composition-lab/benchmarks/bend_roundtrip_probe.mjs PATH/TO/alphaTab.mjs
 *
 * Builds one synthetic whole-note bend, exports GP7 in memory, and compares
 * parsed points, normalized model points and generated MIDI pitch-bend events.
 * Exit 0 means the probe executed; fidelity_equal=false reports a fidelity
 * failure, NOT a passing preservation test. Exceptions/invalid input exit nonzero.
 * No files are written, no upstream code is vendored or permanently patched.
 */
import path from 'node:path';
import { pathToFileURL } from 'node:url';

if (process.argv.length !== 3) {
    throw new Error('Usage: node bend_roundtrip_probe.mjs PATH/TO/alphaTab.mjs');
}
const at = await import(pathToFileURL(path.resolve(process.argv[2])).href);
const settings = new at.Settings();
const score = new at.model.Score();
score.addMasterBar(new at.model.MasterBar());
const track = new at.model.Track();
score.addTrack(track);
const staff = new at.model.Staff();
track.addStaff(staff);
staff.stringTuning.tunings = [64, 59, 55, 50, 45, 40];
const bar = new at.model.Bar();
staff.addBar(bar);
const voice = new at.model.Voice();
bar.addVoice(voice);
const beat = new at.model.Beat();
voice.addBeat(beat);
beat.duration = at.model.Duration.Whole;
const note = new at.model.Note();
note.fret = 7;
note.string = 1;
beat.addNote(note);
score.finish(settings);

// Artificial bend: reach one semitone early, hold, then rise to two semitones.
// alphaTab values are quarter tones; offsets span 0..60 of this whole note.
const sourcePoints = [[0, 0], [10, 2], [45, 2], [60, 4]];
for (const [offset, value] of sourcePoints) {
    note.addBendPoint(new at.model.BendPoint(offset, value));
}
const payload = new at.exporter.Gp7Exporter().export(score, settings);

// Observe parser output before Note.finish normalizes it. Always restore method.
const originalFinish = at.model.Note.prototype.finish;
let parsedPoints;
let reopened;
try {
    at.model.Note.prototype.finish = function (...args) {
        if (this.bendPoints?.length) {
            parsedPoints = this.bendPoints.map(p => [p.offset, p.value]);
        }
        return originalFinish.apply(this, args);
    };
    reopened = at.importer.ScoreLoader.loadScoreFromBytes(payload, settings);
} finally {
    at.model.Note.prototype.finish = originalFinish;
}
if (!parsedPoints) throw new Error('Fixture bend was not observed during parsing');
const reopenedNote = reopened.tracks[0].staves[0].bars[0].voices[0].beats[0].notes[0];
const modelPoints = reopenedNote.bendPoints?.map(p => [p.offset, p.value]) ?? [];

function samples(points) {
    if (!points.length) return null;
    return Array.from({ length: 61 }, (_, offset) => {
        if (offset <= points[0][0]) return points[0][1];
        for (let i = 1; i < points.length; i++) {
            const [x1, y1] = points[i - 1], [x2, y2] = points[i];
            if (offset <= x2) return y1 + (y2 - y1) * (offset - x1) / (x2 - x1);
        }
        return points.at(-1)[1];
    });
}
function equalCurve(a, b) {
    const x = samples(a), y = samples(b);
    return x !== null && y !== null && x.every((value, i) => Math.abs(value - y[i]) < 1e-8);
}
function pitchBends(input) {
    const midi = new at.midi.MidiFile();
    new at.midi.MidiFileGenerator(input, null, new at.midi.AlphaSynthMidiFileHandler(midi, false)).generate();
    // Ignore channel allocation, which can change independently of bend fidelity.
    return midi.events.filter(event => event.constructor.name.includes('Bend')).map(event => ({
        event_class: event.constructor.name,
        tick: event.tick,
        note_key: event.noteKey,
        value: event.value
    }));
}
const sourceMidi = pitchBends(score), reopenedMidi = pitchBends(reopened);
if (!sourceMidi.length || !reopenedMidi.length) throw new Error('Expected MIDI pitch-bend events');
const parsedEqual = equalCurve(sourcePoints, parsedPoints);
const modelEqual = equalCurve(sourcePoints, modelPoints);
const midiEqual = JSON.stringify(sourceMidi) === JSON.stringify(reopenedMidi);
console.log(JSON.stringify({
    probe_executed: true,
    fixture: 'synthetic early rise, hold, second rise; no source score',
    comparison_grid: 61,
    source_points: sourcePoints,
    parsed_before_finish_points: parsedPoints,
    reopened_model_points: modelPoints,
    parsed_curve_equal: parsedEqual,
    model_curve_equal: modelEqual,
    midi_pitch_bends_equal: midiEqual,
    source_midi_bend_events: sourceMidi.length,
    reopened_midi_bend_events: reopenedMidi.length,
    fidelity_equal: parsedEqual && modelEqual && midiEqual,
    limitation: 'One synthetic alphaTab GP7 roundtrip; not corpus coverage, native Guitar Pro playback or listening evidence.'
}, null, 2));
