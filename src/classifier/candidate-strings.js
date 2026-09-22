import { candidateStringsForMidi } from "../guitar/tuning.js";

export function maskProbabilitiesByPitch(probabilities, midi) {
  const allowed = new Set(candidateStringsForMidi(midi).map(x => x.string));
  const masked = probabilities.map((p, index) => allowed.has(index + 1) ? p : 0);
  const total = masked.reduce((sum, p) => sum + p, 0);
  return total > 0 ? masked.map(p => p / total) : masked;
}
