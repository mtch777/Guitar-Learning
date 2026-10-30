// GP5 attaches one grace to each host note. Its importer can therefore split
// one declared source chord into several native beats. Only the source's full
// occurrence membership can establish that those beats belong together.
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const graceMode = b => {
  if (b.graceNote === undefined || b.graceNote === null || b.graceNote === false) return 0;
  if (b.graceNote === 'onBeat') return 1;
  if (b.graceNote === 'beforeBeat') return 2;
  throw Error('Unknown source grace declaration');
};
const sourceKeys = (beat, strings, where) => {
  const result = [], seen = new Set();
  for (const note of beat.notes || []) {
    if (note.rest) continue;
    if (!Number.isSafeInteger(note.string) || note.string < 0 || note.string >= strings ||
        !Number.isSafeInteger(note.fret) || note.fret < 0 || seen.has(note.string)) {
      throw Error(`Ambiguous source grace member at ${where}`);
    }
    seen.add(note.string); result.push(`${strings - note.string}:${note.fret}`);
  }
  return result;
};
const nativeKeys = (beat, strings, where) => {
  const result = [], seen = new Set();
  if (!beat || beat.isempty || !Array.isArray(beat.notes)) throw Error(`Unavailable native grace beat at ${where}`);
  for (const note of beat.notes) {
    if (!Number.isSafeInteger(note.string) || note.string < 1 || note.string > strings ||
        !Number.isSafeInteger(note.fret) || note.fret < 0 || seen.has(note.string)) {
      throw Error(`Ambiguous native grace member at ${where}`);
    }
    seen.add(note.string); result.push(`${note.string}:${note.fret}`);
  }
  return result;
};
const memberSetEqual = (a, b) => a.length === b.length && same([...a].sort(), [...b].sort());
const fragmentMetadata = beat => Object.fromEntries(Object.entries(beat).filter(([key]) =>
  !['id', 'notes', 'playbackstart', 'playbackduration'].includes(key)));

/** Pure plan over the native serializer's data; it never mutates either input. */
export function planSourceGraceChordJoins(native, parts) {
  if (!Array.isArray(parts) || !Array.isArray(native?.tracks) || native.tracks.length !== parts.length) {
    throw Error('Grace track correspondence mismatch');
  }
  const joins = [];
  for (const [ti, raw] of parts.entries()) {
    if (raw.partId !== ti) throw Error('Grace chord source order mismatch');
    if (raw.instrumentId === 1024) continue;
    for (const [mi, measure] of (raw.measures || []).entries()) for (const [vi, voice] of (measure.voices || []).entries()) {
      const source = voice.beats || [], modes = source.map(graceMode);
      if (!modes.some(Boolean)) continue;
      const where = `${ti}:${mi}:${vi}`, track = native.tracks[ti], staff = track?.staves?.[0];
      if (!Number.isInteger(raw.instrumentId) || raw.instrumentId < 0 || raw.instrumentId > 127 ||
          track.staves?.length !== 1 || !Array.isArray(raw.tuning) || !raw.tuning.length ||
          !raw.tuning.every(Number.isSafeInteger) || !same(staff.stringtuning?.tunings, raw.tuning) ||
          staff.ispercussion || staff.capo !== (raw.capo ?? 0)) throw Error(`Grace chord instrument correspondence mismatch at ${where}`);
      const beats = staff.bars?.[mi]?.voices?.[vi]?.beats;
      if (!Array.isArray(beats)) throw Error(`Grace chord voice unavailable at ${where}`);
      let cursor = 0;
      for (let bi = 0; bi < source.length; bi++) {
        const loc = `${where}:${bi}`, keys = sourceKeys(source[bi], raw.tuning.length, loc);
        const first = beats[cursor], firstKeys = nativeKeys(first, raw.tuning.length, loc);
        if (memberSetEqual(keys, firstKeys)) {
          if (!modes[bi] && first.gracetype !== 0) throw Error(`Grace chord ordinary boundary mismatch at ${loc}`);
          cursor++; continue;
        }
        if (!modes[bi] || keys.length < 2) throw Error(`Grace chord member correspondence mismatch at ${loc}`);
        const start = cursor, wanted = new Set(keys), found = new Map(), fragments = [];
        while (found.size < wanted.size) {
          const fragment = beats[cursor], fragmentKeys = nativeKeys(fragment, raw.tuning.length, loc);
          if (fragment.gracetype !== modes[bi] || fragment.displayduration !== 0 || !fragmentKeys.length ||
              !same(fragmentMetadata(first), fragmentMetadata(fragment))) {
            const changed = Object.keys(fragmentMetadata(first)).filter(k => !same(fragmentMetadata(first)[k], fragmentMetadata(fragment)[k]));
            throw Error(`Incompatible native grace fragments at ${loc}: ${changed.join(',')}`);
          }
          for (const [ni, key] of fragmentKeys.entries()) {
            if (!wanted.has(key) || found.has(key)) throw Error(`Grace chord crosses source membership at ${loc}`);
            found.set(key, {native_beat: cursor, native_note: ni});
          }
          fragments.push(cursor++);
        }
        if (fragments.length < 2) throw Error(`Grace chord join needs multiple native fragments at ${loc}`);
        joins.push({track: ti, bar_zero_based: mi, voice: vi, source_beat: bi,
          first_native_beat: start, native_beats: fragments,
          source_member_keys: keys, members_in_source_order: keys.map(key => found.get(key))});
      }
      if (cursor !== beats.length) throw Error(`Unowned native grace fragment at ${where}`);
    }
  }
  if (joins.length) {
    // The native serializer retains ties/slides/hammer-pulls by note ID. A clone
    // must not reinterpret an ambiguous ID or silently drop an unresolved link.
    const beatIds = new Set(), noteIds = new Set(), links = [];
    for (const track of native.tracks) for (const staff of track.staves) for (const bar of staff.bars)
      for (const voice of bar.voices) for (const beat of voice.beats) {
        if (!Number.isSafeInteger(beat.id) || beat.id < 0 || beatIds.has(beat.id)) throw Error('Ambiguous native grace beat ID');
        beatIds.add(beat.id);
        for (const note of beat.notes) {
          if (!Number.isSafeInteger(note.id) || note.id < 0 || noteIds.has(note.id)) throw Error('Ambiguous native grace note ID');
          noteIds.add(note.id);
          for (const [key, target] of Object.entries(note)) if (key.endsWith('noteid')) links.push(target);
        }
      }
    if (links.some(id => !Number.isSafeInteger(id) || !noteIds.has(id))) throw Error('Unresolved native grace note link');
  }
  return {schema: 'source-certified-grace-chord-joins/1', joins,
    joinedSourceChords: joins.length, removedFragmentBeats: joins.reduce((n, j) => n + j.native_beats.length - 1, 0),
    limitations: ['Pitched source-declared simultaneous grace chords only', 'No host-string remapping or missing-note reconstruction',
      'Source and native voice identity still require the existing complete grace check', 'Native performed grace allocation remains renderer behavior']};
}

/** Return a separate native candidate. Failed planning never touches the input. */
export function joinSourceGraceChords(score, parts, at, settings) {
  if (at.model.GraceType.None !== 0 || at.model.GraceType.OnBeat !== 1 || at.model.GraceType.BeforeBeat !== 2) {
    throw Error('Pinned native grace enum required');
  }
  const document = JSON.parse(at.model.JsonConverter.scoreToJson(score));
  const report = planSourceGraceChordJoins(document, parts);
  if (!report.joins.length) return {score, report};
  // All affected voices are planned first. Editing a private serialized candidate
  // retains native note IDs, every note effect and explicit target-note links.
  const byVoice = new Map();
  for (const join of report.joins) {
    const key = `${join.track}:${join.bar_zero_based}:${join.voice}`;
    if (!byVoice.has(key)) byVoice.set(key, []);
    byVoice.get(key).push(join);
  }
  for (const joins of byVoice.values()) {
    const j = joins[0], voice = document.tracks[j.track].staves[0].bars[j.bar_zero_based].voices[j.voice];
    const sourceBeats = voice.beats, starts = new Map(joins.map(x => [x.first_native_beat, x]));
    const removed = new Set(joins.flatMap(x => x.native_beats.slice(1))), beats = [];
    for (let i = 0; i < sourceBeats.length; i++) {
      if (removed.has(i)) continue;
      const join = starts.get(i), beat = sourceBeats[i];
      if (join) beat.notes = join.members_in_source_order.map(x => sourceBeats[x.native_beat].notes[x.native_note]);
      beats.push(beat);
    }
    voice.beats = beats;
  }
  return {score: at.model.JsonConverter.jsonToScore(JSON.stringify(document), settings), report};
}
