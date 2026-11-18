// Optional silent integration check:
// node tests/helpers/piano-app-check.mjs /path/to/render/package.json
// Exercises the real app/renderer/MIDI adapter, public GitHub catalog and local recovery.
// Native GitHub authentication/commit is not simulated here; verify it separately.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {parseMusicXML} from '../../public/piano/learning-songs/score-model.js';

const dependencies = createRequire(resolve(process.argv[2] || 'package.json'));
const {JSDOM} = dependencies('jsdom');
const {createCanvas} = dependencies('@napi-rs/canvas');
const {IDBFactory} = dependencies('fake-indexeddb');

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const app = resolve(root, 'public/piano/learning-songs');
const html = readFileSync(resolve(app, 'index.html'), 'utf8');
const sourceXML = readFileSync(resolve(app, 'scores/conversion-test.musicxml'), 'utf8');
let indexedDB = new IDBFactory();
let remoteCatalog;
const remoteScores = new Map();
let remoteUnavailable = false;
const fetchRequests = [];
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

async function boot({resume = 'running', legacySongs = []} = {}) {
  const dom = new JSDOM(html, {pretendToBeVisual: true, runScripts: 'outside-only', url: 'http://localhost/piano/learning-songs/'});
  const {window} = dom;
  const clock = {seconds: 0};
  const frames = new Map();
  const sounds = [];
  const audioControl = {resumeCalls: 0, pending: [], context: null};
  const renderControl = {loads: [], error: null};
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
  Object.defineProperty(window.HTMLElement.prototype, 'clientHeight', {get() { return this.id === 'score-viewport' ? 300 : 0; }});
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
  globalThis.fetch = async (input, options = {}) => {
    const url = new URL(input);
    fetchRequests.push({url: url.href, options});
    assert.ok(!options.method || options.method === 'GET', 'Static lesson never attempts unauthenticated GitHub writes.');
    if (url.pathname.endsWith('/song-library.json')) {
      if (remoteUnavailable) return {ok: false, status: 503};
      return {ok: true, status: 200, json: async () => structuredClone(remoteCatalog), text: async () => JSON.stringify(remoteCatalog)};
    }
    const relative = url.pathname.split('/learning-songs/')[1];
    if (relative && remoteScores.has(relative)) {
      const text = remoteScores.get(relative);
      return {ok: true, status: 200, text: async () => text};
    }
    const path = url.protocol === 'file:' ? fileURLToPath(url) : relative ? resolve(app, decodeURIComponent(relative)) : null;
    if (!path) throw new Error('Unexpected test request: ' + url.href);
    try { return {ok: true, status: 200, text: async () => readFileSync(path, 'utf8')}; }
    catch (_) { return {ok: false, status: 404}; }
  };
  if (legacySongs.length) {
    const {SongStorage} = await import(pathToFileURL(resolve(app, 'song-storage.js')).href);
    const legacyStorage = await new SongStorage().open();
    for (const song of legacySongs) await legacyStorage.put(song);
    legacyStorage.db?.close();
  }
  window.addEventListener('error', event => errors.push(event.error || event.message));
  window.eval(readFileSync(resolve(app, 'vendor/opensheetmusicdisplay-2.3.1.min.js'), 'utf8'));
  window.eval(readFileSync(resolve(app, 'vendor/fflate-0.8.3.min.js'), 'utf8'));
  const nativeLoad = window.opensheetmusicdisplay.OpenSheetMusicDisplay.prototype.load;
  window.opensheetmusicdisplay.OpenSheetMusicDisplay.prototype.load = async function(xml, ...args) {
    renderControl.loads.push(xml);
    if (renderControl.error) {
      const error = renderControl.error;
      renderControl.error = null;
      throw error;
    }
    return nativeLoad.call(this, xml, ...args);
  };
  globalThis.fflate = window.fflate;
  await import(pathToFileURL(resolve(app, 'script.js')).href + `?v=app-check-${++generation}`);
  const $ = id => window.document.getElementById(id);
  const snapshot = () => window.PianoSongLesson.getSnapshot();
  const keyPitches = (state = '') => [...$('keyboard').querySelectorAll(`.piano-key${state ? '.' + state : ''}`)].map(key => Number(key.dataset.midi));
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
  const select = async id => {
    $('song-select').value = id;
    $('song-select').dispatchEvent(new window.Event('change', {bubbles: true}));
    await settle(() => snapshot().selectedId === id && !$('song-select').disabled, `select ${id}`);
  };

  const renderedModel = () => parseMusicXML(renderControl.loads.at(-1), {DOMParser:window.DOMParser, XMLSerializer:window.XMLSerializer});
  const transpose = async direction => {
    await click(direction > 0 ? 'transpose-up' : 'transpose-down');
    await settle(() => !$('song-select').disabled, 'finish transpose');
  };
  return {dom, window, $, clock, frames, sounds, audioControl, renderControl, renderedModel, snapshot, keyPitches, click, midi, strike, advance, mode, select, transpose};
}

async function run() {
  remoteCatalog = JSON.parse(readFileSync(resolve(app, 'song-library.json'), 'utf8'));
  // Small playable upload for interaction checks; production test songs stay hidden.
  const practiceId = 'integration-practice-song';
  const practicePath = 'scores/integration-practice-song.musicxml';
  const practiceXML = sourceXML.replaceAll('Cuthbert NWC Test', 'Practice phrase');
  remoteScores.set(practicePath, practiceXML);
  remoteCatalog.songs.push({id:practiceId, title:'Practice phrase', composer:'Integration test', scorePath:practicePath});
  const legacyXML = sourceXML.replaceAll('Cuthbert NWC Test', 'Legacy recovery score');
  const hiddenTest = remoteCatalog.songs.find(song => song.sourceFilename === 'MusicXML-upload-test.mxl');
  const hiddenTestXML = readFileSync(resolve(app, hiddenTest.scorePath), 'utf8');
  let ui = await boot({legacySongs: [
    {id: 'phoebe-bridgers-i-know-the-end', title: 'Legacy recovery score', composer: 'Local tester', xml: legacyXML, filename: 'legacy.musicxml'},
    {id:'old-test-copy', title:'Old test copy', xml:hiddenTestXML},
    {id:'real-same-title-upload', title:'MusicXML-upload-test', composer:'User score', xml:sourceXML.replaceAll('Cuthbert NWC Test', 'My own practice')},
  ]});
  assert.equal(ui.snapshot().selectedId, 'phoebe-bridgers-i-know-the-end');
  assert.equal(ui.snapshot().model?.attacks, 1396, 'Fresh default is the actual full Phoebe score.');
  assert.equal(ui.snapshot().model?.notes, 1622, 'Every pitched segment and rest reaches the actual renderer.');
  assert.ok(!ui.$('play-button').disabled);
  assert.ok(ui.$('score').querySelector('svg'));
  assert.equal(ui.$('score').querySelector('.lesson-score-window').dataset.visibleSystemStart, '1');
  assert.equal(ui.$('score').querySelector('.lesson-score-window').dataset.visibleSystemCount, '2',
    'The actual Phoebe score starts with only the first two systems in its window.');
  assert.equal(ui.$('song-title'), null, 'No redundant outer score title.');
  assert.equal(ui.$('test-score-button'), null, 'No test-song CTA.');
  for (const id of ['song-details', 'song-description', 'grading-note', 'score-warnings',
    'keyboard-range', 'input-octave', 'octave-down', 'octave-up']) {
    assert.equal(ui.$(id), null, `${id} is removed from the compact playing view.`);
  }
  assert.equal(ui.window.document.querySelector('.legend'), null);
  assert.equal(ui.$('keyboard').querySelector('.shortcut'), null, 'No computer-key hints occupy the piano keys.');
  assert.equal(ui.$('keyboard-panel').hidden, false, 'Keyboard is shown by default.');
  assert.equal(ui.$('keyboard-toggle').getAttribute('aria-expanded'), 'true');
  for (const id of ['keyboard-toggle', 'midi-button']) {
    assert.equal(ui.$(id).closest('#keyboard-panel'), null, `${id} remains accessible when the keyboard is hidden.`);
    assert.ok(ui.$('keyboard').compareDocumentPosition(ui.$(id)) & ui.window.Node.DOCUMENT_POSITION_FOLLOWING,
      `${id} follows the keyboard in the playing view.`);
  }
  const phoebeKeys = Array.from({length:52}, (_, index) => 46 + index);
  assert.deepEqual(ui.keyPitches(), phoebeKeys, 'All chromatic keys from the real song minimum to maximum appear at once.');
  assert.ok(ui.$('keyboard').querySelector('[data-midi="46"]').classList.contains('black'));
  assert.ok(ui.$('keyboard').querySelector('[data-midi="97"]').classList.contains('black'));
  for (const key of ui.$('keyboard').querySelectorAll('.piano-key')) {
    assert.ok(parseFloat(key.style.left) >= -1e-8);
    // CSSOM serializes percentages to fewer digits than the layout arithmetic.
    assert.ok(parseFloat(key.style.left) + parseFloat(key.style.width) <= 100 + 1e-4, 'Both black endpoints are fully inside the keyboard.');
  }
  checks.push('song-range keyboard includes both black endpoints and every intervening pitch without computer-key or range controls');
  const initialOptions = [...ui.$('song-select').options].map(option => option.value);
  for (const test of remoteCatalog.songs.filter(song => song.testScore)) assert.ok(!initialOptions.includes(test.id));
  assert.ok(!initialOptions.includes('local-old-test-copy'), 'An exact local test copy is hidden.');
  assert.ok(initialOptions.includes('local-real-same-title-upload'), 'A genuine same-title upload remains available.');
  const uploadLink = ui.$('upload-button');
  assert.equal(uploadLink.tagName, 'A');
  assert.equal(uploadLink.href, 'https://github.com/mtch777/Guitar-Learning/upload/main/public/piano/learning-songs/uploads');
  assert.match(uploadLink.textContent, /\.musicxml.*\.xml.*\.mxl/);
  assert.equal(ui.$('song-upload'), null, 'Native GitHub upload replaces browser-only file picker.');
  assert.equal(ui.$('library-note'), null);
  const beforeNativeUpload = ui.snapshot().songCount;
  uploadLink.addEventListener('click', event => event.preventDefault(), {once: true});
  await ui.click('upload-button');
  assert.equal(ui.snapshot().songCount, beforeNativeUpload);
  assert.match(ui.$('library-message').textContent, /commit on GitHub/);
  assert.ok(!/uploaded successfully|saved successfully/i.test(ui.$('library-message').textContent));
  const legacyOption = [...ui.$('song-select').options].find(option => option.textContent.includes('Legacy recovery score'));
  assert.ok(legacyOption && legacyOption.value.startsWith('local-'), 'A local Phoebe-ID recovery file cannot replace the repository default.');
  await ui.select(legacyOption.value);
  assert.ok(!ui.$('local-recovery').hidden, 'Legacy local score is visibly marked as device-only.');
  assert.match(ui.$('local-recovery').textContent, /Device-only copy/);
  assert.ok(ui.$('download-local-score'), 'Legacy local files can be downloaded for GitHub migration.');
  checks.push('actual Phoebe renders; compact UI without Details or legend; exact test copies hidden while genuine local uploads survive');
  checks.push('native GitHub upload link; isolated legacy recovery and migration control');

  await ui.select('phoebe-bridgers-i-know-the-end');
  await ui.click('midi-button');
  await ui.click('play-button');
  const phoebeFirst = ui.snapshot().lesson;
  assert.deepEqual(phoebeFirst.requiredPitches, [61, 85]);
  assert.deepEqual(ui.keyPitches('current'), [61, 85], 'Wait mode shows all required chord keys.');
  ui.strike(60);
  assert.equal(ui.snapshot().lesson.hits, 0);
  assert.equal(ui.snapshot().lesson.currentIndex, phoebeFirst.currentIndex);
  await ui.click('keyboard-toggle');
  assert.equal(ui.$('keyboard-panel').hidden, true);
  assert.equal(ui.$('keyboard-toggle').getAttribute('aria-expanded'), 'false');
  assert.equal(ui.$('keyboard-toggle').closest('[hidden]'), null, 'Show keyboard remains available after hiding the keys.');
  assert.equal(ui.snapshot().playing, true, 'Hiding the visual keyboard does not stop practice.');
  for (const pitch of phoebeFirst.requiredPitches) ui.strike(pitch);
  assert.equal(ui.snapshot().lesson.hits, 2);
  assert.ok(ui.snapshot().lesson.currentIndex > phoebeFirst.currentIndex);
  await ui.click('keyboard-toggle');
  assert.equal(ui.$('keyboard-panel').hidden, false);
  assert.deepEqual(ui.keyPitches('current'), ui.snapshot().lesson.requiredPitches, 'Revealed keyboard shows the current target after hidden MIDI input.');
  await ui.click('play-button');
  await ui.click('restart-button');
  ui.mode('timed');
  await ui.click('play-button');
  assert.deepEqual(ui.keyPitches('playing'), [], 'Count-in does not light notes before their onset.');
  ui.advance(-ui.snapshot().elapsed);
  assert.deepEqual(ui.keyPitches('playing'), [61, 85]);
  ui.strike(61);
  ui.advance(.181);
  assert.equal(ui.snapshot().lesson.hits, 1);
  assert.equal(ui.snapshot().lesson.misses, 1);
  assert.ok(ui.$('score').querySelector('[fill="#16875d"]'));
  assert.ok(ui.$('score').querySelector('[fill="#d63349"]'));
  ui.advance(.02);
  assert.deepEqual(ui.keyPitches('playing'), [61, 80], 'Bass sustains while the first short melody note releases and the next begins.');
  await ui.click('play-button');
  assert.deepEqual(ui.keyPitches('playing'), [], 'Pausing clears sounding-key feedback.');
  await ui.click('play-button');
  assert.deepEqual(ui.keyPitches('playing'), [61, 80], 'Resume restores the notes sounding at the frozen score time.');
  await ui.click('play-button');
  await ui.click('restart-button');
  assert.deepEqual(ui.keyPitches('playing'), [], 'Restart does not leave a sustained key lit.');
  ui.mode('wait');
  checks.push('actual Phoebe first chord blocks wrong input, advances only when complete, and grades separate timed hit/miss heads');
  checks.push('keyboard wait targets, timed onsets/releases/sustains, pause/resume/restart, and hidden MIDI grading agree with the actual score');

  const rowFrame = ui.$('score').querySelector('.lesson-score-window');
  assert.ok(Number(rowFrame.dataset.systemCount) > 2);
  await ui.click('play-button');
  for (let attempts = 0; rowFrame.dataset.visibleSystemStart === '1' && attempts < 512; attempts++) {
    const pitches = ui.snapshot().lesson.requiredPitches;
    assert.ok(pitches.length, 'A current score attack remains playable at the row boundary.');
    for (const pitch of pitches) ui.strike(pitch);
  }
  assert.equal(rowFrame.dataset.visibleSystemStart, '2', 'Correct MIDI input advances to the next pair of rows.');
  assert.equal(rowFrame.dataset.visibleSystemCount, '2');
  const secondRowTime = ui.snapshot().lesson.currentGroup.time;
  assert.equal(ui.$('score-viewport').scrollTop, 0);
  assert.equal(ui.window.document.documentElement.scrollTop, 0);
  await ui.click('play-button');
  await ui.click('restart-button');
  assert.equal(rowFrame.dataset.visibleSystemStart, '1', 'Restart returns to the first pair.');
  ui.mode('timed');
  await ui.click('play-button');
  ui.advance(-ui.snapshot().elapsed + secondRowTime);
  assert.equal(rowFrame.dataset.visibleSystemStart, '2', 'Timed playback reaches the same pair at the same score onset.');
  assert.equal(rowFrame.dataset.visibleSystemCount, '2');
  assert.equal(ui.$('score-viewport').scrollTop, 0);
  assert.equal(ui.window.document.documentElement.scrollTop, 0);
  await ui.click('play-button');
  await ui.click('restart-button');
  ui.mode('wait');
  checks.push('actual MIDI and timed playback advance the same current/next row pair without changing scroll offsets; restart restores rows 1–2');

  const originalXML = ui.renderControl.loads.at(-1);
  const originalPitches = ui.renderedModel().notes.filter(note => !note.isRest).map(note => note.midi);
  const beforeTransposeFetches = fetchRequests.length;
  ui.$('transpose-up').click();
  assert.equal(ui.snapshot().transpose, 0, 'The new offset is not committed before engraving succeeds.');
  assert.ok(ui.$('transpose-up').disabled && ui.$('transpose-down').disabled && ui.$('song-select').disabled);
  ui.$('transpose-up').dispatchEvent(new ui.window.MouseEvent('click', {bubbles:true}));
  await settle(() => !ui.$('song-select').disabled, 'first transposition');
  assert.equal(ui.snapshot().transpose, 1, 'Repeated input while busy cannot queue an accidental extra semitone.');
  assert.equal(ui.$('transpose-value').value, '+1');
  assert.deepEqual(ui.renderedModel().notes.filter(note => !note.isRest).map(note => note.midi), originalPitches.map(pitch => pitch + 1));
  assert.equal(new ui.window.DOMParser().parseFromString(ui.renderControl.loads.at(-1), 'application/xml').querySelector('key > fifths').textContent, '2',
    'The score actually engraved by OSMD changes from D-flat to D major.');
  assert.deepEqual(ui.keyPitches(), phoebeKeys.map(pitch => pitch + 1));
  assert.deepEqual(ui.snapshot().lesson.requiredPitches, [62, 86]);
  assert.equal(ui.$('score').querySelector('.lesson-score-window').dataset.visibleSystemCount, '2');
  assert.equal(ui.$('practice-status').textContent, 'Ready');
  await ui.click('play-button');
  ui.strike(61);
  assert.equal(ui.snapshot().lesson.hits, 0, 'The old key is wrong after a semitone shift.');
  assert.equal(ui.snapshot().lesson.wrong, 1);
  ui.strike(62); ui.strike(86);
  assert.equal(ui.snapshot().lesson.hits, 2, 'The shifted pitches grade against the shifted notation.');
  ui.mode('timed');
  ui.sounds.length = 0;
  await ui.click('play-button');
  ui.advance(-ui.snapshot().elapsed);
  const frequency = midi => 440 * Math.pow(2, (midi - 69) / 12);
  for (const pitch of [62, 86]) assert.ok(ui.sounds.some(sound => Math.abs(sound.frequency - frequency(pitch)) < 1e-8));
  assert.ok(!ui.sounds.some(sound => Math.abs(sound.frequency - frequency(61)) < 1e-8));
  assert.deepEqual(ui.keyPitches('playing'), [62, 86]);
  ui.midi(62);
  await ui.transpose(-1);
  assert.equal(ui.snapshot().playing, false, 'Changing pitch pauses playback.');
  assert.equal(ui.snapshot().elapsed, 0);
  assert.equal(ui.snapshot().lesson.hits, 0);
  assert.equal(ui.snapshot().lesson.misses, 0);
  assert.deepEqual(ui.keyPitches('active'), [], 'Held input is cleared when the keyboard changes pitch.');
  assert.deepEqual(ui.keyPitches('playing'), []);
  assert.equal(ui.snapshot().transpose, 0);
  assert.equal(ui.$('transpose-value').value, '0');
  assert.equal(ui.renderControl.loads.at(-1), originalXML, 'Returning to 0 restores the exact original normalized score.');
  assert.deepEqual(ui.keyPitches(), phoebeKeys);
  ui.mode('wait');
  await ui.transpose(-1);
  assert.equal(ui.snapshot().transpose, -1);
  assert.deepEqual(ui.renderedModel().notes.filter(note => !note.isRest).map(note => note.midi), originalPitches.map(pitch => pitch - 1));
  assert.equal(new ui.window.DOMParser().parseFromString(ui.renderControl.loads.at(-1), 'application/xml').querySelector('key > fifths').textContent, '0');
  assert.deepEqual(ui.keyPitches(), phoebeKeys.map(pitch => pitch - 1));
  assert.deepEqual(ui.snapshot().lesson.requiredPitches, [60, 84]);
  assert.equal(fetchRequests.length, beforeTransposeFetches, 'Pitch changes neither reload nor alter repository songs.');
  checks.push('semitone arrows synchronize real engraved pitches/key signatures, grading, silent audio and full-range keyboard; 0 restores original notation');
  checks.push('pitch change cancels playback, clears the attempt and held keys, keeps two rows, and ignores duplicate busy input');

  const retainedSvg = ui.$('score').querySelector('svg');
  const retainedFrame = ui.$('score').querySelector('.lesson-score-window');
  ui.renderControl.error = new Error('Synthetic engraving refusal');
  await ui.transpose(1);
  assert.equal(ui.snapshot().transpose, -1);
  assert.equal(ui.$('transpose-value').value, '-1');
  assert.equal(ui.$('score').querySelector('svg'), retainedSvg);
  assert.equal(ui.$('score').querySelector('.lesson-score-window'), retainedFrame);
  assert.deepEqual(ui.snapshot().lesson.requiredPitches, [60, 84]);
  assert.deepEqual(ui.keyPitches(), phoebeKeys.map(pitch => pitch - 1));
  assert.equal(ui.$('practice-status').textContent, 'Synthetic engraving refusal');
  assert.equal(ui.$('play-button').disabled, false);
  assert.equal(ui.$('import-message').hidden, true, 'A transpose failure uses the existing status without adding height.');
  checks.push('failed transpose retains previous offset, playable model, keyboard and actual SVG without an extra status row');

  await ui.select(practiceId);
  await settle(() => ui.snapshot().model && !ui.$('song-select').disabled, 'render NWC score');
  assert.equal(ui.snapshot().model.notes, 20);
  assert.equal(ui.snapshot().transpose, 0, 'Selecting another song starts at its original pitch.');
  assert.notDeepEqual(ui.keyPitches(), phoebeKeys, 'Selecting a different song updates the keyboard range.');
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

  // This simulates the repository catalog produced AFTER a GitHub commit/build.
  // Merely opening the native upload page cannot change this catalog or claim success.
  const savedId = 'upload-integration-repository';
  const savedPath = 'scores/upload-integration-repository.musicxml';
  remoteScores.set(savedPath, sourceXML.replaceAll('Cuthbert NWC Test', 'Saved integration fixture'));
  remoteCatalog.songs.push({id: savedId, title: 'Saved integration fixture', composer: 'Integration test', scorePath: savedPath,
    sourcePath: 'uploads/saved-integration.mxl', sourceFilename: 'saved-integration.mxl'});
  await ui.click('refresh-library');
  await settle(() => [...ui.$('song-select').options].some(option => option.value === savedId) && !ui.$('song-select').disabled, 'refresh newly committed repository score');
  await ui.select(savedId);
  assert.equal(ui.snapshot().model.title, 'Saved integration fixture');
  assert.equal(ui.snapshot().model.notes, 20);
  assert.ok(ui.$('local-recovery').hidden, 'Repository score is not presented as local-only recovery.');
  remoteUnavailable = true;
  await ui.click('refresh-library');
  await settle(() => !ui.$('library-message').hidden && !ui.$('refresh-library').disabled, 'failed catalog refresh');
  assert.equal(ui.snapshot().selectedId, savedId);
  assert.equal(ui.snapshot().model.notes, 20);
  assert.ok(ui.$('score').querySelector('svg'));
  assert.match(ui.$('library-message').textContent, /could not be refreshed/i);
  assert.ok(!/saved to GitHub|uploaded successfully/i.test(ui.$('library-message').textContent));
  remoteUnavailable = false;
  checks.push('new GitHub catalog score becomes selectable; failed refresh preserves active score and never claims upload success');

  remoteCatalog.songs.push({id:'broken-integration-score', title:'Broken upload', scorePath:'scores/broken-integration.musicxml'});
  await ui.click('refresh-library');
  await settle(() => !ui.$('refresh-library').disabled, 'refresh bad score entry');
  ui.$('song-select').value = 'broken-integration-score';
  ui.$('song-select').dispatchEvent(new ui.window.Event('change', {bubbles:true}));
  await settle(() => !ui.$('song-select').disabled, 'failed score selection');
  assert.equal(ui.snapshot().selectedId, savedId);
  assert.equal(ui.$('song-select').value, savedId);
  assert.equal(ui.snapshot().model.title, 'Saved integration fixture');
  assert.equal(ui.$('play-button').disabled, false);
  assert.equal(ui.$('practice-status').textContent, 'Previous score kept');
  assert.ok(!/HTTP|endpoint|sha256/i.test(ui.$('import-message').textContent));
  checks.push('failed score selection restores playable previous score and selector with a concise error');

  const speedInput = ui.$('tempo');
  speedInput.value = '75';
  speedInput.dispatchEvent(new ui.window.Event('input', {bubbles:true}));
  speedInput.dispatchEvent(new ui.window.Event('change', {bubbles:true}));
  await ui.click('keyboard-toggle');
  assert.equal(ui.$('keyboard-panel').hidden, true);
  ui.dom.window.close();
  ui = await boot();
  assert.equal(ui.snapshot().selectedId, savedId);
  assert.equal(ui.snapshot().model.title, 'Saved integration fixture');
  assert.equal(ui.snapshot().model.notes, 20);
  assert.equal(ui.snapshot().mode, 'timed');
  assert.equal(ui.snapshot().speed, .75);
  assert.equal(ui.$('keyboard-panel').hidden, true, 'Show/hide preference survives reload.');
  await ui.click('keyboard-toggle');
  assert.equal(ui.$('keyboard-panel').hidden, false);
  assert.ok(ui.$('score').querySelector('svg'));
  assert.equal(ui.snapshot().lesson.hits, 0);
  checks.push('fresh page/module restores repository score, last selection, mode and speed without re-upload');

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
  ui = await boot({resume:'deferred'});
  await ui.click('play-button');
  assert.ok(ui.$('play-button').disabled);
  await ui.transpose(1);
  assert.equal(ui.snapshot().transpose, 1);
  for (const resolve of ui.audioControl.pending.splice(0)) resolve();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(ui.snapshot().playing, false, 'An old audio resume cannot start a transposed/reset attempt.');
  assert.equal(ui.snapshot().elapsed, 0);
  assert.equal(ui.frames.size, 0);
  assert.equal(ui.sounds.length, 0);
  checks.push('transpose cancels a pending audio unlock and leaves the shifted score Ready');

  ui.dom.window.close();
  ui = await boot({resume: 'rejected'});
  ui.mode('timed');
  await ui.click('play-button');
  assert.equal(ui.audioControl.context.state, 'suspended');
  assert.equal(ui.audioControl.context.currentTime, 0);
  assert.equal(ui.snapshot().playing, true);
  assert.ok(ui.snapshot().elapsed < 0);
  assert.match(ui.$('import-message').textContent, /Sound unavailable/);
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
  // A new device has no IndexedDB score data or remembered selection, but every
  // GitHub-backed score remains available and Phoebe is the first/default song.
  indexedDB = new IDBFactory();
  saved.clear();
  ui = await boot();
  assert.equal(ui.snapshot().selectedId, 'phoebe-bridgers-i-know-the-end');
  assert.equal(ui.snapshot().model.attacks, 1396);
  assert.equal(ui.$('keyboard-panel').hidden, false, 'A fresh device defaults to showing the keyboard.');
  assert.ok([...ui.$('song-select').options].some(option => option.value === savedId));
  assert.ok(![...ui.$('song-select').options].some(option => option.value.startsWith('local-')));
  await ui.select(savedId);
  assert.equal(ui.snapshot().model.title, 'Saved integration fixture');
  checks.push('independent device reads shared GitHub songs with no local score storage, defaults to Phoebe');
  assert.ok(fetchRequests.every(request => !request.options.headers?.Authorization));
  ui.dom.window.close();

  saved.set('piano-song-last-selection-v1', hiddenTest.id);
  ui = await boot();
  assert.equal(ui.snapshot().selectedId, 'phoebe-bridgers-i-know-the-end');
  assert.equal(ui.$('song-select').value, 'phoebe-bridgers-i-know-the-end');
  checks.push('remembered hidden test falls back to Phoebe with matching visible selection');
  ui.dom.window.close();

  const savedXML = remoteScores.get(savedPath);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(savedXML));
  remoteCatalog.songs.find(song => song.id === savedId).sha256 = Buffer.from(digest).toString('hex');
  saved.set('piano-song-last-selection-v1', 'old-published-copy');
  ui = await boot({legacySongs:[{id:'old-published-copy', title:'Saved integration fixture', xml:savedXML}]});
  assert.equal(ui.snapshot().selectedId, savedId);
  assert.equal(ui.$('song-select').value, savedId);
  assert.ok(ui.$('local-recovery').hidden);
  assert.ok(![...ui.$('song-select').options].some(option => option.value === 'local-old-published-copy'));
  assert.equal(saved.get('piano-song-last-selection-v1'), savedId);
  checks.push('remembered exact local duplicate resolves to its shared GitHub score without a duplicate entry');
  assert.deepEqual(errors, []);
  ui.dom.window.close();
  console.log(JSON.stringify({status: 'pass', checks, silent: true, generations: generation}, null, 2));
}

run().catch(error => {
  console.error(JSON.stringify({status: 'fail', completedChecks: checks, error: error.message, stack: error.stack, browserErrors: errors.map(String)}, null, 2));
  process.exitCode = 1;
});
