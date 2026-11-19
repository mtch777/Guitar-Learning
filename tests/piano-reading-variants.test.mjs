import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const raw = readFileSync(new URL('../public/piano/sheet-reading/note-reading/script.js', import.meta.url), 'utf8');
const source = raw.replace(/\n\}\);\s*$/, [
  '  window.__test = {gradeMidiNote, getFilteredMidiNotes, next:() => currentNotes.slice(), remaining:() => remainingQuestions.slice()};',
  '});',
].join('\n'));
assert.notEqual(source, raw, 'The reading quiz must expose its controller for regression testing.');

function lesson(search) {
  let controller;
  const angular = {module:() => ({controller:(_name, fn) => {controller = fn;}})};
  const staff = {innerHTML:'', querySelector:() => null};
  class Voice {addTickables() {}}
  class StaveNote {addAccidental() {} setStyle() {}}
  const Vex = {Flow:{
    Voice, StaveNote, GhostNote:class {}, Accidental:class {},
    Factory:class {
      EasyScore() {return {notes:() => [{setStyle() {}}],voice:() => new Voice()};}
      System() {return {addStave() {return {addClef() {return {addTimeSignature() {}};}};}, addConnector() {}};}
      draw() {}
    },
  }};
  const win = {location:{search}};
  const context = vm.createContext({
    angular,Vex,window:win,document:{getElementById:() => staff},
    navigator:{},URLSearchParams,
    Math:Object.assign(Object.create(Math),{random:() => .31}),
  });
  vm.runInContext(source,context);
  const pending = [];
  const timeout = callback => {pending.push(callback);return callback;};
  timeout.cancel = callback => {const i = pending.indexOf(callback);if (i >= 0) pending.splice(i,1);};
  const scope = {};
  controller(scope,timeout);
  return {scope, probe:win.__test, advance:() => {const fn = pending.shift();if (fn) fn();}};
}

const variants = [
  ['?clef=treble&notes=natural',12],
  ['?clef=treble&notes=all',20],
  ['?clef=bass&notes=natural',14],
  ['?clef=bass&notes=all',24],
  ['?clef=both&notes=natural',26],
  ['?clef=both&notes=all',44],
  ['?kind=chord&accidentals=0',5],
  ['?kind=chord&accidentals=1',6],
  ['?kind=chord&accidentals=2',6],
  ['?kind=chord&accidentals=all',18],
];

for (const [search, expected] of variants) {
  test('reading quiz answers every unique item: ' + search, () => {
    const {scope,probe,advance} = lesson(search);
    assert.equal(probe.remaining().length,expected);
    const seen = new Set();
    for (let n = 0; n < expected; n++) {
      const root = probe.next()[0];
      assert.ok(!seen.has(root),'A correct answer cannot repeat before the round finishes.');
      seen.add(root);
      for (const note of probe.next()) probe.gradeMidiNote(note);
      advance();
    }
    assert.equal(scope.roundComplete,true);
    assert.equal(probe.remaining().length,0);
    scope.restartRound();
    assert.equal(scope.roundComplete,false);
    assert.equal(probe.remaining().length,expected);
  });
}
test('Show answer reveals a hint but does not grade or advance', () => {
  const {scope,probe} = lesson('?kind=chord&accidentals=all');
  const root = probe.next()[0], remaining = probe.remaining().length;
  scope.toggleAnswer();
  assert.equal(scope.answerVisible,true);
  assert.equal(probe.next()[0],root);
  assert.equal(probe.remaining().length,remaining);
});
test('Wrong notes do not remove questions from the inventory', () => {
  const {probe,advance} = lesson('?clef=treble&notes=natural');
  const root = probe.next()[0], remaining = probe.remaining().length;
  probe.gradeMidiNote(root === 60 ? 61 : 60);
  advance();
  assert.equal(probe.next()[0],root);
  assert.equal(probe.remaining().length,remaining);
});
