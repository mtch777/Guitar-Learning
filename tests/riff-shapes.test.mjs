import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {buildShapeTimeline, shapeAt, playbackShapeFrame} from '../src/riff-shapes.js';
import {normalizeEvents} from '../src/riff-event-score.js';

const tuning = [64, 59, 55, 50, 45, 40, 35, 28];
const ref = (id = 'A') => ({palette_id: `p${id}`, riff_id: `r${id}`, shape_id: `s${id}`});
const contact = (string_number, fret, roles = ['core'], id = 'A') => ({string_number, fret, pitch: tuning[string_number - 1] + fret,
  roles, sources: [{...ref(id), roles: [...roles]}]});
const used = (point, as_fretting = true, as_tapping = false) => ({string_number: point.string_number, fret: point.fret, pitch: point.pitch, as_fretting, as_tapping});
function metadata(frets = [5, 7], id = 'A') {
  const ordinary_contacts = frets.map(fret => contact(8, fret, ['core'], id));
  return {schema: 'riff-shape-use/1', mode: 'Aeolian', kind: frets.length >= 2 ? 'shape_window' : frets.length === 1 ? 'single_contact_context' : 'no_fretted_contact',
    ordinary_fret_bounds: frets.length ? [Math.min(...frets), Math.max(...frets)] : null,
    ordinary_contacts, tapped_contacts: [], used_contacts: ordinary_contacts.map(point => used(point)),
    open_strings_played: [], reference_shapes: [ref(id)]};
}
const block = (shape_usage = metadata(), offset_q = '0', duration_q = '4') => ({offset_q, duration_q, shape_usage});
const section = (blocks, offset_q = '0', length_q = '16') => ({offset_q, length_q, blocks});
const result = sections => ({tuning, sections});

test('later sections and fractional offsets form exact half-open spans and deterministic seeks', () => {
  const timeline = buildShapeTimeline(result([section([block()], '0', '4'),
    section([block(metadata([8, 10]), '1/3', '2/3'), block(metadata([10, 12]), '1', '3')], '4', '4')]));
  assert.equal(timeline.issues.length, 0);
  assert.deepEqual(timeline.spans.map(span => [span.start_q, span.end_q]), [['0', '4'], ['13/3', '5'], ['5', '8']]);
  assert.equal(shapeAt(timeline, '13/3').sectionIndex, 1); assert.equal(shapeAt(timeline, '13/3').blockIndex, 0);
  assert.equal(shapeAt(timeline, 5).blockIndex, 1); assert.equal(shapeAt(timeline, 8), null);
  assert.equal(shapeAt(timeline, 4), null); assert.equal(shapeAt(timeline, -1), null); assert.equal(shapeAt(timeline, NaN), null);
  assert.equal(shapeAt(timeline, 'bad'), null);
  assert.equal(shapeAt(timeline, 1), shapeAt(timeline, 1));
});

test('same displayed geometry ignores source IDs, ordering and unused tap candidates', () => {
  const first = metadata(), second = metadata([7, 5], 'B');
  second.tapped_contacts = [contact(1, 22, ['tapped'], 'Z')];
  second.reference_shapes.push(ref('Z'));
  const timeline = buildShapeTimeline(result([section([block(first), block(second, '4')])]));
  assert.equal(timeline.spans[0].color, 'blue'); assert.equal(timeline.spans[1].color, 'blue');
  assert.equal(timeline.spans[0].shapeNumber, 1); assert.equal(timeline.spans[1].shapeNumber, 1);
  assert.equal(timeline.spans[1].contacts.length, 2); assert.equal(timeline.spans[1].tappedContacts.length, 1);
});

test('actual transitions alternate colors while returning shapes retain their first-seen number', () => {
  const timeline = buildShapeTimeline(result([section([
    block(metadata()), block(metadata([8, 10]), '4'), block(metadata([11, 13]), '8'), block(metadata(), '12')])]));
  assert.deepEqual(timeline.spans.map(span => span.shapeNumber), [1, 2, 3, 1]);
  assert.deepEqual(timeline.spans.map(span => span.color), ['blue', 'orange', 'blue', 'orange']);
});

test('mixed provenance keeps all roles, core wins display and extensions remain dotted', () => {
  const mixed = metadata();
  mixed.ordinary_contacts[0].roles = ['extension', 'core'];
  mixed.ordinary_contacts[0].sources.push({...ref('B'), roles: ['extension']});
  mixed.ordinary_contacts[1].roles = ['extension']; mixed.ordinary_contacts[1].sources[0].roles = ['extension'];
  mixed.reference_shapes.push(ref('B'), ref('B'));
  const span = buildShapeTimeline(result([section([block(mixed)])])).spans[0];
  assert.equal(span.status, 'available'); assert.equal(span.referenceCount, 2); assert.equal(span.composite, true);
  assert.deepEqual(span.contacts[0].roles, ['core', 'extension']); assert.equal(span.contacts[0].sources.length, 2);
  assert.equal(span.contacts[0].displayRole, 'core'); assert.equal(span.contacts[0].dotted, false);
  assert.equal(span.contacts[1].displayRole, 'extension'); assert.equal(span.contacts[1].dotted, true);
  const sameVisual = structuredClone(mixed); sameVisual.ordinary_contacts[0].roles = ['core'];
  const timeline = buildShapeTimeline(result([section([block(mixed), block(sameVisual, '4')])]));
  assert.deepEqual(timeline.spans.map(value => value.shapeNumber), [1, 1]);
});

test('procedural pooled palettes retain honest provenance without source score identifiers', () => {
  const shape = metadata();
  const publicRef = {palette_id: 'pool-123', artist: 'Invent Animate', provenance_hashes: ['a'.repeat(24)]};
  shape.reference_shapes = [publicRef];
  for (const point of shape.ordinary_contacts) point.sources = [{palette_id: 'pool-123', artist: 'Invent Animate', roles: point.roles}];
  const input = {tuning, phrases: [section([block(shape)])]};
  const before = structuredClone(input), timeline = buildShapeTimeline(input);
  assert.deepEqual(timeline.issues, []);
  assert.equal(timeline.spans[0].status, 'available');
  assert.deepEqual(timeline.spans[0].referenceShapes, [{...publicRef, riff_id: null, shape_id: null}]);
  assert.deepEqual(input, before);
  for (const bad of [{}, {...publicRef, palette_id: 2}, {...publicRef, provenance_hashes: ['source path']}, {...publicRef, artist: 'Other'}]) {
    const invalid = structuredClone(shape); invalid.reference_shapes = [bad];
    assert.equal(buildShapeTimeline({tuning, phrases: [section([block(invalid)])]}).spans[0].status, 'unavailable');
  }
});

test('only actually used tapping contacts outside the ordinary window are displayed', () => {
  const shape = metadata(); const tap = contact(2, 17, ['tapped']);
  shape.tapped_contacts.push(tap, contact(1, 22, ['tapped'])); shape.used_contacts.push(used(tap, false, true));
  const span = buildShapeTimeline(result([section([block(shape)])])).spans[0];
  assert.equal(span.contacts.length, 3); assert.equal(span.contacts[2].key, '1:17'); assert.equal(span.contacts[2].displayRole, 'tapped');
  assert.equal(span.usedContacts.find(point => point.key === '1:17').as_tapping, true);
  assert(!span.contacts.some(point => point.fret === 22));
});

test('a constructed search domain displays the complete planned shape, not unused eligible notes', () => {
  const shape = metadata([5, 7, 9, 11]);
  shape.used_contacts = shape.used_contacts.slice(0, 2);
  shape.ordinary_contacts[1].roles = ['extension'];
  shape.ordinary_contacts[1].sources[0].roles = ['extension'];
  const tap = contact(2, 17, ['tapped']);
  shape.tapped_contacts = [tap, contact(1, 22, ['tapped'])];
  shape.used_contacts.push(used(tap, false, true));
  shape.context_origin = 'constructed_local_domain_from_observed_contacts';
  const input = result([section([block(shape)])]), before = structuredClone(input);
  const timeline = buildShapeTimeline(input), span = shapeAt(timeline, 0);
  assert.deepEqual(timeline.issues, []);
  assert.deepEqual(span.contacts.map(point => point.key), ['1:17', '7:5', '7:7']);
  assert.equal(span.contacts.find(point => point.fret === 7).dotted, true);
  assert.equal(span.contacts.find(point => point.fret === 17).displayRole, 'tapped');
  assert.equal(span.ordinaryContacts.length, 4, 'Preserve the actual search domain as metadata');
  assert.equal(span.outlineKind, 'planned_contacts');
  assert.deepEqual(shapeAt(timeline, 3).contacts, span.contacts, 'Show the whole planned shape throughout its context');
  assert.deepEqual(input, before);
  shape.context_origin = 'observed_palette_modal_subset';
  const observed = buildShapeTimeline(result([section([block(shape)])])).spans[0];
  assert.equal(observed.contacts.length, 5, 'An identified reference shape retains its reference outline');
  assert.equal(observed.outlineKind, 'reference_shape');
});

test('single contacts, open-only and tapping-only contexts are not numbered shapes', () => {
  const single = metadata(); single.kind = 'single_contact_context'; single.used_contacts = single.used_contacts.slice(0, 1);
  const open = metadata([]); open.kind = 'open_string_only'; open.open_strings_played = [8];
  const tap = metadata([]); tap.kind = 'tapped_context_only'; tap.tapped_contacts = [contact(1, 17, ['tapped'])]; tap.used_contacts = [used(tap.tapped_contacts[0], false, true)];
  const timeline = buildShapeTimeline(result([section([block(single), block(open, '4'), block(tap, '8')])]));
  assert.equal(timeline.issues.length, 0);
  assert.deepEqual(timeline.spans.map(span => span.contacts.length), [1, 0, 1]);
  assert.deepEqual(timeline.spans.map(span => span.shapeNumber), [null, null, null]);
  assert.deepEqual(timeline.spans.map(span => span.color), [null, null, null]);
  assert.deepEqual(timeline.spans[1].openStrings, [7]);
  assert(timeline.spans.every(span => span.contacts.every(point => point.fret > 0)));
});

test('missing or malformed metadata remains unavailable without reconstructing a shape from notes', () => {
  const invalid = [null, {...metadata(), schema: 'wrong'}, {...metadata(), kind: 'single_contact_context'},
    {...metadata(), ordinary_fret_bounds: [0, 20]}, {...metadata(), open_strings_played: [9]}];
  const zero = metadata(); zero.ordinary_contacts[0].fret = 0; invalid.push(zero);
  const unknownContact = metadata(); unknownContact.used_contacts.push(used(contact(2, 20))); invalid.push(unknownContact);
  for (const value of invalid) {
    const timeline = buildShapeTimeline(result([section([block(value)])]));
    assert.equal(timeline.spans[0].status, 'unavailable'); assert.deepEqual(timeline.spans[0].contacts, []);
    assert.equal(timeline.spans[0].shapeNumber, null); assert.equal(timeline.issues.length, 1);
  }
});

test('invalid timings and overlapping contexts are reported without ambiguous outlines', () => {
  const invalid = buildShapeTimeline(result([section([block(metadata(), '3', '2'), block(metadata(), 'bad')], '0', '4')]));
  assert.equal(invalid.spans.length, 0); assert.equal(invalid.issues.length, 2);
  const nested = buildShapeTimeline(result([section([block(metadata(), '0', '10'), block(metadata(), '1', '1'), block(metadata(), '3', '1')])]));
  assert(nested.spans.every(span => span.status === 'unavailable'));
});

test('written playback highlights notes outside the outline, open labels and silence at exact endings', () => {
  const timeline = buildShapeTimeline(result([section([block()])])), score = {notes: [
    {string: 7, fret: 5, pitch: 33, start: 0, end: 1}, {string: 0, fret: 20, pitch: 84, start: 1, end: 2},
    {string: 7, fret: 0, pitch: 28, start: 1, end: 2}]};
  assert.equal(playbackShapeFrame(timeline, score, 0).activeContacts[0].inOutline, true);
  const changed = playbackShapeFrame(timeline, score, 1);
  assert.deepEqual(changed.activeContacts.map(note => [note.string, note.fret, note.inOutline]), [[0, 20, false]]);
  assert.deepEqual(changed.openStrings, [7]);
  const rest = playbackShapeFrame(timeline, score, 2);
  assert.deepEqual(rest.activeContacts, []); assert.deepEqual(rest.openStrings, []); assert.equal(rest.span.shapeNumber, 1);
  const end = playbackShapeFrame(timeline, score, 4); assert.equal(end.span, null); assert.deepEqual(end.activeContacts, []);
  assert.deepEqual(playbackShapeFrame(timeline, score, NaN).activeContacts, []);
});

test('building and seeking never mutate the result or normalized score', () => {
  const input = result([section([block()])]), score = {notes: [{string: 7, fret: 5, start: 0, end: 1}]};
  const before = structuredClone({input, score}); const timeline = buildShapeTimeline(input);
  playbackShapeFrame(timeline, score, '1/2'); shapeAt(timeline, 2);
  assert.deepEqual({input, score}, before);
});

test('public Python generation supplies usable shape provenance at actual playback clocks', () => {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const local = path.join(root, '.local/songsterr-venv/Scripts/python.exe'), python = existsSync(local) ? local : 'python3';
  const request = {artists: ['Invent Animate'], mode: 'Aeolian', tempo: 142, seed: 1,
    sections: [{style: 'arpeggio', focus: 'single', length_q: '8', seed: 1}, {style: 'pedal', focus: 'single', length_q: '4', seed: 2}]};
  const execution = spawnSync(python, ['-B', '-X', 'utf8', '-c',
    "import gzip,json,sys;from pathlib import Path;from pattern_engine import generate;print(json.dumps(generate(json.loads(sys.stdin.read()),json.loads(gzip.decompress(Path('pattern-pack.json.gz').read_bytes())))))"],
  {cwd: path.join(root, 'public/riff-builder'), input: JSON.stringify(request), encoding: 'utf8', timeout: 30000, maxBuffer: 20 * 1024 * 1024});
  assert.equal(execution.status, 0, execution.stderr || execution.error?.message);
  const generated = JSON.parse(execution.stdout); assert.equal(generated.status, 'generated');
  const timeline = buildShapeTimeline(generated), score = normalizeEvents(generated);
  assert.deepEqual(timeline.issues, []); assert(timeline.spans.some(span => span.kind === 'shape_window'));
  assert.equal(shapeAt(timeline, 8).sectionIndex, 1);
  for (const note of score.notes) {
    const frame = playbackShapeFrame(timeline, score, note.start);
    assert.equal(frame.span.status, 'available');
    if (note.fret) assert(frame.activeContacts.some(point => point.string === note.string && point.fret === note.fret));
    else assert(frame.openStrings.includes(note.string));
  }
  assert.equal(playbackShapeFrame(timeline, score, 12).span, null);
  assert.deepEqual(playbackShapeFrame(timeline, score, 12).activeContacts, []);
});
