"""Evidence-based repeat candidates on actual bars; no functional section labels.
Pure standard-library callable. Scores are similarities, not probabilities.
"""
from collections import Counter, defaultdict
from fractions import Fraction as Q
from math import isfinite

DEFAULT_WEIGHTS = {'rhythm': .30, 'pitch': .25, 'contour': .15,
                   'harmony': .15, 'arrangement': .15}


def _ratio(a, b):
    keys = set(a) | set(b)
    den = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return sum(min(a.get(k, 0), b.get(k, 0)) for k in keys) / den if den else None


def _key(*v):
    return '|'.join(map(str, v))


def build_bar_features(bars, notes, channels, pitch_notes=None, harmony=None):
    """notes are tie-merged original attacks; pitch_notes optionally technique-aware.
    Bars {bar,start_q,span_q}; notes {part_id,start_q,end_q,pitch,attack}.
    Missing/unknown pitch is never inferred. Percussion participates in rhythm only.
    Harmony optionally maps bar IDs to existing bar-harmony output rows.
    """
    bs = []
    for b in bars:
        a, d = Q(b['start_q']), Q(b['span_q'])
        if d <= 0 or (bs and a != bs[-1][2]):
            raise ValueError('bars must be positive, contiguous and ordered')
        bs.append((b, a, a+d))
    cs = {str(c['part_id']): c for c in channels}
    if len(cs) != len(channels):
        raise ValueError('duplicate channel ID')
    def normalize(rows):
        out=[]
        for n in rows:
            part=str(n['part_id']); a=Q(n['start_q']); z=Q(n['end_q'])
            if part not in cs or z <= a:
                raise ValueError('invalid note channel/time')
            pitch=n.get('pitch')
            if pitch is not None and (isinstance(pitch,bool) or not isinstance(pitch,(int,float)) or not isfinite(pitch)):
                raise ValueError('invalid pitch')
            out.append((n,part,a,z,pitch))
        return out
    ns=normalize(notes); ps=normalize(pitch_notes if pitch_notes is not None else notes)
    result=[]
    for b,a,z in bs:
        d=z-a; rhythm=defaultdict(Counter); pitch=defaultdict(Counter)
        activity=Counter(); unknown=Counter(); pc=Counter(); contour={}
        for n,part,l,r,p in ns:
            if l >= z or r <= a: continue
            activity[part]+=float(min(z,r)-max(a,l))/float(d)
            if n.get('attack',not n.get('tie_destination',False)) and a <= l < z:
                rhythm[part][_key(l-a,r-l)]+=1
        for n,part,l,r,p in ps:
            if l >= z or r <= a: continue
            c=cs[part]
            if c.get('explicit_percussion') or c.get('instrument_id')==1024 or n.get('dead'): continue
            if p is None:
                unknown[part]+=float(min(z,r)-max(a,l))/float(d); continue
            left=max(a,l)-a; duration=min(z,r)-max(a,l)
            pitch[part][_key(left,duration,p)]+=1
            pc[str(p%12)]+=float(duration)
        for part,values in pitch.items():
            base=min(float(k.split('|')[2]) for k in values)
            contour[part]=Counter({_key(*k.split('|')[:2],float(k.split('|')[2])-base):v for k,v in values.items()})
        h=(harmony or {}).get(b['bar'])
        hvec=Counter()
        if h and h.get('candidates'):
            for c in h['candidates']: hvec[str(c['root_pc'])]+=max(0.,c.get('relative_weight',0.))
        elif pc:
            total=sum(pc.values()); hvec=Counter({k:v/total for k,v in pc.items()})
        result.append(dict(bar=b['bar'],start_q=str(a),end_q=str(z),length_q=str(d),
                           rhythm=dict(rhythm),pitch=dict(pitch),contour=contour,
                           harmony=hvec,harmony_basis='candidate_root_weights' if h and h.get('candidates') else 'observed_pitch_duration',
                           arrangement=activity,unknown_pitch_mass=sum(unknown.values()),
                           observed=bool(activity),known_pitch_channels=len(pitch),
                           attack_count=sum(sum(v.values())for v in rhythm.values())))
    return result


def compare_bars(a,b,weights=None):
    w=dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(w)!=set(DEFAULT_WEIGHTS) or any(not isfinite(v) or v<0 for v in w.values()) or not sum(w.values()):
        raise ValueError('invalid feature weights')
    scores={}; per_channel={}; channel_coverage={}
    for feature in ('rhythm','pitch','contour'):
        shared=(set(a['arrangement']) & set(b['arrangement'])) if feature=='rhythm' else (set(a[feature]) & set(b[feature])); vals={}
        for c in sorted(shared):
            v=_ratio(a[feature].get(c,{}),b[feature].get(c,{}))
            if v is not None: vals[c]=v
        # Equal channel votes prevent dense drum or doubled guitar note counts from swamping others.
        scores[feature]=sum(vals.values())/len(vals) if vals else None
        per_channel[feature]=vals
        union=(set(a['arrangement']) | set(b['arrangement'])) if feature=='rhythm' else (set(a[feature]) | set(b[feature]))
        channel_coverage[feature]=len(vals)/len(union) if union else None
    scores['harmony']=_ratio(a['harmony'],b['harmony']) if a['harmony'] and b['harmony'] and a['harmony_basis']==b['harmony_basis'] else None
    scores['arrangement']=_ratio(a['arrangement'],b['arrangement'])
    # Arrangement/pitch-class bag alone cannot establish temporal recurrence.
    temporal= scores['rhythm'] is not None or scores['pitch'] is not None
    den=sum(w[k] for k,v in scores.items() if v is not None)
    s=sum(w[k]*v for k,v in scores.items() if v is not None)/den if den and temporal else None
    if not a['observed'] or not b['observed']: s=None
    meter=min(Q(a['length_q']),Q(b['length_q']))/max(Q(a['length_q']),Q(b['length_q']))
    if s is not None: s*=float(meter)
    return dict(score=s,features=scores,channels=per_channel,meter_similarity=float(meter),
                available_weight=den/sum(w.values()),channel_coverage=channel_coverage,unknown_pitch_mass=[a.get('unknown_pitch_mass',0),b.get('unknown_pitch_mass',0)],
                exact_observed_match=all(a[k]==b[k] for k in ('rhythm','pitch','arrangement','length_q')) and not a.get('unknown_pitch_mass',0) and not b.get('unknown_pitch_mass',0),confidence=None)


def analyze_repeats(features,weights=None,threshold=.82,bar_floor=.55,max_weak_gap=1,min_bars=1):
    """Maximal nonoverlapping diagonal matches with auditable configurable thresholds.
    min_bars=1 retains motifs; no fixed maximum/4/8-bar length or riff restriction.
    Internal loops and weak boundaries remain explicit; no inferred song form.
    """
    if not 0<=bar_floor<=threshold<=1 or type(max_weak_gap)is not int or max_weak_gap<0 or type(min_bars)is not int or min_bars<1:
        raise ValueError('invalid match parameters')
    n=len(features); matrix={}
    for i in range(n):
        for j in range(i+1,n): matrix[i,j]=compare_bars(features[i],features[j],weights)
    def value(i,j):
        if i==j:return 1. if features[i]['observed'] else None
        return matrix[min(i,j),max(i,j)]['score']
    boundaries=[]
    for i in range(n+1):
        s=value(i-1,i) if 0<i<n else None
        boundaries.append(dict(before_index=i,novelty=None if s is None else 1-s,
                               edge=i in (0,n),basis='adjacent_bar_feature_change_not_function'))
    candidates=[]
    for offset in range(1,n):
        # Endpoints must themselves be strong. Weak internal bars can represent changed endings/fills.
        starts=[i for i in range(n-offset) if value(i,i+offset) is not None and value(i,i+offset)>=threshold]
        spans=[]
        for i in starts:
            total=0.; weak=0; best=None
            for k in range(i,min(n-offset,i+offset)):
                s=value(k,k+offset)
                if s is None or s<bar_floor:break
                total+=s; weak=weak+1 if s<threshold else 0
                if weak>max_weak_gap:break
                length=k-i+1
                if s>=threshold and total/length>=threshold and length>=min_bars:best=(i,k+1,total/length)
            if best:spans.append(best)
        # Retain maximal ranges on each diagonal, not every substring of a stronger explanation.
        for i,end,score in spans:
            if any(a<=i and z>=end and (a<i or z>end)for a,z,_ in spans):continue
            length=end-i; comparisons=[matrix[k,k+offset]for k in range(i,end)]
            period=None
            for p in range(1,length//2+1):
                vs=[value(k,k+p)for k in range(i,end-p)]
                if vs and all(v is not None and v>=threshold for v in vs):period=p;break
            av={k:sum(v for v in [c['features'][k]for c in comparisons]if v is not None)/sum(c['features'][k]is not None for c in comparisons) if any(c['features'][k]is not None for c in comparisons)else None for k in DEFAULT_WEIGHTS}
            candidates.append(dict(a_start=i,a_end=end,b_start=i+offset,b_end=end+offset,length_bars=length,
                a_bars=[features[k]['bar']for k in range(i,end)],b_bars=[features[k]['bar']for k in range(i+offset,end+offset)],
                similarity=score,feature_scores=av,
                unknown_pitch_mass=[sum(c['unknown_pitch_mass'][side] for c in comparisons) for side in (0,1)],
                evidence_scope='rhythm_only_or_partial_pitch' if any(c['features']['pitch'] is None or any(c['unknown_pitch_mass']) for c in comparisons) else 'multifeature',
                match_type='exact_observed' if all(c['exact_observed_match'] for c in comparisons) else 'approximate',
                nonexact_bar_offsets=[ix for ix,c in enumerate(comparisons) if not c['exact_observed_match']],
                channel_coverage={k:min(c['channel_coverage'][k] for c in comparisons if c['channel_coverage'][k] is not None) if any(c['channel_coverage'][k] is not None for c in comparisons) else None for k in ('rhythm','pitch','contour')},
                ending_variation_alternative=({'a_bar':features[end]['bar'],'b_bar':features[end+offset]['bar'],'similarity':value(end,end+offset),'included':False} if end<n-offset and end<i+offset and value(end,end+offset) is not None and bar_floor<=value(end,end+offset)<threshold else None),
                bar_scores=[c['score']for c in comparisons],
                available_weight=min(c['available_weight']for c in comparisons),internal_period_bars=period,
                interpretation='repeating_motif_or_loop' if period is not None or length==1 else 'repeated_section_candidate',
                boundary_novelty={k:boundaries[v]['novelty']for k,v in [('a_start',i),('a_end',end),('b_start',i+offset),('b_end',end+offset)]},confidence=None))
    candidates.sort(key=lambda x:(-x['length_bars']*x['similarity'],-x['similarity'],x['a_start'],x['b_start']))
    # Groups require all pairwise edges. No A~B~C transitive merge without A~C evidence.
    edges={};nodes=set()
    for c in candidates:
        a=(c['a_start'],c['a_end']);b=(c['b_start'],c['b_end']);edges[frozenset((a,b))]=c;nodes|={a,b}
    groups=[];seen=set()
    for c in candidates:
        members=[(c['a_start'],c['a_end']),(c['b_start'],c['b_end'])]
        for node in sorted(nodes):
            if node not in members and all(frozenset((node,m))in edges for m in members):members.append(node)
        key=tuple(sorted(members))
        if key in seen:continue
        seen.add(key);groups.append(dict(occurrences=[dict(start_index=a,end_index=b,bars=[f['bar']for f in features[a:b]])for a,b in key],
            interpretation=c['interpretation'],minimum_pair_similarity=min(edges[frozenset((a,b))]['similarity']for ix,a in enumerate(key)for b in key[ix+1:]),confidence=None))
    return dict(schema='bar-section-repeats/1',bar_count=n,parameters=dict(weights=weights or DEFAULT_WEIGHTS,threshold=threshold,bar_floor=bar_floor,max_weak_gap=max_weak_gap,min_bars=min_bars),
                boundaries=boundaries,candidates=candidates,groups=groups,
                limitations=['Candidate repeats, not verified structural sections or verse/chorus labels.',
                             'Bar-aligned equal-length comparisons; insertions/deletions and shifted sub-bar patterns not aligned.',
                             'Missing observations lower evidence coverage, not proof of silence or identity.',
                             'Contour is local within each bar, not a verified constant-transposition claim across a section.',
                             'Thresholds are configurable engineering parameters, not learned confidence.'])
