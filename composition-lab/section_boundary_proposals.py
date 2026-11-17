"""Experimental context-boundary refinement, independent of editor annotations."""
from math import sqrt
import section_repeats as B

def context_boundaries(f):
 n=len(f);m=[[0.0]*n for _ in range(n)]
 for i in range(n):
  for j in range(i,n):
   v=1.0 if i==j and f[i]['observed'] else B.compare_bars(f[i],f[j])['score']
   m[i][j]=m[j][i]=0 if v is None else v
 p=[[0.0]*(n+1) for _ in range(n+1)]
 for i in range(n):
  for j in range(n):p[i+1][j+1]=m[i][j]+p[i][j+1]+p[i+1][j]-p[i][j]
 def rect(a,b,c,d):return p[b][d]-p[a][d]-p[b][c]+p[a][c]
 values=[0.]*(n+1);scales=[None]*(n+1)
 for i in range(1,n):
  for w in range(2,min(i,n-i)+1):
   # Exclude self similarity from within-context averages.
   within=(rect(i-w,i,i-w,i)+rect(i,i+w,i,i+w)-2*w)/(2*w*(w-1))
   cross=rect(i-w,i,i,i+w)/(w*w)
   novelty=max(0.,within-cross)
   if novelty>values[i]:values[i]=novelty;scales[i]=w
 values[0]=values[-1]=max(values,default=0.)
 return values,scales

def refine(f,candidates,extension=1):
 if type(extension) is not int or extension<0:raise ValueError('extension must be a nonnegative integer')
 values,scales=context_boundaries(f);n=len(f);out=[]
 for c in candidates:
  a,z,b,e=c['a_start'],c['a_end'],c['b_start'],c['b_end'];length=z-a
  if length<2:continue
  best=None
  # An endpoint can grow by the existing repeat matcher weak-gap allowance.
  for left in range(-min(extension,a,b),length):
   for right in range(left+2,length+min(extension,n-z,n-e)+1):
    aa,zz,bb,ee=a+left,a+right,b+left,b+right
    if zz>bb:continue
    boundary=(values[aa]+values[zz]+values[bb]+values[ee])/4
    retained=max(0,min(right,length)-max(left,0))/length
    score=boundary*sqrt(retained)
    row=dict(a_start=aa,a_end=zz,b_start=bb,b_end=ee,source_range=[a,z,b,e],boundary_support=boundary,retained_fraction=retained,rank_score=score,view=c.get('view','original'))
    if best is None or score>best['rank_score'] or (score==best['rank_score'] and retained>best['retained_fraction']):best=row
  if best:out.append(best)
 # Keep distinct proposals, evidence order, do not silently partition/assign roles.
 unique={}
 for x in sorted(out,key=lambda x:-x['rank_score']):unique.setdefault(tuple(x[k] for k in ('a_start','a_end','b_start','b_end')),x)
 return dict(boundary_values=values,boundary_scales=scales,proposals=list(unique.values()),limitation='Boundary-ranked alternatives, not functional labels or a final partition; no annotations used.')


def analyze_boundary_proposals(features, extension=1):
 """Opt-in supplementary proposals; original matches remain available unchanged.

 Does not label verse/chorus or claim precision from candidate coverage.
 """
 from section_variant_repeats import analyze
 original=B.analyze_repeats(features)
 variant=analyze(features)
 candidates=[dict(c,view='original') for c in original['candidates']]+[dict(c,view='ordered_pitch') for c in variant['candidates']]
 result=refine(features,candidates,extension=extension)
 result.update(schema='bar-section-boundary-proposals/1',bar_count=len(features),original=original,variant=variant)
 return result
