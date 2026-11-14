"""Positive per-phrase multipliers. No candidate gates or count-based stacking."""
import math, re, collections
from fractions import Fraction as Q
DEFAULTS={'plain_long_singles':0.1,'triplets':2.0,'intervals':2.0,'minor_second':2.0}
ACTIVE={k:1.0 for k in DEFAULTS}
EVENTS='Rhythmic events in order (all attacks/rests; dotted notes/tuplets/ties; simultaneous chords grouped)'
def pitch_flags(groups):
 dyads=[g for g in groups if len(g)==2 and all(isinstance(p,(int,float)) and not isinstance(p,bool) and math.isfinite(p) for p in g) and g[0]!=g[1]]
 return {'intervals':bool(dyads),'minor_second':any(abs(g[0]-g[1])==1 for g in dyads)}
def sounding_flags(notes):
 events=collections.defaultdict(list)
 for i,n in enumerate(notes):
  try:
   start=Q(str(n['start_exact'] if 'start_exact' in n else n['start_beats']))
   duration=Q(str(n['duration_exact'] if 'duration_exact' in n else n['duration_beats']))
   if duration<=0:continue
  except (ValueError,KeyError,TypeError,ZeroDivisionError):return {'intervals':None,'minor_second':None}
  events[start].append((i,n.get('midi_pitch')));events[start+duration].append((i,None,'off'))
 active={};flags={'intervals':False,'minor_second':False};unknown=False;times=sorted(events)
 for j,t in enumerate(times[:-1]):
  for item in events[t]:
   if len(item)==3:active.pop(item[0],None)
  for item in events[t]:
   if len(item)==2:active[item[0]]=item[1]
  if times[j+1]<=max(t,0):continue
  if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in active.values()):
   unknown=True;continue
  pitches=set(active.values())
  if len(active)==2 and len(pitches)==2:
   flags['intervals']=True
   if max(pitches)-min(pitches)==1:flags['minor_second']=True
 if unknown:
  flags={k:True if v else None for k,v in flags.items()}
 return flags

def assigned_notes(notes,groups,source_evidence=False):
 starts=collections.defaultdict(list)
 for n in notes:starts[Q(str(n['start_exact'] if 'start_exact' in n else n['start_beats']))].append(n)
 if len(starts)!=len(groups):return [{**n,'midi_pitch':None} for n in notes]
 assigned=[]
 for (_,slot),pitches in zip(sorted(starts.items()),groups):
  if len(slot)!=len(pitches):return [{**n,'midi_pitch':None} for n in notes]
  if source_evidence and len({Q(str(n['duration_exact'] if 'duration_exact' in n else n['duration_beats'])) for n in slot})>1:pitches=[None]*len(pitches)
  for n,pitch in zip(sorted(slot,key=lambda n:n.get('note_slot',0)),sorted(pitches,key=lambda p:-1 if p is None else p)):
   assigned.append({**n,'midi_pitch':pitch})
 return assigned

def rhythm_flags(notes,row):
 starts=collections.defaultdict(list);durations=[];intervals=[];complete=bool(notes)
 for n in notes:
  try:
   a=Q(str(n['start_exact'] if 'start_exact' in n else n['start_beats']))
   d=Q(str(n['duration_exact'] if 'duration_exact' in n else n['duration_beats']))
   if d<=0 or a<0:complete=False
   starts[a].append(n);durations.append(d);intervals.append((a,a+d))
  except (ValueError,TypeError,KeyError,ZeroDivisionError):complete=False
 ordered=sorted(intervals)
 no_overlap=all(b<=c for (a,b),(c,d) in zip(ordered,ordered[1:]))
 plain=complete and no_overlap and len(starts)>=4 and all(len(v)==1 for v in starts.values()) and len(set(durations))==1 and durations[0]>=1
 # Explicit written labels, including rests/ties. Never infer from off-grid phase.
 triplets=bool(re.search(r'\btriplet\b',row.get(EVENTS,''),re.I))
 try:
  import first_phrase_pitch as F
  flags=sounding_flags(assigned_notes(notes,F.groups(row),source_evidence=True))
 except (ValueError,KeyError,TypeError):flags={'intervals':None,'minor_second':None}
 return {'plain_long_singles':bool(plain),'triplets':triplets,'intervals':flags['intervals']}
def multiplier(flags,weights=None):
 weights=ACTIVE if weights is None else weights
 value=math.prod(weights[k] for k,v in flags.items() if v)
 if not math.isfinite(value) or value<=0:raise ValueError('Combined phrase multipliers exceed numeric precision; use less extreme values. No draw performed.')
 return value
def rhythm(notes,row):
 flags=rhythm_flags(notes,row);return multiplier(flags),flags
