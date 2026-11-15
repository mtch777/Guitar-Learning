import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Exercise the real review selection/rendering functions with DOM drawing
// reduced to nodes; no timer, browser, network or audio is involved.
const source = readFileSync(new URL('../src/fretboard-efficiency-view.js', import.meta.url), 'utf8');
const data = JSON.parse(readFileSync(new URL('../public/data/fretboard-efficiency-fixtures.json', import.meta.url), 'utf8'));

class Node {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {}; this.events = {}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) { this.events[name] = callback; }
}

function between(first, next) {
  const begin = source.indexOf(first), end = source.indexOf(next, begin);
  assert.ok(begin >= 0 && end > begin, `Review function boundary: ${first}`);
  return source.slice(begin, end);
}

function mount(fixtureId = data.fixtures[0].id, actualProfile = false) {
  const fixture = structuredClone(data.fixtures.find(item => item.id === fixtureId));
  const savedProfile = fixture.versions.find(version => version.id === 'strumPick');
  fixture.versions = fixture.versions.filter(version => version.id !== 'strumPick');
  const original = fixture.versions.find(version => version.id === 'optimized');
  const strum = actualProfile ? savedProfile : {
    ...structuredClone(original), id: 'strumPick', label: 'Strum + pick',
    description: 'Open strings, adjacent chord strings, then adjacent rapid single-note strings.',
    objective: {
      priority_order: ['open_misses', 'chord_skipped_strings', 'rapid_single_skipped_strings'],
      priority_labels: ['Exact-pitch open strings', 'Adjacent co-attacked chord strings', 'Adjacent rapid single-note strings'],
      rapid_max_gap_seconds: 0.25,
      chord_skip_definition: 'Count skipped strings within each co-attacked chord.',
      rapid_skip_definition: 'Count skipped strings between rapid single-note attacks.',
      tie_break_order: ['rapid_run_direction_reversals', 'rapid_shift_cost', 'hand_travel_frets', 'fretting_effort']
    },
    metrics: {
      ...original.metrics, chord_skipped_strings: 7, chord_attack_count: 12,
      contiguous_chord_count: 8, rapid_single_skipped_strings: 9,
      rapid_single_pair_count: 24, rapid_single_skip_transition_count: 6,
      rapid_run_direction_reversals: 3, priority_cost: [0, 7, 9], tie_break_cost: [3, 12, 4, 1]
    }
  };
  assert.ok(strum, `${fixtureId} has the requested strumPick profile`);
  fixture.versions.push(strum);
  const legacy = { ...fixture, id: 'legacy', versions: fixture.versions.filter(version => version.id !== 'strumPick') };
  const fields = Object.fromEntries(['result-title', 'riff-summary', 'seek', 'pattern-details'].map(id => [id, new Node()]));
  const versionButtons = new Node(), metrics = new Node(), status = new Node();
  const context = vm.createContext({
    document: { createElement: tag => new Node(tag) },
    $: id => fields[id],
    bundle: data, fixtures: [fixture, legacy], fixture: null, version: null,
    time: 0, boardKey: '', select: new Node('select'), versionButtons, metrics, status,
    sourceLink: new Node('a'),
    stopFollowing() {}, showJumpButtons() {}, draw() {}
  });
  vm.runInContext([
    source.match(/^const number = .*;$/m)[0],
    source.match(/^const seconds = .*;$/m)[0],
    between('function element(', 'function prepareFixture('),
    between('  function showMetrics()', '  function showJumpButtons()'),
    between('  function showDetails()', '  function chooseVersion('),
    between('  function chooseVersion(', '  function chooseFixture('),
    between('  function chooseFixture(', '\n  try {')
  ].join('\n'), context);
  return { context, fixture, strum, fields, versionButtons, metrics, status };
}

function descendants(node) {
  return node.children.flatMap(child => [child, ...descendants(child)]);
}

test('review exposes Strum + pick as a distinct version, preserves defaults, and updates selected objective and metrics', () => {
  const h = mount();
  h.context.chooseFixture(h.fixture.id);
  assert.equal(h.context.version.id, 'optimized');
  assert.deepEqual(h.versionButtons.children.map(button => button.textContent), ['Efficient mapping', 'Greedy comparison', 'Strum + pick']);
  const button = h.versionButtons.children.find(item => item.dataset.version === 'strumPick');
  button.events.click();
  assert.equal(h.context.version.id, 'strumPick');
  assert.equal(button.attributes['aria-pressed'], 'true');
  assert.equal(h.status.textContent, h.strum.description);
  assert.deepEqual(h.metrics.children.map(card => card.children[0].textContent),
    ['Open notes', 'Chord string skips', 'Rapid single-note string skips', 'Hand travel']);
  assert.equal(h.metrics.children[1].children[1].textContent, '7');
  assert.equal(h.metrics.children[2].children[1].textContent, '9');
  assert.match(h.metrics.children[2].children[2].textContent, /6 \/ 24 pairs.*250 ms/);
  const explanation = descendants(h.fields['pattern-details']);
  assert.deepEqual(explanation.filter(node => node.tagName === 'li').map(node => node.textContent), h.strum.objective.priority_labels);
  assert.ok(!explanation.some(node => node.className === 'eff-model'));
  assert.ok(!explanation.some(node => /open_misses|chord_skipped_strings/.test(node.textContent || '')));
  assert.ok(descendants(h.fields['pattern-details']).some(node => node.textContent === 'Selected mapping priorities'));

  h.versionButtons.children.find(item => item.dataset.version === 'greedy').events.click();
  assert.equal(h.context.version.id, 'greedy');
  assert.deepEqual(h.metrics.children.map(card => card.children[0].textContent),
    ['Open notes', 'Rapid shifts', 'Hand travel', 'Largest shift']);
  const originalModel = descendants(h.fields['pattern-details']).find(node => node.className === 'eff-model');
  assert.deepEqual(JSON.parse(originalModel.textContent), data.model);
});

test('legacy two-version review data exposes only its real versions and retains optimized default', () => {
  const h = mount();
  h.context.chooseFixture('legacy');
  assert.equal(h.context.version.id, 'optimized');
  assert.deepEqual(h.versionButtons.children.map(button => button.dataset.version), ['optimized', 'greedy']);
  assert.deepEqual(h.versionButtons.children.map(button => button.textContent), ['Efficient mapping', 'Greedy comparison']);
});

test('review shows missing adjacency diagnostics as unavailable and supports legacy priority metadata', () => {
  const h = mount();
  delete h.strum.metrics.chord_skipped_strings;
  delete h.strum.metrics.rapid_single_skipped_strings;
  delete h.strum.objective.priority_labels;
  h.context.chooseFixture(h.fixture.id);
  h.versionButtons.children.find(item => item.dataset.version === 'strumPick').events.click();
  assert.equal(h.metrics.children[1].children[1].textContent, '—');
  assert.equal(h.metrics.children[2].children[1].textContent, '—');
  const labels = descendants(h.fields['pattern-details']).filter(node => node.tagName === 'li').map(node => node.textContent);
  assert.deepEqual(labels, h.strum.objective.priority_order);
});

for (const fixture of data.fixtures) {
  test(`${fixture.id}: review selects and reports the actual published Strum + pick result`, () => {
    const h = mount(fixture.id, true);
    h.context.chooseFixture(fixture.id);
    h.versionButtons.children.find(button => button.dataset.version === 'strumPick').events.click();
    assert.equal(h.context.version.id, 'strumPick');
    assert.equal(h.context.version.label, 'Strum + pick');
    assert.equal(h.metrics.children[1].children[1].textContent, h.strum.metrics.chord_skipped_strings.toLocaleString());
    assert.equal(h.metrics.children[2].children[1].textContent, h.strum.metrics.rapid_single_skipped_strings.toLocaleString());
    const explanation = descendants(h.fields['pattern-details']);
    assert.deepEqual(explanation.filter(node => node.tagName === 'li').map(node => node.textContent), h.strum.objective.priority_labels);
    assert.ok(explanation.some(node => /250 ms.*Playback speed does not recompute/.test(node.textContent || '')));
  });
}
