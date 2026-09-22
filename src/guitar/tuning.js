export const MAX_FRET = 24;

// Physical strings are numbered lowest-pitched to highest-pitched.
export const DEFAULT_TUNING = [
  { string: 1, note: "D#1", midi: 27 },
  { string: 2, note: "A#1", midi: 34 },
  { string: 3, note: "D#2", midi: 39 },
  { string: 4, note: "G#2", midi: 44 },
  { string: 5, note: "C#3", midi: 49 },
  { string: 6, note: "F#3", midi: 54 },
  { string: 7, note: "A#3", midi: 58 },
  { string: 8, note: "D#4", midi: 63 }
];

export function candidateStringsForMidi(midi, tuning = DEFAULT_TUNING) {
  return tuning.filter(({ midi: openMidi }) =>
    midi >= openMidi && midi <= openMidi + MAX_FRET
  );
}

export function fretForMidiAndString(midi, stringNumber, tuning = DEFAULT_TUNING) {
  const string = tuning.find(item => item.string === stringNumber);
  if (!string) return null;
  const fret = midi - string.midi;
  return fret >= 0 && fret <= MAX_FRET ? fret : null;
}
