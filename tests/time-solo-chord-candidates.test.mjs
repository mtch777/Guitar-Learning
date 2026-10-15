import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = readFileSync(new URL('../src/trainer.js', import.meta.url), 'utf8');
const begin = source.indexOf('// Single source of truth: exactly one score-timed section');
const end = source.indexOf('function displaySongPlayerNotes(', begin);
assert.ok(begin >= 0 && end > begin, 'candidate rendering logic present');
const code = source.slice(begin, end);

function cell() {
  const classes = new Set(['timeSoloNote', 'timeSoloGrayNote']);
  return {
    classList: {
      add(...names) { names.forEach(name => classes.add(name)); },
      remove(...names) { names.forEach(name => classes.delete(name)); },
      contains(name) { return classes.has(name); }
    },
    dataset: {openString: 'false'}, style: {}, textContent: ''
  };
}

test('Time chord candidate markers clear when chord changes and outside solo', () => {
  const a=cell(), b=cell(), c=cell();
  const context=vm.createContext({
    songPlayerCells:new Map([['0:1',a],['0:2',b],['0:3',c]]),
    songPlayerActiveCells:new Set(),
    getSelectedLessonType:()=> 'timeSoloChords',
    revealCell:()=>{}
  });
  vm.runInContext(code,context);
  const paint=(tick) => vm.runInContext('timeSoloCurrentTick = '+tick+'; updateTimeSoloChordCandidates();',context);
  vm.runInContext("timeSoloSections = [{start:100,end:200,noteKeys:new Set(['0:1','0:2'])},{start:200,end:300,noteKeys:new Set(['0:3'])}]",context);
  paint(150);
  assert.equal(a.classList.contains('timeSoloCandidateNote'),true);
  assert.equal(b.classList.contains('timeSoloCandidateNote'),true);
  assert.equal(c.classList.contains('timeSoloGrayNote'),true);
  paint(250);
  assert.equal(a.classList.contains('timeSoloGrayNote'),true,'prior chord must clear');
  assert.equal(b.classList.contains('timeSoloGrayNote'),true,'prior chord must clear');
  assert.equal(c.classList.contains('timeSoloCandidateNote'),true);
  paint(301);
  for (const note of [a,b,c]) {
    assert.equal(note.classList.contains('timeSoloCandidateNote'),false,'no candidate outside solo');
    assert.equal(note.classList.contains('timeSoloGrayNote'),true);
  }
  context.songPlayerActiveCells.add(a);
  paint(150);
  assert.equal(a.classList.contains('timeSoloSelectedNote'),true,'active note stays above candidates');
  assert.equal(a.classList.contains('timeSoloCandidateNote'),false);
});
