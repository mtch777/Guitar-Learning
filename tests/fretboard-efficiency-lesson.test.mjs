import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
import {
  toFretboardEfficiencyScore, efficiencyNotesAtTick,
} from '../src/fretboard-efficiency-score.js';
import {toEventScore} from '../src/riff-event-score.js';
import {setupSongPlayer} from '../src/song-player.js';

// Mandatory native dependency. CI installs this exact package before running
// tests/*.test.mjs; an unavailable native player must fail, never silently skip.
const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const nativeRoot = resolve(root, '.local/qa/node_modules/@coderline/alphatab');
// Exercise the exact browser UMD distribution used by the trainer. The minified
// distribution removes the private bridge methods even at this same version;
// checking only the separate .mjs build previously missed that live failure.
const nativePath = resolve(nativeRoot, 'dist/alphaTab.js');
assert.ok(existsSync(nativePath), 'Install pinned @coderline/alphatab@1.8.4 in .local/qa before native lesson QA');
assert.equal(JSON.parse(readFileSync(resolve(nativeRoot, 'package.json'), 'utf8')).version, '1.8.4');
const at = createRequire(import.meta.url)(nativePath);
const bundle = JSON.parse(readFileSync(resolve(root, 'public/data/fretboard-efficiency-fixtures.json'), 'utf8'));
const verifiedBrowserUrl = 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/alphaTab.js';
const frozenSources = {
  cfa029a2: {notes: 164, ppqn: 960, endTick: 61920, durationMs: 32250},
  da80eca9: {notes: 191, ppqn: 960, endTick: 61920, durationMs: 32250},
  c5a35486: {notes: 241, ppqn: 96, endTick: 4608, durationMs: 24000,
    sha256: '5fa3e52d30a27b3568c7303f47011cb5aaa9777ac2a584ea31e7f797d522ca77'},
  '186bfd78': {notes: 113, ppqn: 96, endTick: 2016, durationMs: 10500,
    sha256: '16fb521d0286d40a8afc9db227282f47e1f7fd4d9296a162ec1606c60f8fac77'},
};
const originalFixtureIds = new Set(['cfa029a2', 'da80eca9']);
const nativeTick = (sourceTick, ppqn) => {
  const tick = sourceTick * 960 / ppqn;
  assert.ok(Number.isSafeInteger(tick), 'Source clocks must fit native ticks exactly, without rounding');
  return tick;
};

test('Song Player loads the exact tested browser distribution and its required native bridge', () => {
  const source = readFileSync(resolve(root, 'src/song-player.js'), 'utf8');
  const declarations = ['ALPHATAB_VERSION', 'ALPHATAB_ROOT', 'ALPHATAB_SCRIPT'].map(name => {
    const declaration = source.match(new RegExp(`const\\s+${name}\\s*=\\s*[^;]+;`));
    assert.ok(declaration, `Locate the actual ${name} loader declaration`);
    return declaration[0];
  });
  const configuredUrl = vm.runInNewContext(`${declarations.join('\n')}\nALPHATAB_SCRIPT`);
  assert.equal(configuredUrl, verifiedBrowserUrl,
    'The browser must load the same version and distribution that passed native QA');
  assert.equal(typeof at.midi.MidiFileGenerator.prototype._generateSlide, 'function');
  assert.equal(typeof at.midi.MidiFileGenerator._getNoteVelocity, 'function');
});

/** Independent standard MIDI reader: no adapter or fixture-derived clocks. */
function rawMidi(path) {
  const bytes = readFileSync(path);
  assert.equal(bytes.toString('ascii', 0, 4), 'MThd');
  const format = bytes.readUInt16BE(8), tracks = bytes.readUInt16BE(10), ppqn = bytes.readUInt16BE(12);
  assert.ok(format < 2 && ppqn > 0 && !(ppqn & 0x8000));
  let cursor = 8 + bytes.readUInt32BE(4), order = 0, endTick = 0;
  const events = [], tempoEvents = [], timeSignatures = [], unsupportedPerformanceEvents = [];
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
        if (type === 88) {
          assert.equal(length, 4);
          timeSignatures.push([tick, bytes[cursor], 2 ** bytes[cursor + 1]]);
        }
        cursor += length;
      } else if (status === 240 || status === 247) {
        unsupportedPerformanceEvents.push({tick, status});
        const length = vlq(); cursor += length; running = null;
      } else {
        const kind = status >> 4, channel = status & 15;
        assert.ok(kind >= 8 && kind <= 14);
        const a = bytes[cursor++], b = [12, 13].includes(kind) ? null : bytes[cursor++];
        if (kind === 8 || kind === 9) events.push({tick, order, track, channel, kind, pitch: a, velocity: b});
        else unsupportedPerformanceEvents.push({tick, kind, channel, a, b});
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
  // MIDI without a tempo event has an explicit standard default of500000µs/q.
  // Record performance messages instead of silently discarding a future source
  // requiring controller, program, bend, SysEx, or changing-tempo support.
  assert.deepEqual(unsupportedPerformanceEvents, [], 'Unrepresented source performance messages require explicit support');
  assert.ok(timeSignatures.every(([tick, numerator, denominator]) => tick === 0 && numerator === 4 && denominator === 4),
    'The native fixture notation currently requires a constant4/4 source');
  const tempoMap = [...new Map([[0, 500000], ...tempoEvents.sort((a, b) => a[0] - b[0])]).entries()]
    .sort((a, b) => a[0] - b[0]);
  const microsecondsPerQuarter = tempoMap[0][1];
  assert.ok(tempoMap.every(([, value]) => value === microsecondsPerQuarter),
    'A changing source tempo map must not be replaced by one tempo');
  return {notes, endTick, ppqn, tempo: 60000000 / microsecondsPerQuarter,
    durationMs: endTick / ppqn * microsecondsPerQuarter / 1000,
    microsecondsPerQuarter, tempoEvents, sha256: createHash('sha256').update(bytes).digest('hex')};
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
const rawSources = new Map(bundle.fixtures.map(fixture => [fixture.id,
  rawMidi(resolve(root, 'tests/fixtures/fretboard-efficiency', fixture.source_filename))]));

test('the three frozen source fixtures remain present with their original clocks and counts', () => {
  assert.deepEqual(bundle.fixtures.map(f => f.id).sort(), Object.keys(frozenSources).sort());
  for (const fixture of bundle.fixtures) {
    const raw = rawSources.get(fixture.id), frozen = frozenSources[fixture.id];
    assert.deepEqual(fixture.versions.map(v => v.id).sort(), ['greedy', 'optimized', 'strumPick'],
      'Every frozen source must retain both existing profiles and the separate picking profile');
    assert.equal(raw.notes.length, frozen.notes);
    assert.equal(raw.ppqn, frozen.ppqn);
    assert.equal(raw.endTick, frozen.endTick);
    assert.equal(raw.durationMs, frozen.durationMs);
    assert.equal(fixture.source_sha256, raw.sha256);
    if (frozen.sha256) assert.equal(raw.sha256, frozen.sha256);
    assert.equal(fixture.ticks_per_beat, raw.ppqn);
    assert.equal(fixture.tempo_bpm, raw.tempo);
  }
});

for (const fixture of bundle.fixtures) {
  const raw = rawSources.get(fixture.id);
  const toNative = tick => nativeTick(tick, raw.ppqn);
  const nativeEnd = toNative(raw.endTick);

  test(`${fixture.id}: actual alphaTab MIDI preserves every raw pitch, velocity, onset, and release`, () => {
    const before = JSON.stringify(fixture);
    for (const version of fixture.versions) {
      const mapping = toFretboardEfficiencyScore(at, fixture, version.id);
      const {events: played, calls} = nativeEvents(mapping.score);
      assert.equal(JSON.stringify(fixture), before, 'Native conversion must not mutate original MIDI or mapping');
      assert.equal(played.length, raw.notes.length, 'No duplicate collapse, tied reattack, or omitted event');
      assert.deepEqual(canonical(played.map(n => [n.startTick, n.endTick, n.pitch, n.velocity, n.channel])),
        canonical(raw.notes.map(n => [toNative(n.startTick), toNative(n.endTick), n.pitch, n.velocity, n.channel])));
      assert.equal(mapping.sourceTicksPerBeat, raw.ppqn);
      assert.equal(mapping.ticksPerBeat, 960);
      const tempos = calls.filter(call => call.method === 'addTempo').map(call => call.args[1]);
      assert.ok(tempos.length > 0 && tempos.every(value => value === raw.tempo));
    }
  });

  for (const version of fixture.versions) {
    const contacts = new Map(version.assignments.map(a => [a.note_id, a]));

    test(`${fixture.id}/${version.id}: actual native tablature uses precisely the selected string contacts`, () => {
      const mapping = toFretboardEfficiencyScore(at, fixture, version.id);
      nativeEvents(mapping.score);
      const heads = nativeAttackHeads(mapping.score);
      const expected = fixture.notes.map(note => {
        const contact = contacts.get(note.id);
        return [toNative(note.start_tick), note.pitch, 9 - contact.string_number, contact.fret];
      });
      assert.deepEqual(canonical(heads.map(n => [n.startTick, n.pitch, n.string, n.fret])), canonical(expected));
      const lowOpen = heads.filter(n => n.pitch === 28);
      assert.equal(lowOpen.length, raw.notes.filter(note => note.pitch === 28).length);
      assert.ok(lowOpen.length > 0);
      assert.ok(lowOpen.every(n => n.string === 1 && n.fret === 0), 'E1 must reach trainer stringIndex0');
      const highOpen = heads.filter(n => n.pitch === 64);
      assert.ok(highOpen.length > 0);
      if (originalFixtureIds.has(fixture.id)) {
        assert.ok(highOpen.every(n => n.string === 8 && n.fret === 0), 'Original A/B E4 remains on the highest open string');
      }
    });

    test(`${fixture.id}/${version.id}: native score preserves the raw end clock, tempo, and any surrounding rests`, () => {
      const mapping = toFretboardEfficiencyScore(at, fixture, version.id);
      const played = nativeEvents(mapping.score).events;
      const nativeTicks = mapping.score.masterBars.reduce((sum, bar) => sum + bar.calculateDuration(), 0);
      assert.equal(mapping.durationTicks, nativeEnd);
      assert.equal(mapping.durationMs, raw.durationMs);
      assert.equal(nativeTicks, nativeEnd, 'Notation must not pad or truncate the source end-of-track');
      assert.equal(Math.min(...played.map(n => n.startTick)), toNative(Math.min(...raw.notes.map(n => n.startTick))));
      assert.equal(Math.max(...played.map(n => n.endTick)), toNative(Math.max(...raw.notes.map(n => n.endTick))));
      assert.equal(mapping.score.masterBars.at(-1).calculateDuration(), nativeEnd % 3840 || 3840);
    });

    test(`${fixture.id}/${version.id}: seek queries preserve complete held grips and exact release boundaries`, () => {
      const mapping = toFretboardEfficiencyScore(at, fixture, version.id);
      const endpoints = [...new Set([0, nativeEnd, ...raw.notes.flatMap(n => [toNative(n.startTick), toNative(n.endTick)])])]
        .sort((a, b) => a - b);
      const probes = [...endpoints, ...endpoints.slice(1).map((t, i) => (t + endpoints[i]) / 2)];
      for (const tick of probes) {
        const expected = fixture.notes.filter(n => toNative(n.start_tick) <= tick && tick < toNative(n.end_tick))
          .map(n => [n.id, n.pitch, 9 - contacts.get(n.id).string_number, contacts.get(n.id).fret]);
        const actual = efficiencyNotesAtTick(mapping, tick)
          .map(n => [n.note_id, n.pitch, n.string, n.fret]);
        assert.deepEqual(canonical(actual), canonical(expected), `Incorrect active occurrences at tick${tick}`);
      }
      assert.deepEqual(efficiencyNotesAtTick(mapping, nativeEnd), []);
      if (originalFixtureIds.has(fixture.id)) {
        const held = efficiencyNotesAtTick(mapping, 5760); //3s, halfway through the2–4s chord.
        assert.equal(held.length, 4);
        const duplicate = held.filter(n => n.pitch === 59);
        assert.equal(duplicate.length, 2);
        assert.equal(new Set(duplicate.map(n => n.string)).size, 2);
        assert.equal(new Set(duplicate.map(n => n.note_id)).size, 2);
      }
    });
  }
}

test('non-default PPQN preserves leading and trailing rests and refuses a nonrepresentable clock', () => {
  const fixture = {id: 'rest-clock-test', label: 'Exact rest clock', ticks_per_beat: 96,
    tempo_bpm: 120, duration_ticks: 192,
    notes: [{id: 0, pitch: 28, velocity: 74, channel: 0, start_tick: 48, end_tick: 96}],
    versions: [{id: 'optimized', assignments: [{note_id: 0, string_number: 8, fret: 0}]}]};
  const mapping = toFretboardEfficiencyScore(at, fixture);
  assert.equal(mapping.durationTicks, 1920);
  assert.equal(mapping.durationMs, 1000);
  assert.deepEqual(nativeEvents(mapping.score).events.map(n => [n.startTick, n.endTick, n.pitch, n.velocity]),
    [[480, 960, 28, 74]]);
  for (const tick of [0, 479, 960, 1440, 1920]) assert.deepEqual(efficiencyNotesAtTick(mapping, tick), []);
  assert.equal(efficiencyNotesAtTick(mapping, 480).length, 1);
  assert.equal(efficiencyNotesAtTick(mapping, 959).length, 1);
  const unsupported = structuredClone(fixture);
  unsupported.ticks_per_beat = 100;
  unsupported.duration_ticks = 200;
  unsupported.notes[0].start_tick = 1;
  unsupported.notes[0].end_tick = 101;
  assert.throws(() => toFretboardEfficiencyScore(at, unsupported), /exact native tick grid/);
});

test('existing Time Solo default and0.75× speed option remain in the real lesson HTML', () => {
  const html = readFileSync(resolve(root, 'index.html'), 'utf8');
  assert.match(html, /<input[^>]*value="timeSoloChords"[^>]*checked/);
  assert.match(html, /<option[^>]*value="timeSoloChords"[^>]*selected/);
  assert.match(html, /<option[^>]*value="0\.75"/);
});

test('native efficiency registration preserves every event of the existing Time score', () => {
  // Explicitly register every lesson even when this individual test is selected.
  for (const fixture of bundle.fixtures) {
    for (const version of fixture.versions) toFretboardEfficiencyScore(at, fixture, version.id);
  }
  const timeScoreAfter = at.importer.ScoreLoader.loadScoreFromBytes(timeBytes, new at.Settings());
  const after = canonical(nativeEvents(timeScoreAfter).events.map(n =>
    [n.track, n.startTick, n.endTick, n.pitch, n.velocity, n.channel]));
  assert.equal(timeNativeBefore.length, 5472);
  assert.deepEqual(after, timeNativeBefore,
    'The exact-velocity registration must not change unrelated Time notes or playback clocks');
});

test('ordinary native MF dynamics remain79 after exact-velocity lesson registration', () => {
  for (const fixture of bundle.fixtures) {
    for (const version of fixture.versions) toFretboardEfficiencyScore(at, fixture, version.id);
  }
  const plain = toEventScore(at, {tempo: 120, duration_q: '1', events: [
    {onset_q: '0', members: [{string_number: 8, fret: 0, pitch: 28, duration_q: '1'}]},
  ]});
  assert.equal(nativeEvents(plain).events[0].velocity, 79);
});

// The real native score/MIDI path is tested above. This controllable UI boundary
// deliberately exercises asynchronous event ordering without producing audio.
function playerHarness({initialLesson = 'efficiency', deferTime = false, deferScript = false,
  setupPlayer = setupSongPlayer} = {}) {
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
    constructor(surface, settings) {
      api = this; this.settings = {importer: {}}; this.calls = []; this.rendered = [];
      this.initialScriptFile = settings?.core?.scriptFile;
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
  const player = setupPlayer({
    isTimeSoloChordsLesson: () => lesson === 'time',
    isFretboardEfficiencyLesson: () => lesson === 'efficiency',
    timeScoreUrl: '/Guitar-Learning/time.gp',
    onActiveNotes: notes => active.push(notes), onPositionChanged: value => positions.push(value),
    onScoreLoaded: value => loaded.push(value), onTrackChanged: value => tracks.push(value),
  });
  return {player, get, active, positions, loaded, tracks,
    get api() { return api; }, get fetches() { return fetches; },
    get requestedScriptUrl() { return script?.src; },
    setLesson(value) { lesson = value; elements.get('lessonTypeSelect').fire('change'); },
    resolveTime() { fetchResolve(timeResponse); },
    resolveScript() { assert.ok(script); window.alphaTab = alphaTab; script.fire('load'); },
    restore() { for (const [name, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor); else delete globalThis[name];
    }},
  };
}
const flush = () => new Promise(resolve => setImmediate(resolve));

test('existing Song Player loads every native lesson and profile, seeks source holds, and keeps0.75× source time', async () => {
  const h = playerHarness();
  try {
    for (const fixture of bundle.fixtures) {
      for (const version of fixture.versions) {
        const raw = rawSources.get(fixture.id);
        const toNative = tick => nativeTick(tick, raw.ppqn), nativeEnd = toNative(raw.endTick);
        const contacts = new Map(version.assignments.map(a => [a.note_id, a]));
        const attacks = [...new Set(raw.notes.map(n => n.startTick))].sort((a, b) => a - b);
        const heldAttack = attacks.find(tick => raw.notes.some(n => n.startTick < tick && tick < n.endTick)) ?? attacks[0];
        const nextBoundary = Math.min(...raw.notes.flatMap(n => [n.startTick, n.endTick]).filter(tick => tick > heldAttack));
        const seekTick = originalFixtureIds.has(fixture.id) ? 5760 : toNative((heldAttack + nextBoundary) / 2);
        const expectedHeld = fixture.notes.filter(n => toNative(n.start_tick) <= seekTick && seekTick < toNative(n.end_tick))
          .map(n => [n.id, n.pitch, 9 - contacts.get(n.id).string_number, contacts.get(n.id).fret]);
        const mapping = await h.player.loadFretboardEfficiency(fixture, version.id);
        assert.equal(h.api.score, mapping.score, 'Existing player must receive the actual native score');
        assert.equal(h.loaded.at(-1).fixtureId, fixture.id);
        assert.equal(h.loaded.at(-1).versionId, version.id);
        assert.equal(h.get('Progress').dataset.versionId, version.id);
        assert.equal(h.get('PlayPause').disabled, false);
        assert.deepEqual(h.api.playbackRange, {startTick: 0, endTick: nativeEnd});
        h.player.seekToTick(seekTick);
        assert.equal(h.api.tickPosition, seekTick);
        assert.deepEqual(canonical(h.active.at(-1).map(n => [n.note_id, n.pitch, n.string, n.fret])), canonical(expectedHeld));
        if (originalFixtureIds.has(fixture.id)) {
          assert.equal(h.active.at(-1).length, 4);
          assert.equal(new Set(h.active.at(-1).filter(n => n.pitch === 59).map(n => n.string)).size, 2);
        }
        h.get('Speed').value = '0.75'; h.get('Speed').fire('change');
        assert.equal(h.api.playbackSpeed, 0.75);
        assert.equal(h.api.tickPosition, seekTick);
        const elapsedSeconds = Math.round(seekTick / 960 * raw.microsecondsPerQuarter / 1000000);
        assert.equal(h.get('CurrentTime').textContent,
          `${Math.floor(elapsedSeconds / 60)}:${String(elapsedSeconds % 60).padStart(2, '0')}`);
        assert.equal(h.positions.at(-1).tick, seekTick);
        assert.ok(Math.abs(h.positions.at(-1).fraction - seekTick / nativeEnd) < 1e-10);
        h.get('PlayPause').fire('click');
        const lowPower = raw.notes.find(n => n.pitch === 28 && raw.notes.some(other =>
          other.pitch === 35 && other.startTick <= n.startTick && n.startTick < other.endTick));
        assert.ok(lowPower, 'Retain the source low E/B dyad playback check for every fixture');
        h.api.emitPosition(toNative(lowPower.startTick));
        assert.deepEqual(canonical(h.active.at(-1).map(n => [n.pitch, n.string, n.fret])),
          canonical([[28, 1, 0], [35, 2, 0]]));
        h.api.emitPosition(nativeEnd);
        h.api.playerFinished.emit();
        assert.deepEqual(h.active.at(-1), []);
        assert.equal(h.get('Progress').value, '1000');
        assert.equal(h.positions.at(-1).tick, nativeEnd);
        assert.match(h.get('PlayPause').textContent, /Play/);
      }
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

test('leaving Time while the native script loads cannot overwrite another lesson tuning', async () => {
  // A separate module instance gives this real loader its own pending script.
  // The score download has already finished; this is the later async boundary
  // that the fetch-only cancellation regression cannot exercise.
  const isolated = await import('../src/song-player.js?qa-deferred-time-script');
  const h = playerHarness({initialLesson: 'time', deferScript: true,
    setupPlayer: isolated.setupSongPlayer});
  try {
    await flush();
    assert.equal(h.fetches, 1);
    assert.equal(h.requestedScriptUrl, verifiedBrowserUrl);
    assert.equal(h.api, undefined, 'Hold the native script after Time has downloaded');
    h.setLesson('intervals');
    h.resolveScript(); await flush();
    assert.equal(h.api.rendered.length, 0, 'An obsolete Time load must not render after leaving its lesson');
    assert.equal(h.tracks.length, 0, 'Late Time tuning must not overwrite the active quiz tuning');
    assert.equal(h.loaded.length, 0);

    h.setLesson('time'); await flush();
    assert.equal(h.api.score.title, 'Time', 'Returning must still load the actual Time score');
    assert.equal(h.api.rendered.length, 1);
    assert.equal(h.fetches, 2);
    assert.ok(h.api.playbackRange.startTick > 0);
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
    assert.equal(h.requestedScriptUrl, verifiedBrowserUrl, 'The dynamically inserted browser script must be the tested bundle');
    h.player.clearFretboardEfficiency();
    h.resolveScript();
    await assert.rejects(loading, /replaced|closed/);
    assert.equal(h.api.initialScriptFile, verifiedBrowserUrl, 'Native player workers must use the same tested distribution');
    assert.equal(h.api.rendered.length, 0);
    assert.equal(h.loaded.length, 0);
  } finally { h.restore(); }
});
