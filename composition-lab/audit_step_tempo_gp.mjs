// Exact native-reference QA. The only reference mutation is the declared BPM.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {loadPlaybackScore} from './songsterr_automation/songsterr_api/playback_score.mjs';

const [moduleArg, rootArg] = process.argv.slice(2);
if (!rootArg) throw Error('alphaTab module and native output folder required');
const root = path.resolve(rootArg), modulePath = path.resolve(moduleArg);
const hash = x => crypto.createHash('sha256').update(x).digest('hex');
const sha = p => hash(fs.readFileSync(p));
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const sharedPath = path.join(root, 'dynamic-native-snapshot.json'), shared = read(sharedPath);
const scopePath = path.join(root, 'tempo-source-scope.json'), scope = read(scopePath);
if (shared.module_sha256 !== sha(modulePath) || shared.core_sha256 !== sha(path.join(path.dirname(modulePath), 'alphaTab.core.mjs')))
    throw Error('Pinned native runtime differs');
const at = await import(pathToFileURL(modulePath));
const plain = x => JSON.parse(JSON.stringify(x, (_k, v) => v instanceof Map ? Object.fromEntries(v) : v));
const ref = n => `native:${n.beat.voice.bar.staff.track.index}:${n.beat.voice.bar.index + 1}:${n.beat.voice.index}:${n.beat.index}:${n.index}`;
const bref = b => `native:${b.voice.bar.staff.track.index}:${b.voice.bar.index + 1}:${b.voice.index}:${b.index}`;
const quarter = new at.model.MasterBar();quarter.timeSignatureNumerator = 1;quarter.timeSignatureDenominator = 4;
const timing = {quarter_ticks: quarter.calculateDuration(), dead_constant: at.midi.MidiFileGenerator._defaultDurationDead,
    palm_mute_constant: at.midi.MidiFileGenerator._defaultDurationPalmMute, position_scale: at.model.BendPoint.MaxPosition};

function trace(name, counterfactual = false) {
    const file = path.join(root, name, 'score.gp');
    if (sha(file) !== shared.cases[name].gp_sha256) throw Error('Actual GP changed');
    const {score} = loadPlaybackScore(at, file, {});
    if (counterfactual) {
        const autos = score.masterBars[scope.bar - 1]?.tempoAutomations;
        if (autos?.length !== 1 || autos[0].ratioPosition !== 0 || autos[0].value !== scope.before_bpm)
            throw Error('Unique exact source tempo required');
        autos[0].value = scope.after_bpm;
    }
    // Snapshot before generation mutates runtime caches. No annotation is added.
    const model = plain(at.model.JsonConverter.scoreToJsObject(score));
    const settings = new at.Settings();settings.notation.notationMode = at.NotationMode.GuitarPro;
    for (const [k, v] of Object.entries(shared.cases[name].playback_profile)) settings.player.vibrato[k] = v;
    const noteMap = new Map(shared.cases[name].notes.map(n => [n.native_ref, n]));
    const midi = new at.midi.MidiFile(), handler = new at.midi.AlphaSynthMidiFileHandler(midi, false);
    const callbacks = [], noteCalls = [], bindings = new WeakMap(), origins = new WeakMap();
    let current = null, execution = null, binding = null;
    const add = midi.addEvent.bind(midi);
    midi.addEvent = e => {origins.set(e, current);if (binding !== null) bindings.set(e, binding);return add(e);};
    const addNote = handler.addNote.bind(handler);
    handler.addNote = (track, start, length, key, velocity, channel) => {
        const n = current?.kind === 'note' ? noteMap.get(current.ref) : null;
        const previous = binding;binding = callbacks.length;
        callbacks.push({native_ref:n?.native_ref??null, source_ref:n?.source_ref??null,
            track,start:start+handler.tickShift,length,key,velocity,channel,execution});
        try {return addNote(track,start,length,key,velocity,channel);} finally {binding = previous;}
    };
    const gen = new at.midi.MidiFileGenerator(score, settings, handler);
    const generateNote = gen._generateNote;
    gen._generateNote = function(n, start, duration, tempo, brush, rasgueado) {
        const previous = current, previousExecution = execution;
        const brushOffset = rasgueado == null && n.isStringed && n.string <= brush.length ? brush[n.string - 1] : 0;
        current = {kind:'note',ref:ref(n),beat_start:start+handler.tickShift,tempo};
        execution = {...current,beat_duration:duration,brush_offset:brushOffset,cap_kind:n.isDead?'dead':n.isPalmMute?'palm_mute':null,
            split_execution:!!(n.beat.hasRasgueado || n.ornament !== at.model.NoteOrnament.None || n.isTrill || n.beat.isTremolo)};
        noteCalls.push(execution);
        try {return generateNote.call(this,n,start,duration,tempo,brush,rasgueado);} finally {current=previous;execution=previousExecution;}
    };
    const generateBeat = gen._generateBeat;
    gen._generateBeat = function(b, start, realBar, tempo) {
        const previous=current;current={kind:'beat',ref:bref(b),beat_start:start+b.playbackStart+handler.tickShift,tempo};
        try {return generateBeat.call(this,b,start,realBar,tempo);} finally {current=previous;}
    };
    gen.generate();
    const events=midi.events.map(e=>({kind:e.constructor.name,data:plain(e),binding:bindings.get(e)??null}));
    const points=new Map();
    for(const e of events.filter(e=>e.kind==='TempoChangeEvent')) {
        const t=e.data.tick,b=e.data.beatsPerMinute;
        if(points.has(t)&&points.get(t)!==b)throw Error('Conflicting simultaneous tempo');
        points.set(t,b);
    }
    const sorted=[...points].sort((a,b)=>a[0]-b[0]);
    function seconds(tick) {
        if(sorted[0]?.[0]!==0 || tick<0)throw Error('Explicit nonnegative native clock required');
        let q=0,bpm=sorted[0][1],sum=0;
        for(const [t,b]of sorted){if(t>tick)break;sum+=(t-q)/timing.quarter_ticks*60/bpm;q=t;bpm=b;}
        return sum+(tick-q)/timing.quarter_ticks*60/bpm;
    }
    for(const c of callbacks){c.start_seconds=seconds(c.start);c.end_seconds=seconds(c.start+c.length);}
    const bars=gen.tickLookup.masterBars.map(b=>({bar:b.masterBar.index+1,start:b.start,end:b.end,
        tempo_changes:b.tempoChanges.map(p=>({tick:p.tick,tempo:p.tempo})),start_seconds:seconds(b.start),end_seconds:seconds(b.end)}));
    return {model,callbacks,events,origins:midi.events.map(e=>origins.get(e)??null),note_calls:noteCalls,performed_bars:bars};
}

const cases=Object.fromEntries(['source','zero','changed'].map(name=>[name,trace(name)]));
const counterfactual=trace('source',true);
const result={schema:'native-step-tempo-supplement/1',shared_snapshot:{file:'dynamic-native-snapshot.json',sha256:sha(sharedPath)},
    source_scope:{file:'tempo-source-scope.json',sha256:sha(scopePath)},adapter_sha256:sha(fileURLToPath(import.meta.url)),timing,cases,counterfactual,
    reference_scope:'Fresh pristine original native score; sole mutation is exact declared bar-start BPM. Shared-renderer limitation remains.'};
const output=path.join(root,'step-tempo-native-supplement.json');
if(fs.existsSync(output))throw Error('Refusing to overwrite native supplement');
fs.writeFileSync(output,JSON.stringify(result,null,2));
console.log(JSON.stringify({status:'STEP_TEMPO_NATIVE_REFERENCE_WRITTEN_NOT_ACCEPTANCE',output,callbacks:cases.source.callbacks.length}));
