"""Reusable weighted opening-phrase scorer; CSV fields addressed by name, never position.
No RNG or selection. CLI scores one seed against all same-known-role openings.
"""
import csv,json,pathlib,statistics,math,argparse
import normalization as N
HERE=pathlib.Path(__file__).parent
CONFIG=json.loads((HERE/'scoring_config.json').read_text())
FIELDS=CONFIG['fields']
def parse_field(value,identifier):
 if identifier in [24,25]:
  value=value.split(';')[0].split(': ',1)[-1]
  if N.bad(value):raise ValueError('unknown phrase-level accent')
  return value
 if identifier==8:
  if N.bad(value):raise ValueError('unestablished arpeggio')
  return value
 return N.parse(value,identifier)
def parse_phrase(row):
 parsed={}
 for field in FIELDS:
  i=field['schema_id']
  try:parsed[i]=parse_field(row[field['field']],i)
  except (ValueError,AssertionError):parsed[i]=None
 return parsed

def compare_parsed(a,b):
 scores={}
 for field in FIELDS:
  i=field['schema_id']
  if a[i] is None or b[i] is None:continue
  scores[i]=100.*(a[i]==b[i]) if i in [8,24,25] else N.compare(a[i],b[i],i)
 numerator=math.fsum(scores[f['schema_id']]*f['weight'] for f in FIELDS if f['schema_id'] in scores)
 denominator=math.fsum(f['weight'] for f in FIELDS if f['schema_id'] in scores)
 return {'score':numerator/denominator if denominator else None,'comparable_fields':len(scores),'comparable_weight':denominator,'scores':scores}

def score_pair(a,b):
 if N.bad(a['Phrase role']) or N.bad(b['Phrase role']) or a['Phrase role']!=b['Phrase role']:return None
 return compare_parsed(parse_phrase(a),parse_phrase(b))

def main():
 p=argparse.ArgumentParser();p.add_argument('--csv',type=pathlib.Path,required=True);p.add_argument('--seed',required=True);p.add_argument('--out',type=pathlib.Path,required=True);args=p.parse_args();args.out.mkdir(exist_ok=True,parents=True)
 first={}
 with args.csv.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f)
  if CONFIG['removed_field'] in reader.fieldnames:raise ValueError('Current schema must omit seconds column. Use updated CSV.')
  for row in reader:
   if row['Status']=='complete' and row['Phrase #']=='1':first[row['Riff ID']]=row
 seed=first[args.seed]
 if N.bad(seed['Phrase role']) or not seed['Phrase role'].strip():raise ValueError('Seed has no established phrase role; cannot form eligible pool.')
 ps=parse_phrase(seed);rows=[]
 for rid,row in sorted(first.items()):
  if rid==args.seed or row['Phrase role']!=seed['Phrase role'] or N.bad(row['Phrase role']):continue
  result=compare_parsed(ps,parse_phrase(row));record={'Artist':row['Artist'],'Riff ID':rid,'Weighted similarity score':result['score'],'Comparable fields':result['comparable_fields'],'Comparable weight':result['comparable_weight'],'Available total weight':sum(f['weight'] for f in FIELDS),'Weight coverage %':100*result['comparable_weight']/sum(f['weight'] for f in FIELDS),'Length (quarter-note beats)':row['Length (quarter-note beats)'],'Category - dominant texture':row['Category - dominant texture']}
  for field in FIELDS:record[f"Score: {field['field']}"]=result['scores'].get(field['schema_id'],'')
  rows.append(record)
 total=math.fsum(r['Weighted similarity score'] or 0 for r in rows)
 if not rows:raise ValueError('No eligible same-role candidate riffs after excluding the seed.')
 if total<=0:raise ValueError('All eligible candidates have zero or unavailable similarity; probabilities are undefined.')
 for r in rows:r['Probability if next draw uses these weights']=(r['Weighted similarity score'] or 0)/total
 assert abs(math.fsum(r['Probability if next draw uses these weights'] for r in rows)-1)<1e-12
 with (args.out/'weighted_seed_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 report={'seed':args.seed,'candidate_count':len(rows),'scored_field_count':len(FIELDS),'sum_scores':total,'probability_sum':math.fsum(r['Probability if next draw uses these weights'] for r in rows),'random_draw_performed':False,'scope':'same known opening role; exclude self; no dedup; no extra filters','config':CONFIG['version']}
 (args.out/'run_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
