import {toEventScore} from './riff-event-score.js';

// The native player uses +/-16 semitones for its per-note pitch wheels.
export const RIFF_MIDI_BEND_RANGE = 16;

function trackName(at, midi, track, name) {
  const data=new TextEncoder().encode(name);
  // alphaTab's deprecated MetaDataEvent cannot serialize. Write this standard
  // SMF track-name meta event through the public MidiFile event interface.
  midi.addEvent({track,tick:0,type:at.midi.MidiEventType.Meta,writeTo(stream) {
    stream.writeByte(0xff);stream.writeByte(0x03);
    at.midi.MidiFile.writeVariableInt(stream,data.length);stream.write(data,0,data.length);
  }});
}

// Generate native notes and per-key curves on isolated source-string channels.
// Both exporters share this exact score, generator and ordering.
function recordRiff(at,result) {
  const score = toEventScore(at, result, `E ${result.request?.mode || ''} - Drop E riff`);
  const staff=score.tracks[0].staves[0];
  const channels=[...new Set(staff.bars.flatMap(bar=>bar.voices.flatMap(voice=>
    voice.beats.flatMap(beat=>beat.notes.map(note=>8-note.string)))))].sort((a,b)=>a-b);
  score.tracks[0].playbackInfo.primaryChannel=channels[0];
  score.tracks[0].playbackInfo.secondaryChannel=channels[0];
  const calls=[];
  const recorder=new Proxy({},{get:(_target,method)=>(...args)=>calls.push({method,args})});
  const generator = new at.midi.MidiFileGenerator(score, new at.Settings(), recorder);
  if(['_determineChannel','_generateTrack','_generateChannel'].some(method=>typeof generator[method]!=='function'))throw new Error('The guitar player does not provide the verified MIDI channel API.');
  // Pinned alphaTab 1.8.4 uses this hook for attacks, bends, ties and the existing
  // chained-slide correction. Override this instance only, never live playback.
  generator._determineChannel=(_track,note)=>8-note.string;
  generator._generateTrack=track=>{
    for(const channel of channels)generator._generateChannel(track,channel,track.playbackInfo);
  };
  generator.generate();
  return {channels,calls};
}

/** Export the full accepted riff at original tempo, independently of preview state.
 * Standard MIDI bends affect a whole channel. Give each guitar string its own
 * channel AND track so other attacks cannot reset or inherit that string's bend.
 * Use the same native note/slide generator; only export routing changes.
 */
export function createRiffMidi(at, result) {
  const {channels,calls}=recordRiff(at,result);
  const trackFor=new Map(channels.map((channel,index)=>[channel,index+1]));
  const midi = new at.midi.MidiFile();
  midi.format = at.midi.MidiFileFormat.MultiTrack;
  trackName(at,midi,0,'Riff tempo and meter');
  for(const channel of channels)trackName(at,midi,trackFor.get(channel),`Drop E string ${channel+1}`);
  class StringMidiHandler extends at.midi.AlphaSynthMidiFileHandler {
    addNote(_track,start,length,key,velocity,channel) {
      super.addNote(trackFor.get(channel),start,length,key,velocity,channel);
    }
    addNoteBend(_track,tick,channel,key,value) {
      super.addNoteBend(trackFor.get(channel),tick,channel,key,value);
    }
    addBend(_track,tick,channel,value) {
      super.addBend(trackFor.get(channel),tick,channel,value);
    }
    addControlChange(_track,tick,_channel,controller,value) {
      super.addControlChange(trackFor.get(_channel),tick,_channel,controller,value);
    }
    addProgramChange(_track,tick,_channel,program) {
      super.addProgramChange(trackFor.get(_channel),tick,_channel,program);
    }
    finishTrack(_track,tick) {
      for(let track=0;track<=channels.length;track++)super.finishTrack(track,tick);
    }
  }
  const handler = new StringMidiHandler(midi, true);
  const windows=new Map(channels.map(channel=>[channel,[]]));
  for(const {method,args} of calls)if(method==='addNote') {
    windows.get(args[5]).push({start:args[1],end:args[1]+args[2],key:args[3]});
  }
  // Native prebends may be prepared one tick before their attack. A per-note
  // event can safely target a not-yet-sounding key; a channel bend cannot do so
  // while that string still sounds a different key. Omit only such inaudible
  // per-note preparation events; replay everything else in native order.
  for(const {method,args} of calls) {
    if(method==='addNoteBend') {
      const active=windows.get(args[2]).filter(note=>note.start<=args[1]&&args[1]<note.end);
      if(active.length&&!active.some(note=>note.key===args[3]))continue;
    }
    handler[method](...args);
  }
  return midi.toBinary();
}

export const RIFF_MPE_BEND_RANGE = 48;
const MPE_MEMBERS = 8;

/** Genuine lower-zone MPE in one SMF track. Members are allocated to sounding
 * voices, not fixed string tracks. Requires an MPE-aware instrument/importer.
 * MPE v1.0: https://d30pueezughrda.cloudfront.net/campaigns/mpe/mpespec.pdf
 */
export function createRiffMpe(at,result) {
  const {channels,calls}=recordRiff(at,result);
  const midi=new at.midi.MidiFile();
  midi.format=at.midi.MidiFileFormat.SingleTrack;
  trackName(at,midi,0,'Drop E riff - MPE lower zone, members 2-9, bend +/-48');
  const handler=new at.midi.AlphaSynthMidiFileHandler(midi,true);
  const cc=(channel,controller,value)=>handler.addControlChange(0,0,channel,controller,value);
  const rpn=(channel,number,value,fine)=>{
    cc(channel,100,number);cc(channel,101,0);cc(channel,6,value);
    if(fine!==undefined)cc(channel,38,fine);
    cc(channel,100,127);cc(channel,101,127);
  };
  // MCM resets pitch ranges, so configure both zones BEFORE explicit ranges.
  // API channels are zero-based; user-facing manager=1, members=2 through 9.
  rpn(15,6,0);rpn(0,6,MPE_MEMBERS);
  rpn(0,0,2,0);handler.addBend(0,0,0,8192);
  for(let channel=1;channel<=MPE_MEMBERS;channel++)rpn(channel,0,RIFF_MPE_BEND_RANGE,0);
  const voices=calls.map((call,index)=>({...call,index})).filter(c=>c.method==='addNote').map(({args,index})=>({
    start:args[1],end:args[1]+args[2],key:args[3],velocity:args[4],source:args[5],index,
  })).sort((a,b)=>a.start-b.start||a.index-b.index);
  const pool=Array.from({length:MPE_MEMBERS},(_,i)=>({channel:i+1,end:-Infinity,key:null,order:-1}));
  for(const voice of voices) {
    // Prefer a released matching key, otherwise the longest-idle member. Never
    // steal a sounding voice or send independently bent notes on one member.
    const free=pool.filter(member=>member.end<=voice.start);
    if(!free.length)throw new Error('MPE export needs more than eight simultaneous note voices.');
    const same=free.filter(member=>member.key===voice.key).sort((a,b)=>b.order-a.order);
    const member=same[0]??free.sort((a,b)=>a.end-b.end||a.channel-b.channel)[0];
    voice.member=member.channel;
    member.end=voice.end;member.key=voice.key;member.order=voice.index;
  }
  const curves=calls.map((call,index)=>({...call,index})).filter(c=>c.method==='addNoteBend').map(({args,index})=>({
    tick:args[1],source:args[2],key:args[3],value:args[4],index,
  })).sort((a,b)=>a.tick-b.tick||a.index-b.index);
  const mpeWheel=value=>Math.round(8192+(Math.max(0,Math.min(16383,Math.floor(value)))-8192)*RIFF_MIDI_BEND_RANGE/RIFF_MPE_BEND_RANGE);
  // Zone-wide controls belong on the manager, not individual members. Native
  // RPN0 is replaced above; other native metadata retains its original clock.
  for(const {method,args} of calls) {
    if(method==='addControlChange') {
      if(args[2]===channels[0]&&![100,101,6,38].includes(args[3]))handler.addControlChange(0,args[1],0,args[3],args[4]);
    } else if(method==='addProgramChange') {
      if(args[2]===channels[0])handler.addProgramChange(0,args[1],0,args[3]);
    } else if(['addTempo','addTimeSignature'].includes(method))handler[method](...args);
    else if(method==='addTickShift') {
      if(args[0]!==0)throw new Error('MPE export does not support shifted grace-note clocks.');
    } else if(!['addNote','addNoteBend','addRest','finishTrack'].includes(method)) {
      throw new Error(`MPE export does not support ${method}.`);
    }
  }
  for(const voice of voices) {
    const own=curves.filter(c=>c.source===voice.source&&c.key===voice.key);
    // Prebend setup can arrive before attack. Resolve its value for this voice,
    // then initialize its member immediately BEFORE Note On. Curves never leak
    // into a previous voice or a new occupant after Note Off/channel reuse.
    const initial=own.filter(c=>c.tick<=voice.start).at(-1)?.value??8192;
    handler.addBend(0,voice.start,voice.member,mpeWheel(initial));
    for(const curve of own)if(curve.tick>voice.start&&(curve.tick<voice.end||
      (curve.tick===voice.end&&curve.index<voice.index))) {
      handler.addBend(0,curve.tick,voice.member,mpeWheel(curve.value));
    }
    // Native terminal bend events recorded before addNote precede its Note Off.
    // Keep that final pitch for the release tail, before this member is reused.
    handler.addNote(0,voice.start,voice.end-voice.start,voice.key,voice.velocity,voice.member);
  }
  for(const {method,args} of calls)if(method==='finishTrack')handler.finishTrack(0,args[1]);
  return midi.toBinary();
}

export function riffMidiFilename(result, date = new Date(), mpe = false) {
  const mode = String(result.request?.mode || 'generated').toLowerCase().replace(/[^a-z0-9-]/g, '-');
  return `drop-e-${mode}-${mpe?'mpe-':''}riff-${date.toISOString().replace(/[:.]/g, '-')}.mid`;
}
