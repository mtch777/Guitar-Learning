// Restore source curve coordinates AFTER the final native finish(), before capture/export.
// source_semantics.curve owns the established units: precise percent when non-null,
// otherwise coarse sixtieths; raw tone / 25 is the native half-semitone value.
// This adapter does not infer missing curves, change bend kind/style, or repair execution.
const own = (x, key) => Object.prototype.hasOwnProperty.call(x, key);
const finite = x => typeof x === 'number' && Number.isFinite(x);
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const fail = (message, where) => { throw Error(`Source bend ${message} at ${where}`); };

function sourcePoints(bend, where) {
  if (!bend || typeof bend !== 'object' || Array.isArray(bend) ||
      !Array.isArray(bend.points) || bend.points.length < 2) fail('requires explicit curve points', where);
  const points = [], bases = [], unsupported = new Set();
  if (bend.tone !== undefined && bend.tone !== null && !finite(bend.tone)) fail('malformed declared peak', where);
  for (const key of Object.keys(bend)) {
    if (!['points', 'tone'].includes(key)) unsupported.add(`bend.${key}`);
  }
  for (const point of bend.points) {
    if (!point || typeof point !== 'object' || Array.isArray(point)) fail('malformed point', where);
    if (!finite(point.tone)) fail('malformed tone', where);
    for (const key of Object.keys(point)) {
      if (!['position', 'precisePosition', 'tone'].includes(key)) unsupported.add(key);
    }
    for (const [key, maximum] of [['position', 60], ['precisePosition', 100]]) {
      if (point[key] !== undefined && point[key] !== null &&
          (!finite(point[key]) || point[key] < 0 || point[key] > maximum)) fail(`malformed ${key}`, where);
    }
    const precise = point.precisePosition !== undefined && point.precisePosition !== null;
    if (!precise && !finite(point.position)) fail('missing point position', where);
    const offset = precise ? point.precisePosition * 3 / 5 : point.position;
    const value = point.tone / 25;
    if (!finite(offset) || !finite(value)) fail('unrepresentable point', where);
    if (points.length && offset < points.at(-1)[0]) fail('nonmonotonic curve', where);
    points.push([offset, value]);
    bases.push(precise ? 'precise_percent' : 'coarse_sixtieths');
  }
  return {points, bases, unsupported: [...unsupported].sort()};
}

function durationEqual(source, native) {
  const d = source.duration;
  const ordinary = native.tupletNumerator === -1 && native.tupletDenominator === -1;
  const tn = ordinary ? 1 : native.tupletNumerator, td = ordinary ? 1 : native.tupletDenominator;
  if (!Array.isArray(d) || d.length !== 2 || !d.every(x => Number.isSafeInteger(x) && x > 0) ||
      !Number.isSafeInteger(native.duration) || native.duration <= 0 ||
      !Number.isSafeInteger(native.dots) || native.dots < 0 || native.dots > 8 ||
      !Number.isSafeInteger(tn) || tn <= 0 || !Number.isSafeInteger(td) || td <= 0) return false;
  const p = 2n ** BigInt(native.dots);
  return BigInt(d[0]) * BigInt(native.duration) * p * BigInt(tn) ===
    BigInt(d[1]) * (2n * p - 1n) * BigInt(td);
}

function meters(parts) {
  const result = [];
  let current = null;
  for (let mi = 0; mi < Math.max(0, ...parts.map(p => p.measures?.length ?? 0)); mi++) {
    let declared = null;
    for (const p of parts) {
      const signature = p.measures?.[mi]?.signature;
      if (signature === undefined || signature === null) continue;
      if (!Array.isArray(signature) || signature.length !== 2 ||
          !signature.every(x => Number.isSafeInteger(x) && x > 0)) fail('malformed meter', `bar ${mi + 1}`);
      if (declared && !equal(declared, signature)) fail('conflicting meter aliases', `bar ${mi + 1}`);
      declared = signature;
    }
    if (declared) current = declared;
    result.push(current);
  }
  return result;
}

// Opt-in execution scope: one rising bend followed immediately by one tied hold
// in the same voice/bar. Do not infer a curve for an unmarked continuation.
function simpleTiedHold(origin, source, mapping, bi, ni, parsed, model, where) {
  const no = reason => ({eligible: false, reason: `simple_tied_hold:${reason}`});
  if (origin.isTieDestination || origin.tieOrigin || origin.bendOrigin || origin.isContinuedBend ||
      !origin.tieDestination) return no('not_an_independent_origin');
  if (origin.bendType !== model.BendType.Bend || origin.bendStyle !== model.BendStyle.Default) return no('origin_execution');
  const raw = source[bi].notes[ni], next = source[bi + 1];
  if (!next) return no('missing_adjacent_source_target');
  const matches = (next.notes || []).map((n, index) => ({n, index})).filter(({n}) =>
    !n.rest && n.string === raw.string && n.fret === raw.fret && n.tie === true && !n.dead);
  if (matches.length !== 1) return no('missing_or_ambiguous_source_target');
  const {n: rawHold, index} = matches[0], hold = mapping.get(`${bi + 1}:${index}`);
  if (!hold || origin.tieDestination !== hold || hold.tieOrigin !== origin || !hold.isTieDestination ||
      hold.tieDestination || hold.bendOrigin !== origin || hold.string !== origin.string || hold.fret !== origin.fret ||
      hold.beat.voice !== origin.beat.voice || origin.beat.nextBeat !== hold.beat || hold.beat.previousBeat !== origin.beat) {
    return no('unresolved_or_nonlocal_links');
  }
  if (hold.bendStyle !== model.BendStyle.Default) return no('continuation_execution');
  const [start, end] = [parsed.points[0], parsed.points.at(-1)], peak = end[1];
  if (!equal(start, [0, 0]) || end[0] !== 60 || peak <= 0 ||
      !parsed.points.every(([x, y], i) => y >= 0 && y <= peak &&
        (!i || x > parsed.points[i - 1][0] && y >= parsed.points[i - 1][1]))) return no('not_simple_rise_and_hold');
  const native = origin.bendPoints?.map(p => [p.offset, p.value]);
  if (!native?.length || !equal(native[0], start) || !equal(native.at(-1), end) ||
      !native.every(([x, y], i) => finite(x) && finite(y) && y >= 0 && y <= peak &&
        (!i || x > native[i - 1][0] && y >= native[i - 1][1]))) return no('origin_endpoints_or_shape');
  const hasSourceCurve = own(rawHold, 'bend') && rawHold.bend !== null && rawHold.bend !== false;
  if (hasSourceCurve) {
    const declared = sourcePoints(rawHold.bend, `${where}/tie_target`);
    if (declared.unsupported.length || declared.points[0][0] !== 0 || declared.points.at(-1)[0] !== 60 ||
        !declared.points.every(([x, y], i) => y === peak && (!i || x > declared.points[i - 1][0]))) return no('continuation_not_constant_plateau');
  }
  const holdPoints = hold.bendPoints || [];
  if (hasSourceCurve && !holdPoints.length) return no('missing_native_explicit_hold');
  if (holdPoints.length && (hold.bendType !== model.BendType.Hold ||
      holdPoints[0].offset !== 0 || holdPoints.at(-1).offset !== 60 ||
      !holdPoints.every((p, i) => finite(p.offset) && p.value === peak && (!i || p.offset > holdPoints[i - 1].offset)))) {
    return no('native_continuation_not_plateau');
  }
  if (!holdPoints.length && (hold.bendType !== model.BendType.None || hold.isContinuedBend)) return no('missing_native_hold_curve');
  const ticks = b => b.duration[0] * 3840 / b.duration[1];
  const originTicks = ticks(source[bi]), holdTicks = ticks(next);
  if (![originTicks, holdTicks].every(Number.isSafeInteger) ||
      origin.beat.displayDuration !== originTicks || origin.beat.playbackDuration !== originTicks ||
      hold.beat.displayDuration !== holdTicks || hold.beat.playbackDuration !== holdTicks ||
      !finite(origin.beat.absoluteDisplayStart) || !finite(origin.beat.absolutePlaybackStart) ||
      hold.beat.absoluteDisplayStart !== origin.beat.absoluteDisplayStart + originTicks ||
      hold.beat.absolutePlaybackStart !== origin.beat.absolutePlaybackStart + originTicks) return no('host_or_tie_clock');
  return {eligible: true, continuation: hasSourceCurve ? 'explicit_constant_curve_unchanged' : 'unmarked_inherited_hold_no_curve_created',
    source_target: [bi + 1, index], origin_ticks: originTicks, continuation_ticks: holdTicks,
    onset_ticks: origin.beat.absolutePlaybackStart, peak_half_semitones: peak};
}

export function restoreSourceBendPoints(score, parts, model, {restoreSimpleTiedHolds = false} = {}) {
  if (typeof restoreSimpleTiedHolds !== 'boolean') throw Error('restoreSimpleTiedHolds must be boolean');
  if (!model?.Note || !model?.BendPoint || !Number.isInteger(model.BendStyle?.Default)) {
    throw Error('Native note, bend point and style classes required');
  }
  if (!Array.isArray(parts) || !Array.isArray(score?.tracks) || parts.length !== score.tracks.length) {
    throw Error('Source bend track correspondence mismatch');
  }
  const meter = meters(parts), writes = [], witnesses = [], excluded = [], planned = new Set();
  let sourceDeclarations = 0, checkedCurves = 0, unchangedCurves = 0;
  for (const [ti, raw] of parts.entries()) {
    const track = score.tracks[ti];
    if (raw.partId !== ti || track.index !== ti) fail('part order mismatch', ti);
    for (const [mi, measure] of (raw.measures || []).entries()) {
      for (const [vi, voice] of (measure.voices || []).entries()) {
        const source = voice.beats || [], declarations = [];
        for (const [bi, beat] of source.entries()) {
          for (const [ni, note] of (beat.notes || []).entries()) {
            if (!own(note, 'bend') || note.bend === null || note.bend === false) continue;
            sourceDeclarations++;
            const source_ref = `part:${ti}/measures/${mi}/voices/${vi}/beats/${bi}/notes/${ni}`;
            const parsed = sourcePoints(note.bend, source_ref);
            let reason = null;
            if (raw.instrumentId === 1024) reason = 'percussion_note';
            else if (beat.graceNote) reason = 'grace_note';
            else if (note.rest === true || note.dead === true) reason = 'rest_or_dead_note';
            else if (parsed.unsupported.length) reason = `unsupported_point_fields:${parsed.unsupported.join(',')}`;
            if (reason) excluded.push({source_ref, reason});
            else declarations.push({bi, ni, source_ref, parsed});
          }
        }
        if (!declarations.length) continue;
        const where = `${ti}:${mi}:${vi}`, staff = track.staves[0];
        if (!Number.isInteger(raw.instrumentId) || raw.instrumentId < 0 || raw.instrumentId > 127 ||
            track.staves.length !== 1 || !staff || staff.isPercussion ||
            track.playbackInfo.program !== raw.instrumentId ||
            !Array.isArray(raw.tuning) || !raw.tuning.length || !raw.tuning.every(Number.isSafeInteger) ||
            !equal(staff.tuning, raw.tuning) || !Number.isSafeInteger(raw.capo ?? 0) ||
            (raw.capo ?? 0) < 0 || staff.capo !== (raw.capo ?? 0)) fail('instrument/tuning/capo mismatch', where);
        const bar = staff.bars[mi], nativeVoice = bar?.voices[vi], master = score.masterBars[mi];
        if (!bar || bar.index !== mi || !nativeVoice || nativeVoice.index !== vi || !meter[mi] ||
            master?.timeSignatureNumerator !== meter[mi][0] || master?.timeSignatureDenominator !== meter[mi][1]) {
          fail('bar/voice/meter correspondence mismatch', where);
        }
        // Grace groups may be collapsed by the GP5 bridge. They need their own checked
        // mapper; excluding this bar/voice avoids silently shifting ordinary beat IDs.
        if (source.some(b => !!b.graceNote) || nativeVoice.beats.some(b => b.graceType !== model.GraceType.None)) {
          for (const d of declarations) excluded.push({source_ref: d.source_ref, reason: 'grace_voice_mapping_unchecked'});
          continue;
        }
        const native = nativeVoice.beats.filter(b => !b.isEmpty);
        if (native.length !== source.length) fail('beat count mismatch', where);
        const mapping = new Map();
        // The complete ordered voice establishes every relative onset, including
        // preceding rests/dots/tuplets. Beat array order alone is not a time proof.
        for (const [bi, beat] of source.entries()) {
          const targetBeat = native[bi];
          if (targetBeat.voice !== nativeVoice || !durationEqual(beat, targetBeat)) fail('beat timing mismatch', `${where}:${bi}`);
          const sourceNotes = (beat.notes || []).filter(n => !n.rest);
          if (sourceNotes.length !== targetBeat.notes.length) fail('note count mismatch', `${where}:${bi}`);
          const byString = new Map();
          for (const [nativeIndex, n] of targetBeat.notes.entries()) {
            if (!(n instanceof model.Note) || n.beat !== targetBeat || !Number.isSafeInteger(n.string) ||
                n.index !== nativeIndex || n.string < 1 || n.string > raw.tuning.length || byString.has(n.string)) fail('ambiguous native member', `${where}:${bi}`);
            byString.set(n.string, n);
          }
          const used = new Set();
          for (const [ni, n] of (beat.notes || []).entries()) {
            if (n.rest) continue;
            const string = raw.tuning.length - n.string, target = byString.get(string);
            for (const flag of ['dead', 'tie']) {
              if (n[flag] !== undefined && n[flag] !== null && typeof n[flag] !== 'boolean') {
                fail(`unknown source ${flag} declaration`, `${where}:${bi}:${ni}`);
              }
            }
            if (!Number.isSafeInteger(n.string) || n.string < 0 || n.string >= raw.tuning.length ||
                !target || used.has(string) || target.isDead !== (n.dead === true) ||
                target.isTieDestination !== (n.tie === true) ||
                (n.dead !== true && (!Number.isSafeInteger(n.fret) || n.fret < 0 || target.fret !== n.fret))) {
              fail('string/fret member mismatch', `${where}:${bi}:${ni}`);
            }
            used.add(string); mapping.set(`${bi}:${ni}`, target);
          }
        }
        for (const declaration of declarations) {
          const {bi, ni, source_ref, parsed} = declaration, target = mapping.get(`${bi}:${ni}`);
          if (planned.has(target)) fail('duplicate native curve owner', source_ref);
          planned.add(target);
          let tiedHold = null;
          const sourceTieFollows = restoreSimpleTiedHolds && (source[bi + 1]?.notes || []).some(n =>
            n.tie === true && n.string === source[bi].notes[ni].string);
          if (target.isTieDestination || target.tieOrigin || target.tieDestination || target.bendOrigin || target.isContinuedBend || sourceTieFollows) {
            if (restoreSimpleTiedHolds) tiedHold = simpleTiedHold(target, source, mapping, bi, ni, parsed, model, source_ref);
            if (!tiedHold?.eligible) {
              excluded.push({source_ref, reason: tiedHold?.reason ?? 'tie_or_continued_bend_topology_unchecked'}); continue;
            }
          }
          if (target.bendStyle !== model.BendStyle.Default) {
            excluded.push({source_ref, reason: 'nondefault_native_bend_timing_style'}); continue;
          }
          if (!Number.isInteger(target.bendType) || target.bendType === model.BendType.None ||
              typeof model.BendType[target.bendType] !== 'string' || !Array.isArray(target.bendPoints) || !target.bendPoints.length) {
            fail('missing or unknown native bend', source_ref);
          }
          const before = target.bendPoints.map(p => [p.offset, p.value]);
          if (!before.every((p, i) => p.every(finite) && p[0] >= 0 && p[0] <= 60 &&
              (!i || p[0] >= before[i - 1][0]))) fail('malformed native bend', source_ref);
          const changed = !equal(before, parsed.points);
          checkedCurves++; if (!changed) unchangedCurves++;
          witnesses.push({source_ref, native_address: [ti, 0, mi, vi, target.beat.index, target.index],
            points_before: before, points_after: parsed.points, position_basis: parsed.bases,
            type: target.bendType, style: target.bendStyle, changed, ...(tiedHold ? {simple_tied_hold: tiedHold} : {})});
          if (changed) writes.push({target, type: target.bendType, style: target.bendStyle,
            points: parsed.points.map(([offset, value]) => new model.BendPoint(offset, value))});
        }
      }
    }
  }
  // Every source curve, identity and clock has been checked; no earlier curve is
  // modified if a later declaration fails. Point construction also precedes writes.
  for (const {target, points, type, style} of writes) {
    target.bendPoints = null; target.maxBendPoint = null;
    for (const point of points) target.addBendPoint(point);
    target.bendType = type; target.bendStyle = style;
  }
  return {schema: 'identity-checked-source-bend-points/1', restoreSimpleTiedHolds, sourceDeclarations, checkedCurves,
    restoredCurves: writes.length, unchangedCurves, excluded, witnesses,
    limitations: ['Regular pitched notes with explicit curves and complete voice correspondence only',
      'Default native bend style only; other styles may rebuild timing',
      'No inferred bend, grace correspondence, point vibrato, or execution repair',
      'Tie/bend-continuation incident curves excluded by default; opt-in admits only checked independent rise origins with one immediate same-voice/bar tied hold and unchanged endpoints; continuation curves are never rewritten',
      'Dead-note placeholders are matched by string/dead identity, not invented pitch',
      'Precise source percent has precedence over coarse sixtieths, matching source_semantics.curve',
      'Native number precision applies; standalone GP serialization may simplify restored curves; use the paired reader',
      'Must run after the final native finish; a subsequent finish may simplify points again']};
}
