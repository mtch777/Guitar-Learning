import assert from 'node:assert/strict';
import test from 'node:test';
import { createTimeSoloWindow } from '../src/time-solo-transport.js';

test('solo window follows score bars and integrates tempo changes', () => {
  const score = { tempo: 120, masterBars: Array.from({ length: 144 }, (_, i) => i) };
  const tickCache = {
    getMasterBar: index => ({ start: index * 960, end: (index + 1) * 960 }),
    masterBars: [
      { tempoChanges: [{ tick: 0, tempo: 120 }] },
      { tempoChanges: [{ tick: 94 * 960, tempo: 60 }] }
    ]
  };
  const window = createTimeSoloWindow(score, tickCache);
  assert.equal(window.startTick, 93 * 960);
  assert.equal(window.endTick, 143 * 960);
  assert.equal(window.startMs, 93 * 500);
  assert.equal(window.endMs, 94 * 500 + 49 * 1000);
  assert.equal(window.durationMs, 500 + 49 * 1000);
  assert.equal(window.tickToMs(95 * 960), 94 * 500 + 1000);
  assert.equal(window.msToTick(94 * 500 + 1000), 95 * 960);
  assert.equal(createTimeSoloWindow({ masterBars: [0] }, tickCache), null);
});

test('player clips Time Solo with chords and always uses solo-relative controls', async () => {
  const { setupSongPlayer } = await import('../src/song-player.js');
  const elements = new Map();
  const makeElement = () => ({
    value: '0', disabled: false, textContent: '', innerHTML: '', files: null,
    listeners: new Map(), appendChild() {},
    addEventListener(name, fn) { this.listeners.set(name, fn); },
    fire(name, event = {}) { return this.listeners.get(name)?.(event); }
  });
  for (const id of [
    'songPlayerFile', 'songPlayerTrack', 'songPlayerPlayPause',
    'songPlayerStop', 'songPlayerSpeed', 'songPlayerProgress',
    'songPlayerCurrentTime', 'songPlayerDuration', 'songPlayerStatus',
    'alphaTabSurface', 'lessonTypeSelect'
  ]) elements.set(id, makeElement());
  elements.get('songPlayerSpeed').options =
    ['0.25', '0.5', '0.75', '0.9', '1', '1.1', '1.25', '1.5', '2']
      .map(value => ({ value }));
  elements.get('songPlayerSpeed').value = '1';
  const keyListeners = [];
  globalThis.document = {
    getElementById: id => elements.get(id),
    createElement: () => makeElement()
  };
  globalThis.window = {
    addEventListener: (name, fn) => { if (name === 'keydown') keyListeners.push(fn); }
  };
  const score = {
    tempo: 120, masterBars: Array.from({ length: 144 }, (_, i) => i),
    tracks: [{ index: 0, name: 'Guitar Solo', staves: [{ stringTuning: { tunings: [40, 45, 50, 55, 59, 64] }, bars: [] }] }]
  };
  let api;
  class FakeApi {
    constructor() {
      api = this;
      for (const name of ['scoreLoaded', 'playerReady', 'playerStateChanged', 'playerPositionChanged', 'playerFinished', 'activeBeatsChanged', 'error']) {
        this[name] = { on: fn => { this[name].emit = fn; } };
      }
      this.settings = { importer: {} };
      this.tickCache = {
        getMasterBar: i => ({ start: i * 960, end: (i + 1) * 960 }),
        masterBars: [{ tempoChanges: [{ tick: 0, tempo: 120 }] }]
      };
      this.calls = [];
    }
    get playbackSpeed() { return this._speed || 1; }
    set playbackSpeed(speed) {
      const oldSpeed = this.playbackSpeed;
      this._speed = speed;
      // Match alphaTab: changing speed scales reported milliseconds while
      // leaving the same musical tick selected.
      if (this._tickPosition != null) {
        this.timePosition *= oldSpeed / speed;
        this.playerPositionChanged.emit({ currentTime: this.timePosition,
          endTime: 72000 / speed, currentTick: this._tickPosition });
      }
    }
    get tickPosition() { return this._tickPosition; }
    set tickPosition(tick) {
      this._tickPosition = tick;
      this.timePosition = tick / 960 * 500 / this.playbackSpeed;
    }
    changeTrackTranspositionPitch() {}
    renderTracks() {}
    updateSettings() {}
    stop() { this.calls.push('stop'); }
    play() { this.calls.push('play'); }
    pause() { this.calls.push('pause'); }
    load(buffer) { this.loadedBuffer = buffer; this.scoreLoaded.emit(score); this.playerReady.emit(); }
  }
  window.alphaTab = { AlphaTabApi: FakeApi };
  let soloLesson = true;
  const bundledBuffer = new ArrayBuffer(7);
  globalThis.fetch = async url => {
    assert.equal(url, '/Guitar-Learning/time.gp');
    return { ok: true, arrayBuffer: async () => bundledBuffer };
  };
  const player = setupSongPlayer({ isTimeSoloChordsLesson: () => soloLesson,
    timeScoreUrl: '/Guitar-Learning/time.gp' });
  const get = id => elements.get(`songPlayer${id}`);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(api.loadedBuffer, bundledBuffer, 'public Time score loads without an upload');
  assert.equal(get('Track').value, '0');
  get('File').files = [{ name: 'time.gp', arrayBuffer: async () => new ArrayBuffer(0) }];
  await get('File').fire('change');
  assert.deepEqual(api.playbackRange, { startTick: 93 * 960, endTick: 143 * 960 });
  assert.equal(api.tickPosition, 93 * 960);
  assert.equal(get('CurrentTime').textContent, '0:00');
  assert.equal(get('Duration').textContent, '0:25');
  for (const speed of ['0.25', '0.5', '0.75', '0.9', '1', '1.1', '1.25', '1.5', '2']) {
    get('Speed').value = speed;
    get('Speed').fire('change');
    assert.equal(get('CurrentTime').textContent, '0:00', `${speed}× before Play`);
    assert.equal(get('Progress').value, '0', `${speed}× before Play`);
    get('PlayPause').fire('click');
    assert.equal(api.calls.at(-1), 'play', `${speed}× starts playback`);
    get('Stop').fire('click');
    assert.equal(api.tickPosition, 93 * 960, `${speed}× Stop resets to solo start`);
  }
  get('Speed').value = '0.75';
  get('Speed').fire('change');
  assert.equal(get('CurrentTime').textContent, '0:00');
  assert.equal(get('Progress').value, '0');
  get('PlayPause').fire('click');
  assert.equal(api.calls.at(-1), 'play');

  api.playerPositionChanged.emit({ currentTime: 48500 / 0.75,
    endTime: 72000 / 0.75, currentTick: 97 * 960 });
  assert.equal(get('CurrentTime').textContent, '0:02');
  assert.equal(get('Progress').value, '80');
  get('Progress').value = '500';
  get('Progress').fire('change');
  assert.equal(api.tickPosition, 118 * 960);
  player.seekToTick(103 * 960);
  assert.equal(api.tickPosition, 103 * 960, 'chord timeline seeks by score tick');
  assert.equal(get('CurrentTime').textContent, '0:05');
  player.seekToTick(118 * 960);

  const key = code => {
    const event = { code, repeat: false, prevented: false, stopped: false,
      preventDefault() { this.prevented = true; }, stopPropagation() { this.stopped = true; } };
    keyListeners[0](event);
    assert.equal(event.prevented, true);
    assert.equal(event.stopped, true);
  };
  key('ArrowLeft');
  assert.equal(api.tickPosition, 108 * 960);
  key('ArrowRight');
  assert.equal(api.tickPosition, 118 * 960);
  globalThis.requestAnimationFrame = () => 1;
  globalThis.cancelAnimationFrame = () => {};
  api.playerStateChanged.emit({ state: 1 });
  get('Speed').value = '0.5';
  get('Speed').fire('change');
  assert.equal(get('CurrentTime').textContent, '0:13');
  assert.equal(api.tickPosition, 118 * 960);
  key('ArrowUp');
  assert.equal(get('Speed').value, '0.75');
  assert.equal(api.playbackSpeed, 0.75);
  assert.equal(api.tickPosition, 118 * 960);
  key('ArrowDown');
  assert.equal(get('Speed').value, '0.5');
  assert.equal(api.playbackSpeed, 0.5);
  key('Space');
  assert.equal(api.calls.at(-1), 'pause');
  api.playerStateChanged.emit({ state: 0 });
  key('Space');
  assert.equal(api.calls.at(-1), 'play');
  get('Stop').fire('click');
  assert.equal(api.tickPosition, 93 * 960);
  assert.equal(get('CurrentTime').textContent, '0:00');
  soloLesson = false;
  elements.get('lessonTypeSelect').fire('change');
  assert.equal(api.playbackRange, null);
  get('File').files = [{ name: 'another.gp', arrayBuffer: async () => new ArrayBuffer(0) }];
  await get('File').fire('change');
  assert.equal(api.playbackRange, null);
  delete globalThis.document;
  delete globalThis.window;
  delete globalThis.requestAnimationFrame;
  delete globalThis.cancelAnimationFrame;
  delete globalThis.fetch;
});
