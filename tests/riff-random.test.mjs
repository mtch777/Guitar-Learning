import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath, pathToFileURL} from 'node:url';
import path from 'node:path';
import {randomRequest, generateRandomRiff} from '../src/riff-random.js';
import {normalizeEvents, toEventScore} from '../src/riff-event-score.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const availability = JSON.parse(readFileSync(path.join(root, 'public/riff-builder/availability.json'), 'utf8'));
const artists = ['Invent Animate', 'Currents', 'ERRA'];
const modes = ['Aeolian', 'Dorian', 'Ionian', 'Mixolydian', 'Lydian', 'Phrygian'];
const tuning = [64, 59, 55, 50, 45, 40, 35, 28];
const nativePath = path.join(root, '.local/qa/node_modules/@coderline/alphatab/dist/alphaTab.mjs');
const at = existsSync(nativePath) ? await import(pathToFileURL(nativePath).href) : null;
const rng = (initial = 1) => { let state = initial >>> 0; return () => ((state = (Math.imul(state, 1664525) + 1013904223) >>> 0) / 4294967296); };
function generated(request, onset = '1/3') {
  const section = request.sections[0];
  return {schema: 'modular-riff-result/1', status: 'generated', request: structuredClone(request), tempo: request.tempo,
    tuning, meter: [4, 4], duration_q: section.length_q,
    events: [{onset_q: onset, section_index: 0, members: [{id: 's0:b0:e0:n0', duration_q: '2/3', pitch: 28, string_number: 8, fret: 0, marks: {}}]}],
    sections: [{index: 0, ...section, offset_q: '0', status: 'generated', blocks: [], refusals: []}],
    refusals: [], provenance: {pattern_pack_sha256: 'same-pack'}, limits: ['No listening claim']};
}
const refused = () => ({status: 'no_choice', events: [], sections: [{status: 'no_choice', refusals: [{reason: 'no_pitch_choice'}]}], refusals: [{section_index: 0, reason: 'no_pitch_choice'}]});

test('samples every artist subset and every available filter without unsupported pairs', () => {
  const random = rng(2026), subsets = new Set(), foundModes = new Set(), styles = new Set(), focuses = new Set();
  let minTempo = 999, maxTempo = 0;
  for (let i = 0; i < 3000; i++) {
    const request = randomRequest(availability, 10, random);
    subsets.add(request.artists.join('|')); foundModes.add(request.mode);
    assert(request.artists.length > 0 && request.artists.every(artist => artists.includes(artist)));
    assert(modes.includes(request.mode)); assert(Number.isInteger(request.tempo));
    minTempo = Math.min(minTempo, request.tempo); maxTempo = Math.max(maxTempo, request.tempo);
    assert.equal(request.sections.length, 10);
    for (const section of request.sections) {
      styles.add(section.style); focuses.add(section.focus);
      assert(request.artists.some(artist => availability.rhythms[artist]?.[section.style]?.[section.focus] > 0));
      assert(request.artists.some(artist => availability.palettes[artist]?.[section.style]?.[request.mode] > 0));
      assert(['4', '8', '16'].includes(section.length_q));
      assert(Number.isSafeInteger(section.seed) && section.seed >= 0);
    }
  }
  assert.equal(subsets.size, 7); assert.equal(foundModes.size, 6);
  assert.equal(styles.size, 6); assert.equal(focuses.size, 5);
  assert.equal(minTempo, 80); assert.equal(maxTempo, 200);
});

test('count bounds, missing support, and invalid random sources fail clearly', () => {
  for (const count of [0, 11, 1.5, '2', NaN]) assert.throws(() => randomRequest(availability, count), /1–10/);
  assert.throws(() => randomRequest({}, 1), /No labelled/);
  for (const value of [1, -0.1, NaN, '0.5']) assert.throws(() => randomRequest(availability, 1, () => value), /Random values/);
});

test('deterministic sampling does not mutate availability', () => {
  const before = JSON.stringify(availability);
  assert.deepEqual(randomRequest(availability, 5, rng(92)), randomRequest(availability, 5, rng(92)));
  assert.notDeepEqual(randomRequest(availability, 5, rng(92)), randomRequest(availability, 5, rng(93)));
  assert.equal(JSON.stringify(availability), before);
});

test('ten sections share global settings and preserve exact clocks, offsets, IDs and actual choices', async () => {
  const calls = [], progress = [];
  const result = await generateRandomRiff(availability, 10, async request => {
    calls.push(structuredClone(request)); return generated(request);
  }, {rng: rng(84), onProgress: value => progress.push(value)});
  assert.equal(result.status, 'generated'); assert.equal(calls.length, 10);
  let offset = 0;
  for (let i = 0; i < 10; i++) {
    assert.deepEqual(calls[i].artists, result.request.artists);
    assert.equal(calls[i].tempo, result.tempo); assert.equal(calls[i].mode, result.request.mode);
    assert.deepEqual(calls[i].sections[0], result.request.sections[i]);
    assert.equal(result.sections[i].index, i); assert.equal(result.sections[i].offset_q, String(offset));
    assert.equal(result.events[i].section_index, i);
    assert.equal(result.events[i].members[0].id, `s${i}:b0:e0:n0`);
    assert.equal(result.events[i].onset_q, `${offset * 3 + 1}/3`);
    offset += Number(calls[i].sections[0].length_q);
  }
  assert.equal(result.duration_q, String(offset));
  assert.equal(new Set(result.events.flatMap(event => event.members.map(member => member.id))).size, 10);
  assert(progress.some(value => value.phase === 'accepted' && value.sectionIndex === 9));
  assert.equal(result.random_generation.global_rerolls, 0);
  assert.deepEqual(Object.keys(result.request).sort(), ['artists', 'mode', 'sections', 'seed', 'tempo']);
});

test('fractional clocks never pass through floating point, even beyond safe-integer denominators', async () => {
  const result = await generateRandomRiff(availability, 2, request => generated(request, '9007199254740993/9007199254740994'), {rng: () => 0});
  assert.equal(result.status, 'generated');
  assert.equal(result.events[0].onset_q, '9007199254740993/9007199254740994');
  assert.equal(result.events[1].onset_q, '45035996273704969/9007199254740994');
});

test('musical failures retry with recorded choices and preserve the accepted request', async () => {
  const calls = [];
  const result = await generateRandomRiff(availability, 1, request => {
    calls.push(structuredClone(request)); return calls.length < 3 ? refused() : generated(request);
  }, {rng: () => 0, maxAttemptsPerSection: 3});
  assert.equal(result.status, 'generated'); assert.equal(calls.length, 3);
  assert.deepEqual(result.request, calls[2]);
  assert.equal(new Set(calls.map(request => request.sections[0].seed)).size, 3);
  assert.deepEqual(result.random_generation.attempts.map(attempt => attempt.status), ['no_choice', 'no_choice', 'generated']);
  assert.equal(result.random_generation.attempts[0].refusals[0].reason, 'no_pitch_choice');
});

test('a later failure publishes no partial audio and never rerolls global settings', async () => {
  let call = 0;
  const result = await generateRandomRiff(availability, 3, request => (++call === 1 ? generated(request) : refused()),
    {rng: rng(22), maxAttemptsPerSection: 2});
  assert.equal(result.status, 'no_choice'); assert.deepEqual(result.events, []);
  assert.equal(call, 3); assert.equal(result.random_generation.successful_sections, 1);
  assert.equal(result.sections[1].index, 1);
  assert.equal(result.refusals.at(-1).reason, 'random_section_attempts_exhausted');
  for (const attempt of result.random_generation.attempts) {
    assert.deepEqual(attempt.request.artists, result.request.artists);
    assert.equal(attempt.request.mode, result.request.mode); assert.equal(attempt.request.tempo, result.request.tempo);
  }
});

test('transport errors and invalid generated clocks stop immediately without partial output', async () => {
  for (const callback of [() => { throw new Error('Worker unavailable'); }, request => ({...generated(request), duration_q: '17/3'})]) {
    const result = await generateRandomRiff(availability, 3, callback, {rng: rng(8)});
    assert.equal(result.status, 'no_choice'); assert.deepEqual(result.events, []);
    assert.equal(result.random_generation.attempts.length, 1);
    assert.equal(result.refusals.at(-1).reason, 'generation_callback_or_contract_error');
  }
});

test('callback inputs and returned original results remain unchanged', async () => {
  const returned = [], before = [];
  const result = await generateRandomRiff(availability, 2, request => {
    const value = generated(request); returned.push(value); before.push(structuredClone(value)); return value;
  }, {rng: rng(123)});
  assert.equal(result.status, 'generated'); assert.deepEqual(returned, before);
});

test('noncanonical callback IDs receive a unique deterministic fallback', async () => {
  const result = await generateRandomRiff(availability, 2, request => {
    const value = generated(request); value.events[0].members[0].id = 'custom'; return value;
  }, {rng: rng(123)});
  assert.equal(result.events[0].members[0].id, 'random:s0:e0:n0:custom');
  assert.equal(result.events[1].members[0].id, 'random:s1:e0:n0:custom');
});

const allExclusions = ['artists', 'mode', 'tempo', 'style', 'focus', 'length_q'];
const currentSettings = () => ({artists: ['Invent Animate'], mode: 'Aeolian', tempo: 142, seed: 0,
  sections: [{style: 'arpeggio', focus: 'single', length_q: '8', seed: 0},
    {style: 'pedal', focus: 'interval', length_q: '4', seed: 0}]});

test('excluded global settings stay exact while other fields still vary', () => {
  const current = currentSettings(); current.artists = ['ERRA', 'Invent Animate', 'Currents']; current.mode = 'Dorian'; current.tempo = 173;
  const before = structuredClone(current), seen = new Set(), random = rng(66);
  for (let i = 0; i < 50; i++) {
    const request = randomRequest(availability, 3, random, {current, exclude: ['artists', 'mode', 'tempo']});
    assert.deepEqual(request.artists, current.artists); assert.equal(request.mode, current.mode); assert.equal(request.tempo, current.tempo);
    request.sections.forEach(section => seen.add(`${section.style}:${section.focus}:${section.length_q}`));
  }
  assert(seen.size > 10); assert.deepEqual(current, before);
});

test('conditional artist and mode sampling accommodates every excluded section style and focus', () => {
  const current = currentSettings();
  current.sections = [{style: 'other', focus: 'triad', length_q: '4'}, {style: 'chordal', focus: 'interval', length_q: '8'}];
  const random = rng(9);
  for (let i = 0; i < 100; i++) {
    const request = randomRequest(availability, 5, random, {current, exclude: ['style', 'focus']});
    assert(request.artists.includes('Invent Animate'), 'Only Invent Animate supplies the labelled other material');
    assert(request.artists.some(artist => artist !== 'Invent Animate'), 'Chordal material requires another selected artist');
    request.sections.forEach((section, index) => {
      const expected = current.sections[index % 2];
      assert.equal(section.style, expected.style); assert.equal(section.focus, expected.focus);
      assert(request.artists.some(artist => availability.rhythms[artist]?.[section.style]?.[section.focus] > 0));
      assert(request.artists.some(artist => availability.palettes[artist]?.[section.style]?.[request.mode] > 0));
    });
  }
});

test('impossible excluded artist/style and incompatible shared modes fail before generation without unlocking', async () => {
  const current = currentSettings(); current.sections[0].style = 'chordal';
  let draws = 0, calls = 0;
  const options = {current, exclude: ['artists', 'style'], rng: () => {draws++; return 0;}};
  assert.throws(() => randomRequest(availability, 1, options.rng, options), /match the excluded values.*Nothing was unlocked/);
  await assert.rejects(generateRandomRiff(availability, 1, request => {calls++; return generated(request);}, options), /Nothing was unlocked/);
  assert.equal(draws, 0); assert.equal(calls, 0); assert.equal(current.sections[0].style, 'chordal');
  const disconnected = {rhythms: {'Invent Animate': {arpeggio: {single: 1}, pedal: {single: 1}}},
    palettes: {'Invent Animate': {arpeggio: {Aeolian: 1}, pedal: {Dorian: 1}}}};
  const two = currentSettings(); two.sections[1].focus = 'single';
  assert.throws(() => randomRequest(disconnected, 2, () => 0, {current: two, exclude: ['style', 'focus']}), /Nothing was unlocked/);
});

test('excluded invalid values are rejected without coercion or silent replacement', () => {
  for (const [key, value] of [['artists', []], ['artists', ['Invent Animate', 'Invent Animate']], ['mode', 'Locrian'], ['tempo', '142'],
    ['tempo', 201], ['style', 'unknown'], ['focus', 'unknown'], ['length_q', '6']]) {
    const current = currentSettings();
    if (['style', 'focus', 'length_q'].includes(key)) current.sections[0][key] = value; else current[key] = value;
    assert.throws(() => randomRequest(availability, 1, () => 0, {current, exclude: [key]}), /Excluded/);
  }
  assert.throws(() => randomRequest(availability, 1, () => 0, {exclude: ['style']}), /current section/);
  assert.throws(() => randomRequest(availability, 1, () => 0, {current: currentSettings(), exclude: ['count']}), /Exclude only/);
});

test('excluded A/B section values repeat for five rows and stay fixed through retries', async () => {
  const current = currentSettings(), before = structuredClone(current), calls = [];
  const result = await generateRandomRiff(availability, 5, (request, {sectionIndex, attempt}) => {
    calls.push({request: structuredClone(request), sectionIndex, attempt});
    return attempt === 1 ? refused() : generated(request);
  }, {rng: () => 0, current, exclude: allExclusions, maxAttemptsPerSection: 2});
  assert.equal(result.status, 'generated'); assert.equal(calls.length, 10); assert.deepEqual(current, before);
  for (const {request, sectionIndex} of calls) {
    const expected = before.sections[sectionIndex % 2];
    assert.deepEqual(request.artists, before.artists); assert.equal(request.mode, before.mode); assert.equal(request.tempo, before.tempo);
    for (const key of ['style', 'focus', 'length_q']) assert.equal(request.sections[0][key], expected[key]);
    assert.notEqual(request.sections[0].seed, expected.seed);
  }
  assert.deepEqual(result.request.sections.map(section => section.length_q), ['8', '4', '8', '4', '8']);
  assert.deepEqual(result.random_generation.exclusions, allExclusions);
  assert.deepEqual(result.random_generation.excluded_values, {artists: before.artists, mode: before.mode, tempo: before.tempo,
    sections: before.sections.map(({style, focus, length_q}) => ({style, focus, length_q}))});
  const one = randomRequest(availability, 1, rng(18), {current, exclude: allExclusions});
  assert.equal(one.sections[0].style, before.sections[0].style); assert.equal(one.sections[0].length_q, before.sections[0].length_q);
});

test('excluded values are snapshotted before async generation and failures remain atomic', async () => {
  const current = currentSettings(); let calls = 0;
  const result = await generateRandomRiff(availability, 2, (request, {sectionIndex}) => {
    calls++; current.tempo = 199; current.sections[0].style = 'chordal';
    assert.equal(request.tempo, 142);
    assert.equal(request.sections[0].style, sectionIndex === 0 ? 'arpeggio' : 'pedal');
    return sectionIndex === 0 ? generated(request) : refused();
  }, {rng: rng(11), current, exclude: allExclusions, maxAttemptsPerSection: 2});
  assert.equal(result.status, 'no_choice'); assert.deepEqual(result.events, []); assert.equal(calls, 3);
  assert.equal(result.random_generation.excluded_values.tempo, 142);
  assert.equal(result.random_generation.excluded_values.sections[0].style, 'arpeggio');
});

const localPython = path.join(root, '.local/songsterr-venv/Scripts/python.exe');
const python = existsSync(localPython) ? localPython : 'python3';
function compose(request) {
    const execution = spawnSync(python, ['-B', '-X', 'utf8', '-c',
      "import gzip,json,sys;from pathlib import Path;from pattern_engine import generate;print(json.dumps(generate(json.loads(sys.stdin.read()),json.loads(gzip.decompress(Path('pattern-pack.json.gz').read_bytes())))))"],
    {cwd: path.join(root, 'public/riff-builder'), input: JSON.stringify(request), encoding: 'utf8', timeout: 30000, maxBuffer: 20 * 1024 * 1024});
    assert.equal(execution.status, 0, execution.stderr || execution.error?.message); return JSON.parse(execution.stdout);
}
function checkNative(result) {
  const source = normalizeEvents(result), played = [], bends = [];
  const handler = new Proxy({}, {get: (_, method) => (...args) => {
    if (method === 'addNote') played.push(args);
    if (method === 'addNoteBend') bends.push(args);
  }});
  const score = toEventScore(at, result);
  new at.midi.MidiFileGenerator(score, new at.Settings(), handler).generate();
  const canonical = values => values.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  const nativeNotes = score.tracks[0].staves[0].bars.flatMap(bar => bar.voices.flatMap(voice => voice.beats.flatMap(beat => beat.notes)));
  const heads = nativeNotes.filter(note => !note.isTieDestination);
  assert.equal(heads.length, source.notes.length, 'Every authored note head survives score conversion');
  assert.deepEqual(canonical(heads.map(note => [Math.round(note.beat.absolutePlaybackStart), note.realValue, 9 - note.string])),
    canonical(source.notes.map(note => [Math.round(note.start * 960), note.pitch, note.string_number])));
  const legatoDestinations = new Set();
  for (const target of heads.filter(note => note.slideOrigin?.slideOutType === at.model.SlideOutType.Legato)) {
    const origin = target.slideOrigin;
    const original = source.notes.find(note => note.string_number === 9 - origin.string && note.pitch === origin.realValue &&
      note.start * 960 <= origin.beat.absolutePlaybackStart && note.end * 960 > origin.beat.absolutePlaybackStart);
    const destination = source.notes.find(note => note.string_number === 9 - target.string && note.pitch === target.realValue &&
      Math.round(note.start * 960) === Math.round(target.beat.absolutePlaybackStart));
    assert.equal(original?.marks?.slide, 'legato', 'Only explicitly authored legato slides may avoid a new MIDI attack');
    assert(destination); assert.equal(original.end, destination.start); assert.equal(origin.slideTarget, target);
    const soundingOrigin = played.find(note => note[1] === original.start * 960 && note[3] === original.pitch);
    assert(soundingOrigin); assert(soundingOrigin[1] + soundingOrigin[2] >= destination.end * 960);
    // AlphaTab's 16-semitone pitch-wheel range uses 8192 at center, 512 per semitone.
    const targetBend = 8192 + (destination.pitch - original.pitch) * 512;
    assert(bends.some(bend => bend[1] === destination.start * 960 && bend[3] === original.pitch && bend[4] === targetBend),
      'The audible pitch bend must reach the destination pitch at its exact clock');
    legatoDestinations.add(destination);
  }
  const reattacked = source.notes.filter(note => !legatoDestinations.has(note));
  assert.equal(played.length, reattacked.length, 'Only verified legato destinations may omit a fresh MIDI attack');
  assert.deepEqual(canonical(played.map(note => [Math.round(note[1]), note[3]])),
    canonical(reattacked.map(note => [Math.round(note.start * 960), note.pitch])));
  assert.equal(score.tempo, result.tempo);
  for (const note of played) assert(note[2] > 0, 'Every audible note has positive duration');
  return {written: heads.length, reattacks: played.length, legatoDestinations: legatoDestinations.size};
}
test('fixed first-seed ten-section request executes the public Python engine', {timeout: 120000}, async t => {
  const result = await generateRandomRiff(availability, 10, compose, {rng: rng(20261105), maxAttemptsPerSection: 8});
  t.diagnostic(JSON.stringify({status: result.status, artists: result.request.artists, mode: result.request.mode,
    attempts: result.random_generation.attempts.length, accepted: result.random_generation.successful_sections,
    choices: result.request.sections.map(section => [section.style, section.focus, section.length_q])}));
  assert.equal(result.status, 'generated', JSON.stringify(result.refusals.at(-1)));
  assert.equal(result.sections.length, 10); assert(result.events.length > 10);
  assert.equal(new Set(result.events.flatMap(event => event.members.map(member => member.id))).size,
    result.events.reduce((sum, event) => sum + event.members.length, 0));
  const whole = compose(result.request);
  assert.equal(whole.status, 'generated');
  assert.deepEqual(result.events, whole.events, 'Random assembly must retain the canonical whole-engine member IDs and clocks');
  assert.deepEqual(result.sections, whole.sections, 'Normal regeneration must not rewrite untouched section identities or evidence');
  await t.test('native alphaTab preserves written notes and audible legato destinations', {skip: at ? false : 'Native alphaTab is not installed'}, () => {
    assert.deepEqual(checkNative(result), {written: 349, reattacks: 344, legatoDestinations: 5});
  });
});

test('fixed first-seed one-section request executes the public Python engine', {timeout: 120000}, async t => {
  const result = await generateRandomRiff(availability, 1, compose, {rng: rng(73051), maxAttemptsPerSection: 8});
  t.diagnostic(JSON.stringify({status: result.status, request: result.request, attempts: result.random_generation.attempts.length}));
  assert.equal(result.status, 'generated', JSON.stringify(result.refusals.at(-1)));
  assert.equal(result.sections.length, 1); assert(result.events.length > 0);
  await t.test('native alphaTab plays all random single-section onsets and pitches', {skip: at ? false : 'Native alphaTab is not installed'}, () => checkNative(result));
});

test('all fields excluded still generate new actual music from fresh seeds', {timeout: 120000}, async t => {
  const current = currentSettings(), before = structuredClone(current);
  const first = await generateRandomRiff(availability, 1, compose, {rng: rng(401), current, exclude: allExclusions});
  const second = await generateRandomRiff(availability, 1, compose, {rng: rng(402), current, exclude: allExclusions});
  t.diagnostic(JSON.stringify({first: first.status, second: second.status, seeds: [first.request.sections[0].seed, second.request.sections[0].seed],
    attempts: [first.random_generation.attempts.length, second.random_generation.attempts.length]}));
  assert.equal(first.status, 'generated'); assert.equal(second.status, 'generated'); assert.deepEqual(current, before);
  for (const result of [first, second]) {
    assert.deepEqual(result.request.artists, current.artists); assert.equal(result.request.mode, current.mode); assert.equal(result.request.tempo, current.tempo);
    for (const key of ['style', 'focus', 'length_q']) assert.equal(result.request.sections[0][key], current.sections[0][key]);
    assert.notEqual(result.request.sections[0].seed, current.sections[0].seed);
  }
  assert.notDeepEqual(first.events, second.events, 'The locked settings allow new music through independently sampled seeds');
  await t.test('locked-settings examples retain native playback', {skip: at ? false : 'Native alphaTab is not installed'}, () => {
    checkNative(first); checkNative(second);
  });
});
