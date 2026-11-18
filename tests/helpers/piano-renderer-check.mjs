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
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', {get() { return 900; }});
Object.defineProperty(window.HTMLElement.prototype, 'offsetWidth', {get() { return 900; }});
window.eval(readFileSync(resolve(root, 'public/piano/learning-songs/vendor/opensheetmusicdisplay-2.3.1.min.js'), 'utf8'));
const xml = readFileSync(resolve(root, 'public/piano/learning-songs/scores/conversion-test.musicxml'), 'utf8');
const model = parseMusicXML(xml, {DOMParser: window.DOMParser, XMLSerializer: window.XMLSerializer});
const renderer = new ScoreRenderer(window.document.getElementById('score'), window.document.getElementById('viewport'));
const report = await renderer.load(model);
assert.equal(report.mappedNotes, model.notes.length);
assert.ok(window.document.querySelector('svg'));
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
renderer.destroy();
dom.window.close();
