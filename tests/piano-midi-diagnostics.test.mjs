import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../public/piano/shared/midi.js', import.meta.url), 'utf8');
const preferenceKey = 'practiceAppMidiEnabledV1';
const failureKey = 'practiceAppMidiFailuresV1';
const timestamp = '2026-11-18T08:00:00.000Z';

function boot(storage = new Map(), options = {}) {
  const events = [];
  const logs = [];
  const flags = {readBlocked: false, writeBlocked: false, consoleBlocked: false, ...options};
  class FixedDate extends Date { constructor() { super(timestamp); } }
  const window = {
    location: {pathname: '/Guitar-Learning/piano/theory/circle-of-fifths/accidentals-count/', search: '?private=value', hash: '#private'},
    dispatchEvent: event => events.push(event)
  };
  const context = vm.createContext({
    window,
    document: {querySelector: selector => {
      assert.equal(selector, 'meta[name="build-version"]');
      return {getAttribute: name => { assert.equal(name, 'content'); return '2155bafd6ded'; }};
    }},
    localStorage: {
      getItem: key => { if (flags.readBlocked) throw new Error('Storage read blocked'); return storage.get(key) ?? null; },
      setItem: (key, value) => { if (flags.writeBlocked) throw new Error('Storage write blocked'); storage.set(key, value); }
    },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    console: {error: (...args) => { if (flags.consoleBlocked) throw new Error('Console blocked'); logs.push(args); }},
    Date: FixedDate
  });
  vm.runInContext(source, context, {filename: 'shared/midi.js'});
  return {api: window.PracticeMIDI, events, logs, storage, flags};
}

const plain = value => JSON.parse(JSON.stringify(value));

test('MIDI preference persists and retains the existing state event', () => {
  const ui = boot();
  assert.equal(ui.api.isEnabled(), false);
  ui.api.setEnabled(true);
  assert.equal(ui.storage.get(preferenceKey), 'true');
  assert.equal(ui.api.isEnabled(), true);
  assert.deepEqual(plain(ui.events[0]), {type: 'practice-midi-state', detail: {enabled: true}});
  assert.equal(boot(ui.storage).api.isEnabled(), true);
  ui.api.setEnabled(false);
  assert.equal(ui.api.isEnabled(), false);
  assert.equal(ui.storage.get(preferenceKey), 'false');
});

test('blocked preference reads and writes preserve the in-memory choice', () => {
  const ui = boot(new Map([[preferenceKey, 'false']]), {readBlocked: true, writeBlocked: true});
  assert.equal(ui.api.isEnabled(), false);
  assert.doesNotThrow(() => ui.api.setEnabled(true));
  assert.equal(ui.api.isEnabled(), true);
  // A stale persisted false must not overwrite the choice after an unsuccessful save.
  ui.flags.readBlocked = false;
  assert.equal(ui.api.isEnabled(), true);
  ui.api.setEnabled(false);
  assert.equal(ui.api.isEnabled(), false);
  assert.equal(ui.events.length, 2);
  assert.equal(ui.logs.length, 0);
  assert.equal(ui.api.getFailureLog().length, 0);
  ui.flags.writeBlocked = false;
  ui.api.setEnabled(true);
  assert.equal(ui.storage.get(preferenceKey), 'true');
});

test('a read failure after a stored preference was loaded retains that preference', () => {
  const ui = boot(new Map([[preferenceKey, 'true']]));
  assert.equal(ui.api.isEnabled(), true);
  ui.flags.readBlocked = true;
  assert.equal(ui.api.isEnabled(), true);
});

test('exact failure details distinguish access denial from later setup failure', () => {
  const ui = boot();
  const denied = Object.assign(new Error('Permission denied by the browser'), {name: 'NotAllowedError'});
  assert.equal(ui.api.reportFailure(denied), 'MIDI access failed: NotAllowedError — Permission denied by the browser');
  const setup = Object.assign(new Error('Could not attach input'), {name: 'SecurityError'});
  assert.equal(ui.api.reportFailure(setup, 'setup'), 'MIDI setup failed: SecurityError — Could not attach input');
  const record = {
    timestamp, stage: 'setup', name: 'SecurityError', message: 'Could not attach input',
    pathname: '/Guitar-Learning/piano/theory/circle-of-fifths/accidentals-count/', build: '2155bafd6ded'
  };
  assert.deepEqual(plain(ui.api.getFailureLog()[1]), record);
  assert.deepEqual(plain(ui.logs[1]), ['MIDI failure:', record]);
  assert.equal(ui.api.isEnabled(), false);
  assert.equal(ui.events.length, 0);
  assert.equal(ui.storage.has(preferenceKey), false);
  assert.doesNotMatch(JSON.stringify(ui.api.getFailureLog()), /private=value|#private|stack|device/);
});

test('string, empty, and undefined failures do not invent permission denial', () => {
  const ui = boot();
  assert.equal(ui.api.reportFailure('Operating system MIDI service unavailable'), 'MIDI access failed: Error — Operating system MIDI service unavailable');
  assert.equal(ui.api.reportFailure(undefined), 'MIDI access failed: Error — Unknown error');
  assert.equal(ui.api.reportFailure(new Error(''), 'setup'), 'MIDI setup failed: Error');
  const unreadable = {get name() { throw new Error(); }, get message() { throw new Error(); }, toString() { throw new Error(); }};
  assert.equal(ui.api.reportFailure(unreadable), 'MIDI access failed: Error — Unknown error');
});

test('history is bounded, survives a fresh page, and returns safe copied records', () => {
  const ui = boot();
  for (let i = 0; i < 25; i++) ui.api.reportFailure(new Error(`Failure ${i}`));
  const saved = ui.api.getFailureLog();
  assert.equal(saved.length, 20);
  assert.equal(saved[0].message, 'Failure 5');
  assert.equal(saved[19].message, 'Failure 24');
  saved[0].message = 'mutated';
  saved.push({message: 'untrusted'});
  assert.equal(ui.api.getFailureLog()[0].message, 'Failure 5');
  assert.deepEqual(plain(boot(ui.storage).api.getFailureLog()), plain(ui.api.getFailureLog()));
  assert.equal(JSON.parse(ui.storage.get(failureKey)).length, 20);
});

test('corrupt history and failed diagnostic storage or console never mask the failure', () => {
  for (const corrupt of ['{broken', '{}', '[null, 5, {"stage":"access"}]']) {
    const ui = boot(new Map([[failureKey, corrupt]]));
    assert.deepEqual(plain(ui.api.getFailureLog()), []);
    ui.api.reportFailure(new Error('Driver unavailable'));
    assert.equal(ui.api.getFailureLog()[0].message, 'Driver unavailable');
  }
  const ui = boot(new Map(), {readBlocked: true, writeBlocked: true, consoleBlocked: true});
  assert.equal(ui.api.reportFailure(new Error('Original failure')), 'MIDI access failed: Error — Original failure');
  assert.equal(ui.api.getFailureLog()[0].message, 'Original failure');
  assert.equal(ui.api.isEnabled(), false);
});

test('diagnostics omit URL queries, fragments, stack data and extra stored fields', () => {
  const ui = boot();
  ui.api.reportFailure(new Error('Failed at https://example.test/midi?token=secret#fragment'));
  assert.equal(ui.api.getFailureLog()[0].message, 'Failed at https://example.test/midi');
  const saved = JSON.parse(ui.storage.get(failureKey));
  saved[0].deviceId = 'private-device';
  saved[0].stack = 'private-stack';
  saved[0].pathname += '?token=secret#fragment';
  ui.storage.set(failureKey, JSON.stringify(saved));
  assert.doesNotMatch(JSON.stringify(boot(ui.storage).api.getFailureLog()), /secret|fragment|private-device|private-stack/);
});
