import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {DOMParser} from '@xmldom/xmldom';
import {parseMusicXML} from '../../public/piano/learning-songs/score-model.js';

const MAX_ENDPOINT_ERROR_QUARTERS = 1 / 64 + 1e-6; // nearest 1/32-quarter grid is <=1/64.
const PYTHON = process.env.PYTHON || 'python';

export async function verifyMidiFidelity(midiFile, scoreFile) {
  const command = new URL('./expected-midi-attacks.py', import.meta.url);
  const decoded = execFileSync(PYTHON, [command.pathname, midiFile], {encoding:'utf8', timeout:30000});
  const expected = JSON.parse(decoded);
  const text = await readFile(scoreFile,'utf8');
  const model = parseMusicXML(text, {DOMParser});
  const actual = model.attacks.map(attack => ({
    midi:attack.midi,
    onset:attack.onset,
    end:attack.onset+attack.duration,
  })).sort((a,b)=>a.midi-b.midi || a.onset-b.onset);
  if (expected.length !== actual.length) {
    throw new Error(`MIDI fidelity mismatch: source has ${expected.length} attacks, sheet has ${actual.length}. No score was accepted.`);
  }
  let maxDelta = 0;
  for (let i=0;i<expected.length;i++) {
    const a=actual[i], e=expected[i];
    const startError = Math.abs(e.onset-a.onset);
    const endError = Math.abs(e.end-a.end);
    maxDelta = Math.max(maxDelta,startError,endError);
    if (a.midi!==e.midi || startError>MAX_ENDPOINT_ERROR_QUARTERS || endError>MAX_ENDPOINT_ERROR_QUARTERS) {
      throw new Error(`MIDI fidelity mismatch at attack ${i+1}: pitch ${e.midi}, onset ${e.onset}, end ${e.end}; sheet pitch ${a.midi}, onset ${a.onset}, end ${a.end}. No score was accepted.`);
    }
  }
  return {attacks:expected.length, maxEndpointErrorQuarters:maxDelta};
}
