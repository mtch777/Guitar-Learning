import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {rankSectionPresets, applySectionPreset} from '../src/riff-presets.js';

const artists = ['Invent Animate', 'Currents', 'ERRA'];
const profile = (songs, lengths = [['8', songs]], extra = {}) => ({distinct_songs: songs, captures: songs, occurrences: songs,
  duration_histogram: lengths.map(([length_q, distinct_songs]) => ({length_q, distinct_songs, occurrences: 1000})),
  metrics: {attacks_per_quarter: {median_q: '3'}, written_empty_fraction: {median_q: '1/4'}, linked_shape_count: {median_q: '2'}}, ...extra});
const preset = (style, focus, by_artist, support = {distinct_songs: 99999}) => ({id: `${style}-${focus}`, label: `${style} / ${focus}`,
  style, focus, by_artist, support, style_scope: 'inherited_containing_riff', length_scope: 'existing_grammar_candidate_gesture_not_verified_phrase'});
const data = presets => ({schema: 'riff-section-presets/1', presets});
function availabilityFor(presets) {
  const availability = {rhythms: {}, palettes: {}};
  for (const item of presets) for (const [artist, evidence] of Object.entries(item.by_artist)) if (evidence.distinct_songs) {
    availability.rhythms[artist] ||= {}; availability.rhythms[artist][item.style] ||= {};
    availability.rhythms[artist][item.style][item.focus] = 1;
    availability.palettes[artist] ||= {}; availability.palettes[artist][item.style] ||= {};
    availability.palettes[artist][item.style].Aeolian = 1;
  }
  return availability;
}

test('rank uses selected artists and distinct songs, never occurrence or all-artist totals', () => {
  const presets = [preset('pedal', 'single', {'Invent Animate': profile(3, undefined, {captures: 100, occurrences: 10000}), ERRA: profile(1)}),
    preset('arpeggio', 'single', {'Invent Animate': profile(5), ERRA: profile(2)}),
    preset('melodic', 'single', {Currents: profile(30), ERRA: profile(12)})];
  const source = data(presets), available = availabilityFor(presets);
  const ia = rankSectionPresets(source, ['Invent Animate'], 'Aeolian', available);
  assert.deepEqual(ia.map(value => value.id), ['arpeggio-single', 'pedal-single']);
  assert.deepEqual(ia.map(value => value.support.distinct_songs), [5, 3]);
  assert(ia.every(value => Object.keys(value.by_artist).join() === 'Invent Animate'));
  const erra = rankSectionPresets(source, ['ERRA'], 'Aeolian', available);
  assert.deepEqual(erra.map(value => value.support.distinct_songs), [12, 2, 1]);
  assert.equal(erra[0].id, 'melodic-single');
  const both = rankSectionPresets(source, ['Invent Animate', 'ERRA'], 'Aeolian', available);
  assert.equal(both.find(value => value.id === 'arpeggio-single').support.distinct_songs, 7);
  assert.equal(both.find(value => value.id === 'pedal-single').support.distinct_songs, 4);
});

test('duplicate presets or equivalent duplicate histogram rows cannot inflate support', () => {
  const one = preset('pedal', 'single', {'Invent Animate': profile(5)});
  assert.throws(() => rankSectionPresets(data([one, structuredClone(one)]), ['Invent Animate'], 'Aeolian', availabilityFor([one])), /Duplicate reference preset/);
  one.by_artist['Invent Animate'].duration_histogram.push({length_q: '16/2', distinct_songs: 5, occurrences: 1000});
  assert.throws(() => rankSectionPresets(data([one]), ['Invent Animate'], 'Aeolian', availabilityFor([one])), /Duplicate observed duration/);
});

test('disabled common choices keep their rank and do not borrow another artist or mode', () => {
  const presets = [preset('arpeggio', 'single', {'Invent Animate': profile(10)}), preset('pedal', 'single', {'Invent Animate': profile(2)})];
  const availability = availabilityFor(presets);
  availability.palettes['Invent Animate'].arpeggio.Aeolian = 0;
  availability.palettes['Invent Animate'].arpeggio.Dorian = 20;
  availability.palettes.Currents = {arpeggio: {Aeolian: 20}};
  const ranked = rankSectionPresets(data(presets), ['Invent Animate'], 'Aeolian', availability);
  assert.equal(ranked[0].id, 'arpeggio-single'); assert.equal(ranked[0].rank, 1);
  assert.equal(ranked[0].available, false); assert.match(ranked[0].disabled_reason, /E Aeolian/);
  assert.equal(ranked[1].available, true);
  assert.deepEqual(Object.keys(ranked[0].availability.palettes_by_artist), ['Invent Animate']);
});

test('length chooses strongest exact supported observation within selected artists', () => {
  const one = preset('pedal', 'single', {'Invent Animate': profile(12, [['6', 12], ['4', 2], ['8', 3], ['16', 1]]),
    Currents: profile(30, [['16', 30]])});
  const ranked = rankSectionPresets(data([one]), ['Invent Animate'], 'Aeolian', availabilityFor([one]));
  assert.equal(ranked[0].section.length_q, '8'); assert.equal(ranked[0].length_selection.strategy, 'observed_supported');
  assert.equal(ranked[0].length_selection.distinct_songs, 3);
  assert.match(ranked[0].length_evidence.description, /8 quarter-note beats in 3/);
});

test('unsupported observed lengths map explicitly, rather than claiming source phrase lengths', () => {
  const one = preset('arpeggio', 'single', {'Invent Animate': profile(12, [['6', 8], ['12', 7], ['3/2', 1]])});
  const selected = rankSectionPresets(data([one]), ['Invent Animate'], 'Aeolian', availabilityFor([one]))[0];
  assert.equal(selected.section.length_q, '4'); assert.equal(selected.length_selection.source_length_q, '6');
  assert.equal(selected.length_selection.strategy, 'nearest_supported');
  assert.match(selected.length_evidence.description, /mapped to 4 beats/); assert.match(selected.length_evidence.description, /shorter on a tie/);
  assert.equal(selected.length_scope, 'existing_grammar_candidate_gesture_not_verified_phrase');
});

test('missing observations are not replaced with an invented default length', () => {
  const one = preset('arpeggio', 'single', {'Invent Animate': profile(1, [])});
  const selected = rankSectionPresets(data([one]), ['Invent Animate'], 'Aeolian', availabilityFor([one]))[0];
  assert.equal(selected.section.length_q, null); assert.equal(selected.available, false); assert.match(selected.disabled_reason, /No observed length/);
});

test('traits retain per-artist medians rather than making a median of medians', () => {
  const one = preset('pedal', 'single', {'Invent Animate': profile(20), ERRA: profile(2, undefined,
    {metrics: {attacks_per_quarter: {median_q: '7'}}})});
  const selected = rankSectionPresets(data([one]), ['Invent Animate', 'ERRA'], 'Aeolian', availabilityFor([one]))[0];
  assert.match(selected.traits[0], /Invent Animate: median 3 attacks/); assert.match(selected.traits[1], /ERRA: median 7 attacks/);
  assert.equal(selected.by_artist.ERRA.metrics.attacks_per_quarter.median_q, '7');
  assert.match(selected.trait_scope, /Descriptive/); assert(!('median' in selected.support));
});

test('apply modifies only the selected section settings and preserves all globals, rows and seeds', () => {
  const one = preset('arpeggio', 'interval', {'Invent Animate': profile(3)});
  const selected = rankSectionPresets(data([one]), ['Invent Animate'], 'Aeolian', availabilityFor([one]))[0];
  const current = {artists: ['Invent Animate'], mode: 'Aeolian', tempo: 137, seed: 111, extra: {keep: true},
    sections: [{style: 'pedal', focus: 'single', length_q: '4', seed: 51},
      {style: 'pedal', focus: 'triad', length_q: '16', seed: 52, annotation: 'keep'},
      {style: 'other', focus: 'interval', length_q: '8', seed: 53}]};
  const before = structuredClone(current), originalPreset = structuredClone(selected), changed = applySectionPreset(current, 1, selected);
  assert.deepEqual(current, before); assert.deepEqual(selected, originalPreset);
  assert.deepEqual(changed, {...before, sections: [before.sections[0], {...before.sections[1], style: 'arpeggio', focus: 'interval', length_q: '8'}, before.sections[2]]});
  changed.extra.keep = false; assert.equal(current.extra.keep, true);
  assert.throws(() => applySectionPreset(current, 4, selected), /existing section/);
  assert.throws(() => applySectionPreset({...current, mode: 'Dorian'}, 1, selected), /changed/);
  assert.throws(() => applySectionPreset({...current, artists: ['ERRA']}, 1, selected), /changed/);
  assert.throws(() => applySectionPreset(current, 1, {...selected, available: false, disabled_reason: 'No evidence'}), /No evidence/);
});

test('ranking and application preserve source aggregates and reject invalid artist scopes', () => {
  const one = preset('pedal', 'single', {'Invent Animate': profile(3)}), source = data([one]), before = structuredClone(source);
  const available = availabilityFor([one]), beforeAvailable = structuredClone(available);
  rankSectionPresets(source, ['Invent Animate'], 'Aeolian', available);
  assert.deepEqual(source, before); assert.deepEqual(available, beforeAvailable);
  for (const scope of [[], ['Invent Animate', 'Invent Animate'], ['Unknown']]) assert.throws(() => rankSectionPresets(source, scope, 'Aeolian', available), /supported reference artists/);
  assert.throws(() => rankSectionPresets(source, ['Invent Animate'], 'Locrian', available), /available E mode/);
});

test('published aggregate ranks each actual artist independently and retains auditable counts', () => {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const source = JSON.parse(readFileSync(path.join(root, 'public/riff-builder/section-presets.json'), 'utf8'));
  const available = JSON.parse(readFileSync(path.join(root, 'public/riff-builder/availability.json'), 'utf8'));
  const before = JSON.stringify(source);
  for (const artist of artists) {
    const ranked = rankSectionPresets(source, [artist], 'Aeolian', available);
    assert(ranked.length > 0); assert(ranked.some(value => value.available));
    for (const [index, item] of ranked.entries()) {
      const original = source.presets.find(value => value.id === item.id);
      assert.deepEqual(Object.keys(item.by_artist), [artist]);
      assert.equal(item.support.distinct_songs, original.by_artist[artist].distinct_songs);
      if (index) assert(ranked[index - 1].support.distinct_songs >= item.support.distinct_songs);
      assert(['4', '8', '16'].includes(item.section.length_q));
      assert(item.length_evidence.description.length > 0);
    }
  }
  assert.equal(JSON.stringify(source), before);
});
