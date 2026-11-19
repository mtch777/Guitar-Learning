import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

class Element {
  constructor() {
    this.children = [];
    this.style = {};
    this.dataset = {};
    this.hidden = true;
    this.classes = new Set();
    this.listeners = new Map();
    this.classList = {
      add: name => this.classes.add(name),
      remove: (...names) => names.forEach(name => this.classes.delete(name)),
      toggle: (name, active) => active ? this.classes.add(name) : this.classes.delete(name),
      contains: name => this.classes.has(name),
    };
  }
  set innerHTML(value) { assert.equal(value, ''); this.children = []; }
  appendChild(node) { this.children.push(node); }
  addEventListener(name, fn) { this.listeners.set(name, fn); }
  click() { return this.listeners.get('click')?.(); }
}

for (const lesson of [
  {directory:'major-scales', button:'newScaleButton', expected:'C – D – E – F – G – A – B – C', total:8},
  {directory:'major-triads', button:'newTriadButton', expected:'C – E – G', total:3},
]) {
  test(`${lesson.directory}: showing the sequence does not play or grade notes`, async () => {
    const ids = ['rootName', 'status', 'midiButton', lesson.button, 'keyboard', 'progressText', 'answerButton', 'answerText'];
    const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
    const midi = {inputs:new Map([['keyboard', {onmidimessage:null}]])};
    let random = 0;
    const context = vm.createContext({
      document: {getElementById:id => elements[id],createElement:() => new Element()},
      window: {setTimeout() { throw Error('Hint must not schedule a grade.'); }, clearTimeout() {}},
      navigator: {requestMIDIAccess:async () => midi},
      Math: Object.assign(Object.create(Math), {random:() => random}),
    });
    const source = readFileSync(new URL(`../public/piano/keyboard-shapes/${lesson.directory}/script.js`, import.meta.url), 'utf8');
    vm.runInContext(source, context);
    assert.equal(elements.progressText.textContent, `0 / ${lesson.total}`);
    elements.answerButton.click();
    assert.equal(elements.answerText.hidden, false);
    assert.equal(elements.answerText.textContent, 'Answer: ' + lesson.expected);
    assert.equal(elements.progressText.textContent, `0 / ${lesson.total}`);
    assert.ok(elements.keyboard.children.every(key => !key.classList.contains('correct')));
    elements.answerButton.click();
    assert.equal(elements.answerText.hidden, true);
    elements.answerButton.click();
    random = 0.25;
    elements[lesson.button].click();
    assert.equal(elements.answerText.hidden, true, 'New question hides the prior answer.');
    assert.equal(elements.progressText.textContent, `0 / ${lesson.total}`);
  });
}

test('note reading: revealing a note name leaves the same note waiting for MIDI input', () => {
  let controller;
  const angular = {module:() => ({controller:(_name, callback) => controller = callback})};
  const scope = {};
  const staff = {innerHTML:'',querySelector:() => null};
  const Vex = {
    Flow:{
      Voice:class {addTickables() {}}, GhostNote:class {},
      Factory:class {
        EasyScore() { return {notes:() => [{setStyle() {}}],voice:() => ({})}; }
        System() { return {addStave() {return {addClef() {return {addTimeSignature() {}}}}},addConnector() {}}; }
        draw() {}
      },
    },
  };
  const source = readFileSync(new URL('../public/piano/sheet-reading/note-reading/script.js', import.meta.url), 'utf8');
  vm.runInNewContext(source, {angular,Vex,document:{getElementById:() => staff},window:{},navigator:{},Math:Object.assign(Object.create(Math),{random:() => 0})});
  controller(scope,() => {throw Error('Hint must not start a timer.');});
  assert.equal(scope.answerAvailable, true);
  assert.equal(scope.answerVisible, false);
  scope.toggleAnswer();
  assert.equal(scope.answerVisible, true);
  assert.equal(scope.answerLabel, 'C4');
  scope.toggleAnswer();
  assert.equal(scope.answerVisible, false);
  scope.toggleAnswer();
  scope.applyFilters();
  assert.equal(scope.answerVisible, false, 'New note resets the hint.');
});
