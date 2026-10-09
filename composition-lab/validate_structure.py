"""Label-blind structural novelty and cautious pitch-class chord hypotheses.

Standalone composition-lab module. No trainer, web, or audio dependencies.
Source section labels are used ONLY after prediction for evaluation.
"""
import argparse,csv,json,math
from pathlib import Path
from collections import Counter
from phrase_analysis import parsed_tracks

NAMES=('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
CHORDS={'power':(0,7),'minor':(0,3,7),'major':(0,4,7),
        'sus2':(0,2,7),'sus4':(0,5,7),'dim':(0,3,6),
        'minor7':(0,3,7,10),'major7':(0,4,7,11),'dom7':(0,4,7,10)}

def track_kind(name):
    s=name.lower()
    if 'bass' in s:return 'bass'
    if any(x in s for x in ('guitar','lead','rhythm','clean','distortion')):return 'guitar'
    return None

def histogram(events):
    result=Counter()
    for _,_,duration,pitches in events:
        for pitch in pitches:result[pitch%12]+=duration
    return result

def gap(a,b):
    dot=sum(a[k]*b[k] for k in set(a)|set(b))
    la=math.sqrt(sum(x*x for x in a.values()))
    lb=math.sqrt(sum(x*x for x in b.values()))
    return 1-dot/(la*lb) if la and lb else (1. if la or lb else 0.)

def chord_candidates(weights,bass_root=None,limit=3):
    if not weights:return []
    total=sum(weights.values());options=[]
    for root in range(12):
        for kind,intervals in CHORDS.items():
            members={(root+i)%12 for i in intervals}
            coverage=sum(weights.get(pc,0) for pc in members)/total
            present=sum(1 for pc in members if weights.get(pc,0)>0)
            score=.7*coverage+.3*present/len(members)
            if bass_root is not None and root==bass_root:score+=.08
            options.append({'name':NAMES[root]+' '+kind,'score':round(score,3),
                            'pitch_coverage':round(coverage,3)})
    return sorted(options,key=lambda x:-x['score'])[:limit]

def analyze(path,bars_per_boundary=12,min_spacing=4,tolerance=1):
    song=parsed_tracks(path);tracks=song['tracks'];n=len(song['meter'])
    groups={'guitar':[],'bass':[]};seen=set();duplicates=[]
    for track in tracks:
        kind=track_kind(track['track'])
        if kind is None:continue
        if kind=='guitar':
            sig=tuple(tuple(bar) for bar in track['measures'])
            if sig in seen:
                duplicates.append(track['track']);continue
            seen.add(sig)
        groups[kind].append(track)
    measures=[]
    for index in range(n):
        guitar=Counter();bass=Counter();density=0
        for tr in groups['guitar']:
            guitar.update(histogram(tr['measures'][index]))
            density+=len(tr['measures'][index])
        for tr in groups['bass']:bass.update(histogram(tr['measures'][index]))
        combined=guitar+bass
        bass_notes=[p for tr in groups['bass']
                    for _,_,_,pitches in tr['measures'][index] for p in pitches]
        bass_root=min(bass_notes)%12 if bass_notes else None
        measures.append({'measure':index+1,'pitch_classes':combined,'density':density,
                         'bass_root':bass_root,'chords':chord_candidates(combined,bass_root)})
    novelty=[]
    for index in range(1,n):
        left=Counter();right=Counter()
        for m in measures[max(0,index-4):index]:left.update(m['pitch_classes'])
        for m in measures[index:min(n,index+4)]:right.update(m['pitch_classes'])
        harmonic=gap(left,right)
        dl=[m['density'] for m in measures[max(0,index-4):index]]
        dr=[m['density'] for m in measures[index:min(n,index+4)]]
        x=sum(dl)/len(dl);y=sum(dr)/len(dr)
        density=abs(x-y)/max(1,x,y)
        novelty.append({'measure':index+1,'score':round(.7*harmonic+.3*density,4),
                        'harmonic_change':round(harmonic,4),'density_change':round(density,4)})
    # Predicted boundary count uses LENGTH ONLY, not source section count.
    budget=max(1,n//bars_per_boundary)
    predicted=[]
    for item in sorted(novelty,key=lambda x:-x['score']):
        if all(abs(item['measure']-x['measure'])>=min_spacing for x in predicted):
            predicted.append(item)
        if len(predicted)==budget:break
    predicted.sort(key=lambda x:x['measure'])
    actual=sorted({m for m,_ in song['sections'] if m>1})
    tp=sum(any(abs(p['measure']-a)<=tolerance for a in actual) for p in predicted)
    recalled=sum(any(abs(p['measure']-a)<=tolerance for p in predicted) for a in actual)
    return {'file':song['file'],'measures':n,
        'guitar_tracks':[t['track'] for t in groups['guitar']],
        'bass_tracks':[t['track'] for t in groups['bass']],
        'exact_duplicate_guitars':duplicates,
        'source_section_labels':[{'measure':m,'label':label} for m,label in song['sections']],
        'blind_boundary_candidates':predicted,
        'evaluation':{'labels':len(actual),'predictions':len(predicted),
            'predictions_near_labels':tp,'labels_near_predictions':recalled,
            'precision':round(tp/len(predicted),3) if predicted else None,
            'recall':round(recalled/len(actual),3) if actual else None,
            'tolerance_measures':tolerance,'type':'in-sample vs tab markers; not held-out'},
        'harmonic_context':[{'measure':m['measure'],
            'bass_root_hypothesis':NAMES[m['bass_root']] if m['bass_root'] is not None else None,
            'pitch_class_weights':{NAMES[k]:round(v,3) for k,v in m['pitch_classes'].most_common()},
            'chord_candidates':m['chords']} for m in measures],
        'limitations':['Chord templates fit measure-wide pitch sets, not validated chords',
                       'No percussion, alignment within measures or phrase ground truth',
                       'Only exactly identical guitar tracks deduplicated',
                       'Boundary budget is a hand-selected length heuristic']}

def write_audit(items,path):
    with open(path,'w',newline='',encoding='utf-8') as file:
        columns=['song','measure','score','nearest_source_boundary','within_one_measure',
                 'human_section_boundary','human_phrase_boundary','notes']
        writer=csv.DictWriter(file,fieldnames=columns);writer.writeheader()
        for item in items:
            refs=[s['measure'] for s in item['source_section_labels'] if s['measure']>1]
            for p in item['blind_boundary_candidates']:
                nearest=min(refs,key=lambda a:abs(a-p['measure'])) if refs else ''
                writer.writerow({'song':item['file'],'measure':p['measure'],
                    'score':p['score'],'nearest_source_boundary':nearest,
                    'within_one_measure':int(bool(refs and abs(nearest-p['measure'])<=1))})

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('files',nargs='+',type=Path)
    ap.add_argument('--output',type=Path)
    ap.add_argument('--audit-csv',type=Path)
    args=ap.parse_args()
    results=[analyze(p) for p in args.files]
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(results,indent=2),encoding='utf-8')
    if args.audit_csv:
        args.audit_csv.parent.mkdir(parents=True,exist_ok=True)
        write_audit(results,args.audit_csv)
    print(json.dumps([{'file':x['file'],'evaluation':x['evaluation']} for x in results],indent=2))
if __name__=='__main__':main()
