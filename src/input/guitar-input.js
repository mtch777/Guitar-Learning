import { fretForMidiAndString } from "../guitar/tuning.js";

export function toPlayedPosition({ midi, string, confidence }) {
  return {
    midi,
    string,
    fret: fretForMidiAndString(midi, string),
    confidence
  };
}
