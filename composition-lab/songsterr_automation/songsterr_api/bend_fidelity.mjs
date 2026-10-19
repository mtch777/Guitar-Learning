/**
 * Opt-in exact model-bend preservation for the alphaTab GP7 pipeline.
 *
 * The current GP7 writer cannot encode every curve accepted by the model, and alphaTab's
 * import normalization can erase interior points. A private, hash-bound sidecar
 * restores the pre-export model curves for explicit alphaTab playback/analysis.
 * The standalone GP file is NOT claimed to preserve those curves. No upstream
 * prototypes are patched; no source data is written by this module.
 */
import { createHash } from 'node:crypto';

const SCHEMA = 'composition-lab.exact-model-bends.v1';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

function notes(score) {
    const result = [];
    for (const [track, t] of score.tracks.entries())
        for (const [staff, s] of t.staves.entries())
            for (const [bar, b] of s.bars.entries())
                for (const [voice, v] of b.voices.entries())
                    for (const [beat, e] of v.beats.entries())
                        for (const [note, n] of e.notes.entries())
                            result.push({ address: [track, staff, bar, voice, beat, note], note: n });
    return result;
}

function identity(n) {
    return { string: n.string, fret: n.fret, tie: n.isTieDestination, dead: n.isDead,
        duration: n.beat.duration, dots: n.beat.dots,
        tuplet: [n.beat.tupletNumerator, n.beat.tupletDenominator], grace: n.beat.graceType };
}

function validateCurve(points) {
    if (!Array.isArray(points) || points.length < 2) throw Error('Invalid exact bend curve');
    let previous = -Infinity;
    for (const p of points) {
        if (!Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite)
            || p[0] < 0 || p[0] > 60 || p[0] < previous) {
            throw Error('Exact bends require finite, ordered offsets in 0..60');
        }
        previous = p[0];
    }
}

function findNote(score, address) {
    if (!Array.isArray(address) || address.length !== 6 || !address.every(x => Number.isInteger(x) && x >= 0)) {
        throw Error('Invalid exact bend address');
    }
    const [t, s, b, v, e, n] = address;
    return score.tracks[t]?.staves[s]?.bars[b]?.voices[v]?.beats[e]?.notes[n];
}

function restore(at, score, sidecar) {
    // Validate the complete restore set before changing any note.
    const seen = new Set();
    const plan = sidecar.curves.map(record => {
        const key = JSON.stringify(record.address);
        if (seen.has(key)) throw Error('Duplicate exact bend address');
        seen.add(key);
        const note = findNote(score, record.address);
        if (!note || JSON.stringify(identity(note)) !== JSON.stringify(record.identity)) {
            throw Error(`Exact bend note identity mismatch at ${key}`);
        }
        validateCurve(record.points);
        if (!Number.isInteger(record.bend_type) || !(record.bend_type in at.model.BendType)
            || record.bend_type === at.model.BendType.None
            || !Number.isInteger(record.bend_style) || !(record.bend_style in at.model.BendStyle)) {
            throw Error('Invalid exact bend type/style');
        }
        return { note, record };
    });
    const continuationPlan = (sidecar.continuations || []).map(record => {
        const note = findNote(score, record.address), origin = findNote(score, record.origin);
        if (!note || !origin || note.tieOrigin !== origin
            || JSON.stringify(identity(note)) !== JSON.stringify(record.identity)
            || typeof record.continued !== 'boolean') throw Error('Exact bend continuation identity mismatch');
        return { note, origin, record };
    });
    for (const { note, record } of plan) {
        note.bendPoints = null;
        note.maxBendPoint = null;
        note.bendType = at.model.BendType.None;
        for (const [offset, value] of record.points) note.addBendPoint(new at.model.BendPoint(offset, value));
        note.bendType = record.bend_type;
        note.bendStyle = record.bend_style;
    }
    for (const { note, origin, record } of continuationPlan) {
        note.bendOrigin = origin;
        note.isContinuedBend = record.continued;
    }
    return plan.length;
}

export function exportWithExactBends(at, score, settings = new at.Settings(), nativeExport = null) {
    const allNotes = notes(score);
    const addresses = new Map(allNotes.map(row => [row.note, row.address]));
    const curves = allNotes.filter(row => row.note.bendPoints?.length).map(({ address, note }) => {
        const points = note.bendPoints.map(p => [p.offset, p.value]);
        validateCurve(points);
        return { address, identity: identity(note), points, bend_type: note.bendType, bend_style: note.bendStyle };
    });
    const continuations = allNotes.filter(row => row.note.bendOrigin !== null).map(({ address, note }) => {
        const origin = addresses.get(note.bendOrigin);
        if (!origin || note.tieOrigin !== note.bendOrigin) throw Error('Unsupported exact bend continuation origin');
        return { address, identity: identity(note), origin, continued: note.isContinuedBend };
    });
    // Capture exact model data first, then allow the existing native writer path.
    const bytes = nativeExport ? nativeExport() : new at.exporter.Gp7Exporter().export(score, settings);
    const sidecar = { schema: SCHEMA, gp_sha256: hash(bytes), curves, continuations,
        scope: 'Exact pre-export alphaTab model note-bend curves; standalone native GP fidelity is not guaranteed.' };
    // Reject an export that cannot support identity-safe restoration immediately.
    const reopened = at.importer.ScoreLoader.loadScoreFromBytes(bytes, settings);
    restore(at, reopened, sidecar);
    return { bytes, sidecar };
}

export function loadWithExactBends(at, bytes, sidecar, settings = new at.Settings()) {
    if (!sidecar || sidecar.schema !== SCHEMA || !Array.isArray(sidecar.curves)
        || !Array.isArray(sidecar.continuations)) throw Error('Invalid exact bend sidecar');
    if (hash(bytes) !== sidecar.gp_sha256) throw Error('Exact bend sidecar GP hash mismatch');
    const score = at.importer.ScoreLoader.loadScoreFromBytes(bytes, settings);
    const restored = restore(at, score, sidecar);
    return { score, restored, native_gp_lossless: false };
}
