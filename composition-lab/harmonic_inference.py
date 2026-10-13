"""Evidence-aware tonal and chord hypotheses from symbolic GP guitar/bass tracks.

Not a verified transcription. Model avoids treating bass notes as automatic roots,
and supports inverse/slash chords, pedals, no-chord and unresolved harmony.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from phrase_development import parse

NAMES = ('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
MODES = {
 'Ionian':(0,2,4,5,7,9,11),'Dorian':(0,2,3,5,7,9,10),
 'Phrygian':(0,1,3,5,7,8,10),'Lydian':(0,2,4,6,7,9,11),
 'Mixolydian':(0,2,4,5,7,9,10),'Aeolian':(0,2,3,5,7,8,10),
 'Locrian':(0,1,3,5,6,8,10)}
CHORDS = {'5':(0,7),'major':(0,4,7),'minor':(0,3,7),
 'sus2':(0,2,7),'sus4':(0,5,7),'dim':(0,3,6),
 'major7':(0,4,7,11),'minor7':(0,3,7,10),'dom7':(0,4,7,10)}
DEFAULTS = {'bass':1.5,'chord':2.5,'bass_chord':3.,'ending':2.,
 'melody':0.55,'scale':1.2,'pedal':0.2,'prior':0.05,
 'min_margin':0.08,'min_coverage':0.72}

def norm(p): return int(p)%12
def name(p): return NAMES[norm(p)]
def category(label):
 s=label.lower()
 if 'drum' in s or 'percussion' in s:return 'drums'
 if 'bass' in s:return 'bass'
 if any(w in s for w in ('guitar','lead','rhythm','distortion','clean')):return 'guitar'
 return 'other'

def collect(score):
 """Per-measure notes, true simultaneous guitar pitch clusters, bass and endings."""
 unique=set();selected=[];excluded=[]
 for track in score['tracks']:
  kind=category(track['name'])
  if kind not in ('guitar','bass'):continue
  signature=repr(track['measures'])
  if kind=='guitar' and signature in unique:
   excluded.append(track['name']);continue
  unique.add(signature);selected.append((kind,track))
 results=[]
 for i in range(score['measures']):
  melody=Counter();bass=Counter();clusters=[];last_notes=[]
  for kind,track in selected:
   for voice,beat,duration,pitches in track['measures'][i]:
    if kind=='bass':
     for p in pitches:bass[norm(p)]+=duration
    else:
     for p in pitches:melody[norm(p)]+=duration
     if len(set(map(norm,pitches)))>=2:
      clusters.append({'onset':beat,'duration':duration,'notes':tuple(sorted(set(map(norm,pitches))))})
     if voice==0 and len(pitches)==1:
      last_notes.append((beat+duration,norm(pitches[0])))
  results.append({'measure':i+1,'melody':melody,'bass':bass,'clusters':clusters,
                  'ending':max(last_notes)[1] if last_notes else None})
 return results,excluded

def chords_for(notes, bass=None, limit=5):
 """Match actual simultaneous note collections; keep inversions and pedal conflicts."""
 notes={norm(p) for p in notes}
 if len(notes)<2:return []
 choices=[]
 for root in range(12):
  for quality,intervals in CHORDS.items():
   chord={(root+x)%12 for x in intervals}
   hit=notes&chord
   if len(hit)<2:continue
   covered=len(hit)/len(notes);completeness=len(hit)/len(chord)
   # Strongly prefer a fully matched observed sonority without pretending
   # extensions, inversions and passing tones are impossible.
   fit=.73*covered+.27*completeness
   relation='absent' if bass is None else ('root' if norm(bass)==root else
                'inversion' if norm(bass) in chord else 'pedal_or_nonchord')
   if relation=='root':fit+=.1
   elif relation=='inversion':fit+=.035
   choices.append({'root':root,'quality':quality,'fit':round(fit,4),
                   'bass_relation':relation,'matched':[name(p) for p in sorted(hit)],
                   'nonchord':[name(p) for p in sorted(notes-chord)]})
 return sorted(choices,key=lambda v:(-v['fit'],-len(v['matched']),v['root']))[:limit]

def analyze_measure(measure,tonic=None,mode=None):
 bass=measure['bass'];clusters=measure['clusters']
 basspc=bass.most_common(1)[0][0] if bass else None
 votes=defaultdict(float);evidence=defaultdict(list)
 for cluster in clusters:
  candidates=chords_for(cluster['notes'],basspc,limit=10)
  if not candidates:continue
  peak=candidates[0]['fit']
  plausible=[x for x in candidates if peak-x['fit']<=.07]
  for c in plausible:
   key=(c['root'],c['quality'])
   weight=cluster['duration']*c['fit']/len(plausible)
   votes[key]+=weight
   evidence[key].append({'bass':c['bass_relation'],'notes':[name(p) for p in cluster['notes']]})
 if not votes:
  return {'label': 'no_explicit_chord','bass_note':name(basspc) if basspc is not None else None,
          'candidates':[],'confidence':'unresolved','reason':'no simultaneous chord evidence'}
 # Use inferred scale as a small tie-breaker, never as evidence that a chord exists.
 if tonic in NAMES and mode in MODES:
  allowed={(NAMES.index(tonic)+n)%12 for n in MODES[mode]}
  for key in list(votes):
   root,quality=key
   pcs={(root+i)%12 for i in CHORDS[quality]}
   votes[key]*=(1+0.06*len(pcs & allowed)/len(pcs))
 ranked=sorted(votes.items(),key=lambda kv:-kv[1])
 options=[]
 for (root,quality),support in ranked[:5]:
  bassrel=Counter(x['bass'] for x in evidence[(root,quality)]).most_common(1)[0][0]
  if basspc is None:label=name(root)+' '+quality
  elif bassrel=='root':label=name(root)+' '+quality
  else:label=name(root)+' '+quality+'/'+name(basspc)
  options.append({'chord':label,'root':name(root),'quality':quality,
                  'support':round(support,4),'bass_relation':bassrel,
                  'observed_clusters':evidence[(root,quality)][:4]})
 total=sum(v for _,v in ranked)
 margin=(ranked[0][1]-ranked[1][1])/total if len(ranked)>1 else 1
 top=options[0]
 flag=('strong' if margin>=.25 and top['bass_relation'] in ('root','inversion')
       else 'moderate' if margin>=.12 else 'ambiguous')
 return {'label':top['chord'] if flag!='ambiguous' else 'ambiguous_chord',
         'bass_note':name(basspc) if basspc is not None else None,
         'candidates':options,'confidence':flag,'score_margin':round(margin,4),
         'reason':'simultaneous chord clusters with separate bass interpretation'}

def tonal_candidates(measures,section_endings=(),weights=None):
 w={**DEFAULTS,**(weights or {})}
 unknown=set(w)-set(DEFAULTS)
 if unknown:raise ValueError('Unknown weights: '+', '.join(sorted(unknown)))
 if any(not isinstance(v,(int,float)) or v<0 for v in w.values()):
  raise ValueError('Weights must be nonnegative')
 centers=Counter();pitch=Counter();sources=defaultdict(Counter)
 endings=set(section_endings)
 endings.add(len(measures))
 for local_idx,m in enumerate(measures,1):
  for pc,v in m['melody'].items():pitch[pc]+=v
  for pc,v in m['bass'].items():
   pitch[pc]+=v
   centers[pc]+=w['bass']*v;sources[pc]['bass']+=w['bass']*v
  if local_idx in endings and m['ending'] is not None:
   pc=m['ending'];centers[pc]+=w['ending'];sources[pc]['ending']+=w['ending']
  basspc=m['bass'].most_common(1)[0][0] if m['bass'] else None
  for cluster in m['clusters']:
   cs=chords_for(cluster['notes'],basspc,10)
   if not cs:continue
   plausible=[c for c in cs if cs[0]['fit']-c['fit']<=.07]
   for c in plausible:
    val=w['chord']*cluster['duration']*c['fit']/len(plausible)
    centers[c['root']]+=val;sources[c['root']]['explicit_chord']+=val
    if c['bass_relation']=='root':
     joint=w['bass_chord']*cluster['duration']/len(plausible)
     centers[c['root']]+=joint;sources[c['root']]['bass_chord_agreement']+=joint
 if not centers or not pitch:return {'status':'insufficient_evidence','ranked':[],'centers':[]}
 norm_center=sum(centers.values());norm_pitch=sum(pitch.values())
 centerlist=sorted([{'tonic':name(pc),'evidence_share':round(centers[pc]/norm_center,4),
                     'sources':dict(sources[pc])} for pc in range(12)],
                   key=lambda x:-x['evidence_share'])
 ranked=[]
 for tonic in range(12):
  for mode,intervals in MODES.items():
   allowed={(tonic+i)%12 for i in intervals}
   coverage=sum(pitch[p] for p in allowed)/norm_pitch
   ranked.append({'tonic':name(tonic),'mode':mode,
                  'score':round(centers[tonic]/norm_center+w['scale']*coverage,5),
                  'collection_coverage':round(coverage,4)})
 ranked.sort(key=lambda x:-x['score'])
 best=ranked[0];second=ranked[1]
 center_margin=centerlist[0]['evidence_share']-centerlist[1]['evidence_share']
 same=[v for v in ranked if v['tonic']==best['tonic']]
 mode_margin=same[0]['score']-same[1]['score']
 has_direct_harmony=any(m['bass'] or m['clusters'] for m in measures)
 status=('melody_only_weak_evidence' if not has_direct_harmony else
         'weak_pitch_collection' if best['collection_coverage']<w['min_coverage'] else
         'ambiguous_tonic' if center_margin<w['min_margin'] or best['tonic']!=centerlist[0]['tonic'] else
         'ambiguous_mode' if mode_margin<w['min_margin'] else 'tentative')
 return {'status':status,'ranked':ranked[:10],'centers':centerlist[:5],
         'center_margin':round(center_margin,4),'mode_margin':round(mode_margin,4),
         'note':'Scores are heuristic rankings, not confidence probabilities'}

def infer_score(score,weights=None):
 measures,excluded=collect(score)
 starts=sorted({1,score['measures']+1}|{m for m,_ in score['sections']})
 ending_numbers={v-1 for v in starts if v>1}
 overall=tonal_candidates(measures,ending_numbers,weights)
 sections=[]
 for start,end in zip(starts,starts[1:]):
  section=measures[start-1:end-1]
  label=next((s for i,s in score['sections'] if i==start),None)
  sections.append({'label':label,'start':start,'end':end-1,
                   'tonality':tonal_candidates(section,(len(section),),weights)})
 # Chords inferred from simultaneous notes, not an averaged 12-note bar bag.
 per_measure=[]
 for m in measures:
  sectional=next((s['tonality'] for s in sections if s['start']<=m['measure']<=s['end']),overall)
  candidate=sectional['ranked'][0] if sectional.get('status')=='tentative' and sectional.get('ranked') else None
  h=analyze_measure(m,candidate['tonic'] if candidate else None,
                       candidate['mode'] if candidate else None)
  h['tonal_context_used']=candidate is not None
  per_measure.append({'measure':m['measure'],'harmony':h})
 return {'song':score['song'],'overall':overall,'sections':sections,
         'measure_harmony':per_measure,'excluded_exact_doubles':excluded,
         'limitations':['No ground-truth key or chord labels','Rests/ties omitted by upstream parser',
            'Mode estimation uses tonal and pitch-class heuristics; no formal cadence parser',
            'Chord groups may represent riffs/dyads instead of sustained functional harmony',
            'No chord propagation from repeated sections in this version']}
def infer(path,weights=None):return infer_score(parse(path),weights)
def main():
 p=argparse.ArgumentParser()
 p.add_argument('files',type=Path,nargs='+')
 p.add_argument('--weights',type=Path)
 p.add_argument('--output',type=Path)
 args=p.parse_args()
 weights=json.loads(args.weights.read_text()) if args.weights else None
 reports=[infer(x,weights) for x in args.files]
 result=json.dumps(reports,indent=2)
 if args.output:
  args.output.parent.mkdir(exist_ok=True,parents=True)
  args.output.write_text(result,encoding='utf-8')
  print('Wrote',args.output)
 else:print(result)
if __name__=='__main__':main()
