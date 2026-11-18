// node scripts/piano/validate_phoebe_score.mjs /path/to/render-dependencies/package.json
// Requires jsdom@31.0.1 and @napi-rs/canvas@1.1.1 in that external dependency prefix.
// Tests the actual deployed model/renderer against every preserved MIDI occurrence.
import {createRequire} from 'node:module';
import {readFileSync, writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {parseMusicXML, secondsAtBeat} from '../../public/piano/learning-songs/score-model.js';
import {ScoreRenderer} from '../../public/piano/learning-songs/score-renderer.js';

const dependencies = createRequire(resolve(process.argv[2] || 'package.json'));
const {JSDOM} = dependencies('jsdom');
const {createCanvas} = dependencies('@napi-rs/canvas');
const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const scores = resolve(root, 'public/piano/learning-songs/scores');
const stem = 'phoebe-bridgers-i-know-the-end';
const source = JSON.parse(readFileSync(resolve(scores, `${stem}-events.json`), 'utf8'));
const provenance = JSON.parse(readFileSync(resolve(scores, `${stem}.provenance.json`), 'utf8'));
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
Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', {get() { return 1100; }});
Object.defineProperty(window.HTMLElement.prototype, 'offsetWidth', {get() { return 1100; }});
window.eval(readFileSync(resolve(root, 'public/piano/learning-songs/vendor/opensheetmusicdisplay-2.3.1.min.js'), 'utf8'));
const model = parseMusicXML(readFileSync(resolve(scores, `${stem}.musicxml`), 'utf8'), {
  DOMParser: window.DOMParser, XMLSerializer: window.XMLSerializer,
});
assert.equal(model.title, 'I Know the End');
assert.equal(model.composer, 'Phoebe Bridgers');
assert.equal(model.attacks.length, 1396);
assert.equal(model.measures.length, 128);
assert.equal(model.notes.filter(note => !note.isRest).length, provenance.notation.written_note_segments);
assert.equal(model.duration, 510);
assert.deepEqual(model.warnings, []);
const attacksByPitchOnset = new Map(model.attacks.map(attack => [`${attack.midi}:${Math.round(attack.onset * 480)}`, attack]));
for (const note of source.notes) {
  const notation = note.notation;
  const attack = attacksByPitchOnset.get(`${note.midi}:${notation.start_tick}`);
  assert.ok(attack, `Source note ${note.id} has a practice attack.`);
  assert.equal(Math.round(attack.duration * 480), notation.end_tick - notation.start_tick, `${note.id} retains its notated hold.`);
  const segments = model.notes.filter(written => written.id.startsWith(`${note.id}-s`));
  assert.ok(segments.length, `${note.id} retains visible notation.`);
  assert.ok(segments.every(segment => segment.midi === note.midi && segment.staff === notation.staff && segment.voice === String(notation.voice)));
  assert.equal(Math.round(segments[0].onset * 480), notation.start_tick);
  assert.equal(Math.round(segments.reduce((sum, segment) => sum + segment.duration, 0) * 480), notation.end_tick - notation.start_tick);
  assert.deepEqual(new Set(attack.noteIds), new Set(segments.map(segment => segment.id)));
}
assert.ok(Math.abs(secondsAtBeat(model, model.duration) - provenance.source_music_seconds) < 1e-8);
assert.deepEqual(model.tempos.map(tempo => tempo.onset), [0, 192]);
const renderer = new ScoreRenderer(window.document.getElementById('score'), window.document.getElementById('viewport'));
const renderReport = await renderer.load(model);
assert.equal(renderReport.mappedNotes, model.notes.length);
assert.ok(window.document.querySelector('svg'));
renderer.color(new Map([[model.attacks[0].id, 'hit'], [model.attacks[1].id, 'miss']]), [model.attacks[2].id]);
const colors = ['#16875d', '#d63349', '#7653b3'].map(color => ({color, elements: window.document.querySelectorAll(`[fill="${color}"], [stroke="${color}"]`).length}));
assert.ok(colors.every(color => color.elements > 0));
renderer.cursorAtBeat(model.duration - 1);
const lastCursor = renderer.cursorStep;
renderer.cursorAtBeat(0);
assert.ok(renderer.cursorStep < lastCursor);
assert.ok(renderer.cursorPositions.every((position, i, all) => i === 0 || position.beat >= all[i - 1].beat));
const report = {
  sourceMidiSha256: provenance.source_sha256, scoreSha256: provenance.musicxml_sha256,
  sourceNoteOccurrences: source.notes.length, actualPracticeAttacks: model.attacks.length,
  allSourcePitchesAndNotatedTimingsMatched: true, allWrittenSegmentsMapped: true,
  modelWarnings: model.warnings, scoreDurationSeconds: secondsAtBeat(model, model.duration),
  measures: model.measures.length, renderReport,
  cursorPositions: renderer.cursorPositions.length, cursorRestartVerified: true,
  greenRedCurrentColorsVerified: colors,
  scope: 'Technical source-note, notation, model, SVG and cursor checks; no audible playback or human musical acceptance claimed.',
};
writeFileSync(resolve(scores, 'phoebe-score-validation.json'), JSON.stringify(report, null, 2) + '\n');
if (process.env.PHOEBE_SCORE_SVG) writeFileSync(process.env.PHOEBE_SCORE_SVG, window.document.querySelector('svg').outerHTML);
console.log(JSON.stringify(report));
renderer.destroy();
dom.window.close();
