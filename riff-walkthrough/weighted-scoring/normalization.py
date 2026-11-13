"""Frozen, previously validated per-field normalizers. Numeric keys are schema IDs, NOT CSV positions."""
import re,json

def bad(s):return bool(re.search(r'unknown|unresolved|not.established|not computed|indeterminate|not applicable|partial|incomplete|unassigned|not available|\?' ,s,re.I))

def number(s):
 if bad(s):raise ValueError('unknown/partial')
 return float(s)

def lead(s):
 if bad(s):raise ValueError('unknown/partial')
 m=re.match(r'(-?\d+(?:\.\d+)?)',s);return float(m[1]) if m else number(s)

def ratio(a,b):return 100 if a==b==0 else 100*min(a,b)/max(a,b)

def pp(a,b):return max(0,100-abs(a-b))

def jac(a,b):return 100 if not(a|b) else 100*len(a&b)/len(a|b)

def edit(a,b):
 if len(a)<len(b):a,b=b,a
 if not a:return 100
 prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  cur=[i]
  for j,y in enumerate(b,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
  prev=cur
 return 100*(1-prev[-1]/max(len(a),len(b)))

def groups(s):return [tuple(sorted(x.split())) for x in re.findall(r'\[([^]]*)\]',s)]

def semi(s):return set() if s.strip() in ['none','none recorded'] else {x.strip() for x in s.split(';') if x.strip()}

def midi(p):
 m=re.fullmatch(r'([A-G])([#b]?)(-?\d+)',p);assert m,p
 return 12*(int(m[3])+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[m[1]]+{'':0,'#':1,'b':-1}[m[2]]

def norm_events(s,drop_pitch=False):
 if s=='none':return []
 out=[]
 for x in s.split(';'):
  x=x.strip(); x=re.sub(r'\[([^]]*)\]',lambda m:'[NOTE]' if drop_pitch else '['+' '.join(sorted(m[1].split()))+']',x)
  out.append(x)
 return out

def parse(s,i):
 if bad(s):raise ValueError('unknown/partial/unestablished')
 if s=='none assigned':raise ValueError('not assigned != absent')
 if i in [5,6,7,23,38]:return s
 if i in [11,12,13,14,15,39,51,52]:return number(s)
 if i==30:return lead(s)
 if i==40:return number(s)
 if i in [46,47]:
  m=re.search(r'\((\d+(?:\.\d+)?)%\)',s)
  if not m:raise ValueError('unparsed usage percentage')
  return float(m[1])
 if i==10:return semi(s)-{'heuristic_hypothesis'}
 if i==26:return {re.sub(r':\s*\d+ notes.*$','',x) for x in semi(s)}
 if i==31:return semi(s.split(' (')[0])
 if i in [41,42]:return semi(s)
 if i==27:
  m=re.fullmatch(r'(\S+) to (\S+) \(mapped\)',s)
  if not m:raise ValueError('not complete mapped pitch range')
  return (midi(m[1]),midi(m[2]))
 if i==32:
  m=re.fullmatch(r'(\d+)\.\.(\d+) \(mapped\)',s)
  if not m:raise ValueError('not complete mapped fret range')
  return tuple(map(float,m.groups()))
 if i==35:return groups(s)
 if i==37:return [(tuple(sorted(g.split())),int(n)) for g,n in re.findall(r'\[([^]]*)\] x(\d+)',s)]
 if i==45:return sorted(semi(s))
 if i in [43,48,49]:return norm_events(s,drop_pitch=i==48)
 if i==50:
  m=re.fullmatch(r'attack onset gaps \(beats x count\): (\{.*\}); actual all-voices silence: ([\d.]+) beats',s)
  if not m:raise ValueError('unparsed gaps/rests')
  return (json.loads(m[1]),float(m[2]))
 if i in [16,17,18,19]:
  if s=='none':return set()
  return {int(x)-1 for x in re.split('[;, ]+',s) if x}
 return s

def compare(a,b,i):
 if i in [5,6,7,23,38,20,21,22]:return 100.0*(a==b)
 if i in [11,12,13,14,15,30,39,51,52]:return ratio(a,b)
 if i in [40,46,47]:return pp(a,b)
 if i in [10,26,31,41,42,16,17,18,19]:return jac(a,b)
 if i in [27,32]:
  scale=24 if i==27 else 12
  return 50*(max(0,1-abs(sum(a)/2-sum(b)/2)/scale)+max(0,1-abs((a[1]-a[0])-(b[1]-b[0]))/scale))
 if i==50:
  keys=a[0].keys()|b[0].keys(); den=sum(max(a[0].get(k,0),b[0].get(k,0)) for k in keys)
  j=100*sum(min(a[0].get(k,0),b[0].get(k,0)) for k in keys)/den if den else 100
  return (j+ratio(a[1],b[1]))/2
 return edit(a,b)
