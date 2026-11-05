/** Common observed gestures inform settings; they do not guarantee generation or taste. */
const ARTISTS = ['Invent Animate', 'Currents', 'ERRA'];
const MODES = ['Aeolian', 'Dorian', 'Ionian', 'Mixolydian', 'Lydian', 'Phrygian'];
const STYLES = ['arpeggio', 'chordal', 'melodic', 'pedal', 'rhythmic', 'other'];
const FOCUSES = ['single', 'interval', 'triad', 'chord', 'mixed'];
const LENGTHS = ['4', '8', '16'];
const clone = value => structuredClone(value);
const gcd = (a, b) => b ? gcd(b, a % b) : a;
function rational(value) {
  if ((typeof value !== 'string' && !Number.isSafeInteger(value)) || !/^\d+(?:\/\d+)?$/.test(String(value))) throw new Error('Observed durations must be exact nonnegative rational values.');
  const [n, d = 1n] = String(value).split('/').map(BigInt);
  if (d <= 0n) throw new Error('Observed duration denominator must be positive.');
  const divisor = gcd(n, d), numerator = n / divisor, denominator = d / divisor;
  return {n: numerator, d: denominator, key: denominator === 1n ? String(numerator) : `${numerator}/${denominator}`,
    value: Number(numerator) / Number(denominator)};
}
function count(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error(`${label} must be a nonnegative count.`);
  return value;
}
function compareDuration(left, right) {
  const a = rational(left.length_q), b = rational(right.length_q), difference = a.n * b.d - b.n * a.d;
  return difference < 0n ? -1 : difference > 0n ? 1 : 0;
}
function lengthChoice(histogram) {
  const bySupport = [...histogram].sort((a, b) => b.distinct_songs - a.distinct_songs || compareDuration(a, b));
  const exact = bySupport.find(value => LENGTHS.includes(value.length_q));
  if (exact) return {length_q: exact.length_q, source_length_q: exact.length_q, strategy: 'observed_supported',
    distinct_songs: exact.distinct_songs,
    text: `Observed ${exact.length_q} quarter-note beats in ${exact.distinct_songs} selected-artist song${exact.distinct_songs === 1 ? '' : 's'}.`};
  if (!bySupport.length) return {length_q: null, source_length_q: null, strategy: 'unavailable', distinct_songs: 0,
    text: 'No observed gesture length is available for the selected artists.'};
  const source = bySupport[0], q = rational(source.length_q), abs = value => value < 0n ? -value : value;
  const chosen = [...LENGTHS].sort((a, b) => {
    const difference = abs(BigInt(a) * q.d - q.n) - abs(BigInt(b) * q.d - q.n);
    return difference < 0n ? -1 : difference > 0n ? 1 : Number(a) - Number(b);
  })[0];
  return {length_q: chosen, source_length_q: source.length_q, strategy: 'nearest_supported', distinct_songs: source.distinct_songs,
    text: `Observed ${source.length_q} quarter-note beats in ${source.distinct_songs} selected-artist song${source.distinct_songs === 1 ? '' : 's'}; mapped to ${chosen} beats, the nearest builder length (shorter on a tie).`};
}
function describeArtist(artist, profile) {
  const parts = [], metrics = profile.metrics || {};
  const value = key => metrics[key]?.median_q === undefined ? null : rational(metrics[key].median_q).value;
  const attacks = value('attacks_per_quarter'), empty = value('written_empty_fraction'), shapes = value('linked_shape_count');
  if (attacks !== null) parts.push(`median ${Number(attacks.toFixed(2))} attacks/beat`);
  if (empty !== null) parts.push(`${Number((empty * 100).toFixed(1))}% median written empty time`);
  if (shapes !== null) parts.push(`median ${Number(shapes.toFixed(2))} linked shapes`);
  return parts.length ? `${artist}: ${parts.join('; ')}.` : `${artist}: ${profile.distinct_songs} distinct songs.`;
}

/** Ranking is by already song-deduplicated support within the selected artists only. */
export function rankSectionPresets(data, selectedArtists, mode, availability) {
  if (data?.schema !== 'riff-section-presets/1' || !Array.isArray(data.presets)) throw new Error('Reference section presets are unavailable.');
  if (!Array.isArray(selectedArtists) || !selectedArtists.length || new Set(selectedArtists).size !== selectedArtists.length || selectedArtists.some(artist => !ARTISTS.includes(artist))) {
    throw new Error('Select one or more supported reference artists.');
  }
  if (!MODES.includes(mode)) throw new Error('Select an available E mode.');
  const seen = new Set(), seenIds = new Set(), ranked = [];
  for (const preset of data.presets) {
    if (!STYLES.includes(preset.style) || !FOCUSES.includes(preset.focus) || typeof preset.id !== 'string') throw new Error('Reference preset style or focus is invalid.');
    const key = `${preset.style}:${preset.focus}`;
    if (seen.has(key) || seenIds.has(preset.id)) throw new Error('Duplicate reference preset would inflate the ranking.');
    seen.add(key); seenIds.add(preset.id);
    const byArtist = {}, histogram = new Map(), support = {distinct_songs: 0, captures: 0, occurrences: 0};
    for (const artist of selectedArtists) {
      const profile = preset.by_artist?.[artist];
      if (!profile) continue;
      const songs = count(profile.distinct_songs, 'Distinct-song support');
      if (!songs) continue;
      byArtist[artist] = clone(profile);
      for (const field of Object.keys(support)) support[field] += count(profile[field], field);
      const lengths = new Set();
      for (const observation of profile.duration_histogram || []) {
        const duration = rational(observation.length_q), songsAtLength = count(observation.distinct_songs, 'Length song support');
        if (!duration.n || songsAtLength > songs) throw new Error('Observed length support is inconsistent.');
        if (lengths.has(duration.key)) throw new Error('Duplicate observed duration would inflate song support.');
        lengths.add(duration.key);
        if (!songsAtLength) continue;
        const existing = histogram.get(duration.key) || {length_q: duration.key, distinct_songs: 0};
        existing.distinct_songs += songsAtLength; histogram.set(duration.key, existing);
      }
    }
    if (!support.distinct_songs) continue;
    const observedLengths = [...histogram.values()].sort(compareDuration), length = lengthChoice(observedLengths);
    const rhythmByArtist = Object.fromEntries(selectedArtists.map(artist => [artist, availability?.rhythms?.[artist]?.[preset.style]?.[preset.focus] || 0]));
    const palettesByArtist = Object.fromEntries(selectedArtists.map(artist => [artist, availability?.palettes?.[artist]?.[preset.style]?.[mode] || 0]));
    const hasRhythm = Object.values(rhythmByArtist).some(value => value > 0), hasPalette = Object.values(palettesByArtist).some(value => value > 0);
    const disabled = !availability ? 'Reference availability has not loaded.' : !length.length_q ? 'No observed length is available.'
      : !hasRhythm ? 'No labelled rhythm templates match these artists, style and focus.'
        : !hasPalette ? `No labelled shape palette matches these artists, style and E ${mode}.` : null;
    ranked.push({id: preset.id, label: preset.label || `${preset.style} · ${preset.focus}`,
      section: {style: preset.style, focus: preset.focus, length_q: length.length_q}, support,
      available: disabled === null, disabled_reason: disabled, length_evidence: {description: length.text},
      length_selection: {...length, text: undefined}, observed_duration_histogram: observedLengths,
      traits: Object.entries(byArtist).map(([artist, profile]) => describeArtist(artist, profile)), by_artist: byArtist,
      style_scope: preset.style_scope, length_scope: preset.length_scope,
      trait_scope: 'Descriptive per-artist, observation-weighted reference measurements; applying a preset changes only style, focus and length.',
      selection: {artists: [...selectedArtists], mode},
      availability: {rhythm_by_artist: rhythmByArtist, palettes_by_artist: palettesByArtist,
        scope: 'Labelled availability is not proof that generation will succeed.'}});
  }
  ranked.sort((a, b) => b.support.distinct_songs - a.support.distinct_songs ||
    STYLES.indexOf(a.section.style) - STYLES.indexOf(b.section.style) || FOCUSES.indexOf(a.section.focus) - FOCUSES.indexOf(b.section.focus));
  return ranked.map((preset, index) => ({...preset, rank: index + 1}));
}

/** Apply one explicit settings choice; retain tempo, mode, artists, seeds and every other row. */
export function applySectionPreset(current, rowIndex, preset) {
  if (!current || !Array.isArray(current.sections) || !Number.isInteger(rowIndex) || rowIndex < 0 || rowIndex >= current.sections.length) {
    throw new Error('Choose an existing section for this preset.');
  }
  if (!preset?.available) throw new Error(preset?.disabled_reason || 'This preset is unavailable for the current selection.');
  if (preset.selection && (current.mode !== preset.selection.mode || !Array.isArray(current.artists) ||
    [...current.artists].sort().join('|') !== [...preset.selection.artists].sort().join('|'))) {
    throw new Error('Reference artists or mode changed. Choose a preset from the current selection.');
  }
  const section = preset.section;
  if (!STYLES.includes(section?.style) || !FOCUSES.includes(section?.focus) || !LENGTHS.includes(section?.length_q)) throw new Error('Preset settings are invalid.');
  const next = clone(current);
  next.sections[rowIndex] = {...next.sections[rowIndex], style: section.style, focus: section.focus, length_q: section.length_q};
  return next;
}
