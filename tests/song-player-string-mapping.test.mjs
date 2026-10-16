import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

// Exercise the actual track-change and display callbacks, with DOM drawing stubbed.
const source = readFileSync(process.env.TRAINER_SOURCE || new URL('../src/trainer.js', import.meta.url), 'utf8');
const callbacks = source.slice(source.indexOf('function displaySongPlayerNotes('), source.indexOf('setupSongPlayer({'));

test('track tuning and active notes agree for 6, 7, and 8 strings, including track switches', () => {
  const shown = [];
  const fields = { rootSelect: {value:"3"}, scaleSelect: {value:"dorian"} };
  const context = vm.createContext({
    songPlayerStringOffset: 0,
    currentTuning: [28, 35, 40, 45, 50, 55, 59, 64],
    songPlayerActiveCells: new Set(),
    songPlayerCells: new Map(),
    getSelectedLessonType: () => 'songPlayer',
    makeCellKey: (s, f) => `${s}:${f}`,
    clearSongPlayerBendVisuals() {},
    hideCell() {},
    revealCell: cell => shown.push(cell),
    buildTrainer() {},
    document: { getElementById: id => fields[id] || null },
    syncSingleSelectDisplay() {},
  });
  for (let s = 0; s < 8; s++) {
    for (let f = 0; f <= 24; f++) {
      context.songPlayerCells.set(`${s}:${f}`, {
        stringIndex: s, fret: f,
        classList: { add() {}, remove() {}, contains() { return false; } }, style: { removeProperty() {} },
      });
    }
  }
  vm.runInContext(callbacks, context);
  for (const count of [6, 7, 8, 6, 8, 7]) {
    const tuning = [64, 59, 55, 50, 45, 40, 35, 28].slice(0, count);
    context.applySongPlayerTrack({ name: 'Fixture', tuningHighToLow: tuning });
    for (let string = 1; string <= count; string++) {
      for (const fret of [0, 4, 12, 24]) {
        shown.length = 0;
        context.displaySongPlayerNotes([{ string, fret }]);
        assert.equal(shown.length, 1);
        const cell = shown[0];
        assert.equal(cell.stringIndex, 8 - count + string - 1);
        assert.equal(cell.fret, fret);
        assert.equal(context.currentTuning[cell.stringIndex] + fret, tuning[count - string] + fret);
      }
    }
    if (count === 6) {
      shown.length = 0;
      context.displaySongPlayerNotes([{ string: 3, fret: 4 }]);
      assert.equal(shown[0].stringIndex, 4, 'D string row');
      assert.equal(context.currentTuning[shown[0].stringIndex] + 4, 54, 'F#3');
    }
  }
  context.applySongPlayerTrack({name:'Time',timeProfile:true,tuningHighToLow:[64,59,55,50,45,40,35,28]});
  assert.deepEqual(Array.from(context.currentTuning),[28,35,40,45,50,55,59,64]);
  assert.equal(fields.rootSelect.value,'6');
  assert.equal(fields.scaleSelect.value,'aeolian');
  shown.length=0;
  context.displaySongPlayerNotes([{string:5,fret:2}]);
  assert.equal(shown[0].stringIndex,4);
  assert.equal(context.currentTuning[4]+shown[0].fret,52);
});
