/** Random settings use labelled availability; actual generation proves feasibility. */
const ARTISTS = ['Invent Animate', 'Currents', 'ERRA'];
const MODES = ['Aeolian', 'Dorian', 'Ionian', 'Mixolydian', 'Lydian', 'Phrygian'];
const STYLES = ['arpeggio', 'chordal', 'melodic', 'pedal', 'rhythmic', 'other'];
const FOCUSES = ['single', 'interval', 'triad', 'chord', 'mixed'];
const LENGTHS = ['4', '8', '16'];
const EXCLUDABLE = ['artists', 'mode', 'tempo', 'style', 'focus', 'length_q'];
const SECTION_FIELDS = ['style', 'focus', 'length_q'];
const TUNING = [64, 59, 55, 50, 45, 40, 35, 28];
const clone = value => structuredClone(value);

function countCheck(count) {
  if (!Number.isInteger(count) || count < 1 || count > 10) throw new RangeError('Choose 1–10 sections.');
}
function draw(rng) {
  const value = rng();
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value >= 1) throw new RangeError('Random values must be in [0, 1).');
  return value;
}
function pick(values, rng) { return values[Math.floor(draw(rng) * values.length)]; }
function seed(rng, previous) {
  const value = Math.floor(draw(rng) * 2147483648);
  return value === previous ? (value + 1) % 2147483648 : value;
}

function exclusions(current, exclude, count) {
  if (!Array.isArray(exclude) || exclude.some(key => !EXCLUDABLE.includes(key))) {
    throw new Error('Exclude only Artists, Mode, Tempo, Style, Focus, or Section length.');
  }
  const keys = EXCLUDABLE.filter(key => exclude.includes(key)), globals = {}, baseline = {};
  if (keys.includes('artists')) {
    const value = current?.artists;
    if (!Array.isArray(value) || !value.length || new Set(value).size !== value.length || value.some(artist => !ARTISTS.includes(artist))) {
      throw new Error('Excluded artists must contain one or more supported artists.');
    }
    globals.artists = [...value]; baseline.artists = [...value];
  }
  if (keys.includes('mode')) {
    if (!MODES.includes(current?.mode)) throw new Error('Excluded mode must be one of the six available E modes.');
    globals.mode = current.mode; baseline.mode = current.mode;
  }
  if (keys.includes('tempo')) {
    if (!Number.isInteger(current?.tempo) || current.tempo < 80 || current.tempo > 200) {
      throw new Error('Excluded tempo must be a whole number from 80 to 200 BPM.');
    }
    globals.tempo = current.tempo; baseline.tempo = current.tempo;
  }
  const sectionKeys = SECTION_FIELDS.filter(key => keys.includes(key));
  let cycle = [{}];
  if (sectionKeys.length) {
    if (!Array.isArray(current?.sections) || !current.sections.length) throw new Error('Excluded section fields need at least one current section.');
    cycle = current.sections.map((section, index) => {
      const locked = {};
      for (const key of sectionKeys) {
        const value = section?.[key];
        const valid = key === 'style' ? STYLES.includes(value) : key === 'focus' ? FOCUSES.includes(value)
          : (typeof value === 'string' || Number.isInteger(value)) && LENGTHS.includes(String(value));
        if (!valid) throw new Error(`Excluded ${key === 'length_q' ? 'section length' : key} is invalid in current section ${index + 1}.`);
        locked[key] = value;
      }
      return locked;
    });
    baseline.sections = clone(cycle);
  }
  return {keys, globals, baseline, previousSeed: current?.seed,
    previousSectionSeeds: Array.from({length: count}, (_, index) => current?.sections?.length ? current.sections[index % current.sections.length]?.seed : undefined),
    sections: Array.from({length: count}, (_, index) => clone(cycle[index % cycle.length]))};
}

function optionsFor(availability, artists, mode, locked = {}) {
  return STYLES.filter(style => locked.style === undefined || style === locked.style).flatMap(style => {
    if (!artists.some(artist => availability?.palettes?.[artist]?.[style]?.[mode] > 0)) return [];
    const focuses = FOCUSES.filter(focus => (locked.focus === undefined || focus === locked.focus)
      && artists.some(artist => availability?.rhythms?.[artist]?.[style]?.[focus] > 0));
    return focuses.length ? [{style, focuses}] : [];
  });
}
function globalOptions(availability, locks) {
  const artistSets = locks.globals.artists ? [locks.globals.artists]
    : Array.from({length: 7}, (_, i) => ARTISTS.filter((_, bit) => (i + 1) & (1 << bit)));
  const modes = locks.globals.mode ? [locks.globals.mode] : MODES;
  return artistSets.map(artists => ({artists, modes: modes.filter(mode =>
    locks.sections.every(locked => optionsFor(availability, artists, mode, locked).length))}))
    .filter(option => option.modes.length);
}
function randomSection(availability, artists, mode, rng, locked = {}, previousSeed) {
  const {style, focuses} = pick(optionsFor(availability, artists, mode, locked), rng);
  return {style, focus: pick(focuses, rng), length_q: pick(locked.length_q === undefined ? LENGTHS : [locked.length_q], rng), seed: seed(rng, previousSeed)};
}

function requestWithExclusions(availability, count, rng, locks) {
  const globals = globalOptions(availability, locks);
  if (!globals.length) throw new Error(locks.keys.length
    ? 'No labelled rhythm and shape combinations match the excluded values. Nothing was unlocked.'
    : 'No labelled rhythm and shape combinations are available.');
  const {artists, modes} = pick(globals, rng), mode = pick(modes, rng);
  const randomTempo = 80 + Math.floor(draw(rng) * 121);
  return {artists: [...artists], mode, tempo: locks.globals.tempo ?? randomTempo, seed: seed(rng, locks.previousSeed),
    sections: Array.from({length: count}, (_, index) => randomSection(availability, artists, mode, rng, locks.sections[index], locks.previousSectionSeeds[index]))};
}

/** Excluded values stay fixed; support is checked before any random sampling. */
export function randomRequest(availability, count, rng = Math.random, {current, exclude = []} = {}) {
  countCheck(count);
  return requestWithExclusions(availability, count, rng, exclusions(current, exclude, count));
}

function gcd(a, b) { while (b) [a, b] = [b, a % b]; return a < 0n ? -a : a; }
function rational(value) {
  if ((typeof value !== 'string' && !Number.isSafeInteger(value)) || !/^-?\d+(?:\/\d+)?$/.test(String(value))) {
    throw new Error('Generated clocks must be exact rationals.');
  }
  let [n, d = '1'] = String(value).split('/'); n = BigInt(n); d = BigInt(d);
  if (d <= 0n) throw new Error('Generated clock denominator must be positive.');
  const divisor = gcd(n, d); return [n / divisor, d / divisor];
}
function add(a, b) { return rationalText([a[0] * b[1] + b[0] * a[1], a[1] * b[1]]); }
function rationalText([n, d]) { const divisor = gcd(n, d); n /= divisor; d /= divisor; return d === 1n ? String(n) : `${n}/${d}`; }
function compare(a, b) { const difference = a[0] * b[1] - b[0] * a[1]; return difference < 0n ? -1 : difference > 0n ? 1 : 0; }

function validateGenerated(result, request) {
  const duration = rational(result.duration_q), zero = rational('0');
  if (compare(duration, rational(request.sections[0].length_q)) !== 0) throw new Error('Generated duration does not match the requested section.');
  if (result.sections?.length !== 1 || result.sections[0].status !== 'generated') throw new Error('Expected one complete generated section.');
  if (compare(rational(result.sections[0].offset_q), zero) !== 0 || compare(rational(result.sections[0].length_q), duration) !== 0) {
    throw new Error('Generated section has inconsistent clocks.');
  }
  if (result.tempo !== request.tempo || JSON.stringify(result.tuning) !== JSON.stringify(TUNING)) throw new Error('Generated tuning or tempo changed unexpectedly.');
  if (!Array.isArray(result.events) || !result.events.length) throw new Error('Generated section contains no musical events.');
  for (const event of result.events) {
    const onset = rational(event.onset_q);
    if (compare(onset, zero) < 0 || compare(onset, duration) >= 0 || !event.members?.length) throw new Error('Generated event lies outside its section.');
    for (const member of event.members) {
      const hold = rational(member.duration_q);
      if (compare(hold, zero) <= 0 || compare(rational(add(onset, hold)), duration) > 0) throw new Error('Generated note hold lies outside its section.');
    }
  }
}

/** Generate sections through the real engine, retrying musical failures only.
 * generateFn(singleSectionRequest, {sectionIndex, attempt}) returns an engine result.
 * onProgress receives {phase,sectionIndex,count,attempt,maxAttemptsPerSection}.
 * A failed riff has no events; callers should keep their prior successful result.
 */
export async function generateRandomRiff(availability, count, generateFn,
  {rng = Math.random, maxAttemptsPerSection = 8, onProgress, current, exclude = []} = {}) {
  if (typeof generateFn !== 'function') throw new TypeError('A generation callback is required.');
  if (!Number.isInteger(maxAttemptsPerSection) || maxAttemptsPerSection < 1 || maxAttemptsPerSection > 32) {
    throw new RangeError('Attempts per section must be between 1 and 32.');
  }
  countCheck(count);
  const locks = exclusions(current, exclude, count);
  const request = requestWithExclusions(availability, count, rng, locks);
  const attempts = [], sections = [], events = [], limits = new Set(), refusals = [];
  let offset = '0', provenance = null, failed = null;
  for (let index = 0; index < count; index++) {
    const attemptedSeeds = new Set([locks.previousSectionSeeds[index]]);
    let accepted = null, chosen = clone(request.sections[index]);
    for (let attempt = 1; attempt <= maxAttemptsPerSection; attempt++) {
      if (attempt > 1) chosen = randomSection(availability, request.artists, request.mode, rng, locks.sections[index]);
      while (attemptedSeeds.has(chosen.seed)) chosen.seed = (chosen.seed + 1) % 2147483648;
      attemptedSeeds.add(chosen.seed);
      const single = {...clone(request), sections: [clone(chosen)]};
      onProgress?.({phase: 'generating', sectionIndex: index, count, attempt, maxAttemptsPerSection});
      const receipt = {section_index: index, attempt, request: clone(single)};
      try {
        const result = await generateFn(single, {sectionIndex: index, attempt});
        receipt.status = result?.status || 'invalid_result';
        receipt.refusals = clone(result?.refusals || []);
        attempts.push(receipt);
        if (result?.status !== 'generated') {
          receipt.reason = result?.sections?.[0]?.refusals?.at(-1)?.reason || 'no_generated_choice';
          continue;
        }
        validateGenerated(result, single);
        if (provenance && JSON.stringify(provenance) !== JSON.stringify(result.provenance)) throw new Error('Reference material changed between generated sections.');
        accepted = result; break;
      } catch (error) {
        receipt.status = 'error'; receipt.reason = String(error?.message || error);
        if (!attempts.includes(receipt)) attempts.push(receipt);
        failed = {section_index: index, reason: 'generation_callback_or_contract_error', message: receipt.reason};
        break;
      }
    }
    request.sections[index] = clone(chosen);
    if (!accepted) {
      failed ||= {section_index: index, reason: 'random_section_attempts_exhausted', attempts: maxAttemptsPerSection};
      sections.push({index, ...clone(chosen), offset_q: offset, status: 'no_choice', blocks: [], refusals: [failed]});
      refusals.push(failed); break;
    }
    provenance ||= clone(accepted.provenance || {});
    const section = {...clone(accepted.sections[0]), index, offset_q: offset}; sections.push(section);
    accepted.events.forEach((event, ei) => {
      const copy = clone(event); copy.onset_q = add(rational(offset), rational(event.onset_q)); copy.section_index = index;
      copy.members.forEach((member, ni) => {
        member.id = /^s0:b\d+:e\d+:n\d+$/.test(member.id || '')
          ? member.id.replace(/^s0:/, `s${index}:`)
          : `random:s${index}:e${ei}:n${ni}:${member.id || ''}`;
      });
      events.push(copy);
    });
    refusals.push(...(accepted.refusals || []).map(value => ({...clone(value), section_index: index})));
    for (const limit of accepted.limits || []) limits.add(limit);
    offset = add(rational(offset), rational(accepted.duration_q));
    onProgress?.({phase: 'accepted', sectionIndex: index, count});
  }
  const requestedDuration = request.sections.reduce((sum, section) => add(rational(sum), rational(section.length_q)), '0');
  return {schema: 'modular-riff-result/1', status: failed ? 'no_choice' : 'generated', request,
    tempo: request.tempo, tuning: [...TUNING], duration_q: requestedDuration, meter: [4, 4],
    events: failed ? [] : events, sections, refusals, provenance: provenance || {}, limits: [...limits],
    random_generation: {count, max_attempts_per_section: maxAttemptsPerSection, attempts,
      exclusions: locks.keys, excluded_values: clone(locks.baseline), section_value_rule: 'Repeat the current section sequence for added rows; one section uses its first row.',
      successful_sections: sections.filter(section => section.status === 'generated').length,
      global_rerolls: 0, scope: 'Labelled availability limits sampling; every accepted section was generated by the actual engine.'}};
}
