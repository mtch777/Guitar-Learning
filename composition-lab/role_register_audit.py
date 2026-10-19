"""Read-only decomposition of accepted written-role boundary observations.

Roles remain heuristic. Same-track role overlap is disclosed, not interpreted
as an independent musical interaction. No new detector, model or generation.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
import math


def extract(observations,composer):
    index=defaultdict(list)
    for role in ('harmony','melody'):
        for records in composer['parts'][role].values():
            for p in records:index[role,p['song_id'],p['bar']].append(p)
    rows=[];unknown=0;seen=set()
    for e in observations['events']:
        if e['partition']!='development' or e['role']!='melody':continue
        identity=e['song_id'],e['part_id'],e['bar']
        if identity in seen:raise ValueError('Duplicate boundary')
        seen.add(identity)
        if e['anchor'] is None:unknown+=1;continue
        def selected(role):
            values=index[role,e['song_id'],e['bar']]
            if not values:raise ValueError('Known boundary missing selected role')
            chosen=min(values,key=lambda p:p['part_id'])
            if sum(p['part_id']==chosen['part_id'] for p in values)!=1:raise ValueError('Ambiguous selected role part')
            if not chosen['tuning']:raise ValueError('Unknown tuning')
            return chosen
        melody,harmony=selected('melody'),selected('harmony')
        if melody['part_id']!=e['part_id']:raise ValueError('Selected melody identity changed')
        first=melody['root_events'][0];q=F(first['local_q'])
        if q!=0:raise ValueError('Original boundary cohort requires bar-start attack')
        if int(first['root'])!=e['target']:raise ValueError('Melody pitch differs')
        active=[x for x in harmony['root_events'] if F(x['local_q'])<=q<F(x['local_q'])+F(x['duration_q'])]
        if len(active)!=1 or int(active[0]['root'])!=e['anchor']:raise ValueError('Active harmony identity differs')
        ml,hl=min(melody['tuning']),min(harmony['tuning'])
        R=e['target']-ml;D=e['target']-e['anchor'];own=e['anchor']-hl;offset=hl-ml;H=e['anchor']-ml
        if R!=e['register'] or R-D!=H or H!=own+offset:raise ValueError('Exact register identity differs')
        rows.append(dict(family=e['family'],song_id=e['song_id'],bar=e['bar'],onset_q=e['onset_q'],
            melody_part=melody['part_id'],harmony_part=harmony['part_id'],melody_tuning=melody['tuning'],harmony_tuning=harmony['tuning'],
            same_part=melody['part_id']==harmony['part_id'],harmony_available_parts=sorted({p['part_id'] for p in index['harmony',e['song_id'],e['bar']]}),
            melody_available_parts=sorted({p['part_id'] for p in index['melody',e['song_id'],e['bar']]}),
            harmony_local_q=active[0]['local_q'],harmony_duration_q=active[0]['duration_q'],
            melody_pitch=e['target'],harmony_pitch=e['anchor'],R=R,D=D,H=H,harmony_own_register=own,tuning_offset=offset))
    return rows,unknown


def summarize(rows):
    if not rows:raise ValueError('Nonempty cohort required')
    groups=defaultdict(list);families=defaultdict(set)
    for r in rows:groups[r['family'],r['song_id']].append(r);families[r['family']].add(r['song_id'])
    fields=('R','D','H','harmony_own_register','tuning_offset');means=Counter();hist={k:Counter() for k in fields};overlap=0
    for (family,song),values in groups.items():
        weight=1/len(families)/len(families[family])/len(values)
        for r in values:
            if r['H']!=r['harmony_own_register']+r['tuning_offset'] or r['R']-r['D']!=r['H']:raise ValueError('Joint identity differs')
            for k in fields:means[k]+=r[k]*weight;hist[k][r[k]]+=weight
            overlap+=int(r['same_part'])*weight
    if not math.isclose(means['H'],means['harmony_own_register']+means['tuning_offset'],abs_tol=1e-9) or not math.isclose(means['R']-means['D'],means['H'],abs_tol=1e-9):raise AssertionError('Weighted identities differ')
    return dict(boundaries=len(rows),families=len(families),songs=len({r['song_id'] for r in rows}),means=dict(means),histograms={k:dict(v) for k,v in hist.items()},same_part_boundaries=sum(r['same_part'] for r in rows),weighted_same_part_share=overlap,
        distinct_part_boundaries=sum(not r['same_part'] for r in rows),
        multiple_harmony_choices=sum(len(r.get('harmony_available_parts',[]))>1 for r in rows))


def verify_raw(rows,report):
    songs={s['song_id']:s for s in report['songs']};groups=0;notes_checked=0
    for row in rows:
        song=songs[row['song_id']];headers=[h for h in song['shared_layout'] if h['bar']==row['bar']]
        if len(headers)!=1:raise ValueError('Ambiguous source bar')
        q=F(row['onset_q']);hq=F(headers[0]['start_q'])+F(row['harmony_local_q'])
        if not hq<=q<hq+F(row['harmony_duration_q']):raise ValueError('Harmony not active at boundary')
        for role,onset in (('melody',q),('harmony',hq)):
            tracks=[t for t in song['tracks'] if t['part_id']==row[role+'_part']]
            if len(tracks)!=1:raise ValueError('Ambiguous accepted track')
            notes=[n for n in tracks[0]['rows'] if n['voice']==0 and F(n['onset_q'])==onset]
            if not notes or any(n['midi'] is None for n in notes):raise ValueError('Unknown accepted pitch')
            if min(n['midi'] for n in notes)!=row[role+'_pitch']:raise ValueError('Accepted written minimum differs')
            for n in notes:
                if row[role+'_tuning'][n['string']]+n['fret']!=n['midi']:raise ValueError('Accepted note/tuning differs')
                notes_checked+=1
            groups+=1
    return dict(pitch_groups=groups,note_tunings=notes_checked)


def alternative_bounds(rows,composer):
    """Diagnostic bounds across active selected harmony parts, not reassignment."""
    index=defaultdict(list)
    for records in composer['parts']['harmony'].values():
        for p in records:index[p['song_id'],p['bar']].append(p)
    decorated=[]
    for row in rows:
        options=[]
        for p in index[row['song_id'],row['bar']]:
            # Original accepted boundary is the first melody attack at bar start.
            for e in p['root_events']:
                if F(e['local_q'])<=0<F(e['local_q'])+F(e['duration_q']):
                    options.append(dict(part_id=p['part_id'],H=int(e['root'])-min(row['melody_tuning']),
                        own=int(e['root'])-min(p['tuning'])))
        if not options or sum(o['part_id']==row['harmony_part'] for o in options)!=1:raise ValueError('Original active choice missing/ambiguous')
        decorated.append(dict(row,options=options))
    groups=defaultdict(list);families=defaultdict(set)
    for r in decorated:groups[r['family'],r['song_id']].append(r);families[r['family']].add(r['song_id'])
    bounds=Counter()
    for (family,song),values in groups.items():
        weight=1/len(families)/len(families[family])/len(values)
        for r in values:
            for field in ('H','own'):
                bounds[field+'_min_mean']+=min(o[field] for o in r['options'])*weight
                bounds[field+'_max_mean']+=max(o[field] for o in r['options'])*weight
    return dict(bounds=dict(bounds),boundaries=len(rows),multiple_active_choices=sum(len(r['options'])>1 for r in decorated),
        interpretation='Per-boundary extrema; may not represent any consistent track assignment, not alternative accepted truth')


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    from engine_contract import sha
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('observations','composer','accepted_report','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args()
    if 'local-artifacts' not in args.output.resolve().parts:parser.error('Private output required')
    if args.output.exists():raise FileExistsError('Preserve earlier audit')
    paths=(args.observations,args.composer,args.accepted_report,Path(__file__))
    seals={str(p):sha(p) for p in paths}
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    composer=read(args.composer);rows,unknown=extract(read(args.observations),composer)
    result=dict(summary=summarize(rows),unknown=unknown,raw_checks=verify_raw(rows,read(args.accepted_report)),
        sensitivity=alternative_bounds(rows,composer),
        per_family={f:summarize([r for r in rows if r['family']==f]) for f in sorted({r['family'] for r in rows})},rows=rows)
    if seals!={p:sha(p) for p in seals}:raise AssertionError('Inputs changed during audit')
    result['input_sha256']=seals
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(boundaries=len(rows),unknown=unknown,means=result['summary']['means'],raw_checks=result['raw_checks'],sensitivity=result['sensitivity'])))
