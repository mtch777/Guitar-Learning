// Restore explicit PITCHED source grace declarations after complete voice alignment.
// Native finish() owns metric/performed clocks. This module never writes clocks.
export function restoreSourceGraces(score, parts, types) {
  if (!types || !Number.isInteger(types.None) || !Number.isInteger(types.OnBeat) ||
      !Number.isInteger(types.BeforeBeat) || new Set([types.None, types.OnBeat, types.BeforeBeat]).size !== 3) {
    throw Error('Explicit native grace types required');
  }
  if (!Array.isArray(parts) || score.tracks.length !== parts.length) throw Error('Grace track correspondence mismatch');
  const writes = [], witnesses = [];
  let checkedBeats = 0, checkedNotes = 0, graceBeats = 0, graceNotes = 0, uncheckedPercussionGraceBeats = 0;
  const kind = beat => {
    const value = beat.graceNote;
    if (value === undefined || value === null || value === false) return types.None;
    if (value === 'onBeat') return types.OnBeat;
    if (value === 'beforeBeat') return types.BeforeBeat;
    throw Error('Unknown source grace declaration');
  };
  const durationEqual = (source, native) => {
    const d = source.duration;
    const noTuplet = native.tupletNumerator === -1 && native.tupletDenominator === -1;
    const tn = noTuplet ? 1 : native.tupletNumerator, td = noTuplet ? 1 : native.tupletDenominator;
    if (!Array.isArray(d) || d.length !== 2 || !d.every(x => Number.isSafeInteger(x) && x > 0) ||
        !Number.isSafeInteger(native.duration) || native.duration <= 0 ||
        !Number.isInteger(native.dots) || native.dots < 0 || native.dots > 8 ||
        !Number.isSafeInteger(tn) || tn <= 0 ||
        !Number.isSafeInteger(td) || td <= 0) return false;
    const power = 2n ** BigInt(native.dots);
    const numerator = (2n * power - 1n) * BigInt(td);
    const denominator = BigInt(native.duration) * power * BigInt(tn);
    return BigInt(d[0]) * denominator === BigInt(d[1]) * numerator;
  };
  for (let ti = 0; ti < parts.length; ti++) {
    const raw = parts[ti], track = score.tracks[ti];
    if (raw.partId !== ti || track.index !== ti) throw Error('Grace source/native part order mismatch');
    for (const [mi, measure] of (raw.measures || []).entries()) {
      for (const [vi, voice] of (measure.voices || []).entries()) {
        const source = voice.beats || [];
        if (raw.instrumentId === 1024) {
          uncheckedPercussionGraceBeats += source.filter(b => !!b.graceNote).length;
          continue;
        }
        const modes = source.map(kind);
        if (!modes.some(x => x !== types.None)) continue;
        const where = `${ti}:${mi}:${vi}`;
        if (!Number.isInteger(raw.instrumentId) || raw.instrumentId < 0 || raw.instrumentId > 127) throw Error(`Unknown pitched source program at ${where}`);
        if (track.staves.length !== 1) throw Error(`Grace staff correspondence mismatch at ${where}`);
        const staff = track.staves[0];
        const capo = raw.capo ?? 0;
        if (staff.isPercussion || !Array.isArray(raw.tuning) || !raw.tuning.length || !raw.tuning.every(Number.isInteger) ||
            JSON.stringify(staff.tuning) !== JSON.stringify(raw.tuning) || !Number.isInteger(capo) || capo < 0 || staff.capo !== capo) {
          throw Error(`Grace instrument/tuning correspondence mismatch at ${where}`);
        }
        const native = staff.bars[mi]?.voices[vi]?.beats;
        if (!native || native.length !== source.length) throw Error(`Grace beat correspondence mismatch at ${where}`);
        const groups = [];
        for (let bi = 0; bi < source.length; bi++) {
          if (modes[bi] === types.None) continue;
          const start = bi, mode = modes[bi];
          while (bi + 1 < source.length && modes[bi + 1] !== types.None) {
            if (modes[++bi] !== mode) throw Error(`Mixed source grace group at ${where}:${start}`);
          }
          if (bi + 1 === source.length || !(source[bi + 1].notes || []).some(n => !n.rest)) {
            throw Error(`Grace group has no ordinary host in this bar at ${where}:${start}`);
          }
          groups.push({first_source_beat: start, last_source_beat: bi, host_source_beat: bi + 1, grace_type: mode});
        }
        for (let bi = 0; bi < source.length; bi++) {
          const a = source[bi], b = native[bi], mode = modes[bi], notes = (a.notes || []).filter(n => !n.rest);
          if (b.isEmpty || ![types.None, types.OnBeat, types.BeforeBeat].includes(b.graceType)) {
            throw Error(`Unsupported native grace/empty beat at ${where}:${bi}`);
          }
          if (mode === types.None && (b.graceType !== types.None || !durationEqual(a, b))) {
            throw Error(`Ordinary beat identity/duration mismatch at ${where}:${bi}`);
          }
          if (notes.length !== b.notes.length || mode !== types.None && !notes.length) {
            throw Error(`Grace note cardinality mismatch at ${where}:${bi}`);
          }
          const sourceKeys = new Set(), nativeKeys = new Map(), sourceStrings = new Set(), nativeStrings = new Set();
          for (const n of b.notes) {
            const key = `${staff.tuning.length - n.string}:${n.fret}`;
            if (nativeKeys.has(key) || nativeStrings.has(n.string)) throw Error(`Ambiguous native member at ${where}:${bi}`);
            nativeKeys.set(key, n); nativeStrings.add(n.string);
          }
          for (const n of notes) {
            if (!Number.isSafeInteger(n.fret) || n.fret < 0 || (!Number.isInteger(n.string) || n.string < 0 || n.string >= raw.tuning.length)) {
              throw Error(`Unsupported source member at ${where}:${bi}`);
            }
            const key = `${n.string}:${n.fret}`;
            if (sourceKeys.has(key) || sourceStrings.has(n.string) || !nativeKeys.has(key)) throw Error(`Grace member correspondence mismatch at ${where}:${bi}`);
            sourceKeys.add(key); sourceStrings.add(n.string); checkedNotes++;
            if (mode !== types.None) {
              if (n.ghost !== undefined && typeof n.ghost !== 'boolean') throw Error(`Unknown source ghost declaration at ${where}:${bi}`);
              const target = nativeKeys.get(key), ghost = n.ghost === true;
              if (target.isGhost !== ghost) writes.push({target, key: 'isGhost', value: ghost});
              graceNotes++;
            }
          }
          checkedBeats++;
          if (mode !== types.None) {
            graceBeats++;
            if (b.graceType !== mode) writes.push({target: b, key: 'graceType', value: mode});
          }
        }
        witnesses.push({track: ti, bar_zero_based: mi, voice: vi, source_and_native_beats: source.length, groups});
      }
    }
  }
  // No partial repairs when a later voice or member fails authentication.
  for (const write of writes) write.target[write.key] = write.value;
  return {
    schema: 'identity-checked-pitched-source-graces/1', checkedBeats, checkedNotes, graceBeats, graceNotes, uncheckedPercussionGraceBeats,
    restoredGraceTypes: writes.filter(x => x.key === 'graceType').length,
    restoredGhostFlags: writes.filter(x => x.key === 'isGhost').length, witnesses,
    limitations: ['Pitched tracks only; percussion grace declarations remain unchecked and unchanged', 'Exact one-to-one voice/beat/member scope only', 'Native finish normalizes grace glyph durations and chooses performed time; neither is asserted equal to source performance', 'No inferred grace execution, host-string recovery or collapsed-group reconstruction']
  };
}
