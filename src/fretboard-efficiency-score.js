// Exact occurrence adapter: optimizer strings are high→low; alphaTab strings
// are low→high. The existing native score writer owns notation and tied holds.
import { DROP_E, toEventScore } from './riff-event-score.js';

export const EFFICIENCY_NATIVE_PPQN = 960;
const velocityRegistrations = new WeakMap();

function exactTick(value, sourcePpqn) {
  const tick = value * EFFICIENCY_NATIVE_PPQN / sourcePpqn;
  if (!Number.isInteger(value) || !Number.isSafeInteger(tick)) {
    throw new Error('This mapping is not on the exact native tick grid. No timing was rounded.');
  }
  return tick;
}

// alphaTab 1.8.4 exposes written dynamics, not arbitrary MIDI velocities. Its
// score-to-MIDI generator runs on the main thread before handing MIDI to the
// synthesizer. Override only registered native note objects; all other scores
// retain alphaTab's original dynamics and articulation behavior.
function registerExactVelocities(at, entries) {
  const Generator = at.midi?.MidiFileGenerator;
  if (typeof Generator?._getNoteVelocity !== 'function') {
    throw new Error('The player does not provide the verified exact-velocity playback API.');
  }
  let velocities = velocityRegistrations.get(Generator);
  if (!velocities) {
    velocities = new WeakMap();
    const original = Generator._getNoteVelocity;
    Generator._getNoteVelocity = function(note) {
      return velocities.has(note) ? velocities.get(note) : original.call(this, note);
    };
    velocityRegistrations.set(Generator, velocities);
  }
  for (const [note, velocity] of entries) velocities.set(note, velocity);
}

export function normalizeFretboardEfficiency(fixture, versionId = 'optimized') {
  if (!fixture || !Array.isArray(fixture.notes) || !fixture.notes.length) {
    throw new Error('The fretboard mapping has no note occurrences.');
  }
  const ppqn = Number(fixture.ticks_per_beat), tempo = Number(fixture.tempo_bpm);
  if (!Number.isInteger(ppqn) || ppqn <= 0 || !Number.isFinite(tempo) || tempo <= 0) {
    throw new Error('The fretboard mapping has an invalid tempo or tick resolution.');
  }
  const durationTicks = exactTick(fixture.duration_ticks, ppqn);
  if (durationTicks <= 0) throw new Error('The fretboard mapping has no duration.');
  const version = fixture.versions?.find(item => item.id === versionId);
  if (!version || !Array.isArray(version.assignments)) throw new Error('This fretboard mapping version is unavailable.');
  const assignments = new Map();
  for (const assignment of version.assignments) {
    if (assignments.has(assignment.note_id)) throw new Error('The fretboard mapping repeats a note assignment.');
    assignments.set(assignment.note_id, assignment);
  }
  const ids = new Set();
  const notes = fixture.notes.map(source => {
    if (!Number.isInteger(source.id) || ids.has(source.id)) throw new Error('The fretboard mapping needs unique note occurrence IDs.');
    ids.add(source.id);
    const assignment = assignments.get(source.id);
    if (!assignment) throw new Error('A source note has no fretboard assignment.');
    const {string_number, fret} = assignment;
    const startTick = exactTick(source.start_tick, ppqn), endTick = exactTick(source.end_tick, ppqn);
    if (!Number.isInteger(string_number) || string_number < 1 || string_number > 8 ||
        !Number.isInteger(fret) || fret < 0 || fret > 24 ||
        DROP_E[string_number - 1] + fret !== source.pitch ||
        startTick < 0 || endTick <= startTick || endTick > durationTicks ||
        !Number.isInteger(source.velocity) || source.velocity < 1 || source.velocity > 127 ||
        !Number.isInteger(source.channel) || source.channel < 0 || source.channel > 15 || source.channel === 9) {
      throw new Error('A source note has invalid timing, velocity, channel, pitch, or Drop E placement.');
    }
    return {note_id: source.id, string: 9 - string_number, string_number, fret,
      pitch: source.pitch, velocity: source.velocity, channel: source.channel,
      startTick, endTick, sourceStartTick: source.start_tick, sourceEndTick: source.end_tick};
  });
  if (assignments.size !== ids.size) throw new Error('The fretboard mapping includes an unknown note assignment.');
  const channels = new Set(notes.map(note => note.channel));
  if (channels.size !== 1) throw new Error('This guitar lesson adapter requires one source MIDI channel.');
  for (let string = 1; string <= 8; string++) {
    const lane = notes.filter(note => note.string === string).sort((a, b) => a.startTick - b.startTick);
    for (let i = 1; i < lane.length; i++) {
      if (lane[i].startTick < lane[i - 1].endTick) throw new Error('Two held notes occupy the same guitar string.');
    }
  }
  return {notes, durationTicks, durationMs: durationTicks / EFFICIENCY_NATIVE_PPQN * 60000 / tempo,
    ticksPerBeat: EFFICIENCY_NATIVE_PPQN, sourceTicksPerBeat: ppqn, tempo,
    fixtureId: fixture.id, versionId, label: fixture.label || fixture.id || 'Drop E mapping',
    versionLabel: version.label || versionId, channel: notes[0].channel};
}

/** Build an actual alphaTab score without changing the source event stream. */
export function toFretboardEfficiencyScore(at, fixture, versionId = 'optimized') {
  const mapping = normalizeFretboardEfficiency(fixture, versionId);
  const result = {tuning: [...DROP_E], tempo: mapping.tempo, meter: [4, 4],
    duration_q: `${mapping.durationTicks}/${EFFICIENCY_NATIVE_PPQN}`,
    events: mapping.notes.map(note => ({
      onset_q: `${note.startTick}/${EFFICIENCY_NATIVE_PPQN}`,
      members: [{string_number: note.string_number, fret: note.fret, pitch: note.pitch,
        duration_q: `${note.endTick - note.startTick}/${EFFICIENCY_NATIVE_PPQN}`}]
    }))};
  const score = toEventScore(at, result, `${mapping.label} · ${mapping.versionLabel}`);
  score.artist = 'Fretboard efficiency study';
  const track = score.tracks[0];
  track.name = `${mapping.label} · Drop E 8 string`;
  track.playbackInfo.primaryChannel = mapping.channel;
  const velocityEntries = [];
  const nativeNotes = track.staves[0].bars.flatMap(bar => bar.voices.flatMap(voice => voice.beats.flatMap(beat => beat.notes)));
  for (const note of nativeNotes) {
    const tick = note.beat.absolutePlaybackStart;
    const occurrence = mapping.notes.find(item => item.string === note.string && item.startTick <= tick && item.endTick > tick);
    if (!occurrence || note.realValue !== occurrence.pitch) throw new Error('The native score lost a source note occurrence.');
    note.efficiencyNoteId = occurrence.note_id;
    velocityEntries.push([note, occurrence.velocity]);
    if (!note.isTieDestination) {
      if (occurrence.note) throw new Error('A held source note was reattacked in the native score.');
      occurrence.note = note;
    }
  }
  if (mapping.notes.some(note => !note.note) ||
      score.masterBars.reduce((sum, bar) => sum + bar.calculateDuration(), 0) !== mapping.durationTicks) {
    throw new Error('The native score changed the occurrence count or final release clock.');
  }
  registerExactVelocities(at, velocityEntries);
  return {...mapping, score};
}

/** Exact active holds from the player's native tick clock, including unisons. */
export function efficiencyNotesAtTick(mapping, tick) {
  if (!mapping || !Number.isFinite(Number(tick))) return [];
  const now = Math.max(0, Number(tick));
  return mapping.notes.filter(note => note.startTick <= now && now < note.endTick)
    .map(note => ({...note, bendSemitones: 0}));
}

/** Published bundles and individual saved fixtures are both uploadable. */
export function readFretboardEfficiencyFile(data, preferredId = null) {
  if (data?.schema === 'drop-e-fretboard-efficiency/1') {
    if (!Array.isArray(data.tuning_high_to_low) || data.tuning_high_to_low.some((pitch, i) => pitch !== DROP_E[i]) ||
        data.tuning_high_to_low.length !== DROP_E.length || !Array.isArray(data.fixtures) || !data.fixtures.length) {
      throw new Error('The fretboard mapping bundle has an invalid Drop E tuning or fixture list.');
    }
    return data.fixtures.find(item => item.id === preferredId) || data.fixtures[0];
  }
  if (data?.notes && data?.versions) return data;
  throw new Error('Choose a saved fretboard efficiency mapping JSON file.');
}
