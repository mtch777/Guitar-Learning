"""Read-only attribution of SAVED research predictions; no fitting or inference.

Annotations enter evaluation only. Emission/message odds decomposition is an
identity, not a causal attribution to an individual transition or a cadence.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def logp(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Invalid saved probability')
    return math.log(max(value, 1e-300))


def pcs(mask):
    if type(mask) is not int or not 0 <= mask < 4096:
        raise ValueError('Typed twelve-PC mask required')
    return [i for i in range(12) if mask & (1 << i)]


def rotation(mask, tonic):
    pcs(mask)
    return ((mask >> tonic) | (mask << (12-tonic))) & 4095


def emission_terms(model, row, state):
    """Independent arithmetic of fixed categorical counts, no infer() call."""
    mode, tonic = divmod(state, 12)
    current = str(rotation(row['mask'], tonic))
    base_count = model['marginal'][mode].get(current, 0)
    base = (base_count + 1/4096)/(model['mode_totals'][mode]+1)
    previous = row['previous_mask']
    if model['kind'] == 'marginal' or previous is None:
        return dict(probability=base, marginal_count=base_count,
                    mode_total=model['mode_totals'][mode], conditional_count=None,
                    context_total=None, backoff=True)
    context_key = str(rotation(previous, tonic))
    context = model['contexts'][mode].get(context_key, {})
    count = context.get(current, 0)
    total = model['context_totals'][mode].get(context_key, 0)
    probability = (count + model['alpha']*base)/(total+model['alpha'])
    return dict(probability=probability, marginal_count=base_count,
                mode_total=model['mode_totals'][mode], conditional_count=count,
                context_total=total, backoff=not bool(context))


def transition_terms(model, left, right):
    mode = left//12
    key = f'{right//12}:{(right%12-left%12)%12}'
    counts = model['key_transitions'][mode]
    count, total = counts.get(key, 0), sum(counts.values())
    return dict(left_state=left, right_state=right, count=count, total=total,
                probability=(count+model['tau']/24)/(total+model['tau']))


def unique(rows, key):
    result = {}
    for row in rows:
        ident = row[key]
        if ident in result:
            raise ValueError('Duplicate saved identity')
        result[ident] = row
    return result


def compare_piece(piece, marginal, ordered):
    """Exhaustive accounting; no results-driven filtering or sample replacement."""
    eligible = [r for r in piece['rows'] if not r['quarantine_reasons']]
    left = unique(marginal, 'observation_ref')
    right = unique(ordered, 'observation_ref')
    ids = [r['id'] for r in eligible]
    if len(ids) != len(set(ids)) or set(ids) != set(left) or set(ids) != set(right):
        raise ValueError('Saved prediction denominator differs')
    result = []
    for row in eligible:
        state = row['target']['state']
        if type(state) is not int or not 0 <= state < 24:
            raise ValueError('Typed evaluation-only target required')
        a, b = left[row['id']], right[row['id']]
        for prediction in (a, b):
            if (prediction['start_q'], prediction['end_q']) != (row['start_q'], row['end_q']):
                raise ValueError('Saved clock differs')
            if len(prediction['posterior']) != 24 or abs(sum(prediction['posterior'])-1) > 1e-10:
                raise ValueError('Saved state distribution differs')
            for p in prediction['posterior']:
                logp(p)
        duration = F(row['end_q'])-F(row['start_q'])
        if duration <= 0 or duration != F(row['duration_q']):
            raise ValueError('Source duration differs')
        la, lb = -logp(a['posterior'][state]), -logp(b['posterior'][state])
        delta = lb-la
        result.append(dict(work=piece['work'], piece=piece['piece'], cell_id=row['id'],
            sequence=row['sequence'], start_q=row['start_q'], end_q=row['end_q'],
            duration_q=str(duration), current_pcs=pcs(row['mask']),
            previous_pcs=None if row['previous_mask'] is None else pcs(row['previous_mask']),
            source_note_refs=row.get('active_note_refs', []), target_evaluation_only=row['target'],
            marginal_nll=la, ordered_nll=lb, ordered_minus_marginal_nll=delta,
            duration_weighted_difference=float(duration)*delta,
            classification='help' if delta < 0 else 'hurt' if delta > 0 else 'tie',
            marginal_map_state=a['marginal_map_state'], ordered_map_state=b['marginal_map_state']))
    return result


def explain(cell, source, predictions, models, previous_reference_state=None):
    target = cell['target_evaluation_only']['state']
    # Fixed comparator: marginal MAP unless it is target, then strongest
    # marginal non-target state. No comparator chosen to improve the narrative.
    marginal = predictions['marginal'][cell['cell_id']]
    competitor = marginal['marginal_map_state']
    if competitor == target:
        competitor = max((s for s in range(24) if s != target),
                         key=lambda s: (marginal['posterior'][s], -s))
    details = {}
    for kind, model in models.items():
        prediction = predictions[kind][cell['cell_id']]
        te, ce = emission_terms(model, source, target), emission_terms(model, source, competitor)
        posterior_odds = logp(prediction['posterior'][target])-logp(prediction['posterior'][competitor])
        emission_odds = logp(te['probability'])-logp(ce['probability'])
        details[kind] = dict(target_emission=te, competitor_emission=ce,
            posterior_log_odds=posterior_odds, emission_log_odds=emission_odds,
            normalized_past_future_message_log_odds=posterior_odds-emission_odds,
            annotation='Message residual includes all past/future evidence and transitions; not one transition cause')
        details[kind]['illustrative_transition_from_same_previous_marginal_MAP'] = (
            None if previous_reference_state is None else dict(
                target=transition_terms(model, previous_reference_state, target),
                competitor=transition_terms(model, previous_reference_state, competitor),
                meaning='One fixed transition lookup; NOT the forward-backward mixture or causal attribution'))
    return dict(**cell, fixed_competitor_state=competitor, fixed_model_evidence=details)


def run(study, output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:
        raise ValueError('Fresh private diagnostic directory required')
    output.mkdir(parents=True)
    original_freeze = json.loads((study/'freeze.json').read_text())
    manifest_path = Path(next(p for p in original_freeze if p.endswith('manifest.json')))
    manifest = json.loads(manifest_path.read_text())
    files = list(study.glob('*.json')) + [Path(p) for p in original_freeze] + [Path(__file__)]
    frozen = {str(p.resolve()): sha(p) for p in files}
    # Validate the study's original dataset/code seals before reading outcomes.
    for path, digest in original_freeze.items():
        if sha(Path(path)) != digest:
            raise ValueError('Original study freeze differs')
    plan = dict(frozen=frozen, ranking='Per-cell ordered-minus-marginal target NLL; top5 help and top5 hurt; ties work/piece/rationalclock/id',
        scope='Saved test predictions only; no fitting/inference/tuning; research-only licensed artifacts stay private',
        emission_attribution='Fixed categorical counts; posterior odds minus emission odds is normalized past/future message residual, not causal cadence attribution')
    (output/'plan-before-ranking.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    saved = {k:json.loads((study/(k+'-test.json')).read_text()) for k in ('marginal','ordered')}
    models = {k:json.loads((study/(k+'-research-model.json')).read_text()) for k in saved}
    predictions = {k:{r['piece']:unique(r['prediction']['rows'], 'observation_ref') for r in v['predictions']} for k,v in saved.items()}
    pieces = {}; cells = []; denominators = Counter()
    for record in manifest['records']:
        if record['split'] != 'test':
            continue
        path = manifest_path.parent/record['file']
        if sha(path) != record['sha256']:
            raise ValueError('Dataset manifest differs')
        piece = json.loads(path.read_text()); pieces[piece['piece']] = piece
        denominators['all_test_source_cells'] += len(piece['rows'])
        denominators['quarantined_test_cells'] += sum(bool(r['quarantine_reasons']) for r in piece['rows'])
        cells += compare_piece(piece, list(predictions['marginal'][piece['piece']].values()), list(predictions['ordered'][piece['piece']].values()))
    if any(set(predictions[k]) != set(pieces) for k in predictions):
        raise ValueError('Saved test piece inventory differs')
    duration = sum((F(c['duration_q']) for c in cells), F(0))
    recomputed = {k:sum(float(F(c['duration_q']))*c[k+'_nll'] for c in cells)/float(duration) for k in saved}
    for k in saved:
        if abs(recomputed[k]-saved[k]['aggregate']['key_label_nll']) > 1e-10:
            raise ValueError('Saved aggregate NLL does not reconcile')
    def rank(c):
        return (c['work'], c['piece'], F(c['start_q']), c['cell_id'])
    chosen = sorted((c for c in cells if c['classification']=='help'),key=lambda c:(c['ordered_minus_marginal_nll'],rank(c)))[:5]
    chosen += sorted((c for c in cells if c['classification']=='hurt'),key=lambda c:(-c['ordered_minus_marginal_nll'],rank(c)))[:5]
    examples=[]
    for cell in chosen:
        source=next(r for r in pieces[cell['piece']]['rows'] if r['id']==cell['cell_id'])
        predecessors=[r for r in pieces[cell['piece']]['rows'] if not r['quarantine_reasons'] and r['sequence']==source['sequence'] and r['end_q']==source['start_q']]
        if len(predecessors)>1:raise ValueError('Ambiguous saved sequence predecessor')
        previous_state=None if not predecessors else predictions['marginal'][cell['piece']][predecessors[0]['id']]['marginal_map_state']
        examples.append(explain(cell, source, {k:predictions[k][cell['piece']] for k in saved},models,previous_state))
    bywork = defaultdict(list)
    for c in cells: bywork[c['work']].append(c)
    works={w:dict(cells=len(rows),counts=dict(Counter(c['classification'] for c in rows)),duration_q=str(sum((F(c['duration_q']) for c in rows),F(0))),weighted_nll_difference_sum=sum(c['duration_weighted_difference'] for c in rows)) for w,rows in sorted(bywork.items())}
    unchanged=all(sha(Path(p))==h for p,h in frozen.items())
    report=dict(status='PASS_SAVED_PREDICTION_ACCOUNTING' if unchanged else 'FAIL_CHANGED',unchanged=unchanged,denominators=dict(denominators),eligible_cells=len(cells),outcomes=dict(Counter(c['classification'] for c in cells)),duration_q=str(duration),recomputed_nll=recomputed,works=works,examples=examples,
        limitations=['No new inference or fitting','Analyst major/minor targets are evaluation-only, not universal truth','NC research only; no guitar, seven-mode, functional or causal-transition claim'])
    (output/'all-cell-differences.json').write_text(json.dumps(cells),encoding='utf-8')
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    result=run(args.study,args.output);print(json.dumps({k:v for k,v in result.items() if k!='examples'}));raise SystemExit(0 if result['unchanged'] else 1)
