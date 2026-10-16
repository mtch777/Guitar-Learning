"""Scratch-trained local boundary and phrase-state organization baselines.

Learned clusters/transitions are hypotheses, not semantic phrase/motif truth.
All model fitting uses family-grouped training data; threshold uses development.
"""
import argparse
from collections import Counter,defaultdict
import hashlib,json,math,pickle,random
from pathlib import Path


def phrase_features(phrase):
    import numpy as np
    notes=phrase[0];p=np.array([n[3] for n in notes],dtype=float);d=np.array([n[4] for n in notes],dtype=float)
    contour=np.interp(np.linspace(0,len(p)-1,8),np.arange(len(p)),p-p[0])/12
    return list(contour)+[float(p.max()-p.min())/24,float(d.mean()),float(d.std()),math.log1p(len(p))]


def form_sequence(record,clusterer):
    import numpy as np
    phrases=list(record['melody']['phrases'].values())
    clusters=clusterer.predict(np.array([phrase_features(p) for p in phrases]))
    meter=record['melody']['metadata']['time_signature'].split('_')[1];num,den=map(int,meter.split('/'));barq=num*4/den
    result=[]
    for p,c in zip(phrases,clusters):
        notes=p[0];length=max(n[0]*barq+n[1]+n[4] for n in notes)-min(n[0]*barq+n[1] for n in notes)
        result.append((int(c),max(1,min(4,round(length/barq)))))
    return result


class FormModel:
    def __init__(self):self.counts=defaultdict(Counter);self.global_counts=Counter()
    def add(self,sequence):
        for i,state in enumerate(sequence):
            phase=min(3,int(4*i/len(sequence)))
            for order in range(min(2,i)+1):self.counts[(phase,tuple(sequence[i-order:i]))][state]+=1
            self.global_counts[state]+=1
    def distribution(self,history,progress):
        phase=min(3,int(4*progress))
        for order in range(min(2,len(history)),-1,-1):
            counts=self.counts.get((phase,tuple(history[-order:]) if order else ()))
            if counts:return counts
        return self.global_counts
    def nll(self,sequence):
        # Include one explicit unknown-state outcome in the smoothing mass.
        values=[];vocabulary=len(self.global_counts)+1
        for i,state in enumerate(sequence):
            counts=self.distribution(sequence[:i],i/len(sequence))
            values.append(-math.log((counts[state]+.5)/(sum(counts.values())+.5*vocabulary)))
        return values
    def sample(self,rng,history,progress):
        counts=self.distribution(history,progress)
        return rng.choices(list(counts),weights=list(counts.values()),k=1)[0]


def main():
    import numpy as np
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import precision_recall_fscore_support
    p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.mkdir(exist_ok=False,parents=True);records=json.loads(args.corpus.read_text(encoding='utf-8'))
    split={s:[r for r in records if r['split']==s] for s in ['train','development','test']}
    arrays={}
    for s,rows in split.items():
        examples=[x for r in rows for x in r['boundary_rows']]
        arrays[s]=(np.array([r['x'] for r in examples]),np.array([r['y'] for r in examples]))
    model=HistGradientBoostingClassifier(max_iter=120,max_leaf_nodes=15,random_state=17,class_weight='balanced',early_stopping=False)
    model.fit(*arrays['train'])
    def measure(y,pred):
        a,b,c,_=precision_recall_fscore_support(y,pred,average='binary',zero_division=0);return dict(precision=float(a),recall=float(b),f1=float(c))
    devp=model.predict_proba(arrays['development'][0])[:,1]
    threshold=max(np.arange(.05,1,.05),key=lambda t:measure(arrays['development'][1],devp>=t)['f1'])
    testx,testy=arrays['test'];baseline={}
    for feature,name in [(0,'duration'),(1,'rest'),(3,'pitch_jump'),(5,'beat_strength')]:
        values=sorted(set(float(np.quantile(arrays['train'][0][:,feature],q)) for q in np.linspace(0,1,21)))
        cut=max(values,key=lambda t:measure(arrays['development'][1],arrays['development'][0][:,feature]>t)['f1'])
        baseline[name]=dict(threshold=cut,**measure(testy,testx[:,feature]>cut))
    boundary=dict(model=measure(testy,model.predict_proba(testx)[:,1]>=threshold),threshold=float(threshold),baselines=baseline,
                  labels=int(testy.sum()),events=len(testy),scope='exact attack boundaries from existing MTC annotations; one tradition; not independent human adjudication')
    features=np.array([phrase_features(p) for r in split['train'] for p in r['melody']['phrases'].values()])
    clusters=MiniBatchKMeans(n_clusters=32,random_state=17,n_init=3,batch_size=512).fit(features)
    form=FormModel();permuted=FormModel();rng=random.Random(17)
    for r in split['train']:
        sequence=form_sequence(r,clusters);form.add(sequence);shuffled=list(sequence);rng.shuffle(shuffled);permuted.add(shuffled)
    form_values=[];shuffle_values=[];independent_values=[]
    for r in split['test']:
        sequence=form_sequence(r,clusters);form_values+=form.nll(sequence);shuffle_values+=permuted.nll(sequence)
        total=sum(form.global_counts.values());vocabulary=len(form.global_counts)+1
        independent_values += [-math.log((form.global_counts[s]+.5)/(total+.5*vocabulary)) for s in sequence]
    form_report=dict(test_phrase_states=len(form_values),paired_nll=sum(form_values)/len(form_values),
        shuffled_training_nll=sum(shuffle_values)/len(shuffle_values),independent_nll=sum(independent_values)/len(independent_values),
        scope='32 learned contour clusters + 1-4 bar length buckets; second-order transitions with progress bins; not learned semantic story')
    with (args.out/'models.pkl').open('wb') as stream:pickle.dump(dict(boundary=model,boundary_threshold=threshold,clusters=clusters,form=form),stream)
    report=dict(boundary=boundary,form=form_report,split_pieces={k:len(v) for k,v in split.items()},
        model_sha256=hashlib.sha256((args.out/'models.pkl').read_bytes()).hexdigest(),license='trained from MTC CC BY-NC-SA noncommercial research; local weights only')
    (args.out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':
    # Persist importable class names rather than __main__.FormModel.
    from structural_learning import main as run
    run()
