import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {
  toFretboardEfficiencyScore, efficiencyNotesAtTick,
} from '../src/fretboard-efficiency-score.js';
import {toEventScore} from '../src/riff-event-score.js';
import {setupSongPlayer} from '../src/song-player.js';

// Mandatory native dependency. CI installs this exact package before running
// tests/*.test.mjs; an unavailable native player must fail, never silently skip.
const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const nativeRoot = resolve(root, '.local/qa/node_modules/@coderline/alphatab');
const nativePath = resolve(nativeRoot, 'dist/alphaTab.mjs');
assert.ok(existsSync(nativePath), 'Install pinned @coderline/alphatab@1.8.4 in .local/qa before native lesson QA');
assert.equal(JSON.parse(readFileSync(resolve(nativeRoot, 'package.json'), 'utf8')).version, '1.8.4');
const at = await import(pathToFileURL(nativePath).href);
const bundle = JSON.parse(readFileSync(resolve(root, 'public/data/fretboard-efficiency-fixtures.json'), 'utf8'));

/** Independent standard MIDI reader: no adapter or fixture-derived clocks. */
function rawMidi(path) {
  const bytes = readFileSync(path);
  assert.equal(bytes.toString('ascii', 0, 4), 'MThd');
  const format = bytes.readUInt16BE(8), tracks = bytes.readUInt16BE(10), ppqn = bytes.readUInt16BE(12);
  assert.ok(format < 2 && ppqn > 0 && !(ppqn & 0x8000));
  let cursor = 8 + bytes.readUInt32BE(4), order = 0, endTick = 0;
  const events = [], tempoEvents = [];
  for (let track = 0; track < tracks; track++) {
    assert.equal(bytes.toString('ascii', cursor, cursor + 4), 'MTrk');
    const end = cursor + 8 + bytes.readUInt32BE(cursor + 4);
    cursor += 8;
    let tick = 0, running = null;
    function vlq() {
      let value = 0, byte;
      do { assert.ok(cursor < end); byte = bytes[cursor++]; value = value * 128 + (byte & 127); } while (byte >= 128);
      return value;
    }
    while (cursor < end) {
      tick += vlq();
      let status = bytes[cursor];
      if (status >= 128) { cursor++; if (status < 240) running = status; }
      else { assert.notEqual(running, null); status = running; }
      if (status === 255) {
        const type = bytes[cursor++], length = vlq();
        if (type === 81) { assert.equal(length, 3); tempoEvents.push([tick, bytes.readUIntBE(cursor, 3)]); }
        cursor += length;
      } else if (status === 240 || status === 247) {
        const length = vlq(); cursor += length; running = null;
      } else {
        const kind = status >> 4, channel = status & 15;
        assert.ok(kind >= 8 && kind <= 14);
        const a = bytes[cursor++], b = [12, 13].includes(kind) ? null : bytes[cursor++];
        if (kind === 8 || kind === 9) events.push({tick, order, track, channel, kind, pitch: a, velocity: b});
      }
      endTick = Math.max(endTick, tick); order++;
    }
    assert.equal(cursor, end);
  }
  assert.equal(cursor, bytes.length);
  const pending = new Map(), notes = [];
  for (const e of events.sort((a, b) => a.tick - b.tick || a.order - b.order)) {
    const key = `${e.track}:${e.channel}:${e.pitch}`;
    if (e.kind === 9 && e.velocity > 0) {
      const note = {pitch: e.pitch, velocity: e.velocity, channel: e.channel, startTick: e.tick};
      notes.push(note);
      if (!pending.has(key)) pending.set(key, []);
      pending.get(key).push(note);
    } else {
      const note = pending.get(key)?.shift();
      assert.ok(note, 'Raw MIDI note-off must have a matching occurrence');
      note.endTick = e.tick;
      assert.ok(note.endTick > note.startTick);
    }
  }
  assert.ok([...pending.values()].every(notes => notes.length === 0));
  const tempos = [...new Set(tempoEvents.map(e => e[1]))];
  assert.deepEqual(tempos, [500000]);
  return {notes, endTick, ppqn, tempo: 120};
}

const canonical = rows => rows.map(row => JSON.stringify(row)).sort();
function nativeEvents(score) {
  const events = [], calls = [];
  const handler = new Proxy({}, {get: (_, method) => (...args) => {
    calls.push({method, args});
    if (method === 'addNote') {
      const [track, startTick, duration, pitch, velocity, channel] = args;
      events.push({track, startTick, endTick: startTick + duration, pitch, velocity, channel});
    }
  }});
  new at.midi.MidiFileGenerator(score, new at.Settings(), handler).generate();
  return {events, calls};
}

function nativeAttackHeads(score) {
  return score.tracks.flatMap(track => track.staves.flatMap(staff => staff.bars.flatMap(bar =>
    bar.voices.flatMap(voice => voice.beats.flatMap(beat => beat.notes
      .filter(note => !note.isTieDestination)
      .map(note => ({startTick: beat.absolutePlaybackStart, pitch: note.realValue,
        string: note.string, fret: note.fret})))))));
}

// Capture an actual pre-existing lesson before registering any efficiency
// notes. A scoped velocity override must leave every ordinary Time event intact.
const timeBytes = new Uint8Array(readFileSync(resolve(root, 'public/time.gp')));
const timeScoreBefore = at.importer.ScoreLoader.loadScoreFromBytes(timeBytes, new at.Settings());
const timeNativeBefore = canonical(nativeEvents(timeScoreBefore).events.map(n =>
  [n.track, n.startTick, n.endTick, n.pitch, n.velocity, n.channel]));

for (const fixture of bundle.fixtures) {
  const raw = rawMidi(resolve(root, 'tests/fixtures/fretboard-efficiency', fixture.source_filename));
  const optimized = fixture.versions.find(v => v.id === 'optimized');
  const contacts = new Map(optimized.assignments.map(a => [a.note_id, a]));

  test(`${fixture.id}: actual alphaTab MIDI preserves every raw pitch, velocity, onset, and release`, () => {
    const before = JSON.stringify(fixture);
    const mapping = toFretboardEfficiencyScore(at, fixture);
    const played = nativeEvents(mapping.score).events;
    assert.equal(JSON.stringify(fixture), before, 'Native conversion must not mutate original MIDI or mapping');
    assert.equal(played.length, raw.notes.length, 'No duplicate collapse, tied reattack, or omitted event');
    const row = n => [n.startTick, n.endTick, n.pitch, n.velocity];
    assert.deepEqual(canonical(played.map(row)), canonical(raw.notes.map(row)));
    assert.equal(raw.notes.length, fixture.id === 'cfa029a2' ? 164 : 191);
  });

  test(`${fixture.id}: actual native tablature uses precisely the optimized string contacts`, () => {
    const mapping = toFretboardEfficiencyScore(at, fixture);
    nativeEvents(mapping.score);
    const heads = nativeAttackHeads(mapping.score);
    const expected = fixture.notes.map(note => {
      const contact = contacts.get(note.id);
      return [note.start_tick, note.pitch, 9 - contact.string_number, contact.fret];
    });
    assert.deepEqual(canonical(heads.map(n => [n.startTick, n.pitch, n.string, n.fret])), canonical(expected));
    const lowOpen = heads.filter(n => n.pitch === 28);
    assert.ok(lowOpen.length > 0);
    assert.ok(lowOpen.every(n => n.string === 1 && n.fret === 0), 'E1 must reach trainer stringIndex0');
    const highOpen = heads.filter(n => n.pitch === 64);
    assert.ok(highOpen.length > 0);
    assert.ok(highOpen.every(n => n.string === 8 && n.fret === 0), 'E4 must remain on the highest string');
  });

  test(`${fixture.id}: native score duration is exactly32.25s including the partial final bar`, () => {
    const mapping = toFretboardEfficiencyScore(at, fixture);
    const played = nativeEvents(mapping.score).events;
    const nativeTicks = mapping.score.masterBars.reduce((sum, bar) => sum + bar.calculateDuration(), 0);
    assert.equal(raw.ppqn, 960);
    assert.equal(raw.endTick, 61920);
    assert.equal(mapping.durationTicks, 61920);
    assert.equal(mapping.durationMs, 32250);
    assert.equal(nativeTicks, 61920, 'A full final bar must not pad the score');
    assert.equal(Math.max(...played.map(n => n.endTick)), 61920);
    assert.equal(mapping.score.masterBars.at(-1).calculateDuration(), 480);
  });

  test(`${fixture.id}: seek queries preserve complete held grips and exact release boundaries`, () => {
    const mapping = toFretboardEfficiencyScore(at, fixture);
    const endpoints = [...new Set(raw.notes.flatMap(n => [n.startTick, n.endTick]))].sort((a, b) => a - b);
    const probes = [...endpoints, ...endpoints.slice(1).map((t, i) => (t + endpoints[i]) / 2)];
    for (const tick of probes) {
      const expected = fixture.notes.filter(n => n.start_tick <= tick && tick < n.end_tick)
        .map(n => [n.id, n.pitch, 9 - contacts.get(n.id).string_number, contacts.get(n.id).fret]);
      const actual = efficiencyNotesAtTick(mapping, tick)
        .map(n => [n.note_id, n.pitch, n.string, n.fret]);
      assert.deepEqual(canonical(actual), canonical(expected), `Incorrect active occurrences at tick${tick}`);
    }
    assert.deepEqual(efficiencyNotesAtTick(mapping, 61920), []);
    const held = efficiencyNotesAtTick(mapping, 5760); //3s, halfway through the2–4s chord.
    assert.equal(held.length, 4);
    const duplicate = held.filter(n => n.pitch === 59);
    assert.equal(duplicate.length, 2);
    assert.equal(new Set(duplicate.map(n => n.string)).size, 2);
    assert.equal(new Set(duplicate.map(n => n.note_id)).size, 2);
  });
}

test('existing Time Solo default and0.75× speed option remain in the real lesson HTML', () => {
  const html = readFileSync(resolve(root, 'index.html'), 'utf8');
  assert.match(html, /<input[^>]*value="timeSoloChords"[^>]*checked/);
  assert.match(html, /<option[^>]*value="timeSoloChords"[^>]*selected/);
  assert.match(html, /<option[^>]*value="0\.75"/);
});

test('native efficiency registration preserves every event of the existing Time score', () => {
  // Explicitly register both lessons even when this individual test is selected.
  for (const fixture of bundle.fixtures) toFretboardEfficiencyScore(at, fixture);
  const timeScoreAfter = at.importer.ScoreLoader.loadScoreFromBytes(timeBytes, new at.Settings());
  const after = canonical(nativeEvents(timeScoreAfter).events.map(n =>
    [n.track, n.startTick, n.endTick, n.pitch, n.velocity, n.channel]));
  assert.ok(timeNativeBefore.length > 0);
  assert.deepEqual(after, timeNativeBefore,
    'The exact-velocity registration must not change unrelated Time notes or playback clocks');
});

test('ordinary native MF dynamics remain79 after exact-velocity lesson registration', () => {
  for (const fixture of bundle.fixtures) toFretboardEfficiencyScore(at, fixture);
  const plain = toEventScore(at, {tempo: 120, duration_q: '1', events: [
    {onset_q: '0', members: [{string_number: 8, fret: 0, pitch: 28, duration_q: '1'}]},
  ]});
  assert.equal(nativeEvents(plain).events[0].velocity, 79);
});

// The real native score/MIDI path is tested above. This controllable UI boundary
// deliberately exercises asynchronous event ordering without producing audio.
function playerHarness({initialLesson = 'efficiency', deferTime = false, deferScript = false} = {}) {
  const saved = new Map(['document', 'window', 'fetch', 'requestAnimationFrame', 'cancelAnimationFrame']
    .map(name => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  const elements = new Map(), active = [], positions = [], loaded = [], tracks = [];
  function element() {
    return {value: '0', disabled: false, textContent: '', innerHTML: '', files: null, dataset: {},
      children: [], listeners: new Map(), appendChild(child) { this.children.push(child); },
      addEventListener(name, fn) { if (!this.listeners.has(name)) this.listeners.set(name, []); this.listeners.get(name).push(fn); },
      fire(name, event = {}) { let value; for (const fn of this.listeners.get(name) || []) value = fn(event); return value; }};
  }
  for (const id of ['songPlayerFile', 'songPlayerTrack', 'songPlayerPlayPause', 'songPlayerStop',
    'songPlayerSpeed', 'songPlayerProgress', 'songPlayerCurrentTime', 'songPlayerDuration',
    'songPlayerStatus', 'alphaTabSurface', 'lessonTypeSelect']) elements.set(id, element());
  const get = name => elements.get(`songPlayer${name}`);
  get('Speed').value = '1';
  get('Speed').options = ['0.5', '0.75', '1', '1.25'].map(value => ({value}));
  let lesson = initialLesson, api, script, fetchResolve, fetches = 0;
  const deferredFetch = new Promise(resolve => { fetchResolve = resolve; });
  class Signal {
    listeners = [];
    on(fn) { this.listeners.push(fn); }
    emit(value) { for (const fn of this.listeners) fn(value); }
  }
  class FakeApi {
    constructor() {
      api = this; this.settings = {importer: {}}; this.calls = []; this.rendered = [];
      this._speed = 1; this._tick = 0; this._time = 0;
      for (const name of ['scoreLoaded', 'playerReady', 'playerStateChanged', 'playerPositionChanged',
        'playerFinished', 'activeBeatsChanged', 'error']) this[name] = new Signal();
    }
    get playbackSpeed() { return this._speed; }
    set playbackSpeed(value) { this._speed = value; if (this.score) this.emitPosition(this._tick); }
    get tickPosition() { return this._tick; }
    set tickPosition(value) { this.emitPosition(value); }
    get timePosition() { return this._time; }
    set timePosition(value) { this.emitPosition(value * this._speed / 500 * 960); }
    emitPosition(tick) {
      this._tick = tick; this._time = tick / 960 * 500 / this._speed;
      if (this.score) this.playerPositionChanged.emit({currentTick: tick, currentTime: this._time,
        endTime: this.score.masterBars.reduce((sum, bar) => sum + bar.calculateDuration(), 0) / 960 * 500 / this._speed});
    }
    renderScore(score) {
      this.score = score; this.rendered.push(score); this._tick = 0;
      const generator = new at.midi.MidiFileGenerator(score, new at.Settings(), new Proxy({}, {get: () => () => {}}));
      generator.generate(); this.tickCache = generator.tickLookup;
      this.scoreLoaded.emit(score); this.playerReady.emit();
    }
    load(bytes) { this.renderScore(at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(bytes), new at.Settings())); }
    renderTracks(value) { this.selectedTracks = value; }
    updateSettings() {}
    changeTrackTranspositionPitch() {}
    stop() { this.calls.push('stop'); this._tick = 0; this._time = 0; this.playerStateChanged.emit({state: 0}); }
    play() { this.calls.push('play'); this.playerStateChanged.emit({state: 1}); }
    pause() { this.calls.push('pause'); this.playerStateChanged.emit({state: 0}); }
  }
  const alphaTab = {...at, AlphaTabApi: FakeApi};
  globalThis.document = {getElementById: id => elements.get(id), createElement: () => element(),
    head: {appendChild(value) { script = value; }}};
  globalThis.window = {addEventListener() {}, ...(deferScript ? {} : {alphaTab})};
  globalThis.requestAnimationFrame = () => 1;
  globalThis.cancelAnimationFrame = () => {};
  const timeResponse = {ok: true, arrayBuffer: async () => timeBytes.buffer};
  globalThis.fetch = async url => {
    assert.equal(url, '/Guitar-Learning/time.gp'); fetches++;
    return deferTime ? deferredFetch : timeResponse;
  };
  const player = setupSongPlayer({
    isTimeSoloChordsLesson: () => lesson === 'time',
    isFretboardEfficiencyLesson: () => lesson === 'efficiency',
    timeScoreUrl: '/Guitar-Learning/time.gp',
    onActiveNotes: notes => active.push(notes), onPositionChanged: value => positions.push(value),
    onScoreLoaded: value => loaded.push(value), onTrackChanged: value => tracks.push(value),
  });
  return {player, get, active, positions, loaded, tracks,
    get api() { return api; }, get fetches() { return fetches; },
    setLesson(value) { lesson = value; elements.get('lessonTypeSelect').fire('change'); },
    resolveTime() { fetchResolve(timeResponse); },
    resolveScript() { assert.ok(script); window.alphaTab = alphaTab; script.fire('load'); },
    restore() { for (const [name, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor); else delete globalThis[name];
    }},
  };
}
const flush = () => new Promise(resolve => setImmediate(resolve));

test('existing Song Player loads both native lessons, seeks held duplicates, and keeps0.75× source time', async () => {
  const h = playerHarness();
  try {
    for (const fixture of bundle.fixtures) {
      const mapping = await h.player.loadFretboardEfficiency(fixture, 'optimized');
      assert.equal(h.api.score, mapping.score, 'Existing player must receive the actual native score');
      assert.equal(h.loaded.at(-1).fixtureId, fixture.id);
      assert.equal(h.get('PlayPause').disabled, false);
      assert.deepEqual(h.api.playbackRange, {startTick: 0, endTick: 61920});
      h.player.seekToTick(5760);
      assert.equal(h.api.tickPosition, 5760);
      assert.equal(h.active.at(-1).length, 4);
      assert.equal(new Set(h.active.at(-1).filter(n => n.pitch === 59).map(n => n.string)).size, 2);
      h.get('Speed').value = '0.75'; h.get('Speed').fire('change');
      assert.equal(h.api.playbackSpeed, 0.75);
      assert.equal(h.api.tickPosition, 5760);
      assert.equal(h.get('CurrentTime').textContent, '0:03');
      assert.equal(h.positions.at(-1).tick, 5760);
      assert.ok(Math.abs(h.positions.at(-1).fraction - 3 / 32.25) < 1e-10);
      h.get('PlayPause').fire('click');
      h.api.emitPosition(8160);
      assert.deepEqual(canonical(h.active.at(-1).map(n => [n.pitch, n.string, n.fret])),
        canonical([[28, 1, 0], [35, 2, 0]]));
      h.api.emitPosition(61920);
      h.api.playerFinished.emit();
      assert.deepEqual(h.active.at(-1), []);
      assert.equal(h.get('Progress').value, '1000');
      assert.equal(h.positions.at(-1).tick, 61920);
      assert.match(h.get('PlayPause').textContent, /Play/);
    }
  } finally { h.restore(); }
});

test('delayed position callbacks after pause or stop cannot restore stale highlights; paused seek can', async () => {
  const h = playerHarness();
  try {
    await h.player.loadFretboardEfficiency(bundle.fixtures[0]);
    h.get('PlayPause').fire('click'); h.api.emitPosition(5760);
    assert.equal(h.active.at(-1).length, 4);
    h.get('PlayPause').fire('click');
    assert.deepEqual(h.active.at(-1), []);
    h.api.emitPosition(5760); //Late native position event queued before pause.
    assert.deepEqual(h.active.at(-1), [], 'Paused notes must stay cleared after delayed callbacks');
    h.player.seekToTick(5760);
    assert.equal(h.active.at(-1).length, 4, 'An explicit paused seek must preview the held chord');
    h.get('Stop').fire('click');
    assert.deepEqual(h.active.at(-1), []);
    h.api.emitPosition(5760); //Late position event queued before stop.
    assert.deepEqual(h.active.at(-1), [], 'Stopped notes must stay cleared after delayed callbacks');
    assert.equal(h.get('Progress').value, '0', 'A stale callback must not move the stopped cursor');
  } finally { h.restore(); }
});

test('a delayed bundled Time response cannot replace the newly selected native mapping', async () => {
  const h = playerHarness({initialLesson: 'time', deferTime: true});
  try {
    assert.equal(h.fetches, 1);
    h.setLesson('efficiency');
    const mapping = await h.player.loadFretboardEfficiency(bundle.fixtures[1]);
    h.resolveTime(); await flush();
    assert.equal(h.api.score, mapping.score);
    assert.equal(h.loaded.at(-1).fixtureId, 'da80eca9');
    assert.equal(h.api.rendered.length, 1, 'An obsolete fetch must not render another score');
  } finally { h.restore(); }
});

test('returning from mapping restores the existing Time score and its solo transport', async () => {
  const h = playerHarness({initialLesson: 'time'});
  try {
    await flush();
    const originalTime = h.api.score;
    assert.equal(originalTime.title, 'Time');
    assert.ok(h.api.playbackRange.startTick > 0);
    h.setLesson('efficiency');
    await h.player.loadFretboardEfficiency(bundle.fixtures[0]);
    h.get('Speed').value = '0.75'; h.get('Speed').fire('change');
    h.player.seekToTick(5760);
    h.setLesson('time'); await flush();
    assert.equal(h.api.score, originalTime, 'Restore the same existing score instead of reinterpreting a mapping as Time');
    assert.ok(h.api.playbackRange.startTick > 0);
    assert.equal(h.api.playbackSpeed, 0.75);
    assert.equal(h.get('CurrentTime').textContent, '0:00');
    assert.equal(h.get('Progress').value, '0');
    assert.deepEqual(h.active.at(-1), []);
    assert.equal(h.fetches, 1, 'Restoring an existing Time score needs no second download');
  } finally { h.restore(); }
});

test('leaving before the native script is ready cancels a pending mapping load', async () => {
  const h = playerHarness({deferScript: true});
  try {
    const loading = h.player.loadFretboardEfficiency(bundle.fixtures[0]);
    h.player.clearFretboardEfficiency();
    h.resolveScript();
    await assert.rejects(loading, /replaced|closed/);
    assert.equal(h.api.rendered.length, 0);
    assert.equal(h.loaded.length, 0);
  } finally { h.restore(); }
});
