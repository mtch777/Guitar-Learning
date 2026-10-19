"""Source-free aggregate views of the private written-relationship profile.

No note sequences, score names, occurrence identities or private annotations
are copied into the result. These attack-group rates are not note percentages.
"""
from collections import defaultdict
import math


def summarize(model):
    if model.get('scope') != 'development_fit':
        raise ValueError('Development profile required; held-out inventory stays separate')
    features = defaultdict(list)
    identities = set()
    for row in model['technique_song_summaries']:
        key = row['song_id'], row['feature']
        if key in identities:
            raise ValueError('Duplicate song/feature summary')
        identities.add(key)
        n, y = row['eligible_attack_groups'], row['positive_attack_groups']
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (n, y)) or not 0 <= y <= n or n <= 0:
            raise ValueError('Positive eligible integer support required')
        if row['song_id'] not in model['training_songs'] or row['family'] not in model['training_families']:
            raise ValueError('Summary outside fitted partition')
        features[row['feature']].append((row['family'], n, y))
    result = {}
    for feature, rows in sorted(features.items()):
        families = defaultdict(list)
        for family, n, y in rows:families[family].append(y/n)
        rates = [y/n for family, n, y in rows]
        result[feature] = dict(eligible_groups=sum(n for f,n,y in rows),
            positive_groups=sum(y for f,n,y in rows),
            pooled_rate=sum(y for f,n,y in rows)/sum(n for f,n,y in rows),
            equal_score_rate=sum(rates)/len(rates),
            equal_family_rate=sum(sum(v)/len(v) for v in families.values())/len(families),
            eligible_scores=len(rows),positive_scores=sum(y>0 for f,n,y in rows),
            eligible_families=len(families),positive_families=sum(any(v>0 for v in values) for values in families.values()),
            minimum_score_rate=min(rates),maximum_score_rate=max(rates))
    answers = defaultdict(lambda: [0, 0.0])
    for table in model['tables']:
        if table['kind'] != 'same_pedal_call_answer_variation':continue
        for outcome in table['outcomes']:
            value = outcome['outcome']
            if any(type(value.get(k)) is not bool for k in ('response_pitch_same','response_rhythm_same')):
                raise ValueError('Explicit Boolean response comparisons required')
            if type(outcome['count']) is not int or outcome['count'] < 0:
                raise ValueError('Nonnegative integer comparison count required')
            key = ('same' if value['response_pitch_same'] else 'changed')+'_pitch_'+('same' if value['response_rhythm_same'] else 'changed')+'_rhythm'
            if not math.isfinite(outcome['weight']) or outcome['weight']<0:
                raise ValueError('Finite nonnegative answer weight required')
            answers[key][0] += outcome['count'];answers[key][1] += outcome['weight']
    mass=sum(v[1] for v in answers.values())
    return dict(schema='written-relationship-aggregate-summary-v1',artist=model['artist'],
        development_scores=len(model['training_songs']),development_families=len(model['training_families']),
        features=result,repeated_call_answer_variation={k:dict(count=v[0],family_weighted_share=v[1]/mass if mass else None) for k,v in sorted(answers.items())},
        limitations=['Regular track attack groups; positive if any member has the covered annotation, not individual note percentages',
            'Song families reduce version-count dominance; differing versions within a family still affect its average',
            'Answer variation compares approved repeated exact-call patterns within accepted pedal phrases, not general phrase intent',
            'No artist feel, performed-technique absence or musical-quality claim'])
