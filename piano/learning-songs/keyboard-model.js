const WHITE_PITCH_CLASSES = [0, 2, 4, 5, 7, 9, 11];
const BLACK_WIDTH = 0.62;
const validPitch = midi => Number.isInteger(midi) && midi >= 0 && midi <= 127;

/** Exact song range, using piano-key geometry rather than equal chromatic widths. */
export function keyboardLayout(attacks = []) {
  let min = Infinity, max = -Infinity;
  for (const note of attacks) if (validPitch(note.midi)) {
    min = Math.min(min, note.midi); max = Math.max(max, note.midi);
  }
  if (!Number.isFinite(min)) return {min: null, max: null, units: 0, whiteCount: 0, keys: []};
  const keys = [];
  for (let midi = min; midi <= max; midi++) {
    const pitchClass = midi % 12;
    const black = !WHITE_PITCH_CLASSES.includes(pitchClass);
    const whitePosition = Math.floor(midi / 12) * 7
      + WHITE_PITCH_CLASSES.filter(pitch => pitch < pitchClass).length;
    keys.push({midi, black, left: whitePosition - (black ? BLACK_WIDTH / 2 : 0), width: black ? BLACK_WIDTH : 1});
  }
  // Black endpoints retain their full visible width without inventing adjacent notes.
  const start = keys[0].left, end = keys.at(-1).left + keys.at(-1).width;
  const units = end - start;
  return {
    min, max, units, whiteCount: keys.filter(key => !key.black).length,
    keys: keys.map(key => ({...key, left: (key.left - start) / units, width: key.width / units})),
  };
}

/** Sounding score pitches at the exact lesson clock; independent of input grades. */
export function playingPitchesAt(notes, seconds) {
  const pitches = new Set();
  if (!Number.isFinite(seconds) || seconds < 0) return pitches;
  for (const note of notes) {
    if (validPitch(note.midi) && note.time <= seconds && seconds < note.endTime) pitches.add(note.midi);
  }
  return pitches;
}
