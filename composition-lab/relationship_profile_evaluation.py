"""Held-out annotation prediction, distinct from exact vocabulary coverage.

Fixed smoothing is declared before evaluation. This does not tune on held-out
outcomes or establish musical correctness. Scores use family/song weights from
the profile, never raw event pooling across duplicate song versions.
"""
from collections import defaultdict
import math

from artist_relationship_profiles import heldout_support, signature

KINDS = ('technique_given_context', 'technique_given_written_harmony_labels',
         'technique_given_accepted_pedal_role')


def evaluate_boolean_relationships(model, held, prior_mass=1.0, epsilon=1e-6):
    """Compare a context-conditioned estimate with its feature-only baseline.

    One prior unit means one eligible family-equivalent in the profile's weight
    units. Unseen contexts back off to the fitted feature marginal. The reported
    denominator excludes unknown features upstream. Sparse support is exposed.
    """
    heldout_support(model, held)  # Fail closed on scope, artist or family leakage.
    if (isinstance(prior_mass, bool) or not isinstance(prior_mass, (int, float))
            or not math.isfinite(prior_mass) or prior_mass <= 0):
        raise ValueError('Positive finite prior mass required')
    if (isinstance(epsilon, bool) or not isinstance(epsilon, (int, float))
            or not math.isfinite(epsilon) or not 0 < epsilon < .5):
        raise ValueError('Finite clipping epsilon between zero and one half required')
    totals = defaultdict(lambda: [0.0, 0.0])
    index = {}

    def masses(table):
        positive = total = 0.0
        for outcome in table['outcomes']:
            if type(outcome['outcome']) is not bool:
                raise ValueError('Boolean outcomes required')
            weight = outcome['weight']
            if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0:
                raise ValueError('Finite nonnegative profile weight required')
            if 'song_counts' in outcome:
                counts = outcome['song_counts']
                if any(isinstance(v['count'], bool) or not isinstance(v['count'], int) or v['count'] < 0 for v in counts):
                    raise ValueError('Nonnegative integer song outcome count required')
                if len({v['song_id'] for v in counts}) != len(counts) or sum(v['count'] for v in counts) != outcome['count']:
                    raise ValueError('Song outcome counts must reconcile')
            total += weight
            positive += weight * outcome['outcome']
        if total <= 0:
            raise ValueError('Positive eligible profile weight required')
        return positive, total

    for table in model['tables']:
        if table['kind'] not in KINDS:
            continue
        feature = (table['kind'], table['condition']['feature'])
        key = (feature, signature(table['condition']))
        if key in index:
            raise ValueError('Duplicate fitted condition')
        positive, total = masses(table)
        index[key] = positive, total
        totals[feature][0] += positive
        totals[feature][1] += total

    rows = {}
    song_scores = defaultdict(lambda: dict(count=0, baseline_loss=0.0, conditional_loss=0.0))
    for table in held['tables']:
        if table['kind'] not in KINDS:
            continue
        feature = (table['kind'], table['condition']['feature'])
        positive, total = masses(table)
        for outcome in table['outcomes']:
            if any(v['song_id'] not in held['observed_songs'] or v['family'] not in held['observed_families'] for v in outcome.get('song_counts', [])):
                raise ValueError('Song support outside held-out partition')
        row = rows.setdefault(feature, dict(kind=feature[0], feature=feature[1],
            definition_coupled_context=(feature[0]=='technique_given_context' and feature[1] in
                ('double_stop','power_chord','extended_power_chord','close_interval_texture')),
            eligible_count=0, positive_count=0, weighted_eligible_mass=0.0,
            fitted_context_mass=0.0, backoff_mass=0.0, unsupported_mass=0.0,
            conditional_log_loss=0.0, baseline_log_loss=0.0,
            conditional_brier=0.0, baseline_brier=0.0))
        row['eligible_count'] += table['eligible_count']
        row['positive_count'] += sum(o['count'] for o in table['outcomes'] if o['outcome'])
        if feature not in totals:
            row['unsupported_mass'] += total
            continue
        base_positive, base_total = totals[feature]
        baseline = base_positive / base_total
        fitted = index.get((feature, signature(table['condition'])))
        if fitted is None:
            prediction = baseline
            row['backoff_mass'] += total
        else:
            prediction = (fitted[0] + prior_mass * baseline) / (fitted[1] + prior_mass)
            row['fitted_context_mass'] += total
        row['weighted_eligible_mass'] += total
        for name, p in [('baseline', baseline), ('conditional', prediction)]:
            p = min(1-epsilon, max(epsilon, p))
            row[name+'_log_loss'] += -positive*math.log(p) - (total-positive)*math.log1p(-p)
            row[name+'_brier'] += positive*(1-p)**2 + (total-positive)*p**2
            for outcome in table['outcomes']:
                for support in outcome.get('song_counts', []):
                    key = feature, support['family'], support['song_id']
                    score = song_scores[key]
                    n = support['count']
                    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
                        raise ValueError('Nonnegative integer song outcome count required')
                    score[name+'_loss'] += -n*math.log(p if outcome['outcome'] else 1-p)
                    if name == 'baseline':score['count'] += n
    family_scores = defaultdict(lambda: defaultdict(list))
    per_song = []
    for (feature, family, sid), score in song_scores.items():
        if not score['count']:continue
        baseline = score['baseline_loss']/score['count']
        conditional = score['conditional_loss']/score['count']
        family_scores[feature][family].append(baseline-conditional)
        per_song.append(dict(kind=feature[0],feature=feature[1],family=family,song_id=sid,
            eligible_count=score['count'],baseline_log_loss=baseline,
            conditional_log_loss=conditional,log_loss_improvement=baseline-conditional))
    for row in rows.values():
        mass = row['weighted_eligible_mass']
        for metric in ('log_loss', 'brier'):
            for name in ('baseline', 'conditional'):
                key = name+'_'+metric
                row[key] = row[key]/mass if mass else None
            row[metric+'_improvement'] = row['baseline_'+metric]-row['conditional_'+metric] if mass else None
        gains = [sum(v)/len(v) for v in family_scores[row['kind'],row['feature']].values()]
        row['family_sensitivity'] = dict(families=len(gains),
            improving_families=sum(v > 0 for v in gains),
            minimum_family_log_loss_improvement=min(gains) if gains else None,
            maximum_family_log_loss_improvement=max(gains) if gains else None,
            minimum_leave_one_family_out_improvement=min((sum(gains)-v)/(len(gains)-1) for v in gains) if len(gains)>1 else None,
            maximum_leave_one_family_out_improvement=max((sum(gains)-v)/(len(gains)-1) for v in gains) if len(gains)>1 else None)
    return dict(schema='written-relationship-prediction-v1', prior_mass=prior_mass,
        epsilon=epsilon, heldout_songs=len(held['observed_songs']),
        heldout_families=len(held['observed_families']), results=list(rows.values()), per_song=per_song,
        limitations=['Previously examined held-out split; diagnostic, not a pristine final test',
            'Predicts written group-any-technique annotations, not note percentages, listening quality or artist intent',
            'Condition selection and smoothing were not optimized on these outcomes',
            'Cardinality-defined chord/dyad labels share definition information with context; their gain is not a newly discovered artist relationship',
            'Family ranges and leave-one-family-out sensitivity are descriptive, not confidence intervals or independent new tests',
            'Positive improvement means lower predictive error only; no generator promotion follows'])
