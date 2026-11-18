import test from 'node:test';
import assert from 'node:assert/strict';
import {LessonEngine} from '../public/piano/learning-songs/lesson-engine.js';

const group = (time, pitches, prefix = `at-${time}`) => ({
  time, endTime: time + 0.5,
  notes: pitches.map((midi, index) => ({id: `${prefix}-${index}`, midi, duration: 1})),
});

test('wait mode requires every chord key, preserves partial hits, and rejects the wrong octave', () => {
  const lesson = new LessonEngine([group(0, [60, 64, 67, 60]), group(1, [60])]);
  lesson.start();
  assert.equal(lesson.grade(72).outcome, 'wrong');
  assert.equal(lesson.currentIndex, 0);
  assert.equal(lesson.hits, 0);

  let state = lesson.grade(64, 20);
  assert.equal(state.outcome, 'hit');
  assert.deepEqual(state.requiredPitches, [60, 67]);
  assert.equal(state.currentIndex, 0);
  assert.equal(lesson.grade(64).outcome, 'duplicate');
  assert.equal(lesson.wrong, 1);
  state = lesson.update(1000);
  assert.equal(state.misses, 0, 'Waiting has no timing deadline.');
  assert.equal(state.statuses.get('at-0-1'), 'hit');

  state = lesson.grade(60);
  assert.deepEqual(state.hitIds, ['at-0-0', 'at-0-3'], 'One physical key satisfies same-onset unisons.');
  assert.equal(state.currentIndex, 0);
  state = lesson.grade(67);
  assert.equal(state.currentIndex, 1);
  assert.equal(state.hits, 4);
  assert.equal(state.statuses.get('at-1-0'), 'pending', 'The first C strike cannot also satisfy a later C.');
  assert.equal(lesson.update(2000).currentIndex, 1);
  state = lesson.grade(60);
  assert.equal(state.complete, true);
  assert.equal(state.hits, 5);
  assert.equal(state.running, false);
});

test('wait mode cannot skip to a later pitch and skips rests without inventing tie attacks', () => {
  // Upstream has combined the tied C into one four-second attack and omitted
  // its continuation heads. Empty groups are rest positions, not requirements.
  const lesson = new LessonEngine([
    {time: 0, notes: []},
    {time: 1, endTime: 5, notes: [{id: 'c-tied', midi: 60, duration: 8, noteIds: ['c1', 'c2', 'c3']}]},
    {time: 3, notes: []},
    group(6, [62]),
  ]);
  assert.equal(lesson.currentIndex, 1);
  lesson.start();
  assert.equal(lesson.grade(62).outcome, 'wrong');
  assert.equal(lesson.currentIndex, 1);
  assert.equal(lesson.grade(60).currentIndex, 3);
  assert.equal(lesson.total, 2, 'Tied continuation IDs are rendering metadata, not additional attacks.');
  assert.equal(lesson.grade(62).complete, true);
});

test('timed mode marks each missed chord note red while preserving already green notes', () => {
  const lesson = new LessonEngine([group(1, [60, 64, 67]), group(2, [72])], {mode: 'timed'});
  lesson.start();
  assert.equal(lesson.grade(60, 1).outcome, 'hit');
  const state = lesson.update(1.181);
  assert.deepEqual(state.missIds, ['at-1-1', 'at-1-2']);
  assert.deepEqual([...state.statuses.values()], ['hit', 'miss', 'miss', 'pending']);
  assert.equal(state.hits, 1);
  assert.equal(state.misses, 2);
  assert.equal(state.currentIndex, 1);
  assert.equal(lesson.grade(64, 1.2).outcome, 'wrong');
  assert.equal(lesson.statuses.get('at-1-1'), 'miss', 'Late strikes cannot repaint misses.');
  assert.equal(lesson.update(20).misses, 3);
  assert.equal(lesson.update(30).misses, 3, 'Repeated frames cannot count one miss twice.');
  assert.equal(lesson.statuses.get('at-1-0'), 'hit');
});

test('timing windows include both exact boundaries and exclude genuinely early or late strikes', () => {
  for (const strike of [0.82, 1.18]) {
    const lesson = new LessonEngine([group(1, [60])], {mode: 'timed'});
    lesson.start();
    if (strike === 1.18) assert.equal(lesson.update(strike).misses, 0);
    assert.equal(lesson.grade(60, strike).outcome, 'hit', `${strike} is on the inclusive boundary.`);
  }
  const early = new LessonEngine([group(1, [60])], {mode: 'timed'});
  early.start();
  assert.equal(early.grade(60, 0.819).outcome, 'wrong');
  assert.equal(early.hits, 0);
  assert.equal(early.statuses.get('at-1-0'), 'pending');
  const late = new LessonEngine([group(1, [60]), group(2, [62])], {mode: 'timed'});
  late.start();
  assert.equal(late.grade(60, 1.181).outcome, 'wrong');
  assert.equal(late.statuses.get('at-1-0'), 'miss');
});

test('one timed strike selects the nearest unhit occurrence, with an earlier-onset tie break', () => {
  const lesson = new LessonEngine([group(1, [60]), group(1.2, [60])], {mode: 'timed'});
  lesson.start();
  let state = lesson.grade(60, 1.15);
  assert.deepEqual(state.hitIds, ['at-1.2-0']);
  assert.equal(state.currentIndex, 0, 'An earlier unresolved occurrence is still required.');
  assert.equal(state.statuses.get('at-1-0'), 'pending');
  state = lesson.grade(60, 1.17);
  assert.deepEqual(state.hitIds, ['at-1-0']);
  assert.equal(state.complete, true);

  const tiedDistance = new LessonEngine([group(1, [60]), group(1.2, [60])], {mode: 'timed'});
  tiedDistance.start();
  assert.deepEqual(tiedDistance.grade(60, 1.1).hitIds, ['at-1-0']);
  assert.equal(tiedDistance.statuses.get('at-1.2-0'), 'pending');
});

test('timed unisons share a strike but a repeated pitch at a later onset needs another strike', () => {
  const lesson = new LessonEngine([group(1, [60, 60]), group(2, [60])], {mode: 'timed'});
  lesson.start();
  assert.equal(lesson.grade(60, 1).hitIds.length, 2);
  assert.equal(lesson.grade(60, 1.01).outcome, 'duplicate');
  assert.equal(lesson.hits, 2);
  assert.equal(lesson.wrong, 0);
  assert.equal(lesson.update(2).statuses.get('at-2-0'), 'pending');
  assert.equal(lesson.grade(60, 2).complete, true);
});

test('a missing frame cannot let an expired note match a later strike', () => {
  const lesson = new LessonEngine([group(0, [60]), group(3, [60])], {mode: 'timed'});
  lesson.start();
  const state = lesson.grade(60, 3);
  assert.deepEqual(state.missIds, ['at-0-0']);
  assert.deepEqual(state.hitIds, ['at-3-0']);
  assert.equal(state.hits, 1);
  assert.equal(state.misses, 1);
  assert.equal(state.complete, true);
});

test('pause ignores queued input and time updates; resume uses the caller frozen elapsed clock', () => {
  const lesson = new LessonEngine([group(1, [60]), group(2, [62])], {mode: 'timed'});
  lesson.start();
  lesson.grade(60, 1);
  lesson.pause();
  assert.equal(lesson.update(90).elapsed, 1);
  assert.equal(lesson.grade(62, 90).reason, 'paused');
  assert.equal(lesson.misses, 0);
  assert.equal(lesson.hits, 1);
  assert.equal(lesson.start(1).running, true);
  assert.equal(lesson.grade(62, 2).complete, true);
});

test('mode changes preserve grades and pause; explicit reset alone clears results', () => {
  const lesson = new LessonEngine([group(1, [60, 64]), group(2, [67])], {mode: 'timed'});
  lesson.start();
  lesson.grade(60, 1);
  lesson.grade(61, 1.1);
  lesson.update(1.2);
  let state = lesson.setMode('wait');
  assert.equal(state.running, false);
  assert.equal(state.hits, 1);
  assert.equal(state.misses, 1);
  assert.equal(state.wrong, 1);
  assert.equal(state.currentIndex, 1);
  lesson.start();
  assert.equal(lesson.grade(67).complete, true);
  state = lesson.reset();
  assert.equal(state.mode, 'wait');
  assert.equal(state.elapsed, 0);
  assert.equal(state.currentIndex, 0);
  assert.equal(state.running, false);
  assert.equal(state.complete, false);
  assert.deepEqual([state.hits, state.misses, state.wrong, state.pending], [0, 0, 0, 3]);
  assert.ok([...state.statuses.values()].every(status => status === 'pending'));
});

test('empty lessons complete cleanly, and a count-in allows an early first-note strike', () => {
  for (const groups of [[], [{time: 0, notes: []}]]) {
    const lesson = new LessonEngine(groups);
    assert.equal(lesson.start().complete, true);
    assert.equal(lesson.running, false);
    assert.equal(lesson.grade(60).reason, 'complete');
    assert.equal(lesson.wrong, 0);
  }
  const countIn = new LessonEngine([group(0, [60])], {mode: 'timed'});
  countIn.start(-1);
  assert.equal(countIn.grade(60, -0.18).outcome, 'hit');
});

test('out-of-order callbacks and invalid input do not rewind or corrupt a live lesson', () => {
  const lesson = new LessonEngine([group(1, [60]), group(2, [62])], {mode: 'timed'});
  lesson.start();
  lesson.update(0.9);
  assert.equal(lesson.grade(60, 0.8).reason, 'stale-time');
  assert.equal(lesson.update(0).elapsed, 0.9);
  assert.equal(lesson.grade('60', 0.9).reason, 'invalid-pitch');
  assert.equal(lesson.grade(128, 0.9).reason, 'invalid-pitch');
  assert.equal(lesson.wrong, 0);
  assert.throws(() => lesson.setMode('other'), /mode/);
  assert.equal(lesson.mode, 'timed');
  assert.equal(lesson.running, true, 'Invalid configuration must not partially pause or mutate the session.');
  assert.throws(() => lesson.update(NaN), /finite/);
  assert.throws(() => lesson.start(0), /rewind/);
  assert.equal(lesson.grade(60, 1).outcome, 'hit');
});

test('input and snapshots cannot mutate engine grades or alter the source attacks', () => {
  const input = [group(1, [60, 64])];
  const original = JSON.stringify(input);
  const lesson = new LessonEngine(input);
  lesson.start();
  lesson.grade(60);
  assert.equal(JSON.stringify(input), original);
  input[0].notes[1].midi = 12;
  const state = lesson.snapshot();
  state.statuses.set('at-1-1', 'hit');
  state.requiredPitches.length = 0;
  assert.equal(lesson.statuses.get('at-1-1'), 'pending');
  assert.deepEqual(lesson.snapshot().requiredPitches, [64]);
  assert.equal(lesson.grade(64).complete, true);
});

test('constructor rejects ambiguous note identities, clocks, pitches and duplicate onset groups', () => {
  assert.throws(() => new LessonEngine([group(2, [60]), group(1, [62])]), /ordered/);
  assert.throws(() => new LessonEngine([group(0, [60]), group(0, [62], 'other')]), /Simultaneous/);
  assert.throws(() => new LessonEngine([{time: 0, notes: [{id: 'a', midi: 60}, {id: 'a', midi: 64}]}]), /Duplicate/);
  assert.throws(() => new LessonEngine([{time: 0, notes: [{midi: 60}]}]), /stable id/);
  assert.throws(() => new LessonEngine([group(0, [128])]), /MIDI/);
  assert.throws(() => new LessonEngine([group(-1, [60])]), /nonnegative/);
  assert.throws(() => new LessonEngine([{...group(2, [60]), endTime: 1}]), /endTime/);
  assert.throws(() => new LessonEngine([], {timingWindowMs: -1}), /timing window/);
});
