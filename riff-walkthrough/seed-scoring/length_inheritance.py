"""Length constraints only; never changes relationship labels or generates notes."""
from fractions import Fraction
INHERITING=('Intended same notes and timing as (phrase #s)','Intended same rhythm and holds as (phrase #s)')
def known_targets(text):
 # Parse explicit phrase-number tokens only. Counts inside 'unknown comparisons: 2' are NOT links.
 return [int(t.strip()) for t in text.split(';') if t.strip().lstrip('-').isdigit()]
def resolve(rows):
 ids={int(r['Phrase #']) for r in rows};original={int(r['Phrase #']):Fraction(str(r['Length (beats)'])) for r in rows}
 if any(x<=0 for x in original.values()):raise ValueError('Blueprint phrase lengths must be positive')
 edges=set();warnings=[]
 for r in rows:
  i=int(r['Phrase #'])
  for label in INHERITING:
   s=r[label]
   if any(t in s.lower() for t in ['unknown','unresolved','indeterminate']):warnings.append({'phrase':i,'field':label,'source_value':s,'action':'Known explicit targets only; unknown comparisons not inferred.'})
   for j in known_targets(s):
    if j not in ids or j==i:raise ValueError(f'Invalid repeat target {i}->{j}')
    edges.add((i,j))
 # Equality links define components; seed anchors its entire connected repeat family.
 neighbors={i:set() for i in ids};deps={i:set() for i in ids}
 for i,j in edges:
  neighbors[i].add(j);neighbors[j].add(i)
  if (j,i) not in edges or i>j:deps[i].add(j)
 # Strongly connected cycles without pairwise reciprocal links anchor at earliest phrase.
 index={};low={};stack=[];on=set();scc=[]
 def visit(v):
  index[v]=len(index);low[v]=index[v];stack.append(v);on.add(v)
  for w in deps[v]:
   if w not in index:visit(w);low[v]=min(low[v],low[w])
   elif w in on:low[v]=min(low[v],index[w])
  if low[v]==index[v]:
   group=[]
   while True:
    w=stack.pop();on.remove(w);group.append(w)
    if w==v:break
   scc.append(set(group))
 for i in sorted(ids):
  if i not in index:visit(i)
 membership={v:k for k,g in enumerate(scc) for v in g};outgoing={k:set() for k in range(len(scc))}
 for i in ids:
  for j in deps[i]:
   if membership[i]!=membership[j]:outgoing[membership[i]].add(membership[j])
 lengths=dict(original);sources={};conflicts=[];seen=set()
 for first in sorted(ids):
  if first in seen:continue
  group=set();todo=[first]
  while todo:
   x=todo.pop()
   if x in group:continue
   group.add(x);todo.extend(neighbors[x]-group)
  seen.update(group)
  if 1 in group:anchors=[1]
  else:
   comps={membership[x] for x in group};anchors=sorted(min(scc[k]) for k in comps if not outgoing[k])
  values={original[a] for a in anchors}
  if len(values)!=1:
   conflicts.append({'phrases':sorted(group),'source_phrases':anchors,'source_lengths_beats':[float(original[a]) for a in anchors],'action':'Unresolved conflicting source lengths; no automatic choice or label change.'})
   for i in group:sources[i]=None
  else:
   for i in group:lengths[i]=original[anchors[0]];sources[i]=anchors[0]
 position=Fraction(0);changes=[]
 for r in rows:
  i=int(r['Phrase #']);r['Original length (beats)']=float(original[i]);r['Length (beats)']=float(lengths[i]);r['Start position (beats)']=float(position);position+=lengths[i];r['End position (beats)']=float(position)
  r['Length source phrase #']=sources[i] if sources[i] is not None else ''
  r['Length resolution']='unresolved conflicting sources' if sources[i] is None else 'seed authoritative' if sources[i]==1 else 'earliest source after reciprocal/chain resolution'
  if lengths[i]!=original[i]:changes.append({'phrase':i,'from_beats':float(original[i]),'to_beats':float(lengths[i]),'source_phrase':sources[i]})
 remaining=[]
 for i,j in sorted(edges):
  if lengths[i]!=lengths[j]:remaining.append({'phrase':i,'target':j,'phrase_beats':float(lengths[i]),'target_beats':float(lengths[j])})
 for r in rows:
  relevant=[x for x in remaining if x['phrase']==r['Phrase #'] or x['target']==r['Phrase #']]
  r['Length conflict']='unresolved repeat-length conflict' if relevant else 'none detected for known exact-repeat/rhythm targets'
 return {'inheritance_rule':'Only exact notes/timing and rhythm/holds links; reciprocal links use earliest phrase; chains resolved; seed phrase1 authoritative. Pitch-only and variation links do not propagate length.','length_changes':changes,'length_conflicts':remaining,'source_conflicts':conflicts,'unknown_link_warnings':warnings,'blueprint_total_beats':float(position)}
