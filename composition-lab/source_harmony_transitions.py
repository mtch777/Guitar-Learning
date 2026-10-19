"""Exact source harmony transition inventory from accepted composer/report data.

Selected-model denominator only; written minima/roles are proxies. No fit or GP
export. Raw locations/events and source identities must remain private.
"""
from collections import Counter,defaultdict
from fractions import Fraction as F
from pathlib import Path
import argparse,json
from engine_contract import sha


def extract(composer,report):
    songs={s['song_id']:s for s in report['songs']};seqs={};attacks={};info={};expected={};rows=[];excluded=Counter();counter_matches=0
    if len(songs)!=len(report['songs']):raise ValueError('Duplicate source song')
    for name in ('changed_section','rest_gap_or_invalid_bar','unknown_section','missing_model_attack','unknown_or_changed_tuning','unknown_or_dead_pitch','tie_destination_or_mixed_attack'):excluded[name]=0
    for s in composer['source_sequences']:
     key=s['song_id'],s['part_id']
     if key in seqs:raise ValueError('Duplicate source sequence')
     seqs[key]=s['roots']
    for family,ps in composer['parts']['harmony'].items():
     for p in ps:
      sid,pid=p['song_id'],p['part_id'];key=sid,pid;song=songs[sid];
      if song['provisional_partition']!='development':raise ValueError('Development source cohort required')
      headers={h['bar']:h for h in song['shared_layout']};baseq=F(headers[p['bar']]['start_q']);roots={F(e['local_q']):e for e in p['root_events']};cursor=F(0)
      value=dict(family=family,tuning=p['tuning'],song_id=sid,part_id=pid)
      if key in info:assert info[key]==value
      info[key]=value;counter={int(k):v for k,v in p['root_steps'].items()}
      if key in expected:assert expected[key]==counter
      expected[key]=counter
      for e in p['events']:
       if e['intervals']:
        q=baseq+cursor;root=roots[cursor];assert F(root['duration_q'])==F(e['duration_q']);identity=sid,pid,q
        if identity in attacks:raise ValueError('Duplicate model attack')
        attacks[identity]=dict(bar=p['bar'],local_q=str(cursor),root=int(root['root']),span=max(e['intervals'])-min(e['intervals']),cardinality=len(e['intervals']),tuning=p['tuning'])
       cursor+=F(e['duration_q'])
    rawgroups={}
    for key in info:
     sid,pid=key;ts=[t for t in songs[sid]['tracks'] if t['part_id']==pid];assert len(ts)==1;groups=defaultdict(list)
     for n in ts[0]['rows']:
      if n['voice']==0:groups[F(n['onset_q'])].append(n)
     rawgroups[key]=groups
    for key,meta in info.items():
     roots=seqs[key];historical=Counter()
     for a,b in zip(roots,roots[1:]):
      if a['end_q']!=b['onset_q'] or a['section']!=b['section']:continue
      historical[int(b['root'])-int(a['root'])]+=1
     assert dict(historical)==expected[key],('Historical counter mismatch',key)
     counter_matches+=1
     for a,b in zip(roots,roots[1:]):
      excluded['all_adjacent_root_pairs']+=1
      if F(a['end_q'])!=F(b['onset_q']):excluded['rest_gap_or_invalid_bar']+=1;continue
      if a['section'] is None or b['section'] is None:excluded['unknown_section']+=1;continue
      if a['section']!=b['section']:excluded['changed_section']+=1;continue
      qa,qb=F(a['onset_q']),F(b['onset_q']);sid,pid=key;pa,pb=attacks.get((sid,pid,qa)),attacks.get((sid,pid,qb))
      if pa is None or pb is None:excluded['missing_model_attack']+=1;continue
      if not pa['tuning'] or pa['tuning']!=pb['tuning']:excluded['unknown_or_changed_tuning']+=1;continue
      ns=rawgroups[key].get(qa,[])+rawgroups[key].get(qb,[])
      if not ns or any(n['midi'] is None or n.get('raw_note',{}).get('dead') for n in ns):excluded['unknown_or_dead_pitch']+=1;continue
      if any(n['tie_destination'] for n in ns):excluded['tie_destination_or_mixed_attack']+=1;continue
      left=rawgroups[key][qa];right=rawgroups[key][qb]
      assert all(qa+F(n['duration_q'])==F(a['end_q']) for n in left) and all(qb+F(n['duration_q'])==F(b['end_q']) for n in right), 'Source duration join differs'
      assert min(n['midi'] for n in left)==a['root']==pa['root'];assert min(n['midi'] for n in right)==b['root']==pb['root'];assert max(n['midi'] for n in right)-min(n['midi'] for n in right)==pb['span'] and len(right)==pb['cardinality']
      lowest=min(pa['tuning']);R=int(a['root'])-lowest;step=int(b['root'])-int(a['root']);assert type(R)is int and type(step)is int and -127<=step<=127
      rows.append(dict(family=meta['family'],song_id=sid,part_id=pid,previous_q=str(qa),onset_q=str(qb),section=a['section'],origin_register=R,voicing_span=pb['span'],cardinality=pb['cardinality'],step=step,destination_register=int(b['root'])-lowest))
    excluded['eligible']=len(rows);assert excluded['all_adjacent_root_pairs']==sum(v for k,v in excluded.items() if k!='all_adjacent_root_pairs')
    context_families=defaultdict(set)
    for row in rows:context_families[row['origin_register'],row['voicing_span']].add(row['family'])
    summary=dict(schema='source-conditional-transition-inventory-v1',rows=len(rows),families=len({e['family'] for e in rows}),songs=len({e['song_id'] for e in rows}),source_tracks=counter_matches,exact_historical_track_counters=True,denominators=dict(excluded),contexts=len(context_families),context_family_support_histogram=dict(Counter(len(v) for v in context_families.values())),origin_register_range=[min(e['origin_register'] for e in rows),max(e['origin_register'] for e in rows)],voicing_span_range=[min(e['voicing_span'] for e in rows),max(e['voicing_span'] for e in rows)],fit_performed=False,limitations=['Written minimum/main voice and heuristic harmony role only','Historical counters include matching unknown sections; conditional inventory excludes them explicitly','Exact destination shape chosen before step in historical consumer; no absolute destination pitch in context','Development only; examined outer held-out untouched'])
    return dict(events=rows,inventory=summary)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('composer','report','output'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.output.resolve().parts:p.error('Private output required')
    if a.output.exists():raise FileExistsError('Preserve prior inventory')
    seals={str(x):sha(x) for x in (a.composer,a.report,Path(__file__))}
    read=lambda v:json.loads(v.read_text(encoding='utf-8-sig'))
    result=extract(read(a.composer),read(a.report))
    if seals!={v:sha(v) for v in seals}:raise AssertionError('Extraction inputs/code changed')
    result['input_code_sha256']=seals;a.output.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    print(json.dumps(result['inventory'],indent=2))
