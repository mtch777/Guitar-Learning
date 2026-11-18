// Optional integration check: node tests/helpers/piano-renderer-check.mjs /path/to/render/package.json
// Uses the actual vendored browser OSMD bundle, jsdom and @napi-rs/canvas.
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {parseMusicXML} from '../../public/piano/learning-songs/score-model.js';
import {ScoreRenderer} from '../../public/piano/learning-songs/score-renderer.js';
process.on('uncaughtException', error => { console.error(error.message); process.exit(1); });

const dependencies = createRequire(resolve(process.argv[2] || 'package.json'));
const {JSDOM} = dependencies('jsdom');
const {createCanvas} = dependencies('@napi-rs/canvas');
const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const dom = new JSDOM('<!doctype html><div id="viewport"><div id="score"></div></div>', {
  pretendToBeVisual: true, runScripts: 'outside-only', url: 'http://localhost/',
});
const {window} = dom;
const canvases = new WeakMap();
window.HTMLCanvasElement.prototype.getContext = function(type) {
  if (!canvases.has(this)) canvases.set(this, createCanvas(this.width || 300, this.height || 150));
  return canvases.get(this).getContext(type);
};
window.HTMLCanvasElement.prototype.toDataURL = function() {
  return canvases.get(this)?.toDataURL() || createCanvas(1, 1).toDataURL();
};
let availableWidth = 900;
let availableHeight = 300;
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', {get() { return availableWidth; }});
Object.defineProperty(window.HTMLElement.prototype, 'offsetWidth', {get() { return availableWidth; }});
Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', {get() { return this.id === 'viewport' ? availableHeight : 0; }});
const observers = [];
window.ResizeObserver = class {
  constructor(callback) { this.callback = callback; observers.push(this); }
  observe(target) { (this.targets ||= []).push(target); }
  disconnect() { this.disconnected = true; }
};
window.eval(readFileSync(resolve(root, 'public/piano/learning-songs/vendor/opensheetmusicdisplay-2.3.1.min.js'), 'utf8'));
const xml = readFileSync(resolve(root, 'public/piano/learning-songs/scores/conversion-test.musicxml'), 'utf8');
const model = parseMusicXML(xml, {DOMParser: window.DOMParser, XMLSerializer: window.XMLSerializer});
const renderer = new ScoreRenderer(window.document.getElementById('score'), window.document.getElementById('viewport'));
const checkSystemWindow = (model, index) => {
  const row = renderer.systems[index];
  const next = renderer.systems[index + 1];
  const last = next || row;
  const measure = model.measures[row.measures[0]];
  renderer.cursorAtBeat(measure.onset);
  assert.equal(renderer.visibleSystem, index, 'Measure membership selects its actual engraved system.');
  assert.equal(renderer.frame.dataset.visibleSystemCount, next ? '2' : '1');
  const top = -parseFloat(renderer.host.style.top);
  const height = parseFloat(renderer.frame.style.height);
  const bottom = top + height;
  assert.ok(top <= row.top + .01, 'The current system is complete at the top.');
  assert.ok(bottom >= last.bottom - .01, 'The next system is complete at the bottom.');
  assert.ok(height <= availableHeight + .5, 'Two whole systems fit the allocated viewport height.');
  if (index > 0) assert.ok(top >= renderer.systems[index - 1].bottom - .01, 'No previous system is visible.');
  if (index + 2 < renderer.systems.length) assert.ok(bottom <= renderer.systems[index + 2].top + .01, 'No third system is visible.');
  assert.equal(renderer.viewport.scrollTop, 0);
  assert.equal(renderer.viewport.scrollLeft, 0);
};
const report = await renderer.load(model);
assert.equal(report.mappedNotes, model.notes.length);
assert.ok(window.document.querySelector('svg'));
assert.equal(window.document.querySelectorAll('.osmd-title, .osmd-subtitle, .osmd-composer, .osmd-lyricist').length, 0, 'Printed titles and credits do not consume the practice window.');
for (let index = 0; index < renderer.systems.length; index++) checkSystemWindow(model, index);
const first = model.attacks[0], second = model.attacks[1], third = model.attacks[2];
const statuses = new Map([[first.id, 'hit'], [second.id, 'miss']]);
renderer.color(statuses, [third.id]);
const colored = color => window.document.querySelectorAll(`[fill="${color}"], [stroke="${color}"]`).length;
assert.ok(colored('#16875d') > 0, 'Actual SVG has green hits.');
assert.ok(colored('#d63349') > 0, 'Actual SVG has red misses.');
assert.ok(colored('#7653b3') > 0, 'Actual SVG has purple current pending notes.');
renderer.cursorAtBeat(model.duration - 1);
const endStep = renderer.cursorStep;
renderer.cursorAtBeat(0);
assert.ok(renderer.cursorStep < endStep, 'Restart moves the native cursor backwards.');
renderer.cursorAtBeat(2);
renderer.resize();
assert.equal(renderer.beat, 2);
assert.ok(colored('#16875d') > 0, 'Resize keeps hit colors.');
assert.ok(colored('#d63349') > 0, 'Resize keeps miss colors.');
console.log(JSON.stringify({report, cursorPositions: renderer.cursorPositions.length, svgCount: window.document.querySelectorAll('svg').length, colors: ['#16875d', '#d63349', '#7653b3'].map(color => [color, colored(color)])}));
const fixture = `<?xml version="1.0"?><score-partwise version="4.0">
<part-list><score-part id="P1"><part-name>Piano</part-name></score-part><score-part id="P2"><part-name>Unison</part-name></score-part></part-list>
<part id="P1"><measure number="0" implicit="yes"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time><staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef></attributes>
<note id="chord-c"><pitch><step>C</step><octave>4</octave></pitch><duration>8</duration><tie type="start"/><voice>1</voice><type>half</type><staff>1</staff><notations><tied type="start"/></notations></note>
<note id="chord-e"><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>8</duration><voice>1</voice><type>half</type><staff>1</staff></note>
<backup><duration>8</duration></backup><note id="bass-c"><pitch><step>C</step><octave>3</octave></pitch><duration>8</duration><voice>2</voice><type>half</type><staff>2</staff></note></measure>
<measure number="1"><note id="tied-c"><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><tie type="stop"/><voice>1</voice><type>quarter</type><staff>1</staff><notations><tied type="stop"/></notations></note>
<note id="next-d"><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration><voice>1</voice><type>quarter</type><staff>1</staff></note>
<backup><duration>8</duration></backup><note id="bass-rest"><rest/><duration>8</duration><voice>2</voice><type>half</type><staff>2</staff></note><barline location="right"><repeat direction="backward"/></barline></measure></part>
<part id="P2"><measure number="0" implicit="yes"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
<note id="unison-c"><pitch><step>C</step><octave>4</octave></pitch><duration>8</duration><type>half</type></note></measure><measure number="1"><note id="other-g"><pitch><step>G</step><octave>3</octave></pitch><duration>8</duration><type>half</type></note><barline location="right"><repeat direction="backward"/></barline></measure></part></score-partwise>`;
const complex = parseMusicXML(fixture, {DOMParser: window.DOMParser, XMLSerializer: window.XMLSerializer});
const complexReport = await renderer.load(complex);
assert.equal(complexReport.mappedNotes, 8, 'Map chords, both staves, voices, parts, rests, and written tie continuations.');
const cAttack = complex.attacks.find(attack => attack.noteIds.includes('chord-c'));
const eAttack = complex.attacks.find(attack => attack.noteIds.includes('chord-e'));
const bassAttack = complex.attacks.find(attack => attack.noteIds.includes('bass-c'));
assert.equal(cAttack.noteIds.length, 3);
renderer.color(new Map([[cAttack.id, 'hit'], [eAttack.id, 'miss']]), [bassAttack.id]);
for (const id of cAttack.noteIds) assert.equal(renderer.appliedColors.get(id), '#16875d');
const cGraphical = renderer.noteMap.get('chord-c').graphical;
const eGraphical = renderer.noteMap.get('chord-e').graphical;
const cHeads = cGraphical.getNoteheadSVGs();
const eHeads = eGraphical.getNoteheadSVGs();
assert.equal(cHeads[cGraphical.vfnote[1]].getAttribute('fill'), '#16875d', 'One chord member stays green.');
assert.equal(eHeads[eGraphical.vfnote[1]].getAttribute('fill'), '#d63349', 'The other chord member is independently red.');
assert.ok(renderer.cursorPositions.every((position, i, values) => i === 0 || position.beat >= values[i - 1].beat));
assert.ok(renderer.cursorPositions.at(-1).beat <= complex.duration);
renderer.cursorAtBeat(3);
renderer.resize();
assert.equal(renderer.beat, 3);
assert.equal(renderer.appliedColors.get('tied-c'), '#16875d');
const previousDisplay = renderer.osmd;
const previousSvg = window.document.querySelector('svg');
await assert.rejects(() => renderer.load({...complex, notes: complex.notes.map(note => note.id === 'chord-c' ? {...note, midi: 99} : note)}), /Cannot match/);
assert.equal(renderer.osmd, previousDisplay, 'A failed replacement preserves the usable renderer.');
assert.equal(window.document.querySelector('svg'), previousSvg, 'A failed replacement preserves its original SVG.');
assert.equal(renderer.appliedColors.get('tied-c'), '#16875d');
console.log(JSON.stringify({complexReport, tieUnisonHeads: cAttack.noteIds.length, writtenCursorBeats: renderer.cursorPositions.map(position => position.beat), failedReplacementPreserved: true}));

const phoebe = parseMusicXML(readFileSync(resolve(root, 'public/piano/learning-songs/scores/phoebe-bridgers-i-know-the-end.musicxml'), 'utf8'), {DOMParser:window.DOMParser, XMLSerializer:window.XMLSerializer});
await renderer.load(phoebe);
assert.equal(renderer.noteMap.size, 1622);
const hit = phoebe.attacks[0], missed = phoebe.attacks[1], current = phoebe.attacks[2];
renderer.color(new Map([[hit.id, 'hit'], [missed.id, 'miss']]), [current.id]);
renderer.cursorAtBeat(123);
const fitChecks = [];
for (const width of [390, 320, 280, 1348]) {
  availableWidth = width;
  if (width === 390) {
    observers[0].callback();
    await new Promise(resolve => setTimeout(resolve, 150));
  } else renderer.resize();
  assert.equal(renderer.renderedWidth, width, 'Container width drives engraving.');
  assert.equal(renderer.beat, 123, 'Width changes retain the native cursor beat.');
  assert.equal(renderer.noteMap.size, phoebe.notes.length, 'All written notes and rests remain mapped.');
  for (const id of hit.noteIds) assert.equal(renderer.appliedColors.get(id), '#16875d');
  for (const id of missed.noteIds) assert.equal(renderer.appliedColors.get(id), '#d63349');
  for (const id of current.noteIds) assert.equal(renderer.appliedColors.get(id), '#7653b3');
  for (const svg of window.document.querySelectorAll('svg')) {
    assert.ok(Number(svg.getAttribute('width')) <= width + .5, 'Actual SVG surface fits its available width.');
    assert.ok(Number(svg.getAttribute('viewBox').split(/\s+/)[2]) * renderer.osmd.Zoom <= width + .5);
  }
  const measures = renderer.osmd.GraphicSheet.MusicPages.flatMap(page => page.MusicSystems.flatMap(system => system.GraphicalMeasures.flat().filter(Boolean)));
  assert.ok(measures.every(measure => measure.minimumStaffEntriesWidth <= 0 || measure.staffEntriesScaleFactor >= .999), 'Dense measures are not compressed below the renderer\'s non-overlapping width.');
  const heads = [...renderer.noteMap.values()].filter(({note}) => !note.isRest && !note.isHidden);
  for (const {graphical, note} of heads) {
    const vexNote = graphical.vfnote?.[0];
    assert.ok(vexNote.getNoteHeadBeginX() * renderer.osmd.Zoom >= -.5, 'No pitched head is clipped on the left.');
    assert.ok(vexNote.getNoteHeadEndX() * renderer.osmd.Zoom <= width + .5, 'No pitched head is clipped on the right.');
    const row = renderer.systems[renderer.systemForMeasure.get(note.measureIndex)];
    const ys = vexNote.getYs();
    assert.ok(Math.min(...ys) * renderer.osmd.Zoom >= row.top - .5, 'High ledger note centers remain inside their actual system.');
    assert.ok(Math.max(...ys) * renderer.osmd.Zoom <= row.bottom + .5, 'Low ledger note centers remain inside their actual system.');
    if (vexNote.hasStem()) {
      const stem = vexNote.getStemExtents();
      assert.ok(Math.min(stem.topY, stem.baseY) * renderer.osmd.Zoom >= row.top - .5, 'Stem tops remain inside system bounds.');
      assert.ok(Math.max(stem.topY, stem.baseY) * renderer.osmd.Zoom <= row.bottom + .5, 'Stem bottoms remain inside system bounds.');
    }
  }
  for (let index = 0; index < renderer.systems.length; index++) checkSystemWindow(phoebe, index);
  renderer.cursorAtBeat(123);
  fitChecks.push({width, height:availableHeight, zoom:renderer.osmd.Zoom, mapped:renderer.noteMap.size, systems:renderer.systems.length,
    maxPairHeight:Math.max(...renderer.systems.map((row,index) => (renderer.systems[index+1] || row).bottom - row.top + 8))});
}
assert.ok(observers[0].targets.includes(renderer.container), 'Observe the actual score container.');
assert.ok(observers[0].targets.includes(renderer.viewport), 'Observe height-only changes in the allocated viewport.');
const fullHeightZoom = renderer.osmd.Zoom;
availableWidth = 844;
availableHeight = 175;
renderer.resize();
for (let index = 0; index < renderer.systems.length; index++) checkSystemWindow(phoebe, index);
fitChecks.push({width:availableWidth,height:availableHeight,zoom:renderer.osmd.Zoom,mapped:renderer.noteMap.size,systems:renderer.systems.length});
availableWidth = 1348;
availableHeight = 300;
renderer.resize();
renderer.cursorAtBeat(123);
availableHeight = 140;
observers[0].callback();
await new Promise(resolve => setTimeout(resolve, 150));
assert.equal(renderer.renderedHeight, 140, 'Height-only changes re-engrave the two-row window.');
assert.equal(renderer.beat, 123);
assert.ok(renderer.osmd.Zoom < fullHeightZoom, 'A shallow landscape window uses a fitting native scale.');
for (let index = 0; index < renderer.systems.length; index++) checkSystemWindow(phoebe, index);
for (const id of hit.noteIds) assert.equal(renderer.appliedColors.get(id), '#16875d');
for (const id of missed.noteIds) assert.equal(renderer.appliedColors.get(id), '#d63349');
const lastIndex = renderer.systems.length - 1;
checkSystemWindow(phoebe, lastIndex);
assert.equal(renderer.frame.dataset.visibleSystemCount, '1', 'The final row never pulls a previous row back in.');
renderer.cursorAtBeat(0);
assert.equal(renderer.visibleSystem, 0, 'Restart returns to the first two systems.');
availableHeight = 300;
renderer.resize();
assert.ok(Math.abs(renderer.osmd.Zoom - fullHeightZoom) < 1e-8, 'Restoring height restores the original two-row engraving scale.');
console.log(JSON.stringify({responsivePhoebe:fitChecks, observerWidthAndHeight:true, finalSingleSystem:true, colorsAndCursorPreserved:true}));
renderer.destroy();
assert.equal(observers[0].disconnected, true);
dom.window.close();
