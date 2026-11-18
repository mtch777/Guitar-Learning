import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const lessons = ['color-to-note', 'accidentals-count', 'accidentals-order'];
const neutral = '#202833';
const wrong = '#E53935';
// Starting at C, clockwise sectors advance by a perfect fifth.
const sectorForPitch = pitch => Array.from({length: 12}, (_, i) => (i * 7) % 12).indexOf(pitch);

class Element {
  constructor() {
    this.attributes = new Map();
    this.children = [];
    this.style = {};
    this.listeners = new Map();
    this.classes = new Set();
    this.classList = {
      add: name => this.classes.add(name),
      toggle: (name, enabled) => enabled ? this.classes.add(name) : this.classes.delete(name),
      contains: name => this.classes.has(name),
    };
  }
  set className(value) { this.classes = new Set(value.split(/\s+/)); }
  get className() { return [...this.classes].join(' '); }
  set innerHTML(value) { assert.equal(value, ''); this.children = []; }
  set textContent(value) { this.text = value; this.children = []; }
  get textContent() { return this.text || ''; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  appendChild(element) { this.children.push(element); }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  click() { return this.listeners.get('click')?.(); }
}

async function boot(lesson, random = 0) {
  const elements = Object.fromEntries(['circleSvg', 'midiButton', 'restartButton', 'status', 'sequenceProgress'].map(id => [id, new Element()]));
  const input = {};
  const access = {inputs: new Map([['test', input]])};
  const timers = new Map();
  let timerId = 0;
  let now = 0;
  let selection = random;
  const context = vm.createContext({
    document: {
      getElementById: id => elements[id],
      createElementNS: () => new Element(),
      createElement: () => new Element(),
    },
    navigator: {requestMIDIAccess: async () => access},
    Math: Object.assign(Object.create(Math), {random: () => selection}),
    window: {
      setTimeout: (callback, delay) => { const id = ++timerId; timers.set(id, {callback, at: now + delay}); return id; },
      clearTimeout: id => timers.delete(id),
    },
  });
  const source = readFileSync(new URL(`../public/piano/theory/circle-of-fifths/${lesson}/script.js`, import.meta.url), 'utf8');
  vm.runInContext(source, context, {filename: `${lesson}/script.js`});
  const wedges = elements.circleSvg.children.filter(element => element.getAttribute('class') === 'wedge');
  const checks = elements.circleSvg.children.filter(element => element.getAttribute('class') === 'check');
  assert.equal(wedges.length, 12);
  assert.ok(wedges.every(element => element.getAttribute('fill') === neutral));
  await elements.midiButton.click();
  assert.equal(typeof input.onmidimessage, 'function');
  return {
    elements, wedges, checks,
    select: value => { selection = value; },
    strike: (midi, velocity = 100, command = 0x90) => input.onmidimessage({data: [command, midi, velocity]}),
    pending: () => timers.size,
    advance: milliseconds => {
      now += milliseconds;
      for (const [id, timer] of [...timers]) {
        if (timer.at <= now && timers.has(id)) { timers.delete(id); timer.callback(); }
      }
    },
    reset: () => elements.restartButton.click(),
    fills: () => wedges.map(element => element.getAttribute('fill')),
    flashing: () => wedges.flatMap((element, i) => element.getAttribute('fill') === wrong ? [i] : []),
  };
}

for (const lesson of lessons) {
  test(`${lesson}: wrong MIDI input flashes its actual fifths location in any octave and restores the prompt`, async () => {
    for (let pitch = 0; pitch < 12; pitch++) {
      // Use a different correct response whenever the input would otherwise be right.
      const random = lesson === 'accidentals-order'
        ? (pitch === 6 ? 11.25 / 12 : 0)
        : (pitch === 0 ? 1.25 / 12 : 0);
      const ui = await boot(lesson, random);
      const before = ui.fills();
      const sector = sectorForPitch(pitch);
      for (const octaveBase of [48, 84]) {
        ui.strike(octaveBase + pitch);
        assert.deepEqual(ui.flashing(), [sector], `MIDI ${octaveBase + pitch}`);
        assert.deepEqual(ui.fills().filter((_, i) => i !== sector), before.filter((_, i) => i !== sector));
        // Inputs during the existing feedback lock cannot leave multiple red wedges.
        ui.strike(octaveBase + (pitch + 1) % 12);
        assert.deepEqual(ui.flashing(), [sector]);
        assert.equal(ui.pending(), 1);
        ui.advance(350);
        assert.deepEqual(ui.fills(), before);
        assert.equal(ui.pending(), 0);
      }
    }
  });

  test(`${lesson}: a wrong note on a solved sector retains its completion check`, async () => {
    const ui = await boot(lesson);
    const solvedSector = lesson === 'accidentals-order' ? 1 : 0;
    ui.strike(lesson === 'accidentals-order' ? 66 : 60);
    assert.equal(ui.checks[solvedSector].style.display, 'block');
    ui.advance(450);
    const before = ui.fills();
    ui.strike(lesson === 'accidentals-order' ? 67 : 60);
    assert.deepEqual(ui.flashing(), [solvedSector]);
    assert.equal(ui.checks[solvedSector].style.display, 'block');
    ui.advance(350);
    assert.deepEqual(ui.fills(), before);
    assert.equal(ui.checks[solvedSector].style.display, 'block');
  });

  test(`${lesson}: reset cancels stale wrong-flash and correct-advance callbacks`, async () => {
    const ui = await boot(lesson);
    ui.strike(69); // A is wrong for initial C (or the initial G accidental sequence).
    assert.deepEqual(ui.flashing(), [3]);
    ui.select(lesson === 'accidentals-order' ? 2.25 / 12 : 3.25 / 12); // New prompt A.
    ui.reset();
    assert.equal(ui.pending(), 0);
    const afterReset = ui.fills();
    assert.equal(afterReset[3], '#FDD835');
    ui.advance(350);
    assert.deepEqual(ui.fills(), afterReset);

    if (lesson === 'accidentals-order') [66, 61, 68].forEach(midi => ui.strike(midi));
    else ui.strike(lesson === 'color-to-note' ? 69 : 65);
    assert.equal(ui.elements.status.textContent, 'Correct ✓');
    assert.equal(ui.pending(), 1);
    ui.select(0);
    ui.reset();
    const restarted = ui.fills();
    const status = ui.elements.status.textContent;
    ui.advance(450);
    assert.deepEqual(ui.fills(), restarted);
    assert.equal(ui.elements.status.textContent, status);
    assert.ok(ui.checks.every(check => check.style.display === 'none'));
  });

  test(`${lesson}: note-off and zero-velocity messages do not create feedback`, async () => {
    const ui = await boot(lesson);
    const before = ui.fills();
    ui.strike(69, 100, 0x80);
    ui.strike(69, 0);
    assert.deepEqual(ui.fills(), before);
    assert.equal(ui.pending(), 0);
  });
}

for (const lesson of ['accidentals-count', 'accidentals-order']) {
  test(`${lesson}: incorrect input matching the prompt tonic restores its colored sector`, async () => {
    const ui = await boot(lesson, lesson === 'accidentals-count' ? 1.25 / 12 : 0); // G.
    const before = ui.fills();
    ui.strike(67);
    assert.deepEqual(ui.flashing(), [1]);
    ui.advance(350);
    assert.deepEqual(ui.fills(), before);
    assert.equal(ui.fills()[1], '#7CB342');
    ui.strike(lesson === 'accidentals-count' ? 62 : 66);
    assert.equal(ui.elements.status.textContent, 'Correct ✓');
  });
}

test('accidentals-order: a wrong input resets the sequence while preserving the active key', async () => {
  const ui = await boot('accidentals-order', 1.25 / 12); // D: F-sharp, C-sharp.
  ui.strike(66);
  assert.equal(ui.elements.sequenceProgress.children[0].textContent, 'F#');
  ui.strike(60);
  assert.deepEqual(ui.flashing(), [0]);
  assert.equal(ui.fills()[2], '#C0CA33');
  ui.advance(350);
  assert.equal(ui.elements.sequenceProgress.children[0].textContent, '');
  assert.ok(ui.elements.sequenceProgress.children[0].classList.contains('active'));
  [66, 61].forEach(midi => ui.strike(midi));
  assert.equal(ui.checks[2].style.display, 'block');
});

test('accidentals-order: the shared F-sharp/G-flat sector is checked only after both questions', async () => {
  const ui = await boot('accidentals-order', 5.25 / 12);
  [66, 61, 68, 63, 70, 65].forEach(midi => ui.strike(midi));
  assert.equal(ui.checks[6].style.display, 'none');
  ui.select(5.25 / 11);
  ui.advance(450);
  assert.match(ui.elements.status.textContent, /^Gb/);
  [70, 63, 68, 61, 66, 71].forEach(midi => ui.strike(midi));
  assert.equal(ui.checks[6].style.display, 'block');
});
