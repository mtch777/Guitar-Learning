import {toEventScore} from './riff-event-score.js';

/** Standard MIDI for the full accepted riff, at its original tempo.
 * Use the same score adapter and slide fixes as playback. SMF-compatible mode
 * converts alphaTab's per-note bends to standard channel pitch-bend messages;
 * simultaneous independent bends cannot be guaranteed. Timbre depends on the synth.
 * Preview speed, cursor position and phrase selection never change this export.
 */
export function createRiffMidi(at, result) {
  const score = toEventScore(at, result, `E ${result.request?.mode || ''} - Drop E riff`);
  const midi = new at.midi.MidiFile();
  midi.format = at.midi.MidiFileFormat.SingleTrackMultiChannel;
  const handler = new at.midi.AlphaSynthMidiFileHandler(midi, true);
  new at.midi.MidiFileGenerator(score, new at.Settings(), handler).generate();
  return midi.toBinary();
}

export function riffMidiFilename(result, date = new Date()) {
  const mode = String(result.request?.mode || 'generated').toLowerCase().replace(/[^a-z0-9-]/g, '-');
  return `drop-e-${mode}-riff-${date.toISOString().replace(/[:.]/g, '-')}.mid`;
}
