/** Display declared reference geometry or the generator's planned contacts. */
const TUNING = [64, 59, 55, 50, 45, 40, 35, 28];
const ROLES = ['core', 'extension', 'tapped', 'unspecified'];
const KINDS = ['shape_window', 'single_contact_context', 'open_string_only', 'tapped_context_only', 'no_fretted_contact'];
const clone = value => structuredClone(value);
const gcd = (a, b) => b ? gcd(b, a % b) : (a < 0n ? -a : a);
function q(value) {
  if ((typeof value !== 'string' && !Number.isSafeInteger(value)) || !/^\d+(?:\/\d+)?$/.test(String(value))) throw new Error('Clock is not a nonnegative exact rational');
  const [n, d = 1n] = String(value).split('/').map(BigInt);
  if (d <= 0n) throw new Error('Clock denominator is not positive');
  const divisor = gcd(n, d); return [n / divisor, d / divisor];
}
const add = (a, b) => [a[0] * b[1] + b[0] * a[1], a[1] * b[1]];
const compare = (a, b) => a[0] * b[1] < b[0] * a[1] ? -1 : a[0] * b[1] > b[0] * a[1] ? 1 : 0;
const number = a => Number(a[0]) / Number(a[1]);
const text = a => {const divisor = gcd(a[0], a[1]), n = a[0] / divisor, d = a[1] / divisor; return d === 1n ? String(n) : `${n}/${d}`;};
const identity = source => JSON.stringify([source.palette_id ?? null, source.riff_id ?? null, source.shape_id ?? null]);
function orderedRoles(roles) {
  if (!Array.isArray(roles) || !roles.length || roles.some(role => !ROLES.includes(role))) throw new Error('Contact roles are missing or unsupported');
  return ROLES.filter(role => roles.includes(role));
}
function reference(source) {
  if (!source || typeof source !== 'object') throw new Error('Shape reference is invalid');
  const out = {};
  for (const key of ['palette_id', 'riff_id', 'shape_id']) {
    if (source[key] != null && (typeof source[key] !== 'string' || !source[key].length)) throw new Error('Shape reference identifier is invalid');
    out[key] = source[key] ?? null;
  }
  if (!out.palette_id && !out.riff_id && !out.shape_id) throw new Error('Shape reference has no identifier');
  if (source.artist !== undefined) {
    if (!['Invent Animate', 'Currents', 'ERRA'].includes(source.artist)) throw new Error('Shape reference artist is invalid');
    out.artist = source.artist;
  }
  if (source.provenance_hashes !== undefined) {
    if (!Array.isArray(source.provenance_hashes) || source.provenance_hashes.some(value => typeof value !== 'string' || !/^[a-f0-9]{16,64}$/.test(value))) throw new Error('Shape reference provenance is invalid');
    out.provenance_hashes = [...new Set(source.provenance_hashes)];
  }
  return out;
}
function geometry(contact, tuning) {
  if (!contact || !Number.isInteger(contact.string_number) || contact.string_number < 1 || contact.string_number > 8 ||
    !Number.isInteger(contact.fret) || contact.fret < 1 || contact.fret > 24 ||
    contact.pitch !== tuning[contact.string_number - 1] + contact.fret) throw new Error('Contact is not a valid fretted position');
  return {key: `${contact.string_number - 1}:${contact.fret}`, string: contact.string_number - 1,
    string_number: contact.string_number, fret: contact.fret, pitch: contact.pitch};
}
function decorated(contact) {
  const roles = orderedRoles(contact.roles);
  const displayRole = roles.includes('core') ? 'core' : roles.includes('extension') ? 'extension'
    : roles.includes('tapped') ? 'tapped' : 'unspecified';
  return {...contact, roles, displayRole, dotted: displayRole === 'extension'};
}
function contactList(values, tuning) {
  if (!Array.isArray(values)) throw new Error('Contact list is missing');
  const map = new Map();
  for (const value of values) {
    const point = geometry(value, tuning), roles = orderedRoles(value.roles);
    if (!Array.isArray(value.sources)) throw new Error('Contact provenance is missing');
    const sources = value.sources.map(source => ({...reference(source), roles: orderedRoles(source.roles)}));
    const existing = map.get(point.key);
    if (existing) {
      existing.roles = orderedRoles([...existing.roles, ...roles]);
      for (const source of sources) if (!existing.sources.some(old => JSON.stringify(old) === JSON.stringify(source))) existing.sources.push(source);
    } else map.set(point.key, {...point, roles, sources});
  }
  return [...map.values()].sort((a, b) => a.string - b.string || a.fret - b.fret).map(decorated);
}
function unavailable(reason) {
  return {status: 'unavailable', kind: 'unavailable', reason, color: null, shapeNumber: null,
    contacts: [], ordinaryContacts: [], tappedContacts: [], usedContacts: [], openStrings: [],
    openStringNumbers: [], referenceShapes: [], referenceCount: 0, composite: false, ordinaryFretBounds: null};
}
function view(metadata, tuning) {
  if (!metadata) return unavailable('Generation shape metadata is unavailable');
  try {
    if (metadata.schema !== 'riff-shape-use/1' || !KINDS.includes(metadata.kind)) throw new Error('Shape metadata schema or kind is unsupported');
    const ordinaryContacts = contactList(metadata.ordinary_contacts, tuning), tappedContacts = contactList(metadata.tapped_contacts, tuning);
    const ordinary = new Map(ordinaryContacts.map(contact => [contact.key, contact])), tapped = new Map(tappedContacts.map(contact => [contact.key, contact]));
    if (!Array.isArray(metadata.used_contacts) || !Array.isArray(metadata.open_strings_played) || !Array.isArray(metadata.reference_shapes)) throw new Error('Shape usage or provenance is missing');
    const used = new Map();
    for (const value of metadata.used_contacts) {
      const point = geometry(value, tuning);
      if (typeof value.as_fretting !== 'boolean' || typeof value.as_tapping !== 'boolean' || (!value.as_fretting && !value.as_tapping)) throw new Error('Played contact has no explicit hand role');
      if (value.as_fretting && !ordinary.has(point.key)) throw new Error('Played fretting contact is outside the recorded window');
      if (value.as_tapping && !ordinary.has(point.key) && !tapped.has(point.key)) throw new Error('Played tapping contact is outside the recorded palettes');
      const evidence = [ordinary.get(point.key), tapped.get(point.key)].filter(Boolean);
      const existing = used.get(point.key);
      used.set(point.key, decorated({...point, roles: [...new Set(evidence.flatMap(contact => contact.roles))],
        sources: evidence.flatMap(contact => clone(contact.sources)), as_fretting: value.as_fretting || Boolean(existing?.as_fretting),
        as_tapping: value.as_tapping || Boolean(existing?.as_tapping)}));
    }
    const usedContacts = [...used.values()].sort((a, b) => a.string - b.string || a.fret - b.fret);
    const frettingCount = usedContacts.filter(contact => contact.as_fretting).length, tappingCount = usedContacts.filter(contact => contact.as_tapping).length;
    if (metadata.open_strings_played.some(string => !Number.isInteger(string) || string < 1 || string > 8)) throw new Error('Open string identity is invalid');
    const openStringNumbers = [...new Set(metadata.open_strings_played)].sort((a, b) => a - b);
    const expectedKind = frettingCount >= 2 ? 'shape_window' : frettingCount === 1 ? 'single_contact_context'
      : tappingCount ? 'tapped_context_only' : openStringNumbers.length ? 'open_string_only' : 'no_fretted_contact';
    if (metadata.kind !== expectedKind) throw new Error('Shape kind disagrees with the actually used contacts');
    const frets = ordinaryContacts.map(contact => contact.fret);
    const bounds = frets.length ? [Math.min(...frets), Math.max(...frets)] : null;
    if (JSON.stringify(metadata.ordinary_fret_bounds) !== JSON.stringify(bounds)) throw new Error('Recorded fret bounds disagree with the ordinary window');
    const referenceShapes = [...new Map(metadata.reference_shapes.map(source => {const ref = reference(source); return [identity(ref), ref];})).values()];
    const constructed = metadata.context_origin === 'constructed_local_domain_from_observed_contacts';
    const contacts = metadata.kind === 'shape_window' && !constructed ? [...ordinaryContacts,
      ...usedContacts.filter(contact => contact.as_tapping && !ordinary.has(contact.key)).map(contact => ({...contact, displayRole: 'tapped', dotted: false}))]
      : usedContacts.map(contact => contact.as_tapping && !contact.as_fretting ? {...contact, displayRole: 'tapped', dotted: false} : contact);
    return {status: 'available', kind: metadata.kind, mode: metadata.mode, color: null, shapeNumber: null,
      contacts, ordinaryContacts, tappedContacts, usedContacts, openStringNumbers, openStrings: openStringNumbers.map(string => string - 1),
      outlineKind: constructed || metadata.kind !== 'shape_window' ? 'planned_contacts' : 'reference_shape',
      referenceShapes, referenceCount: referenceShapes.length, composite: referenceShapes.length > 1, ordinaryFretBounds: bounds};
  } catch (error) {return unavailable(error.message);}
}

/** Whole-unit contexts include their rests. Gaps and unavailable metadata are not inferred shapes. */
export function buildShapeTimeline(result) {
  const spans = [], issues = [];
  const tuning = Array.isArray(result?.tuning) && result.tuning.length === 8 ? result.tuning : TUNING;
  const phrases = result?.phrases ?? result?.sections;
  for (const [sectionIndex, section] of (Array.isArray(phrases) ? phrases : []).entries()) {
    for (const [blockIndex, block] of (Array.isArray(section?.blocks) ? section.blocks : []).entries()) {
      try {
        const sectionStart = q(section.offset_q), sectionEnd = add(sectionStart, q(section.length_q));
        const start = add(sectionStart, q(block.offset_q)), duration = q(block.duration_q), end = add(start, duration);
        if (duration[0] <= 0n || compare(end, sectionEnd) > 0 || !Number.isFinite(number(start)) || !Number.isFinite(number(end))) throw new Error('Block timing is outside its section');
        const shape = view(block.shape_usage, tuning);
        spans.push({sectionIndex, blockIndex, start: number(start), end: number(end), start_q: text(start), end_q: text(end), ...shape});
        if (shape.status === 'unavailable') issues.push({sectionIndex, blockIndex, reason: shape.reason});
      } catch (error) {issues.push({sectionIndex, blockIndex, reason: error.message});}
    }
  }
  spans.sort((a, b) => compare(q(a.start_q), q(b.start_q)) || a.sectionIndex - b.sectionIndex || a.blockIndex - b.blockIndex);
  for (let i = 0; i < spans.length; i++) for (let j = i + 1; j < spans.length && compare(q(spans[j].start_q), q(spans[i].end_q)) < 0; j++) {
    for (const span of [spans[i], spans[j]]) Object.assign(span, unavailable('Generation shape contexts overlap'));
    issues.push({sectionIndex: spans[j].sectionIndex, blockIndex: spans[j].blockIndex, reason: 'Generation shape contexts overlap'});
  }
  let previous = null, color = 'orange'; const numbers = new Map();
  for (const span of spans) if (span.status === 'available' && span.kind === 'shape_window') {
    const key = JSON.stringify(span.contacts.map(contact => [contact.string, contact.fret, contact.displayRole]).sort((a, b) => a[0] - b[0] || a[1] - b[1]));
    if (!numbers.has(key)) numbers.set(key, numbers.size + 1);
    if (key !== previous) color = color === 'blue' ? 'orange' : 'blue';
    span.shapeNumber = numbers.get(key); span.color = color; previous = key;
  }
  return {spans, issues};
}

/** Playback uses numeric quarter-note clocks; exact string clocks also work on seek. */
export function shapeAt(timeline, quarter) {
  let exact = null;
  if (typeof quarter === 'number') {if (!Number.isFinite(quarter) || quarter < 0) return null;}
  else {try {exact = q(quarter);} catch {return null;}}
  return (timeline?.spans || []).find(span => exact
    ? compare(q(span.start_q), exact) <= 0 && compare(exact, q(span.end_q)) < 0
    : span.start <= quarter && quarter < span.end) || null;
}

/** Written note clock only: native articulation and acoustic tails stay with the player. */
export function playbackShapeFrame(timeline, normalizedScore, quarter) {
  const span = shapeAt(timeline, quarter);
  let clock;
  try {clock = typeof quarter === 'number' ? quarter : number(q(quarter));} catch {clock = NaN;}
  const activeContacts = [], openStrings = new Set();
  if (!Number.isFinite(clock) || clock < 0) return {span, activeContacts, openStrings: []};
  for (const note of normalizedScore?.notes || []) {
    if (!Number.isInteger(note.string) || note.string < 0 || note.string > 7 || !Number.isInteger(note.fret) || note.fret < 0 || note.fret > 24 ||
      !Number.isFinite(note.start) || !Number.isFinite(note.end) || note.start > clock || clock >= note.end) continue;
    if (note.fret === 0) openStrings.add(note.string);
    else activeContacts.push({...clone(note), key: `${note.string}:${note.fret}`, inOutline: Boolean(span?.contacts.some(contact => contact.string === note.string && contact.fret === note.fret))});
  }
  return {span, activeContacts, openStrings: [...openStrings].sort((a, b) => a - b)};
}
