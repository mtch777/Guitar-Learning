// The engine owns musical choices. This adapter only writes its exact event clock.
export const DROP_E = [64, 59, 55, 50, 45, 40, 35, 28];
export const qValue = value => { const [n, d = 1] = String(value).split('/').map(Number); return n / d; };
const EPS = 1e-8;

export function normalizeEvents(result) {
  const tuning = result.tuning || DROP_E;
  const duration = qValue(result.duration_q ?? result.sections?.reduce((n, s) => n + qValue(s.length_q), 0));
  if (!Number.isFinite(duration) || duration <= 0) throw new Error('Generated riff has no valid length.');
  const notes = [];
  for (const event of result.events || []) {
    for (const member of event.members || event.notes || []) {
      const string = member.string_number - 1;
      const start = qValue(member.onset_q ?? event.onset_q);
      const hold = qValue(member.duration_q ?? event.duration_q);
      if (!Number.isInteger(string) || string < 0 || string >= tuning.length ||
          !Number.isInteger(member.fret) || member.fret < 0 || member.fret > 24 ||
          tuning[string] + member.fret !== member.pitch || !Number.isFinite(start) ||
          !Number.isFinite(hold) || start < -EPS || hold <= 0 || start + hold > duration + EPS) {
        throw new Error('Generated note has invalid timing or Drop E placement.');
      }
      const marks = member.marks || {};
      notes.push({...member, string, start, end: start + hold,
        onset_q: member.onset_q ?? event.onset_q, duration_q: member.duration_q ?? event.duration_q,
        palm_mute: Boolean(member.palm_mute ?? marks.palm_mute),
        hp: Boolean(member.hp ?? marks.hp), accent: Boolean(member.accent ?? marks.accentuated ?? marks.accent)});
    }
  }
  if (!notes.length) throw new Error('No notes were generated.');
  for (let string = 0; string < tuning.length; string++) {
    const lane = notes.filter(n => n.string === string).sort((a, b) => a.start - b.start);
    for (let i = 1; i < lane.length; i++) {
      if (lane[i].start < lane[i - 1].end - EPS) throw new Error('Generated notes overlap on the same string.');
    }
  }
  return {tuning_high_to_low: tuning, tempo: result.tempo, notes, duration_q: duration, meter: [4, 4]};
}

function notation(duration) {
  for (const [num, den] of [[1, 1], [3, 2], [5, 4], [7, 4], [9, 8]]) {
    for (const type of [1, 2, 4, 8, 16, 32, 64, 128]) {
      for (let dots = 0; dots <= 2; dots++) {
        if (Math.abs(4 / type * (2 - 1 / 2 ** dots) * den / num - duration) < EPS) return {type, dots, num, den};
      }
    }
  }
  throw new Error(`Playback cannot yet write this exact duration (${duration} beats). Nothing was rounded.`);
}

function splitSpan(start, end) {
  try {notation(end-start); return [start];} catch { /* Split the written value into tied durations. */ }
  for (const [num, den] of [[1,1],[3,2],[5,4],[7,4],[9,8]]) {
    const units=(end-start)/(den/num/32);
    if (Math.abs(units-Math.round(units))>EPS) continue;
    const values=[1,2,4,8,16,32,64,128].flatMap(type=>[0,1,2].map(dots=>4/type*(2-1/2**dots)*den/num)).sort((a,b)=>b-a);
    const points=[];let now=start;
    while(end-now>EPS){const value=values.find(x=>x<=end-now+EPS);if(!value)break;points.push(now);now+=value;}
    if(Math.abs(now-end)<EPS)return points;
  }
  notation(end-start); // precise unsupported-duration error
}

export function toEventScore(at, result, title = 'Drop E riff') {
  const source = normalizeEvents(result), m = at.model, score = new m.Score();
  if (Math.abs(source.duration_q / 4 - Math.round(source.duration_q / 4)) > EPS) throw new Error('Choose whole 4/4 bars for the current player.');
  score.title = title; score.artist = 'Original Drop E composition';
  const track = new m.Track(); score.addTrack(track); track.name = 'Drop E 8 string'; track.playbackInfo.program = 30;
  const staff = new m.Staff(); track.addStaff(staff); staff.stringTuning.tunings = [...source.tuning_high_to_low];
  staff.showStandardNotation = false; staff.showTablature = true;
  const previous = new Map();
  for (let barStart = 0; barStart < source.duration_q - EPS; barStart += 4) {
    const barEnd = barStart + 4, master = new m.MasterBar();
    master.timeSignatureNumerator = 4; master.timeSignatureDenominator = 4;
    if (!barStart) master.tempoAutomations.push(m.Automation.buildTempoAutomation(false, 0, source.tempo, 2));
    score.addMasterBar(master);
    const bar = new m.Bar(); staff.addBar(bar); const voice = new m.Voice(); bar.addVoice(voice);
    const boundaries = [barStart, barEnd];
    for (const note of source.notes) for (const point of [note.start, note.end]) if (point > barStart + EPS && point < barEnd - EPS) boundaries.push(point);
    boundaries.sort((a, b) => a - b);
    const unique = boundaries.filter((n, i) => !i || n - boundaries[i - 1] > EPS);
    const points = unique.slice(0,-1).flatMap((n,i)=>splitSpan(n,unique[i+1])); points.push(barEnd);
    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i], end = points[i + 1], value = notation(end - start);
      const beat = new m.Beat(); voice.addBeat(beat); beat.isEmpty = false;
      beat.duration = value.type; beat.dots = value.dots;
      if (value.num !== 1) {beat.tupletNumerator = value.num; beat.tupletDenominator = value.den;}
      beat.dynamics = m.DynamicValue.MF;
      for (const original of source.notes.filter(n => n.start <= start + EPS && n.end > start + EPS)) {
        const note = new m.Note(); note.string = source.tuning_high_to_low.length - original.string;
        note.fret = original.fret; note.isPalmMute = original.palm_mute;
        note.isHammerPullOrigin = original.hp && Math.abs(end - original.end) < EPS;
        const marks=original.marks || {}, attacking=Math.abs(start-original.start)<EPS, ending=Math.abs(end-original.end)<EPS;
        note.accentuated = Number(marks.accentuated) || (original.accent ? 1 : 0);
        note.dynamics = m.DynamicValue[String(marks.velocity || 'mf').toUpperCase()] ?? m.DynamicValue.MF;
        note.isLetRing=Boolean(marks.let_ring); note.isGhost=Boolean(marks.ghost); note.isStaccato=Boolean(marks.staccato);
        note.isLeftHandTapped=Boolean(marks.left_hand_tap)&&attacking;
        beat.tap ||= Boolean(marks.tapping)&&attacking;
        if(marks.up_stroke&&attacking)beat.pickStroke=m.PickStroke.Up;
        if(marks.slide&&ending){
          if(!['legato','shift'].includes(marks.slide))throw new Error('Unsupported slide type in generated notes.');
          note.slideOutType=marks.slide==='legato'?m.SlideOutType.Legato:m.SlideOutType.Shift;
        }
        if (start > original.start + EPS) {
          note.isTieDestination = true; note.tieOrigin = previous.get(original);
          if (!note.tieOrigin) throw new Error('Held note lost its native tie origin.');
          note.tieOrigin.tieDestination = note;
        }
        beat.addNote(note); previous.set(original, note);
      }
    }
  }
  score.finish(new at.Settings());
  return score;
}
