"""Apply a declared output-change request to a saved musical model.

No source scores or proposed notes are inputs. The original saved model and
request remain immutable; the output is realized through the existing inverse.
The optional denied worker verifies reconstruction with lower/source files absent.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

from qa_isolation_harness import strict_json
from source_observation_evidence import digest


def reconstruct(model):
    if model.get('tier') == 3:
        import support_material_uses as uses
        return uses.reconstruct(model, {'variation': 0})
    import connected_tier2
    return connected_tier2.reconstruct(model, {'variation': 0})


def apply(model, request):
    if type(request) is not dict:
        raise ValueError('Explicit output-change request required')
    kind = request.get('kind')
    if kind == 'movement' and set(request) == {'kind', 'controls', 'max_candidates'}:
        import movement_output_control
        return movement_output_control.intervene(model, request['controls'],
                                                  max_candidates=request['max_candidates'])
    if kind == 'rhythm' and set(request) == {'kind', 'requests', 'percent', 'seed', 'max_combinations'}:
        import rhythm_output_control
        return rhythm_output_control.intervene(model, request['requests'], request['percent'],
            seed=request['seed'], max_combinations=request['max_combinations'])
    if kind == 'connected' and set(request) == {'kind', 'movement', 'rhythm_requests',
            'rhythm_percent', 'seed', 'max_candidates', 'max_rhythm_combinations'}:
        import connected_output_control
        return connected_output_control.intervene(model, request['movement'], request['rhythm_requests'],
            request['rhythm_percent'], seed=request['seed'], max_candidates=request['max_candidates'],
            max_rhythm_combinations=request['max_rhythm_combinations'])
    raise ValueError('Explicit supported movement, rhythm or connected output request required')


def run(model_path, request_path, output, *, denied=False):
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    model_bytes = model_path.read_bytes(); request_bytes = request_path.read_bytes()
    model = strict_json(model_bytes.decode('utf-8-sig'))
    request = strict_json(request_bytes.decode('utf-8-sig'))
    def save(name, value):
        (output / name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf8')
    def sha(value):
        return hashlib.sha256(value).hexdigest()
    lab = Path(__file__).resolve().parent
    save('freeze.json', dict(model_sha256=sha(model_bytes), request_sha256=sha(request_bytes),
        model_path=str(model_path.resolve()), request_path=str(request_path.resolve()),
        runtime=dict(executable=sys.executable, version=list(sys.version_info[:3])),
        code={p.name: sha(p.read_bytes()) for p in sorted(lab.glob('*.py'))},
        scope='Caller-declared complete population; no source lookup or post-result selection'))
    baseline = reconstruct(model)
    snapshot = digest(model)
    changed, decision = apply(model, request)
    if digest(model) != snapshot:
        raise ValueError('Operation mutated its input')
    if not decision.get('satisfied', False) and changed != model:
        raise ValueError('Unsatisfied request committed a partial edit')
    actual = reconstruct(changed)
    save('decision.json', decision)
    save('current-model.json', changed)
    save('current-t1.json', actual)
    saved = strict_json((output/'current-model.json').read_text(encoding='utf8'))
    if reconstruct(saved) != actual:
        raise ValueError('Saved current inverse differs')
    proof = {}
    if denied:
        from qa_isolation_harness import execute
        if model.get('tier') == 3:
            from run_support_arrangement_qa import bundle
            code, hashes = bundle(lab, boundary='source')
            code += "\nreconstruct=sys.modules['support_material_uses'].reconstruct\n"
        else:
            from run_connected_tier2_qa import bundle
            code, hashes = bundle(lab)
        runtime = dict(implementation=sys.implementation.name, version=list(sys.version_info[:3]),
                       executable=str(Path(sys.executable).resolve()))
        checksum = sha(code.encode())
        save('inverse-freeze.json', dict(module_hashes=hashes, operator_sha256=checksum, runtime=runtime))
        for name, upper, expected in [('baseline', model, baseline), ('current', saved, actual)]:
            receipt = execute(code, upper, {'variation': 0}, expected, output/(name+'-denied'),
                timeout=600, purpose='exact_zero', expected_runtime=runtime,
                expected_operator_sha256=checksum)
            proof[name] = receipt['status']
            save('inverse-results.json', proof)
            if receipt['status'] != 'PASS':
                raise ValueError('Source/lower-denied inverse failed: '+name)
    if model_path.read_bytes() != model_bytes or request_path.read_bytes() != request_bytes:
        raise ValueError('Frozen input files changed')
    result = dict(status=decision['status'], satisfied=decision.get('satisfied', False),
        score_changed=actual != baseline, baseline_facts=len(baseline['facts']),
        final_facts=len(actual['facts']), saved_inverse=True, input_unchanged=True,
        qa2=proof if denied else 'DENIED_WORKER_NOT_RUN',
        qa1='SELECTION_RECEIPT_REQUIRED_SEPARATELY',
        qa3='Final output counts verified; musical capability and listening scope require separate review',
        elapsed_s=round(time.monotonic()-started, 3))
    save('result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('request', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--denied', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.model, args.request, args.output, denied=args.denied)), flush=True)
