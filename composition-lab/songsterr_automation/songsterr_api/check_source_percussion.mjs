// Independent raw source -> reimported GP7 percussion oracle. Does not restore.
export function checkSourcePercussion(score, parts, types = {None: 0, OnBeat: 1, BeforeBeat: 2}) {
  const differences = [], witnesses = [], counts = {tracks: 0, beats: 0, notes: 0, graceBeats: 0};
  const fail = (code, where, expected, actual) => differences.push({code, ...where, expected, actual});
  if (!Array.isArray(parts) || parts.length !== score.tracks.length) return {status: 'FAIL_INDEPENDENT_SOURCE_PERCUSSION', differences: [{code: 'TRACK_COUNT'}], counts, witnesses};
  for (const [ti, raw] of parts.entries()) {
    if (raw.instrumentId !== 1024) continue;
    const t = score.tracks[ti], where = {track: ti}; counts.tracks++;
    if (raw.partId !== ti || t.index !== ti || t.staves.length !== 1 || !t.staves[0].isPercussion) {fail('INSTRUMENT_DOMAIN', where, 'corresponding percussion staff', null); continue;}
    if (t.staves[0].bars.length !== raw.measures.length) fail('BAR_COUNT', where, raw.measures.length, t.staves[0].bars.length);
    let mapped = 0, total = 0;
    for (const bar of t.staves[0].bars) for (const v of bar.voices) for (const b of v.beats) total += b.notes.length;
    for (const [mi, measure] of raw.measures.entries()) for (const [vi, voice] of (measure.voices || []).entries()) {
      const source = voice.beats || [], actual = t.staves[0].bars[mi]?.voices[vi]?.beats;
      const loc = {...where, bar_zero_based: mi, voice: vi};
      if (!actual || source.length !== actual.length) {fail('BEAT_COUNT', loc, source.length, actual?.length ?? null); continue;}
      let ticks = 0;
      for (let bi = 0; bi < source.length; bi++) {
        const a = source[bi], b = actual[bi], at = {...loc, source_beat: bi}; counts.beats++;
        let mode;
        if (a.graceNote === undefined || a.graceNote === false || a.graceNote === null) mode = types.None;
        else if (a.graceNote === 'onBeat') mode = types.OnBeat;
        else if (a.graceNote === 'beforeBeat') mode = types.BeforeBeat;
        else {fail('SOURCE_GRACE', at, 'known declaration', a.graceNote); continue;}
        if (b.isEmpty || b.graceType !== mode) fail('GRACE_MODE', at, mode, b.graceType);
        if (b.displayStart !== ticks) fail('NOMINAL_ONSET', at, ticks, b.displayStart);
        const d = a.duration;
        if (!Array.isArray(d) || d.length !== 2 || !d.every(x => Number.isSafeInteger(x) && x > 0)) {fail('SOURCE_DURATION', at, 'positive fraction', d); continue;}
        const noTuplet = b.tupletNumerator === -1 && b.tupletDenominator === -1;
        const tn = noTuplet ? 1 : b.tupletNumerator, td = noTuplet ? 1 : b.tupletDenominator;
        const nativeValid = Number.isSafeInteger(b.duration) && b.duration > 0 && Number.isInteger(b.dots) && b.dots >= 0 && b.dots <= 8 &&
          Number.isSafeInteger(tn) && tn > 0 && Number.isSafeInteger(td) && td > 0;
        if (!nativeValid) fail('NATIVE_NOTATION', at, 'finite positive duration/tuplet and valid dots', {duration: b.duration, dots: b.dots, tn, td});
        let length = 0;
        if (mode === types.None) {
          const numerator = BigInt(d[0]) * 3840n, denominator = BigInt(d[1]);
          if (numerator % denominator) {fail('UNSUPPORTED_EXACT_GRID', at, 'integer960PPQ ticks', d); continue;}
          length = Number(numerator / denominator);
          if (nativeValid) {
            const power = 2n ** BigInt(b.dots), num = 3840n * (2n * power - 1n) * BigInt(td), den = BigInt(b.duration) * power * BigInt(tn);
            if (num !== BigInt(length) * den) fail('REGULAR_NOTATION', at, length, `${num}/${den}`);
          }
        } else {
          counts.graceBeats++;
          let host = bi + 1;
          while (host < source.length && source[host].graceNote) {
            if (source[host].graceNote !== a.graceNote) fail('MIXED_GRACE_GROUP', at, a.graceNote, source[host].graceNote);
            host++;
          }
          if (host === source.length || !(source[host].notes || []).some(n => !n.rest)) fail('GRACE_HOST', at, 'following ordinary attack in same bar', null);
        }
        if (b.displayDuration !== length) fail('NOMINAL_DURATION', at, length, b.displayDuration);
        ticks += length;
        const rawNotes = (a.notes || []).filter(n => !n.rest), expected = rawNotes.map(n => n.fret);
        if (expected.some(k => !Number.isSafeInteger(k) || k < 0 || k > 127)) fail('UNKNOWN_SOURCE_MEMBER', at, 'known percussion keys', expected);
        const outputs = expected.map(id => {
          const matches = [...new Set(t.percussionArticulations.filter(a => a.id === id).map(a => a.outputMidiNumber))];
          if (matches.length !== 1) {fail('SOURCE_ARTICULATION_ID', at, 'one declared output for source ID', id); return null;}
          return matches[0];
        });
        const keys = [], memberRows = [];
        for (const n of b.notes) {
          const index = n.percussionArticulation;
          const articulation = Number.isInteger(index) && index >= 0 ? t.percussionArticulations[index] : null;
          if (!articulation || !Number.isInteger(articulation.outputMidiNumber)) {fail('ARTICULATION_INDEX', at, 'explicit table entry', index); continue;}
          keys.push(articulation.outputMidiNumber); memberRows.push({native_note: n.index, index, id: articulation.id, gm: articulation.outputMidiNumber});
        }
        if (JSON.stringify([...outputs].sort((a,b)=>a-b)) !== JSON.stringify([...keys].sort((a,b)=>a-b))) fail('GM_KEY_MEMBERSHIP', at, outputs, keys);
        for (const id of new Set(expected.filter((id,i) => id !== outputs[i]))) {
          const need = expected.filter(x => x === id).length, actual = memberRows.filter(x => x.id === id).length;
          if (need !== actual) fail('SOURCE_ARTICULATION_ID', at, {id,count:need}, {id,count:actual});
        }
        for (const key of new Set(expected)) {
          const group = rawNotes.filter(n => n.fret === key);
          if (group.length < 2) continue;
          const allowed = ['fret','string','dead','ghost','accentuated'];
          const fields = n => JSON.stringify(Object.keys(n).sort().map(k => [k,n[k]]));
          if (group.some(n => Object.keys(n).some(k => !allowed.includes(k)) || fields(n) !== fields(group[0]))) fail('AMBIGUOUS_DUPLICATE_SOURCE_FIELDS', at, 'identical repeated source declarations', group);
          for (const n of b.notes.filter(n => t.percussionArticulations[n.percussionArticulation]?.outputMidiNumber === key)) {
            if (n.isGhost !== (group[0].ghost === true) || n.isDead !== (group[0].dead === true) || n.accentuated !== (group[0].accentuated ?? 0)) fail('DUPLICATE_MEMBER_FLAGS', at, group[0], {ghost:n.isGhost,dead:n.isDead,accentuated:n.accentuated});
          }
        }
        counts.notes += b.notes.length; mapped += b.notes.length;
        witnesses.push({...at, source_grace: mode, source_percussion_ids:expected, expected_midi_keys:outputs, expected_nominal_ticks: length, actual_nominal_ticks: b.displayDuration, members: memberRows});
      }
    }
    if (mapped !== total) fail('UNMAPPED_NATIVE_NOTES', where, total, mapped);
  }
  return {schema: 'independent-source-percussion/1', status: differences.length ? 'FAIL_INDEPENDENT_SOURCE_PERCUSSION' : 'PASS_INDEPENDENT_SOURCE_PERCUSSION', counts, differences, witnesses,
    limits: ['Raw source IDs, multiplicity, grace mode and nominal clock checked independently', 'Native articulation IDs can differ from output MIDI keys; canonical output is a declared library interpretation, not source timbre equivalence', 'Percussion display glyphs and performed grace allocation are native choices, not source acoustic truth', 'Actual MIDI callbacks require a separate native execution check']};
}
