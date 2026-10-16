"""Export actual external predictions and two separate private listening studies."""
import argparse,base64,hashlib,json,math,random,sys,zipfile
from collections import Counter,defaultdict
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from external_score_export import project,write_projected_gp,opening_key
from learned_phrase_adapter import view
from playback_review import read_midi_notes
from composition_engine import make_voicing,ROLES
from joint_roles import JointRoleModel,source_rows


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def prior_audit(prior):
    bundle=json.loads((prior/'consolidated-review-v2.json').read_text());cases=bundle['manifest']['cases'];media=bundle['media'];out={}
    for seconds in (4,8):
        groups=defaultdict(list)
        for c in cases:
            key=opening_key(media[c['id']]['notes'],seconds,part=2)
            if not key:raise ValueError('No melody attacks; cannot certify duplicate opening')
            groups[digest(key)].append(c['id'])
        out[str(seconds)+'s_melody_duplicate_groups']=[g for g in groups.values() if len(g)>1]
    selected=['final-'+str(i).zfill(2) for i in (1,2,6,11)]
    out['reported_sweet_cases']=selected
    out['reported_sweet_first_8s_melody_all_equal']=len({digest(opening_key(media[i]['notes'],8,part=2)) for i in selected})==1
    return out


def rows_from_score(score,track_index,count=8):
    return [(F(e['onset_q']),F(e['duration_q']),n['midi'],80) for m in score['tracks'][track_index]['measures'][:count] for e in m['voices'][0] for n in e['notes']]


def export(root):
    dest=root/'exports';dest.mkdir(exist_ok=False);prior=root.parent/'autonomous-v1';cases=[];audit=prior_audit(prior)
    projections=json.loads((root/'source-projections.json').read_text());records=[]
    for family in ('cloud','sweet'):
        source=json.loads((prior/(family+'.canonical.json')).read_text());roles=ROLES[family];start=next(r['start_bar']-1 for r in projections if r['family']==family)
        lead,projection=view(source['tracks'][roles['melody']],start,8)
        lead_rows=[(n['bar']*4+n['position'],n['duration'],n['pitch'],80) for n in lead]
        info={80:dict(source['tracks'][roles['melody']],name='Fixed source lead'),25:dict(source['tracks'][roles['harmony']],name='Accompaniment'),32:dict(source['tracks'][roles['bass']],name='Bass')}
        def emit(name,rows,study,method,bars=8,extra=None):
            instruments=dict(info)
            if study=='phrases' or name.endswith('-full'):instruments[80]=dict(info[80],name='Source-seeded lead')
            for _,_,_,program in rows:
                if program not in instruments:instruments[program]=dict(name='External program '+str(program),program=program,tunings=[[64,59,55,50,45,40]])
            score,repairs=project(rows,instruments,bars);path=dest/(family+'-'+name+'.gp');write_projected_gp(score,path)
            path.with_suffix('.expected.json').write_text(json.dumps(score));record=dict(id=path.stem,family=family,study=study,method=method,bars=bars,repairs=repairs,**(extra or {}));records.append(record)
            if study:cases.append(record)
        # Matched source motif, then the historical cached model's continuation.
        baseline=json.loads(sorted((prior/'compositions').glob('*'+family+'.expected.json'))[0].read_text())
        cached=[r for r in rows_from_score(baseline,1) if r[0]>=8]
        emit('cached', [r for r in lead_rows if r[0]<8]+cached,'phrases','Controlled cached-pool baseline: identical source motif for two bars, then prior source-independent cached continuation; explicit splice, not contextual generation')
        for folder in sorted(root.glob(family+'-selector-*')):
            if not (folder/'raw-notes.json').exists():continue
            inference=json.loads((folder/'execution.json').read_text());seed=inference['seed']
            label='full-abc' if folder.name.endswith('ABC') else ('no-selector' if '-off-' in folder.name else 'full-aba')
            raw=json.loads((folder/'raw-notes.json').read_text())['notes'];rows=[];max_error=0
            invalid=sum(n[0]*4+n[1]<0 or n[4]<=0 for n in raw)
            if invalid:
                records.append(dict(id=folder.name,family=family,study=None,inference=inference,status='gp_export_rejected',invalid_timing_events=invalid,method='Upstream inference completed but emitted invalid timing; raw output retained, no GP/listening sample fabricated'));continue
            for bar,pos,inst,pitch,duration,velocity,*unused in raw:
                onset=F(str(bar*4+pos));dur=F(str(duration));q=onset.limit_denominator(24);d=dur.limit_denominator(24);max_error=max(max_error,float(abs(q-onset)),float(abs(d-dur)));rows.append((q,d,pitch,80))
            if max_error>.005:raise ValueError('Excessive upstream timing approximation')
            count=math.ceil(max(a+b for a,b,_,_ in rows)/4)
            method='Official contextual Yin-Yang '+label+'; source-seeded, supplied form, not learned form; full raw inference retained'
            emit(label+'-seed'+str(seed)+'-full',rows,None,method,count,dict(inference=inference,max_quantization_error_q=max_error))
            # One deterministic paired retry (both on/off), never select by a
            # listening score. Cloud seed1701 no-selector had negative duration.
            review_seed=1702 if family=='cloud' else 1701
            if label!='full-abc' and seed==review_seed:emit(label,rows,'phrases',method,8,dict(seed_prefix_is_source=True,seed=seed))
        # Source-conditioned local quarter-grid baseline, same lead and intro.
        graph=json.loads((prior/(family+'.sounding.json')).read_text());joint=JointRoleModel().fit(source_rows(graph,roles,source['duration_q']));rng=random.Random(1701);support=[]
        origin=F(source['tracks'][roles['melody']]['measures'][start]['onset_q'])
        for role,program in [('harmony',25),('bass',32)]:
            for m in source['tracks'][roles[role]]['measures'][start:start+3]:
                for e in m['voices'][0]:
                    if e.get('grace_type'):continue
                    for n in e['notes']:
                        onset=F(e['onset_q'])-origin
                        if onset<10 and n['midi'] is not None and (n.get('tie') or {}).get('destination')!='true':support.append((onset,F(e['duration_q']),n['midi'],program))
        for q in range(10,32):
            active=[p for a,d,p,program in lead_rows if a<=q<a+d];anchor=max(active) if active else next(p for a,d,p,program in reversed(lead_rows) if a<=q)
            classes,bass=joint.sample(rng,(anchor%12,q%4));voicing=make_voicing(classes,anchor,info[25]['tunings'][0])
            support.extend((F(q),F(1),p,25) for p,s,f in voicing)
            tuning=info[32]['tunings'][0];pc=(anchor+bass)%12;pitch=min((p for p in range(min(tuning),max(tuning)+25) if p%12==pc),key=lambda p:abs(p-min(tuning)-10));support.append((F(q),F(1),pitch,32))
        emit('quarter-grid',lead_rows+support,'arrangement','Local joint-role quarter-grid baseline, fixed eight-bar source lead and five-second source accompaniment prefix')
        for label,pattern in [('amt-future',family+'-amt-future-*-controls'),('amt-prefix',family+'-amt-prefix-*-controls'),('amt-masked',family+'-amt-future-*-masked')]:
            paths=[p for p in sorted(root.glob(pattern)) if (p/'arranged-events.json').exists() and (label!='amt-future' or not p.name.endswith('masked'))]
            if label=='amt-prefix' and not paths:
                failures=[p for p in sorted(root.glob(pattern)) if (p/'execution.json').exists() and json.loads((p/'execution.json').read_text()).get('status')=='failed']
                if len(failures)==1:
                    records.append(dict(id=failures[0].name,family=family,study=None,inference=json.loads((failures[0]/'execution.json').read_text()),method='Prefix-only AMT did not complete within exploratory resource bounds; no GP or listening case fabricated'));continue
            if len(paths)!=1:raise ValueError('Expected exactly one successful '+label+' '+family)
            folder=paths[0];raw=json.loads((folder/'arranged-events.json').read_text());rows=list(lead_rows);errors=[]
            for t,d,n in zip(raw[::3],raw[1::3],raw[2::3]):
                program,pitch=divmod(n-11000,128)
                if program==80:continue
                onset,dur=F(t,50),F(d-10000,50);q=F(round(onset*8),8);length=max(F(1,8),F(round(dur*8),8));errors += [float(abs(q-onset)),float(abs(length-dur))];rows.append((q,length,pitch,program))
            emit(label,rows,'arrangement' if label!='amt-masked' else None,'Official AMT '+label+'; fixed lead retained by construction; raw MIDI kept; masked variant explicitly restricts generated instruments to guitar/bass',extra=dict(inference=json.loads((folder/'execution.json').read_text()),max_support_quantization_error_q=max(errors,default=0)))
    (root/'comparison-records.json').write_text(json.dumps(dict(cases=cases,records=records,prior_opening_audit=audit),indent=2));print('Exported',len(list(dest.glob('*.gp'))),'GPs;',len(records)-len(list(dest.glob('*.gp'))),'rejected/failed records retained')


def bundle(root,aggregate,copying_report=None):
    records=json.loads((root/'comparison-records.json').read_text());dest=root/'exports';results=[]
    template=json.loads((root.parent/'autonomous-v1/consolidated-review-v2.json').read_text())['manifest']
    comparison_checks={};pending={}
    for study in ('phrases','arrangement'):
        cases=[];media={};case_programs={};selected=[c for c in records['cases'] if c['study']==study];random.Random(20261016).shuffle(selected)
        for index,r in enumerate(selected,1):
            ident=study+'-'+str(index).zfill(2);path=dest/(r['id']+'.gp');seconds,notes=read_midi_notes(path.with_suffix('.mid'));assert abs(seconds-16)<.01
            roll=[dict(start=round(a,6),end=round(b,6),pitch=p,velocity=v,part=c) for a,b,p,v,c in notes];data=path.read_bytes();score=json.loads(path.with_suffix('.expected.json').read_text())
            cases.append(dict(id=ident,family=r['family'],familyTitle=r['family'].title()+' '+study+' comparison',label='Case '+str(index).zfill(2),audio=ident+'.wav',roll=ident+'.json',gp=ident+'.gp',gpSha256=hashlib.sha256(data).hexdigest(),seconds=seconds,method=r['method'],tracks=[dict(name=t['name'],strings=len(t['tunings'][0]),program=t['program']) for t in score['tracks']]))
            media[ident]=dict(gpBase64=base64.b64encode(data).decode(),notes=roll)
            verified=json.loads(path.with_suffix('.alphatab.json').read_text());case_programs[ident]={t['channel']:t['program'] for t in verified['tracks']}
            results.append(dict(r,notes=len(notes),tracks=len(score['tracks'])))
        prefix=4 if study=='phrases' else 5
        manifest=dict(template,cases=cases,version=digest(cases)[:16],title='External pipeline comparison: '+study,intro=f'Eight-bar / 16-second comparisons. The first {prefix} seconds are intentionally shared source context. Judge changes afterward.',asideIntro='Private source-bearing experiment; nothing uploaded. Prefixes intentionally match; full upstream melody outputs are also in the private GP package.',guidance='Judge development and source character after the shared opening. Simple fixed-gain synthesis; use GP/raw MIDI for instrument playback. A small two-source pilot, not artist training or a quality verdict.')
        manifest['ratingMetrics']=[['coherence','Overall coherence'],['melody','Source character'],['harmony','Harmony / ensemble fit'],['phrasing','Idea development'],['holds','Meaningful pauses/holds'],['resolution','Meaningful ending'],['playability','Playability (if assessable)']]
        if study=='arrangement':
            manifest['ratingMetrics'][1]=['melody','Source character of supporting parts']
            manifest['guidance']='The lead is identical across cases. Judge the supporting parts after the shared five-second intro: harmony, rhythm, texture and interaction. These are excerpts, not song endings. Simple fixed-gain synthesis; use GP/raw MIDI for instrument playback. No artist-specific fitting or quality verdict.'
        else:manifest['guidance']+=' These are excerpts; full upstream GP/MIDI outputs are in the private package.'
        manifest['judgments']=[]
        pending[root/(study+'-review.json')]=json.dumps(dict(format='composition-private-review-v1',manifest=manifest,media=media),separators=(',',':'))
        checks={}
        for family in ('cloud','sweet'):
            family_cases=[c for c in cases if c['family']==family]
            signatures=[];lead_signatures=[]
            for c in family_cases:
                notes=media[c['id']]['notes'];tail=[dict(n,start=n['start']-prefix,end=n['end']-prefix,part=case_programs[c['id']][n['part']]) for n in notes if n['start']>=prefix]
                signatures.append(digest(opening_key(tail,16-prefix)))
                if study=='arrangement':
                    from sounding_graph import build_sounding
                    r=next(r for r in selected if r['method']==c['method'] and r['family']==family)
                    score=json.loads((dest/(r['id']+'.expected.json')).read_text());graph=build_sounding(score)
                    ti=next(t['index'] for t in score['tracks'] if t['name'].startswith('Fixed source lead'))
                    signature=sorted((n['onset_q'],n['duration_q'],n['midi']) for n in graph['sustains'].values() if n['track']==ti);lead_signatures.append(signature)
                    checked=json.loads((dest/(r['id']+'.alphatab.json')).read_text());channel=checked['tracks'][ti]['channel']
                    actual=sorted((n['start']*2,(n['end']-n['start'])*2,n['pitch']) for n in notes if n['part']==channel)
                    expected=sorted((float(F(a)),float(F(d)),p) for a,d,p in signature)
                    if len(actual)!=len(expected) or any(p!=q or abs(a-b)>1e-5 or abs(d-e)>1e-5 for (a,d,p),(b,e,q) in zip(actual,expected)):raise AssertionError('Independent MIDI lead sustain/timing mismatch')
            checks[family]=dict(cases=len(family_cases),distinct_post_prefix_event_streams=len(set(signatures)))
            if len(set(signatures))!=len(family_cases):raise AssertionError('Duplicate post-prefix review outputs; do not ask user to judge identical material')
            if lead_signatures:
                if any(s!=lead_signatures[0] for s in lead_signatures):raise AssertionError('Arrangement lead lock violated')
                checks[family]['fixed_lead_identical']=True
                checks[family]['independent_midi_lead_checked']=True
        comparison_checks[study]=checks
    report=dict(format='external-pipeline-comparison-v1',prior_opening_audit=records['prior_opening_audit'],comparison_checks=comparison_checks,runs=records['records'],human_judgments=None,scope='small seeded two-source pilot; Cloud paired selector retry at seed1702 after invalid seed1701 output; no artist-specific fitting; supplied form; selector candidate budget differs; raw predictions retained privately',independent_gp_import='all exported GPs verified before bundle packaging')
    # Keep only aggregate measurements: never publish notes or source excerpts.
    archive=root/'External_Pipeline_Comparison.zip'
    if aggregate.exists() or archive.exists() or any(p.exists() for p in pending):raise FileExistsError('Preserve prior reports and review bundles')
    aggregate.write_text(json.dumps(report,indent=2))
    for target,data in pending.items():target.write_text(data)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(dest.glob('*.gp')):z.write(path,'gp/'+path.name)
        for path in sorted(root.glob('phrases-review.json')):z.write(path,path.name)
        z.write(root/'arrangement-review.json','arrangement-review.json');z.write(aggregate,'aggregate-results.json')
        if copying_report:z.write(copying_report,'copying-results.json')
        for path in sorted(root.glob('*/raw.mid')):z.write(path,'raw-midi/'+path.parent.name+'.mid')
        for path in sorted(root.glob('*/output/yin_yang/*.mid')):z.write(path,'raw-midi/'+path.parents[2].name+'.mid')
        z.writestr('README.txt','PRIVATE SOURCE-BEARING EXPERIMENT. Do not publish.\nLoad either review JSON at composition-ablation-review.html?study=final.\nPhrase study: first 4 seconds intentionally match; judge afterward. Arrangement study: fixed lead throughout, shared 5-second source intro; judge supporting parts afterward.\nGP folder includes full upstream outputs and matched eight-bar review excerpts. Raw MIDI is unprojected, including explicitly rejected invalid upstream predictions for debugging; check aggregate-results.json.\nAMT MIDI uses 10ms timing; GP support uses a 1/8-quarter grid and may require octave changes. Fixed GP lead is retained from the rational source projection.\nSource lead projection omits chord notes, other voices, grace notes and tie continuations. Not full source fidelity or certified physical playability.\nForm is supplied ABA/ABC; not learned form. Two songs, small seeded pilot: no generalization or quality claim. Cloud paired retry uses seed1702 after invalid seed1701 no-selector timing; raw failed result retained.\n')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    print(json.dumps(dict(cases=len(results),gp_files=len(list(dest.glob('*.gp'))),zip_bytes=archive.stat().st_size,zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--stage',choices=['export','bundle'],required=True);p.add_argument('--aggregate',type=Path);p.add_argument('--copying-report',type=Path);a=p.parse_args()
    if not a.workspace.resolve().is_relative_to(Path(__file__).resolve().parents[1]/'local-artifacts'):p.error('Source-bearing outputs must stay under private local-artifacts')
    if a.stage=='export':export(a.workspace)
    else:
        if not a.aggregate:p.error('--aggregate is required for bundle stage')
        bundle(a.workspace,a.aggregate,a.copying_report)
