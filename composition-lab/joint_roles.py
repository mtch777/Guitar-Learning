"""Empirical joint-role conditional model; no asserted chord/root truth.

Learns accompaniment pitch-class sets and bass relation jointly from source
sustains. This is a sparse two-song baseline, not validated harmonic reasoning.
"""
from collections import Counter,defaultdict
from fractions import Fraction as F
import math


def source_rows(graph,roles,duration):
    nodes=list(graph['sustains'].values());rows=[]
    for q in range(int(F(duration))):
        active={role:[n['midi'] for n in nodes if n['track']==ti and n['midi'] is not None and F(n['onset_q'])<=q<F(n['end_q'])] for role,ti in roles.items()}
        if not active['melody'] or not active['harmony'] or not active['bass']:continue
        anchor=max(active['melody']);classes=tuple(sorted({(p-anchor)%12 for p in active['harmony']}))
        # Large source chords are represented without claiming their root.
        target=(classes,(min(active['bass'])-anchor)%12)
        rows.append(((anchor%12,q%4),target))
    return rows


class JointRoleModel:
    def __init__(self):self.contexts=defaultdict(Counter);self.global_counts=Counter()
    def fit(self,rows):
        for context,target in rows:self.contexts[context][target]+=1;self.global_counts[target]+=1
        if not self.global_counts:raise ValueError('No simultaneous role evidence')
        return self
    def distribution(self,context):return self.contexts.get(context) or self.global_counts
    def sample(self,rng,context):
        counts=self.distribution(context);return rng.choices(list(counts),weights=list(counts.values()),k=1)[0]
    def evaluate(self,rows):
        vocabulary=len(self.global_counts)+1;paired=[];independent=[];unseen=0
        for context,target in rows:
            counts=self.distribution(context)
            paired.append(-math.log((counts[target]+.5)/(sum(counts.values())+.5*vocabulary)))
            independent.append(-math.log((self.global_counts[target]+.5)/(sum(self.global_counts.values())+.5*vocabulary)))
            unseen+=target not in self.global_counts
        return dict(rows=len(rows),conditional_nll=sum(paired)/len(paired) if paired else None,
            independent_nll=sum(independent)/len(independent) if independent else None,unseen_targets=unseen,
            scope='source-disjoint two-song test; joint PC-set/bass token NLL is not harmonic accuracy')
