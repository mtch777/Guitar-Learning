"""Auditable notation-rate gaps; not artist intent, audio quality or causation.

Source model weights and generated equal-piece weights remain explicit. Unknown
features never become negative labels; unsupported strata remain unsupported.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
import math

from annotation_context_gap import decompose


def _count(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError('Nonnegative integer support required')
    return value


def _rate(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:
        raise ValueError('Finite numeric rate0–1 required')
    return value


def rank_rate_report(report):
    """Check eligible piece counts and add signed gaps to existing frozen rates."""
    results = []
    pieces = report['pieces']
    names = [p['file'] for p in pieces]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate generated piece identity')
    for feature, supplied in report['features'].items():
        rates = []
        positive = known = positive_pieces = 0
        for piece in pieces:
            n = _count(piece['known'].get(feature, 0))
            y = _count(piece['positive'].get(feature, 0))
            if y > n:
                raise ValueError('Positive support exceeds eligible support')
            if n:
                rates.append(y/n)
                positive_pieces += y > 0
            positive += y
            known += n
        source = supplied['source_family_balanced_attack_rate']
        if source is not None:_rate(source)
        generated = sum(rates)/len(rates) if rates else None
        existing = supplied['generated_equal_piece_attack_rate']
        if existing is not None:_rate(existing)
        if (generated is None) != (existing is None) or (generated is not None and abs(generated-existing)>1e-12):
            raise ValueError('Generated rate does not reconcile with per-piece support')
        if ('known_generated_groups' in supplied and supplied['known_generated_groups'] != known) or ('positive_generated_groups' in supplied and supplied['positive_generated_groups'] != positive):
            raise ValueError('Aggregate generated support does not reconcile with pieces')
        gap = 100*(generated-source) if generated is not None and source is not None else None
        results.append(dict(feature=feature, source_rate=source, generated_rate=generated,
                            signed_gap_pp=gap, absolute_gap_pp=abs(gap) if gap is not None else None,
                            generated_known=known, generated_positive=positive,
                            eligible_pieces=len(rates), positive_pieces=positive_pieces,
                            total_pieces=len(pieces)))
    return sorted(results,key=lambda r:(r['absolute_gap_pp'] is None,-(r['absolute_gap_pp'] or 0),r['feature']))


def audit_split(events, model):
    """Verify actual model membership and event family boundaries independently."""
    eligible = [e for e in events if not e.get('flagged')]
    if any(e['partition'] not in ('development','held_out') for e in eligible):
        raise ValueError('Unknown partition cannot establish leakage safety')
    train = [e for e in eligible if e['partition']=='development']
    held = [e for e in eligible if e['partition']=='held_out']
    train_songs={e['song_id'] for e in train}; held_songs={e['song_id'] for e in held}
    train_families={e['family'] for e in train}; held_families={e['family'] for e in held}
    if train_songs & held_songs or train_families & held_families:
        raise ValueError('Development/held-out identity or family leakage')
    if train_songs != set(model['training_songs']) or train_families != set(model['training_families']):
        raise ValueError('Model membership does not match eligible development observations')
    if len(train) != model['training_events']:
        raise ValueError('Model event support mismatch')
    artist_train={e['artist'] for e in train}
    return dict(training_events=len(train),training_songs=len(train_songs),
                training_families=len(train_families),heldout_events=len(held),
                heldout_songs=len(held_songs),heldout_families=len(held_families),
                heldout_unknown_artist_events=sum(e['artist'] not in artist_train for e in held),
                song_overlap=0,family_overlap=0,
                limitation='Checks supplied conservative family identities; does not certify composition identity or transcription correctness')


def support(events, feature):
    known=[e for e in events if feature in e.get('known',())]
    positive=[e for e in known if feature in e.get('labels',())]
    if any(feature in e.get('labels',()) and feature not in e.get('known',()) for e in events):
        raise ValueError('Positive annotation has unknown eligibility')
    return dict(events=len(events),eligible=len(known),positive=len(positive),
                eligible_songs=len({e['song_id'] for e in known}),
                positive_songs=len({e['song_id'] for e in positive}),
                eligible_families=len({e.get('family',e['song_id']) for e in known}),
                positive_families=len({e.get('family',e['song_id']) for e in positive}))


def stratified_accounting(source, generated, feature, fields):
    """Exact shared-stratum accounting using caller-supplied positive weights.

    Missing stratum fields are excluded and counted, not labelled a musical role.
    Components depend on decomposition order; they are not causal attributions.
    """
    def table(rows):
        values=defaultdict(lambda:[F(0),F(0)]);missing=unknown=0
        for event in rows:
            if feature in event.get('labels',()) and feature not in event.get('known',()):
                raise ValueError('Positive annotation has unknown eligibility')
            if feature not in event.get('known',()):unknown+=1;continue
            if any(event.get(f) is None for f in fields):missing+=1;continue
            weight=F(str(event.get('weight',1)))
            if weight<=0:raise ValueError('Positive observation weight required')
            key=tuple(event[f] for f in fields)
            values[key][0]+=weight;values[key][1]+=weight*int(feature in event.get('labels',()))
        return values,missing,unknown
    a,am,au=table(source);b,bm,bu=table(generated)
    result=decompose(a,b)
    # Compact exact decomposition as finite decimals; original event weights
    # remain reproducible inputs. Never fabricate rates for unshared strata.
    compact={k:float(F(v)) if v is not None else None for k,v in result.items() if k!='components' and k!='shared_contexts'}
    compact.update(shared_strata=result['shared_contexts'],
                   components={k:float(F(v)) for k,v in result['components'].items()} if result['components'] else None,
                   source_missing_stratum=am,generated_missing_stratum=bm,
                   source_unknown_feature=au,generated_unknown_feature=bu,
                   fields=list(fields),weighting='caller-supplied event weights; default pooled events',
                   limitation='Descriptive shared-stratum identity; not causal or artist-style accuracy')
    return compact
