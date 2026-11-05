/** Random settings use labelled availability; actual generation proves feasibility. */
const ARTISTS = ['Invent Animate', 'Currents', 'ERRA'];
const MODES = ['Aeolian', 'Dorian', 'Ionian', 'Mixolydian', 'Lydian', 'Phrygian'];
const STYLES = ['arpeggio', 'chordal', 'melodic', 'pedal', 'rhythmic', 'other'];
const FOCUSES = ['single', 'interval', 'triad', 'chord', 'mixed'];
const LENGTHS = ['4', '8', '16'];
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
function seed(rng) { return Math.floor(draw(rng) * 2147483648); }

function optionsFor(availability, artists, mode) {
  return STYLES.flatMap(style => {
    if (!artists.some(artist => availability?.palettes?.[artist]?.[style]?.[mode] > 0)) return [];
    const focuses = FOCUSES.filter(focus => artists.some(artist => availability?.rhythms?.[artist]?.[style]?.[focus] > 0));
    return focuses.length ? [{style, focuses}] : [];
  });
}
function globalOptions(availability) {
  return Array.from({length: 7}, (_, i) => ARTISTS.filter((_, bit) => (i + 1) & (1 << bit)))
    .map(artists => ({artists, modes: MODES.filter(mode => optionsFor(availability, artists, mode).length)}))
    .filter(option => option.modes.length);
}
function randomSection(availability, artists, mode, rng) {
  const {style, focuses} = pick(optionsFor(availability, artists, mode), rng);
  return {style, focus: pick(focuses, rng), length_q: pick(LENGTHS, rng), seed: seed(rng)};
}

/** Every artist subset/style/focus/mode with labelled support remains eligible. */
export function randomRequest(availability, count, rng = Math.random) {
  countCheck(count);
  const globals = globalOptions(availability);
  if (!globals.length) throw new Error('No labelled rhythm and shape combinations are available.');
  const {artists, modes} = pick(globals, rng), mode = pick(modes, rng);
  return {artists: [...artists], mode, tempo: 80 + Math.floor(draw(rng) * 121), seed: seed(rng),
    sections: Array.from({length: count}, () => randomSection(availability, artists, mode, rng))};
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
  {rng = Math.random, maxAttemptsPerSection = 8, onProgress} = {}) {
  if (typeof generateFn !== 'function') throw new TypeError('A generation callback is required.');
  if (!Number.isInteger(maxAttemptsPerSection) || maxAttemptsPerSection < 1 || maxAttemptsPerSection > 32) {
    throw new RangeError('Attempts per section must be between 1 and 32.');
  }
  const request = randomRequest(availability, count, rng);
  const attempts = [], sections = [], events = [], limits = new Set(), refusals = [];
  let offset = '0', provenance = null, failed = null;
  for (let index = 0; index < count; index++) {
    const attemptedSeeds = new Set();
    let accepted = null, chosen = clone(request.sections[index]);
    for (let attempt = 1; attempt <= maxAttemptsPerSection; attempt++) {
      if (attempt > 1) chosen = randomSection(availability, request.artists, request.mode, rng);
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
      successful_sections: sections.filter(section => section.status === 'generated').length,
      global_rerolls: 0, scope: 'Labelled availability limits sampling; every accepted section was generated by the actual engine.'}};
}
