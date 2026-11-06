export function fraction(value) { const [a, b = '1'] = String(value).split('/'); return Number(a) / Number(b); }

// Adapt the composer's written score without selecting or changing any notes.
export function toNativeScore(at, source, title = 'Drop E riff') {
  const m = at.model, score = new m.Score();
  score.title = title; score.artist = 'Original Drop E composition';
  const track = new m.Track(); score.addTrack(track); track.name = 'Drop E 8 string';
  track.playbackInfo.program = 30;
  const staff = new m.Staff(); track.addStaff(staff);
  staff.stringTuning.tunings = [...source.tuning_high_to_low];
  staff.showStandardNotation = false; staff.showTablature = true;
  for (const [barIndex, sourceBar] of source.bars.entries()) {
    const master = new m.MasterBar();
    master.timeSignatureNumerator = source.meter[0]; master.timeSignatureDenominator = source.meter[1];
    if (!barIndex) master.tempoAutomations.push(m.Automation.buildTempoAutomation(false, 0, source.tempo, 2));
    score.addMasterBar(master);
    const bar = new m.Bar(); staff.addBar(bar); const voice = new m.Voice(); bar.addVoice(voice);
    for (const sourceBeat of sourceBar) {
      const beat = new m.Beat(); voice.addBeat(beat);
      beat.duration = sourceBeat.type; beat.dots = sourceBeat.dots || 0; beat.isEmpty = false;
      beat.dynamics = m.DynamicValue[(sourceBeat.velocity || 'mf').toUpperCase()];
      for (const sourceNote of sourceBeat.notes) {
        const note = new m.Note();
        note.string = source.tuning_high_to_low.length - sourceNote.string;
        note.fret = sourceNote.fret;
        note.isPalmMute = Boolean(sourceBeat.palmMute);
        note.isHammerPullOrigin = Boolean(sourceNote.hp);
        note.accentuated = sourceNote.accentuated || 0;
        note.dynamics = beat.dynamics;
        beat.addNote(note);
      }
    }
  }
  score.finish(new at.Settings());
  return score;
}

import {mountBuilder} from "./riff-builder-view.js";
export {mountBuilder};
if(typeof document!=="undefined")mountBuilder();
