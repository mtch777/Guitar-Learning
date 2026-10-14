"""Step 5: conditional sequence generation, using existing 16-bar GP shell only for export."""
from __future__ import annotations
import argparse,copy,json,random,zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
import generate_composition_v2 as shell
from sequence_model import SequenceModel

UNITS=(1,2,4,8,16)

def fit_voicing(anchor,shape,tuning,max_fret=14):
    """Move only by octaves when needed; never change intervals within a chord."""
    for k in sorted(range(-5,6),key=lambda k:abs(k)):
        notes=[anchor+12*k+d for d in shape]
        if len(set(notes))!=len(notes):continue
        try:
            positions=[];used=set()
            for pitch in notes:
                options=[(fret,s) for s,open_p in enumerate(tuning)
                         if s not in used for fret in (pitch-open_p,) if 0<=fret<=max_fret]
                if not options:raise ValueError()
                fret,string=min(options)
                used.add(string);positions.append((pitch,string,fret))
            return positions
        except ValueError:continue
    return None

def produce_bars(model,tuning,bars=16,seed=17):
    rng=random.Random(seed);last=rng.choices(list(model.pitch_starts),weights=list(model.pitch_starts.values()),k=1)[0]
    history=[];output=[];orders=Counter();rests=0
    for _ in range(bars):
        remaining=16;events=[];count=0
        while remaining>0:
            def valid(tok):
                units,delta,shape=tok
                if units>remaining:return False
                if delta is None:return not shape or not history # new source sequence beginning
                return True
            options=[]
            for k in range(min(len(history),model.max_order),-1,-1):
                d=model.next_counts[k].get(tuple(history[-k:]) if k else (),{})
                # Filter unplayable chord offsets and preserve exact learned intervals
                c=Counter()
                for tok,n in d.items():
                    if not valid(tok):continue
                    unit,delta,shape=tok
                    if not shape or fit_voicing(last+(delta or 0),shape,tuning) is not None:c[tok]=n
                if c:
                    options=list(c.items());orders[k]+=1;break
            if not options:
                # Timing-only fallback (not a stylistic invention): pad with a legal rest.
                unit=max(u for u in UNITS if u<=remaining)
                events.append(shell._event(unit,[],tuning));remaining-=unit;rests+=1
                history=[];continue
            tok=rng.choices([x for x,_ in options],weights=[n for _,n in options],k=1)[0]
            unit,delta,shape=tok
            if shape:
                notes=fit_voicing(last+(delta or 0),shape,tuning)
                if notes is None:raise AssertionError('filtered unplayable shape')
                actual=[p for p,s,f in notes]
                # writer chooses string/fret itself; match its approved fret constraints
                try:event=shell._event(unit,actual,tuning,palm=False)
                except ValueError:
                    history=[];continue
                last=actual[0]
            else:event=shell._event(unit,[],tuning);rests+=1
            events.append(event);history.append(tok);history=history[-model.max_order:] if model.max_order else []
            remaining-=unit;count+=1
            if count>32:raise AssertionError('excessive events')
        output.append(events)
    return output,{'context_uses':dict(orders),'rest_events':rests}

def export(template,output,source_paths,seed=17,max_order=4):
    model=SequenceModel.from_paths(source_paths,max_order)
    with zipfile.ZipFile(template) as z:
        root=ET.fromstring(z.read('Content/score.gpif'))
    track=next(t for t in root.findall('./Tracks/Track') if 'rhythm' in (t.findtext('Name') or '').lower())
    tuning=[int(n) for n in track.findtext("./Staves/Staff/Properties/Property[@name='Tuning']/Pitches").split()]
    bars,report=produce_bars(model,tuning,16,seed)
    groups=[bars[i:i+4] for i in (0,4,8,12)]
    old=shell.compose_four_bars,shell.transform_a,shell.transform_reprise
    shell.compose_four_bars=lambda rng,stats,tuning,style='a':copy.deepcopy(groups[0 if style=='a' else 2])
    shell.transform_a=lambda phrase,rng,tuning:copy.deepcopy(groups[1])
    shell.transform_reprise=lambda phrase,rng,tuning:copy.deepcopy(groups[3])
    try:legacy=shell.render_gp(template,output,source_paths,seed)
    finally:shell.compose_four_bars,shell.transform_a,shell.transform_reprise=old
    # Remove false V2 descriptions from legacy shell report.
    for key in ('tonal_center','mode','harmonic_roots_by_bar','sections','limitations'):legacy.pop(key,None)
    legacy.update({'algorithm':'conditional_variable_order_events','training_events':model.event_count,
                   'training_sequences':model.sequence_count,'max_context':max_order,
                   'context_uses':report['context_uses'],
                   'rest_events':report['rest_events'],
                   'remaining_limits':['4/4, representable sixteenth-based durations',
                     'single output voice with simultaneous chords',
                     'fixed 16-bar serializer sections (not learned structure)',
                     'source articulations not modeled at this step',
                     'not listening-tested']})
    return legacy

def main():
    p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,nargs='+',required=True)
    p.add_argument('--template',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,default=17);p.add_argument('--order',type=int,default=4)
    a=p.parse_args();report=export(a.template,a.output,a.sources,a.seed,a.order)
    Path(str(a.output)+'.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()