import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import {
  efficiencySelectionFromSearch,
  efficiencySourceTick,
  efficiencyPositionAtTick,
  efficiencyFretWindow
} from '../src/fretboard-efficiency-lesson.js';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const data = JSON.parse(readFileSync(new URL('../public/data/fretboard-efficiency-fixtures.json', import.meta.url), 'utf8'));
const source = readFileSync(new URL('../src/fretboard-efficiency-lesson.js', import.meta.url), 'utf8')
  .replace(/^export /gm, '')
  .replaceAll('import.meta.env.BASE_URL', JSON.stringify('/Guitar-Learning/'));

function selectFromHtml(id) {
  const content = html.match(new RegExp(`<select id="${id}"[^>]*>([\\s\\S]*?)</select>`))?.[1];
  assert.ok(content, `Real lesson HTML contains ${id}`);
  const options = [...content.matchAll(/<option value="([^"]+)"[^>]*>([^<]+)<\/option>/g)]
    .map(([, value, label]) => ({ value, textContent: label }));
  let selected = options[0]?.value || '';
  return {
    options, disabled: false,
    get value() { return selected; },
    set value(value) { selected = options.some(option => option.value === value) ? value : ''; },
    add(option) { options.push(option); },
    addEventListener() {}
  };
}

function mount(search, bundle = data) {
  const fields = {
    fretboardEfficiencyRiff: selectFromHtml('fretboardEfficiencyRiff'),
    fretboardEfficiencyMapping: selectFromHtml('fretboardEfficiencyMapping'),
    songPlayerStatus: {}, fretboardEfficiencyInfo: {}, fretboardEfficiencyLink: {}
  };
  const location = new URL('https://example.test/Guitar-Learning/' + search);
  const loads = [], selections = [], requests = [];
  const context = vm.createContext({
    URL, URLSearchParams,
    Option: function (label, value) { this.textContent = label; this.value = value; },
    window: { location, history: { replaceState(_state, _title, url) { location.href = String(url); } } },
    document: { getElementById: id => fields[id] },
    fetch: async url => { requests.push(url); return { ok: true, json: async () => bundle }; }
  });
  vm.runInContext(source, context);
  const lesson = context.setupFretboardEfficiencyLesson({
    isSelected: () => true,
    onSelection: (fixture, version) => selections.push({ fixture, version }),
    player: { loadFretboardEfficiency: async (fixture, versionId) => { loads.push({ fixture, versionId }); } }
  });
  return { lesson, fields, loads, selections, requests, location };
}

test('the real lesson selector corresponds to every published built-in fixture, including MIDI rewrite', () => {
  const options = selectFromHtml('fretboardEfficiencyRiff').options;
  assert.deepEqual(options.map(option => option.value).sort(), data.fixtures.map(fixture => fixture.id).sort());
  for (const option of options) {
    assert.equal(option.textContent, data.fixtures.find(fixture => fixture.id === option.value).label);
  }
  const rewrite = data.fixtures.find(fixture => fixture.id === 'c5a35486');
  assert.ok(rewrite, 'C is present in the actual published data');
  assert.equal(rewrite.source_filename, '2026-11-15_midi_rewrite.mid');
  assert.equal(rewrite.source_sha256, 'c5a35486923e3b819d9f7cb7176cb1c39546c26471093862e5e67c27fbe46461');
});

for (const fixtureId of ['cfa029a2', 'da80eca9', 'c5a35486']) {
  test(`${fixtureId}: all three mapping URLs load that exact fixture and retain shareable selection`, async () => {
    for (const versionId of ['optimized', 'greedy', 'strumPick']) {
      const harness = mount(`?lesson=fretboardEfficiency&riff=${fixtureId}&mapping=${versionId}`);
      await harness.lesson.activate();
      assert.equal(harness.fields.fretboardEfficiencyRiff.value, fixtureId);
      assert.equal(harness.fields.fretboardEfficiencyMapping.value, versionId);
      assert.equal(harness.loads.length, 1, harness.fields.songPlayerStatus.textContent);
      assert.equal(harness.loads[0].fixture, data.fixtures.find(fixture => fixture.id === fixtureId));
      assert.equal(harness.loads[0].versionId, versionId);
      assert.equal(harness.selections[0].version.id, versionId);
      if (versionId === 'strumPick') {
        assert.ok(harness.fields.fretboardEfficiencyInfo.title.includes(
          harness.selections[0].version.objective.priority_labels.join(' → ')));
      }
      assert.equal(harness.fields.fretboardEfficiencyLink.hidden, false);
      const link = new URL(harness.fields.fretboardEfficiencyLink.href);
      assert.equal(link.pathname, '/Guitar-Learning/');
      assert.equal(link.searchParams.get('lesson'), 'fretboardEfficiency');
      assert.equal(link.searchParams.get('riff'), fixtureId);
      assert.equal(link.searchParams.get('mapping'), versionId);
      assert.equal(harness.location.href, link.href);
      assert.deepEqual(harness.requests, ['/Guitar-Learning/data/fretboard-efficiency-fixtures.json']);
      assert.equal(harness.fields.fretboardEfficiencyRiff.disabled, false);
      assert.equal(harness.fields.fretboardEfficiencyMapping.disabled, false);
    }
  });
}

test('default Time lesson and A/optimized fallback remain unchanged', () => {
  assert.deepEqual(efficiencySelectionFromSearch(''), {
    selected: false, fixtureId: 'cfa029a2', versionId: 'optimized'
  });
  assert.deepEqual(efficiencySelectionFromSearch('?lesson=fretboardEfficiency&riff=missing&mapping=missing'), {
    selected: true, fixtureId: 'cfa029a2', versionId: 'optimized'
  });
  assert.match(html, /<option value="timeSoloChords" selected>/);
});

test('uploaded fixture selection still loads its supplied data and stays distinct from built-in share links', async () => {
  const harness = mount('?lesson=fretboardEfficiency&riff=cfa029a2');
  const uploaded = structuredClone(data.fixtures[0]);
  uploaded.id = 'uploaded-fixture';
  uploaded.label = 'Uploaded fixture';
  harness.lesson.syncSelection(uploaded, 'optimized');
  assert.equal(harness.fields.fretboardEfficiencyRiff.value, uploaded.id);
  assert.equal(harness.fields.fretboardEfficiencyLink.hidden, true);
  await harness.lesson.activate();
  assert.equal(harness.loads.at(-1).fixture, uploaded);
  harness.fields.fretboardEfficiencyRiff.value = 'c5a35486';
  await harness.lesson.activate();
  assert.equal(harness.loads.at(-1).fixture.id, 'c5a35486');
  assert.equal(harness.fields.fretboardEfficiencyLink.hidden, false);
  assert.equal(new URL(harness.fields.fretboardEfficiencyLink.href).searchParams.get('riff'), 'c5a35486');
});

function syntheticProfileBundle() {
  const bundle = structuredClone(data);
  for (const fixture of bundle.fixtures) {
    fixture.versions = fixture.versions.filter(version => version.id !== 'strumPick');
    const profile = structuredClone(fixture.versions.find(version => version.id === 'optimized'));
    Object.assign(profile, {
      id: 'strumPick', label: 'Strum + pick',
      description: 'Open strings first, then adjacent co-attacked chord strings, then adjacent rapid single-note strings.',
      objective: {
        priority_order: ['open_misses', 'chord_skipped_strings', 'rapid_single_skipped_strings'],
        priority_labels: ['Exact-pitch open strings', 'Adjacent co-attacked chord strings', 'Adjacent rapid single-note strings'],
        rapid_max_gap_seconds: 0.25,
        chord_skip_definition: 'Unplayed strings between notes attacked together.',
        rapid_skip_definition: 'Unplayed strings between consecutive rapid single-note attacks.',
        tie_break_order: ['rapid_run_direction_reversals', 'rapid_shift_cost', 'hand_travel_frets', 'fretting_effort']
      }
    });
    Object.assign(profile.metrics, {
      chord_skipped_strings: 7, chord_attack_count: 12, contiguous_chord_count: 8,
      rapid_single_skipped_strings: 9, rapid_single_pair_count: 24,
      rapid_single_skip_transition_count: 6, rapid_run_direction_reversals: 3,
      priority_cost: [profile.metrics.open_exceptions, 7, 9], tie_break_cost: [3, 12, 4, 1]
    });
    fixture.versions.push(profile);
  }
  return bundle;
}

test('a supplied third profile uses its own picking metrics and objective without replacing the original defaults', async () => {
  const bundle = syntheticProfileBundle();
  const harness = mount('?lesson=fretboardEfficiency&riff=c5a35486&mapping=strumPick', bundle);
  await harness.lesson.activate();
  assert.equal(harness.loads.at(-1).versionId, 'strumPick');
  assert.equal(harness.fields.fretboardEfficiencyMapping.options.find(option => option.value === 'strumPick').textContent, 'Strum + pick');
  assert.match(harness.fields.fretboardEfficiencyInfo.textContent, /7 chord string skips/);
  assert.match(harness.fields.fretboardEfficiencyInfo.textContent, /9 rapid single-note string skips/);
  assert.match(harness.fields.fretboardEfficiencyInfo.title, /adjacent co-attacked chord strings/);
  assert.doesNotMatch(harness.fields.fretboardEfficiencyInfo.title, /then rapid neck shifts/);
  assert.doesNotMatch(harness.fields.fretboardEfficiencyInfo.title, /open_misses|chord_skipped_strings/);
  assert.equal(harness.fields.fretboardEfficiencyMapping.options.find(option => option.value === 'strumPick').disabled, false);
  harness.fields.fretboardEfficiencyMapping.value = 'optimized';
  await harness.lesson.activate();
  assert.equal(harness.loads.at(-1).versionId, 'optimized');
  assert.match(harness.fields.fretboardEfficiencyInfo.title, /then rapid neck shifts/);
  assert.match(harness.fields.fretboardEfficiencyInfo.textContent, /rapid shifts/);
});

test('legacy uploads disable the absent profile and never load optimized under a strumPick selection', async () => {
  const bundle = syntheticProfileBundle();
  const harness = mount('?lesson=fretboardEfficiency&riff=cfa029a2&mapping=strumPick', bundle);
  await harness.lesson.activate();
  const legacy = structuredClone(bundle.fixtures[0]);
  legacy.id = 'legacy-upload';
  legacy.versions = legacy.versions.filter(version => version.id !== 'strumPick');
  harness.lesson.syncSelection(legacy, 'optimized');
  assert.equal(harness.fields.fretboardEfficiencyMapping.value, 'optimized');
  assert.equal(harness.fields.fretboardEfficiencyMapping.options.find(option => option.value === 'strumPick').disabled, true);
  assert.equal(harness.fields.fretboardEfficiencyMapping.options.find(option => option.value === 'greedy').disabled, false);
  const previousLoads = harness.loads.length;
  harness.fields.fretboardEfficiencyMapping.value = 'strumPick';
  await harness.lesson.activate();
  assert.equal(harness.loads.length, previousLoads);
  assert.match(harness.fields.songPlayerStatus.textContent, /unavailable/);
  harness.fields.fretboardEfficiencyRiff.value = 'cfa029a2';
  await harness.lesson.activate();
  assert.equal(harness.loads.at(-1).versionId, 'strumPick');
  assert.equal(harness.fields.fretboardEfficiencyMapping.options.find(option => option.value === 'strumPick').disabled, false);
});

test('missing adjacency diagnostics are unavailable rather than zero in the lesson', async () => {
  const bundle = syntheticProfileBundle();
  const version = bundle.fixtures[0].versions.find(item => item.id === 'strumPick');
  delete version.metrics.chord_skipped_strings;
  delete version.metrics.rapid_single_skipped_strings;
  const harness = mount('?lesson=fretboardEfficiency&riff=cfa029a2&mapping=strumPick', bundle);
  await harness.lesson.activate();
  assert.match(harness.fields.fretboardEfficiencyInfo.textContent, /— chord string skips/);
  assert.match(harness.fields.fretboardEfficiencyInfo.textContent, /— rapid single-note string skips/);
});

test('the actual trainer viewport uses source ticks for C and preserves A/B native-clock behavior', () => {
  assert.ok(data.fixtures.some(fixture => fixture.id === 'c5a35486'), 'C is required for the clock regression');
  const trainer = readFileSync(new URL('../src/trainer.js', import.meta.url), 'utf8');
  const begin = trainer.indexOf('function updateEfficiencyViewport(');
  const end = trainer.indexOf('function displaySongPlayerNotes(', begin);
  assert.ok(begin >= 0 && end > begin);
  for (const fixture of data.fixtures) {
    const board = {
      dataset: {}, style: { setProperty() {} }, classList: { toggle() {} },
      querySelector: () => ({ classList: { toggle() {} } }), querySelectorAll: () => []
    };
    const stage = { classList: { toggle() {} } };
    const caption = {};
    const cells = new Map();
    for (let string = 0; string < 8; string++) {
      for (let fret = 0; fret <= 24; fret++) {
        cells.set(`${string}|${fret}`, { dataset: { fret: String(fret) }, style: {}, hidden: false });
      }
    }
    let lookupTick;
    const context = vm.createContext({
      EFFICIENCY_LESSON_ID: 'fretboardEfficiency',
      getSelectedLessonType: () => 'fretboardEfficiency',
      document: {
        querySelector: selector => selector === '.physicalFretboard' ? board : stage,
        getElementById: id => id === 'fretboardEfficiencyRange' ? { value: 'follow' } : caption
      },
      fretboardEfficiencyFixture: fixture,
      fretboardEfficiencyVersion: null,
      fretboardEfficiencyTick: 0,
      fretboardEfficiencyWindow: null,
      songPlayerCells: cells,
      currentTuning: [28, 35, 40, 45, 50, 55, 59, 64],
      efficiencySourceTick, efficiencyFretWindow,
      efficiencyPositionAtTick(version, tick) {
        lookupTick = tick;
        return efficiencyPositionAtTick(version, tick);
      },
      sizeFretboardNotes() {}
    });
    vm.runInContext(trainer.slice(begin, end), context);
    for (const version of fixture.versions) {
      context.fretboardEfficiencyVersion = version;
      context.fretboardEfficiencyWindow = null;
      const assignments = new Map(version.assignments.map(item => [item.note_id, item]));
      const nativeTicks = [1000, ...version.positions.map(position => position.tick * 960 / fixture.ticks_per_beat)];
      for (const nativeTick of nativeTicks) {
        const sourceTick = nativeTick * fixture.ticks_per_beat / 960;
        context.fretboardEfficiencyTick = nativeTick;
        const notes = fixture.notes.filter(note => note.start_tick <= sourceTick && sourceTick < note.end_tick)
          .map(note => ({ string: 9 - assignments.get(note.id).string_number, fret: assignments.get(note.id).fret }));
        context.updateEfficiencyViewport(notes);
        assert.equal(lookupTick, sourceTick, `${fixture.id}: native ${nativeTick} must use source ${sourceTick}`);
        const frame = fixture.versions.find(item => item.id === version.id).positions
          .findLast(position => position.tick <= sourceTick);
        if (frame) assert.ok(caption.textContent.includes(`Hand position ${frame.position}`));
        for (const note of notes) assert.equal(cells.get(`${note.string - 1}|${note.fret}`).hidden, false);
        for (let string = 0; string < 8; string++) assert.equal(cells.get(`${string}|0`).hidden, false);
      }
    }
    assert.equal(efficiencySourceTick(1000, fixture.ticks_per_beat), fixture.id === 'c5a35486' ? 100 : 1000);
  }
});
