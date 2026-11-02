// Source-authenticated percussion only. Ordinary fallback grace groups remain
// complete beats; no member joining, host guessing, or direct clock writes.
const defaults = new WeakMap();
function defaultArticulations(at) {
  if (!defaults.has(at)) {
    // GP5 has GM IDs with no table. GP7 writes a library-authored table and then
    // interprets note values as indexes. Obtain that exact public serialization,
    // including glyph metadata, without copying private library constants.
    const score = new at.model.Score(), track = new at.model.Track(), staff = new at.model.Staff();
    score.addMasterBar(new at.model.MasterBar()); score.addTrack(track); track.addStaff(staff); staff.isPercussion = true;
    const bar = new at.model.Bar(), voice = new at.model.Voice(), beat = new at.model.Beat();
    staff.addBar(bar); bar.addVoice(voice); voice.addBeat(beat); beat.duration = 1;
    const settings = new at.Settings(); score.finish(settings);
    const bytes = new at.exporter.Gp7Exporter().export(score, settings);
    const table = at.importer.ScoreLoader.loadScoreFromBytes(bytes, settings).tracks[0].percussionArticulations;
    if (!table.length) throw Error('Native percussion default table unavailable');
    defaults.set(at, table);
  }
  return defaults.get(at).map(a => Object.assign(new at.model.InstrumentArticulation(), a));
}
const graceKind = (b, types) => {
  if (b.graceNote === undefined || b.graceNote === null || b.graceNote === false) return types.None;
  if (b.graceNote === 'onBeat') return types.OnBeat;
  if (b.graceNote === 'beforeBeat') return types.BeforeBeat;
  throw Error('Unknown source percussion grace declaration');
};
function regularDurationEqual(raw, beat) {
  const d = raw.duration, noTuplet = beat.tupletNumerator === -1 && beat.tupletDenominator === -1;
  const n = noTuplet ? 1 : beat.tupletNumerator, t = noTuplet ? 1 : beat.tupletDenominator;
  if (!Array.isArray(d) || d.length !== 2 || !d.every(v => Number.isSafeInteger(v) && v > 0) ||
      !Number.isSafeInteger(beat.duration) || beat.duration <= 0 || !Number.isInteger(beat.dots) || beat.dots < 0 || beat.dots > 8 ||
      !Number.isSafeInteger(n) || n <= 0 || !Number.isSafeInteger(t) || t <= 0) return false;
  const power = 2n ** BigInt(beat.dots);
  return BigInt(d[0]) * BigInt(beat.duration) * power * BigInt(n) === BigInt(d[1]) * (2n * power - 1n) * BigInt(t);
}
export function restoreSourcePercussion(score, parts, at) {
  const types = at?.model?.GraceType;
  if (!types || !Array.isArray(parts) || score.tracks.length !== parts.length) throw Error('Percussion track correspondence required');
  const writes = [], witnesses = [], tables = [];
  let notesChecked = 0, beatsChecked = 0, graceBeats = 0;
  for (const [ti, raw] of parts.entries()) {
    const track = score.tracks[ti];
    if (raw.partId !== ti || track.index !== ti) throw Error('Percussion source/native part order mismatch');
    if (raw.instrumentId !== 1024) continue;
    if (track.staves.length !== 1 || !track.staves[0].isPercussion || track.staves[0].bars.length !== raw.measures.length) throw Error('Percussion staff/bar correspondence mismatch');
    const existing = track.percussionArticulations, generated = existing.length === 0;
    const table = generated ? defaultArticulations(at) : existing;
    if (generated) writes.push({target: track, key: 'percussionArticulations', value: table});
    tables.push({track: ti, existing_entries: existing.length, resulting_entries: table.length, canonical_default_required: generated});
    let nativeCount = 0;
    for (const bar of track.staves[0].bars) for (const voice of bar.voices) for (const beat of voice.beats) nativeCount += beat.notes.length;
    let mappedCount = 0;
    for (const [mi, measure] of raw.measures.entries()) for (const [vi, voice] of (measure.voices || []).entries()) {
      const source = voice.beats || [], native = track.staves[0].bars[mi].voices[vi]?.beats;
      const where = `${ti}:${mi}:${vi}`;
      if (!native || native.length !== source.length) throw Error(`Percussion beat correspondence mismatch at ${where}`);
      const modes = source.map(b => graceKind(b, types));
      for (let bi = 0; bi < source.length; bi++) {
        const a = source[bi], b = native[bi], mode = modes[bi], loc = `${where}:${bi}`;
        if (b.isEmpty || ![types.None, types.OnBeat, types.BeforeBeat].includes(b.graceType)) throw Error(`Unsupported percussion native beat at ${loc}`);
        if (mode === types.None && (b.graceType !== types.None || !regularDurationEqual(a, b))) throw Error(`Ordinary percussion duration/identity mismatch at ${loc}`);
        if (mode !== types.None) {
          let host = bi + 1;
          while (host < source.length && modes[host] !== types.None) {
            if (modes[host] !== mode) throw Error(`Mixed percussion grace group at ${loc}`);
            host++;
          }
          if (host === source.length || !(source[host].notes || []).some(n => !n.rest)) throw Error(`Percussion grace has no ordinary host at ${loc}`);
          graceBeats++;
          if (b.graceType !== mode) writes.push({target: b, key: 'graceType', value: mode});
        }
        const rawNotes = (a.notes || []).filter(n => !n.rest), keys = rawNotes.map(n => n.fret);
        if (keys.some(k => !Number.isSafeInteger(k) || k < 0 || k > 127)) throw Error(`Unknown source percussion member at ${loc}`);
        if (keys.length !== b.notes.length || mode !== types.None && !keys.length) throw Error(`Percussion note cardinality mismatch at ${loc}`);
        const actual = new Map();
        for (const n of b.notes) {
          const value = n.percussionArticulation;
          // An attached GP5 percussion grace can still carry its key as fret.
          const fretGrace = value < 0 && b.graceType !== types.None;
          const entry = existing[value];
          const key = fretGrace ? n.fret : generated ? value : keys.includes(entry?.id) ? entry.id : entry?.outputMidiNumber;
          if (!Number.isSafeInteger(key) || !keys.includes(key)) throw Error(`Percussion member correspondence mismatch at ${loc}`);
          if (!actual.has(key)) actual.set(key, []);
          actual.get(key).push({n, fretGrace});
        }
        for (const key of new Set(keys)) {
          const sourceMembers = rawNotes.filter(n => n.fret === key), members = actual.get(key) || [];
          if (members.length !== sourceMembers.length) throw Error(`Percussion member multiplicity mismatch at ${loc}`);
          if (sourceMembers.length > 1) {
            const allowed = new Set(['fret', 'string', 'dead', 'ghost', 'accentuated']);
            const signature = n => JSON.stringify(Object.entries(n).sort(([a], [b]) => a.localeCompare(b)));
            if (sourceMembers.some(n => Object.keys(n).some(k => !allowed.has(k)) || signature(n) !== signature(sourceMembers[0]))) throw Error(`Ambiguous duplicate source percussion fields at ${loc}`);
            const first = sourceMembers[0];
            if (['ghost','dead'].some(k => first[k] !== undefined && typeof first[k] !== 'boolean') || first.accentuated !== undefined && ![0,1,2].includes(first.accentuated)) throw Error(`Unknown duplicate source percussion flags at ${loc}`);
            const fields = ['fret','string','dynamics','isGhost','isDead','accentuated','isPalmMute','isLetRing','vibrato','slideInType','slideOutType','isTieDestination','isHammerPullOrigin'];
            const nativeSignature = n => JSON.stringify(fields.map(k => n[k]));
            if (members.some(({n}) => n.isGhost !== (first.ghost === true) || n.isDead !== (first.dead === true) || n.accentuated !== (first.accentuated ?? 0) || nativeSignature(n) !== nativeSignature(members[0].n))) throw Error(`Ambiguous duplicate native percussion fields at ${loc}`);
          }
        }
        const mapping = [];
        const used = new Map();
        for (const key of keys) {
          const ordinal = used.get(key) || 0, member = actual.get(key)?.[ordinal]; used.set(key, ordinal + 1);
          if (!member) throw Error(`Missing percussion member at ${loc}`);
          const {n, fretGrace} = member;
          let index;
          if (!generated && !fretGrace) index = n.percussionArticulation; // Retain authenticated notation choice.
          else {
            const declaredOutputs = [...new Set(table.filter(a => a.id === key).map(a => a.outputMidiNumber))];
            if (declaredOutputs.length !== 1) throw Error(`Unknown source percussion ID${key} at ${loc}`);
            const matches = table.flatMap((a, i) => (generated ? a.id === key : a.outputMidiNumber === declaredOutputs[0]) ? [i] : []);
            if (matches.length !== 1) throw Error(`Ambiguous percussion articulation candidates for GM${key} at ${loc}: ${matches.join(',')}`);
            index = matches[0];
          }
          if (n.percussionArticulation !== index) writes.push({target: n, key: 'percussionArticulation', value: index});
          if (fretGrace) {writes.push({target: n, key: 'fret', value: -1}); writes.push({target: n, key: 'string', value: -1});}
          mapping.push({source_percussion_id: key, native_note: n.index, articulation_index: index, articulation_id: table[index].id, output_midi: table[index].outputMidiNumber});
          notesChecked++; mappedCount++;
        }
        witnesses.push({track: ti, bar_zero_based: mi, voice: vi, source_beat: bi, source_grace: mode, mappings: mapping}); beatsChecked++;
      }
    }
    if (mappedCount !== nativeCount) throw Error('Unmapped native percussion occurrences');
  }
  for (const w of writes) w.target[w.key] = w.value;
  return {schema: 'identity-checked-source-percussion/1', notesChecked, beatsChecked, graceBeats, tables, witnesses,
    restoredGraceTypes: writes.filter(w => w.key === 'graceType').length,
    remappedArticulations: writes.filter(w => w.key === 'percussionArticulation').length,
    restoredAttachedGraceKeys: writes.filter(w => w.key === 'fret').length,
    limits: ['Complete one-to-one source/native beat groups only; split or missing groups refuse', 'Repeated keys retain complete multiplicity and native occurrence order; differing duplicate fields or ambiguous new notation choices refuse', 'No clock writes; native finish determines performed grace allocation', 'Source nominal duration is not acoustic performance']};
}
