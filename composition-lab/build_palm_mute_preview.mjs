// Export/render only actual isolated-inverse captures. No musical choices here.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const [qaArg, captureArg, python, backend, modulePath, font] = process.argv.slice(2);
if (!font) throw Error('QA folder, original capture, backend Python/root, alphaTab module and soundfont required');
const qa = path.resolve(qaArg), capture = path.resolve(captureArg);
const lab = path.dirname(fileURLToPath(import.meta.url)), out = path.join(qa, 'native-preview');
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const result = read(path.join(qa, 'result.json')), demo = read(path.join(qa, 'demonstration.json'));
if (result.status !== 'PASS_SOURCE_PALM_MUTE_CHANGE') throw Error('Verified actual palm-mute worker change required');
if (fs.existsSync(out)) throw Error('Fresh native output folder required; preserve earlier failures');
fs.mkdirSync(out);
process.on('uncaughtException', error => {
    fs.writeFileSync(path.join(out, 'failure.json'), JSON.stringify({status: 'FAIL_RETAINED', error: String(error), stack: error.stack}, null, 2));
    console.error(error);
    process.exitCode = 1;
});
function run(executable, args, log) {
    const r = spawnSync(executable, args, {cwd: lab, encoding: 'utf8', timeout: 600000, windowsHide: true});
    fs.writeFileSync(path.join(out, log), (r.stdout || '') + '\n' + (r.stderr || ''));
    if (r.status !== 0) throw Error(`Command failed: ${log}`);
}
const binding = `from pathlib import Path
import json,sys
from source_fact_tier1 import extract
from check_palm_mute_artifacts import source_scope
q,c=map(Path,sys.argv[1:3])
z=json.loads((q/'zero-isolated/worker/output.json').read_bytes())
a=json.loads((q/'changed-isolated/worker/output.json').read_bytes())
assert extract(c)==z==extract(q/'zero-capture')
assert extract(q/'changed-capture')==a
scope=source_scope(z,a,json.loads((q/'demonstration.json').read_bytes()))
print(json.dumps(dict(status='PASS_ACTUAL_WORKER_AND_SOURCE_SCOPE',part=scope['part'],bar=scope['bar'],position_q=scope['position_q'],member_refs=scope['members'])))`;
run(python, ['-c', binding, qa, capture], 'worker-binding-before.json');
const scope = read(path.join(out, 'worker-binding-before.json'));
if (scope.part !== demo.clip.part || scope.bar < demo.clip.first || scope.bar > demo.clip.last)
    throw Error('Declared clip does not contain the actual target');
for (const name of ['source', 'zero', 'changed'])
    run(python, [path.join(lab, 'export_owned_capture.py'), name === 'source' ? capture : path.join(qa, name + '-capture'), backend, path.join(out, name)], `${name}-export.log`);
run(process.execPath, [path.join(lab, 'songsterr_automation/songsterr_api/export_csv_gp7.mjs'), modulePath, out, '--restore-pitched-graces'], 'native-gp.log');
for (const name of ['source', 'zero', 'changed']) {
    const v = read(path.join(out, name, 'gp7-validation.json'));
    if (v.error || v.directSource?.differences !== 0 ||
        !['PASS_INDEPENDENT_PITCHED_SOURCE_GRACES', 'NO_COVERED_PITCHED_GRACE_VOICES'].includes(v.directPitchedGraces?.status))
        throw Error(`Native GP/source validation failed: ${name}`);
}
run(process.execPath, [path.join(lab, 'audit_dynamic_gp.mjs'), modulePath, qa, out, 'gp_with_exact_model_bends', capture], 'native-snapshot.log');
run(process.execPath, [path.join(lab, 'audit_palm_mute_gp.mjs'), modulePath, out], 'native-mute-supplement.log');
const jobs = [];
for (const name of ['source', 'zero', 'changed'])
    for (const mode of ['focused', 'ensemble'])
        jobs.push({case_id: name + '-' + mode, method: name, mode, file: path.join(out, name, 'score.gp'),
            out: path.join(out, name, mode + '.wav'), track: scope.part, start_bar: demo.clip.first,
            end_bar: demo.clip.last, target_bar: scope.bar, target_offset_q: scope.position_q});
fs.writeFileSync(path.join(out, 'audio-jobs.json'), JSON.stringify(jobs, null, 2));
run(process.execPath, [path.join(lab, 'render_source_passages.mjs'), modulePath, font, path.join(out, 'audio-jobs.json')], 'audio-render.log');
run(python, [path.join(lab, 'check_palm_mute_artifacts.py'), out, qa], 'native-artifact-audit.log');
run(python, ['-c', binding, qa, capture], 'worker-binding-after.json');
const audit = read(path.join(out, 'palm-mute-artifact-audit.json'));
console.log(JSON.stringify({status: 'NATIVE_PALM_MUTE_OUTPUT_CHECKED', audit_status: audit.status,
    output: out, pcm_difference_measured: audit.pcm_difference_measured, listening_judgment: null}));
