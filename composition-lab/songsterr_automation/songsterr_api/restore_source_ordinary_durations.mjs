// GP5's alphaTab importer falls back to Quarter for base duration 128. Restore
// only this observed loss, authenticated by source fraction, bridge notation,
// and the same ordinary note/rest occurrence. Native clocks are rebuilt later.
function fractionEqual(source, value, dots, enters, times) {
  const d = source.duration;
  if (!Array.isArray(d) || d.length !== 2 || !d.every(n => Number.isSafeInteger(n) && n > 0)) return false;
  if (![value, enters, times].every(n => Number.isSafeInteger(n) && n > 0) || !Number.isInteger(dots) || dots < 0 || dots > 2) return false;
  const power = 2n ** BigInt(dots);
  return BigInt(d[0]) * BigInt(value) * power * BigInt(enters) === BigInt(d[1]) * (2n * power - 1n) * BigInt(times);
}
const ordinary = row => !row.graceNote;
const tuplets = beat => beat.tupletNumerator === -1 && beat.tupletDenominator === -1 ? [1, 1] : [beat.tupletNumerator, beat.tupletDenominator];
function membersMatch(source, beat, track, staff, percussion) {
  const raw = (source.notes || []).filter(n => !n.rest);
  if (raw.length !== beat.notes.length || (raw.length === 0) !== beat.isRest) return false;
  const expected = raw.map(n => percussion ? [n.fret] : [n.string, !!n.dead, n.dead ? null : n.fret]);
  const actual = beat.notes.map(n => {
    if (!percussion) return [staff.tuning.length - n.string, !!n.isDead, n.isDead ? null : n.fret];
    // This repair precedes percussion-table restoration. If a native table
    // already exists, compare its declared source articulation ID.
    const id = track.percussionArticulations.length ? track.percussionArticulations[n.percussionArticulation]?.id : n.percussionArticulation;
    return [id];
  });
  const sorted = values => values.map(v => JSON.stringify(v)).sort();
  return JSON.stringify(sorted(expected)) === JSON.stringify(sorted(actual));
}

export function restoreSourceOrdinaryDurations(score, parts, bridgeNotation, at) {
  const writes = [], locations = [];
  if (!parts) return {restored128thBeats: 0, locations};
  for (const [ti, source] of parts.entries()) {
    const hasCandidate = source.measures?.some(m => m.voices?.some(v => v.beats?.some(b => ordinary(b) && b.type === 128)));
    if (!hasCandidate) continue;
    const track = score.tracks[ti], staff = track?.staves[0], percussion = source.instrumentId === 1024;
    if (score.tracks.length !== parts.length || track?.staves.length !== 1 || staff.bars.length !== source.measures.length || staff.isPercussion !== percussion ||
        !percussion && JSON.stringify(staff.tuning) !== JSON.stringify(source.tuning)) throw Error(`128th staff correspondence mismatch at ${ti}`);
    for (const [mi, measure] of source.measures.entries()) for (const [vi, voice] of (measure.voices || []).entries()) {
      const rows = voice.beats || [];
      if (!rows.some(b => ordinary(b) && b.type === 128)) continue;
      const expected = rows.flatMap((b, i) => ordinary(b) ? [{b, i}] : []);
      const actual = (staff.bars[mi].voices[vi]?.beats || []).filter(b => b.graceType === at.model.GraceType.None && !b.isEmpty);
      if (expected.length !== actual.length) throw Error(`128th ordinary occurrence mismatch at ${ti}:${mi}:${vi}`);
      for (let bi = 0; bi < expected.length; bi++) {
        const {b: raw, i: sourceIndex} = expected[bi], beat = actual[bi], loc = `${ti}:${mi}:${vi}:${sourceIndex}`;
        if (raw.type !== 128) continue;
        if (!membersMatch(raw, beat, track, staff, percussion)) throw Error(`128th note/rest identity mismatch at ${loc}`);
        const [enters, times] = tuplets(beat);
        if (beat.duration === 128 && fractionEqual(raw, 128, beat.dots, enters, times)) continue;
        const lane = bridgeNotation?.[ti]?.[mi]?.[vi], notation = lane?.[sourceIndex];
        // Do not infer bridge alignment when grace conversion changed its
        // inventory. Existing grace restorers own those cases.
        if (lane?.length !== rows.length || notation?.value !== 128 || notation.dots !== (raw.dots || 0) ||
            !fractionEqual(raw, notation.value, notation.dots, notation.enters, notation.times)) throw Error(`128th bridge notation authentication failed at ${loc}`);
        // Native GP7 preserves this notation but its current tick calculation
        // loses the fractional second dot (51 rather than 52.5 ticks). Do not
        // certify that independent playback defect as a successful repair.
        if (notation.dots === 2) throw Error(`Unsupported double-dotted 128th native timing at ${loc}`);
        if (beat.duration !== at.model.Duration.Quarter || beat.dots !== (notation.dots ? 1 : 0) ||
            enters !== notation.enters || times !== notation.times) throw Error(`Unsupported 128th native duration mismatch at ${loc}`);
        writes.push({beat, dots: notation.dots}); locations.push(loc);
      }
    }
  }
  // Refuse the complete repair before changing any score object.
  for (const {beat, dots} of writes) {beat.duration = 128; beat.dots = dots;}
  return {restored128thBeats: writes.length, locations};
}
