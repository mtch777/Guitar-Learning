// Optional silent integration check:
// node tests/helpers/piano-app-check.mjs /path/to/render/package.json
// Exercises the real app, renderer, upload/storage and MIDI event adapter.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const dependencies = createRequire(resolve(process.argv[2] || 'package.json'));
const {JSDOM} = dependencies('jsdom');
const {createCanvas} = dependencies('@napi-rs/canvas');
const {IDBFactory} = dependencies('fake-indexeddb');
const {zipSync, strToU8} = dependencies('fflate');
const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const app = resolve(root, 'public/piano/learning-songs');
const html = readFileSync(resolve(app, 'index.html'), 'utf8');
const sourceXML = readFileSync(resolve(app, 'scores/conversion-test.musicxml'), 'utf8');
const indexedDB = new IDBFactory();
const saved = new Map();
const localStorage = {
  getItem: key => saved.get(key) ?? null,
  setItem: (key, value) => saved.set(key, String(value)),
  removeItem: key => saved.delete(key),
  clear: () => saved.clear(),
};
const checks = [];
const errors = [];
let generation = 0;

async function settle(predicate, label) {
  for (let attempt = 0; attempt < 400; attempt++) {
    if (predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 5));
  }
  throw new Error(`Timed out: ${label}`);
}

async function boot({resume = 'running'} = {}) {
  const dom = new JSDOM(html, {pretendToBeVisual: true, runScripts: 'outside-only', url: 'http://localhost/piano/learning-songs/'});
  const {window} = dom;
  const clock = {seconds: 0};
  const frames = new Map();
  const sounds = [];
  const audioControl = {resumeCalls: 0, pending: [], context: null};
  let frameId = 0;
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
  const parameter = () => ({value: 0, setTargetAtTime() {}, setValueAtTime() {}, exponentialRampToValueAtTime() {}, cancelScheduledValues() {}});
  const node = () => ({connect() {}, disconnect() {}, gain: parameter()});
  class SilentAudioContext {
    constructor() {
      this.state = resume === 'running' ? 'running' : 'suspended';
      this.destination = {};
      audioControl.context = this;
    }
    // Different origins expose accidental scheduling on the lesson clock.
    // A suspended context deliberately stays frozen while performance advances.
    get currentTime() { return this.state === 'running' ? 37 + clock.seconds : 0; }
    async resume() {
      audioControl.resumeCalls++;
      if (resume === 'rejected') throw new Error('Test audio permission denied');
      if (resume === 'deferred') await new Promise(resolve => audioControl.pending.push(resolve));
      this.state = 'running';
    }
    createGain() { return node(); }
    createDynamicsCompressor() { return node(); }
    createOscillator() {
      const context = this;
      const oscillator = {...node(), frequency: parameter(), start(time) { sounds.push({frequency: this.frequency.value, time, contextTime: context.currentTime}); }, stop() {}};
      return oscillator;
    }
  }
  const device = {id: 'test-midi', name: 'Silent test MIDI', state: 'connected', onmidimessage: null};
  const access = {inputs: new Map([[device.id, device]]), onstatechange: null};
  Object.defineProperty(window.navigator, 'requestMIDIAccess', {value: async () => access});
  window.requestAnimationFrame = callback => { const id = ++frameId; frames.set(id, callback); return id; };
  window.cancelAnimationFrame = id => frames.delete(id);
  window.AudioContext = SilentAudioContext;
  Object.defineProperty(window, 'indexedDB', {value: indexedDB});
  Object.defineProperty(window, 'localStorage', {value: localStorage});
  for (const [name, value] of Object.entries({window, document: window.document, DOMParser: window.DOMParser, XMLSerializer: window.XMLSerializer,
    navigator: window.navigator, localStorage, indexedDB, AudioContext: SilentAudioContext,
    performance: {now: () => clock.seconds * 1000},
    requestAnimationFrame: window.requestAnimationFrame, cancelAnimationFrame: window.cancelAnimationFrame})) {
    Object.defineProperty(globalThis, name, {configurable: true, writable: true, value});
  }
  globalThis.fetch = async input => {
    const url = new URL(input);
    assert.equal(url.protocol, 'file:', 'Integration fetch reads only repository fixtures.');
    try { return {ok: true, status: 200, text: async () => readFileSync(fileURLToPath(url), 'utf8')}; }
    catch (_) { return {ok: false, status: 404}; }
  };
  window.addEventListener('error', event => errors.push(event.error || event.message));
  window.eval(readFileSync(resolve(app, 'vendor/opensheetmusicdisplay-2.3.1.min.js'), 'utf8'));
  window.eval(readFileSync(resolve(app, 'vendor/fflate-0.8.3.min.js'), 'utf8'));
  globalThis.fflate = window.fflate;
  await import(pathToFileURL(resolve(app, 'script.js')).href + `?v=app-check-${++generation}`);
  const $ = id => window.document.getElementById(id);
  const snapshot = () => window.PianoSongLesson.getSnapshot();
  const click = async id => { $(id).click(); await new Promise(resolve => setImmediate(resolve)); };
  const midi = (pitch, on = true, velocity = 100) => {
    assert.equal(typeof device.onmidimessage, 'function', 'MIDI must be connected through the real button.');
    device.onmidimessage({data: new Uint8Array([on ? 0x90 : 0x80, pitch, velocity])});
  };
  const strike = pitch => { midi(pitch); midi(pitch, false); };
  const advance = seconds => {
    clock.seconds += seconds;
    const callbacks = [...frames.values()]; frames.clear();
    for (const callback of callbacks) callback(clock.seconds * 1000);
  };
  const mode = value => {
    const input = window.document.querySelector(`input[name="lesson-mode"][value="${value}"]`);
    input.checked = true;
    input.dispatchEvent(new window.Event('change', {bubbles: true}));
  };
  const upload = async (name, bytes) => {
    await click('upload-button');
    const file = new window.File([bytes], name);
    file.arrayBuffer = async () => Uint8Array.from(bytes).buffer;
    Object.defineProperty($('song-upload'), 'files', {configurable: true, value: [file]});
    $('song-upload').dispatchEvent(new window.Event('change', {bubbles: true}));
    await settle(() => !$('import-message').hidden && !$('song-select').disabled, `upload ${name}`);
  };
  return {dom, window, $, clock, frames, sounds, audioControl, snapshot, click, midi, strike, advance, mode, upload};
}

async function run() {
  let ui = await boot();
  assert.equal(ui.snapshot().selectedId, 'phoebe-bridgers-i-know-the-end');
  assert.equal(ui.snapshot().model, null);
  assert.ok(ui.$('play-button').disabled);
  assert.match(ui.$('empty-description').textContent, /verified notation file is still needed/);
  checks.push('honest Phoebe default requires a real score');

  await ui.click('test-score-button');
  await settle(() => ui.snapshot().model && !ui.$('song-select').disabled, 'render NWC score');
  assert.equal(ui.snapshot().model.notes, 20);
  assert.ok(ui.$('score').querySelector('svg'));
  assert.equal(ui.snapshot().storagePersistent, true);
  await ui.click('midi-button');
  assert.match(ui.$('midi-status').textContent, /Connected: Silent test MIDI/);
  await ui.click('play-button');
  assert.equal(ui.snapshot().playing, true);
  const first = ui.snapshot().lesson;
  assert.ok(first.requiredPitches.length > 1, 'Real NWC fixture starts with a chord.');
  const wrong = [...Array(128).keys()].find(pitch => !first.requiredPitches.includes(pitch));
  ui.strike(wrong);
  assert.equal(ui.snapshot().lesson.currentIndex, first.currentIndex);
  assert.equal(ui.snapshot().lesson.hits, 0);
  assert.equal(ui.snapshot().lesson.wrong, 1);
  ui.midi(first.requiredPitches[0]);
  const partial = ui.snapshot().lesson;
  assert.ok(partial.hits > 0);
  assert.equal(partial.currentIndex, first.currentIndex);
  ui.midi(first.requiredPitches[0]);
  assert.equal(ui.snapshot().lesson.hits, partial.hits, 'Held MIDI retriggers cannot add grades.');
  ui.midi(first.requiredPitches[0], false);
  for (const pitch of partial.requiredPitches) ui.strike(pitch);
  assert.ok(ui.snapshot().lesson.currentIndex > first.currentIndex);
  assert.ok(ui.$('score').querySelector('[fill="#16875d"]'));
  checks.push('real MIDI adapter: wrong pitch blocked, partial chord waits, held key deduplicated, complete chord advances');

  await ui.click('play-button');
  const pausedWait = ui.snapshot();
  ui.strike(pausedWait.lesson.requiredPitches[0]);
  assert.equal(ui.snapshot().lesson.hits, pausedWait.lesson.hits);
  await ui.click('restart-button');
  assert.equal(ui.snapshot().lesson.hits, 0);
  assert.equal(ui.snapshot().lesson.wrong, 0);
  assert.equal(ui.snapshot().playing, false);
  checks.push('wait pause ignores input; restart clears grades');

  ui.mode('timed');
  await ui.click('play-button');
  assert.ok(ui.snapshot().elapsed < 0, 'Timed mode has a count-in.');
  ui.advance(-ui.snapshot().elapsed);
  assert.equal(ui.snapshot().elapsed, 0);
  ui.strike(ui.snapshot().lesson.requiredPitches[0]);
  const greenHits = ui.snapshot().lesson.hits;
  assert.ok(greenHits > 0);
  ui.advance(.181);
  assert.ok(ui.snapshot().lesson.misses > 0);
  assert.ok(ui.$('score').querySelector('[fill="#d63349"]'));
  assert.ok(ui.$('score').querySelector('[fill="#16875d"]'));
  assert.ok(ui.sounds.length > 0, 'Silent fake audio receives scheduled notes.');
  assert.equal(ui.sounds[0].time, ui.sounds[0].contextTime, 'Scheduling translates the lesson clock into the different audio-clock origin.');
  await ui.click('play-button');
  const pausedTimed = ui.snapshot();
  ui.advance(30);
  ui.strike(pausedTimed.lesson.requiredPitches[0]);
  assert.equal(ui.snapshot().elapsed, pausedTimed.elapsed);
  assert.equal(ui.snapshot().lesson.hits, pausedTimed.lesson.hits);
  assert.equal(ui.snapshot().lesson.misses, pausedTimed.lesson.misses);
  await ui.click('play-button');
  assert.ok(Math.abs(ui.snapshot().elapsed - pausedTimed.elapsed) < 1e-9);
  assert.equal(ui.snapshot().lesson.hits, greenHits);
  checks.push('timed count-in, shared audio/RAF clock, green hits/red misses, frozen pause and coherent resume');

  // Reach each remaining onset through RAF and fresh MIDI messages. Completion
  // of grading must not restart or end the last sustained playback note.
  for (let guard = 0; !ui.snapshot().lesson.complete && guard < 100; guard++) {
    const state = ui.snapshot();
    ui.advance(Math.max(0, state.lesson.currentGroup.time - state.elapsed));
    for (const pitch of ui.snapshot().lesson.requiredPitches) ui.strike(pitch);
  }
  assert.ok(ui.snapshot().lesson.complete);
  assert.ok(ui.snapshot().playing, 'Last attack completion keeps sustained playback running.');
  await ui.click('play-button');
  const finalPaused = ui.snapshot();
  const soundsBeforeResume = ui.sounds.length;
  ui.advance(10);
  await ui.click('play-button');
  assert.ok(ui.snapshot().lesson.complete, 'Resume after final attack must retain final grades.');
  assert.ok(Math.abs(ui.snapshot().elapsed - finalPaused.elapsed) < 1e-9);
  assert.ok(ui.sounds.length > soundsBeforeResume, 'Resume reschedules held notes silently.');
  ui.advance(100);
  assert.equal(ui.snapshot().playing, false);
  assert.match(ui.$('play-button').textContent, /Play again/);
  await ui.click('restart-button');
  assert.equal(ui.snapshot().lesson.hits, 0);
  assert.equal(ui.snapshot().lesson.misses, 0);
  checks.push('last attack is separate from playback end; pause/resume preserves final held-note grades');

  const uploadedXML = sourceXML.replaceAll('Cuthbert NWC Test', 'Saved integration fixture');
  const archive = zipSync({
    'META-INF/container.xml': strToU8('<container><rootfiles><rootfile full-path="score.musicxml" media-type="application/vnd.recordare.musicxml+xml"/></rootfiles></container>'),
    'score.musicxml': strToU8(uploadedXML),
  });
  await ui.upload('saved-integration.mxl', archive);
  assert.ok(!ui.$('import-message').classList.contains('error'), ui.$('import-message').textContent);
  assert.equal(ui.snapshot().model.title, 'Saved integration fixture');
  const savedId = ui.snapshot().selectedId;
  assert.match(savedId, /^upload-/);
  assert.equal(ui.snapshot().songCount, 3);
  assert.ok(!/storage is unavailable/.test(ui.$('import-message').textContent));
  await ui.upload('invalid.musicxml', strToU8('<not-a-score/>'));
  assert.ok(ui.$('import-message').classList.contains('error'));
  assert.equal(ui.snapshot().selectedId, savedId);
  assert.equal(ui.snapshot().model.notes, 20);
  assert.ok(ui.$('score').querySelector('svg'));
  checks.push('real MXL upload saves to IndexedDB; rejected upload retains usable prior score');

  const speedInput = ui.$('tempo');
  speedInput.value = '75';
  speedInput.dispatchEvent(new ui.window.Event('input', {bubbles:true}));
  speedInput.dispatchEvent(new ui.window.Event('change', {bubbles:true}));
  ui.dom.window.close();
  ui = await boot();
  assert.equal(ui.snapshot().selectedId, savedId);
  assert.equal(ui.snapshot().songCount, 3);
  assert.equal(ui.snapshot().model.title, 'Saved integration fixture');
  assert.equal(ui.snapshot().model.notes, 20);
  assert.equal(ui.snapshot().mode, 'timed');
  assert.equal(ui.snapshot().speed, .75);
  assert.ok(ui.$('score').querySelector('svg'));
  assert.equal(ui.snapshot().lesson.hits, 0);
  checks.push('fresh page/module restores saved score, selection, mode and speed without re-upload');

  ui.dom.window.close();
  ui = await boot({resume: 'deferred'});
  await ui.click('play-button');
  assert.equal(ui.snapshot().playing, false);
  assert.ok(ui.$('play-button').disabled, 'A pending audio resume disables a second Play.');
  assert.match(ui.$('play-button').textContent, /Starting/);
  await ui.click('play-button');
  assert.equal(ui.audioControl.resumeCalls, 1, 'Double Play cannot start overlapping unlock requests.');
  ui.mode('wait');
  assert.ok(!ui.$('play-button').disabled);
  for (const resolve of ui.audioControl.pending.splice(0)) resolve();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(ui.snapshot().mode, 'wait');
  assert.equal(ui.snapshot().playing, false, 'An old resume completion cannot start the changed mode.');
  assert.equal(ui.snapshot().elapsed, 0);
  assert.equal(ui.frames.size, 0);
  checks.push('delayed audio resume disables double Play; changing mode cancels the pending start');

  ui.dom.window.close();
  ui = await boot({resume: 'rejected'});
  ui.mode('timed');
  await ui.click('play-button');
  assert.equal(ui.audioControl.context.state, 'suspended');
  assert.equal(ui.audioControl.context.currentTime, 0);
  assert.equal(ui.snapshot().playing, true);
  assert.ok(ui.snapshot().elapsed < 0);
  assert.match(ui.$('import-message').textContent, /Test audio permission denied/);
  ui.advance(-ui.snapshot().elapsed + .181);
  assert.ok(ui.snapshot().elapsed > .18, 'A denied audio device cannot freeze the lesson clock.');
  assert.ok(ui.snapshot().lesson.misses > 0, 'Silent timed grading continues after the count-in.');
  assert.ok(ui.$('score').querySelector('[fill="#d63349"]'));
  assert.equal(ui.audioControl.context.currentTime, 0);
  assert.equal(ui.sounds.length, 0);
  await ui.click('play-button');
  checks.push('rejected audio resume leaves audio clock frozen but count-in, score and missed-note grading continue silently');
  assert.deepEqual(errors, []);
  ui.dom.window.close();
  console.log(JSON.stringify({status: 'pass', checks, silent: true, generations: generation}, null, 2));
}

run().catch(error => {
  console.error(JSON.stringify({status: 'fail', completedChecks: checks, error: error.message, stack: error.stack, browserErrors: errors.map(String)}, null, 2));
  process.exitCode = 1;
});
