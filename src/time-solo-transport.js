// The original Time score's guitar solo spans measures 94–143, inclusive.
export const TIME_SOLO_FIRST_BAR = 93;
export const TIME_SOLO_LAST_BAR = 142;
const TICKS_PER_QUARTER = 960; // alphaTab's MIDI division

export function createTimeSoloWindow(score, tickCache) {
  if (!score?.masterBars?.[TIME_SOLO_LAST_BAR] || !tickCache?.getMasterBar) return null;
  const first = tickCache.getMasterBar(score.masterBars[TIME_SOLO_FIRST_BAR]);
  const last = tickCache.getMasterBar(score.masterBars[TIME_SOLO_LAST_BAR]);
  const startTick = Number(first?.start);
  const endTick = Number(last?.end);
  if (!Number.isFinite(startTick) || !Number.isFinite(endTick) || endTick <= startTick) return null;

  // The player's milliseconds scale with playback speed. Use the score's
  // tempo map to translate between musical ticks and speed-independent time.
  const changes = [];
  for (const bar of tickCache.masterBars || []) {
    for (const change of bar.tempoChanges || []) {
      const tick = Number(change.tick);
      const tempo = Number(change.tempo);
      if (Number.isFinite(tick) && tick >= 0 && Number.isFinite(tempo) && tempo > 0) {
        changes.push({ tick, tempo });
      }
    }
  }
  changes.sort((a, b) => a.tick - b.tick);
  let previousTick = 0;
  let elapsed = 0;
  let tempo = Number(score.tempo) > 0 ? Number(score.tempo) : 120;
  const points = [{ tick: 0, ms: 0, tempo }];
  for (const change of changes) {
    elapsed += (change.tick - previousTick) * 60000 / (TICKS_PER_QUARTER * tempo);
    previousTick = change.tick;
    tempo = change.tempo;
    if (points.at(-1).tick === change.tick) points.pop();
    points.push({ tick: change.tick, ms: elapsed, tempo });
  }
  const toMs = tick => {
    let point = points[0];
    for (const next of points) {
      if (next.tick > tick) break;
      point = next;
    }
    return point.ms + (tick - point.tick) * 60000 / (TICKS_PER_QUARTER * point.tempo);
  };
  const toTick = ms => {
    let point = points[0];
    for (const next of points) {
      if (next.ms > ms) break;
      point = next;
    }
    return Math.round(point.tick + (ms - point.ms) * TICKS_PER_QUARTER * point.tempo / 60000);
  };
  const startMs = toMs(startTick);
  const endMs = toMs(endTick);
  return { startTick, endTick, startMs, endMs, durationMs: endMs - startMs,
    tickToMs: toMs, msToTick: toTick };
}
