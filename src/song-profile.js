import { TIME_SOLO_DROP_E_TUNING } from './data/time-solo.js';

export function isTimeFile(name) {
  return /^time(?:\(\d+\))?\.gp$/i.test(String(name).trim());
}

export function applySongPitch(api, score, timeProfile) {
  // Time is played in the source score's F# minor key; reset any previous
  // transposition on every track when a new score is uploaded.
  for (const track of score.tracks) {
    api.changeTrackTranspositionPitch([track], 0);
  }
}

export function timeNotePosition(note) {
  const staff = note.beat.voice.bar.staff;
  const tuning = staff.stringTuning.tunings;
  const sourceIndex = tuning.length - note.string;
  const pitch = tuning[sourceIndex] + note.fret + (staff.capo || 0);
  const preferred = 8 - tuning.length + note.string - 1;
  const candidates = TIME_SOLO_DROP_E_TUNING.flatMap((open, index) => {
    const fret = pitch - open;
    return fret >= 0 && fret <= 24 ? [{ index, fret }] : [];
  });
  // Preserve the original concert pitch and octave. Only the visual fingering
  // changes: optimize for the active F# minor CAGED hand position. Rakes are
  // filtered by the caller, and alphaTab retains the source bend/slide events.
  const barIndex = staff.bars?.indexOf(note.beat.voice.bar) ?? -1;
  const shape = timeCagedShapeForBar(barIndex);
  const range = shape === 'a' ? [9, 12] : shape === 'high-e' ? [14, 17] : [2, 5];
  const distance = fret => fret < range[0] ? range[0] - fret :
    fret > range[1] ? fret - range[1] : 0;
  // Prefer pentatonic frets inside the hand position, but never silently
  // change a pitch. For non-pentatonic passing notes, choose the nearest fret.
  const pentatonic = new Set([6, 9, 11, 1, 4]);
  candidates.sort((a, b) => {
    const score = c => distance(c.fret) * 100 +
      (c.index < 2 ? 40 : 0) +
      (pentatonic.has(((pitch % 12) + 12) % 12) ? 0 : 4) +
      Math.abs(c.index - preferred);
    return score(a) - score(b);
  });
  const position = candidates[0];
  return position ? { string: position.index + 1, fret: position.fret } : null;
}

/** Source score uses zero-based bar numbers; return the assigned hand position. */
export function timeCagedShapeForBar(barIndex) {
  if (barIndex >= 104 && barIndex <= 109) return 'a';
  if (barIndex >= 110 && barIndex <= 125) return 'high-e';
  return 'low-e';
}
