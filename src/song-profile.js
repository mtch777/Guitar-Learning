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
  // Keep the original string whenever possible. Open/first-fret notes may
  // need the next lower string when source tuning differs; never clamp their pitch.
  candidates.sort((a, b) => Math.abs(a.index - preferred) - Math.abs(b.index - preferred));
  const position = candidates[0];
  return position ? { string: position.index + 1, fret: position.fret } : null;
}
