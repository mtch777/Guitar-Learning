"""Fixed public-rhythm bridge; input is JSON data, never executable Python."""
import copy,json,re,sys
from generation import build_selection_model,generate,assess,to_reference_payload,digest,LAW_VERSION
from generation.evidence import canonical
BRIDGE_VERSION='rhythm-pages-bridge/1'
MAX_INPUT=4194304
MAX_RAW=67108864
FORBIDDEN={'pitch','midi','fret','string','tuning','pitches','pitch_group','marks','raw_note','raw_beat',
 'raw_origin_note','raw_origin_beat','human_feedback','annotation','source_path','ledger_path','parser_bindings','imported_source_code'}

def load(text,limit=MAX_INPUT):
 if not isinstance(text,str) or len(text.encode('utf8'))>limit:raise ValueError('Bridge input byte budget exceeded or non-text JSON')
 obj=json.loads(text)
 if not isinstance(obj,dict):raise ValueError('JSON object required')
 return obj

def public_reference(text):
 ref=load(text)
 if not str(ref.get('schema','')).startswith('public-'):raise ValueError('Only public rhythm projection schema is accepted')
 def scan(value):
  if isinstance(value,dict):
   bad=FORBIDDEN.intersection(value)
   if bad:raise ValueError('Non-rhythm/private field rejected: '+','.join(sorted(bad)))
   for v in value.values():scan(v)
  elif isinstance(value,list):
   for v in value:scan(v)
  elif isinstance(value,str) and re.search(r'(?i)(?:[a-z]:[\\/]|file://|/users/|/home/)',value):
   raise ValueError('Local path rejected from public generation input')
 scan(ref)
 if not ref.get('available',True):raise ValueError('Unavailable reference cannot provide generation evidence')
 selected=ref.get('selection')
 if not isinstance(selected,dict) or not selected.get('range_q'):raise ValueError('Explicit selected interval required')
 # New public identity binds exact projection and selection. Never impersonate private receipts.
 original_projection_id=selected.get('selection_id')
 projection_sha=digest(ref)
 receipt={'schema':'browser-rhythm-projection/1','public_payload_sha256':projection_sha,
  'upstream_public_selection_id':original_projection_id,'private_model_identity_equivalent':False,
  'projection_policy':'rhythm-only; pitches, tablature, techniques and private annotations omitted; absent marks remain unknown'}
 projected=copy.deepcopy(ref)
 projected['selection']['binding']={'public_projection':receipt}
 projected['selection']['selection_id']=digest({'receipt':receipt,'range_q':selected['range_q'],'voices':selected.get('voices'),'view_id':selected.get('view_id')})
 projected['source_hash_bindings']={'public_projection_sha256':projection_sha}
 return projected,receipt

def execute(command,payload):
 if not isinstance(payload,dict):raise ValueError('Payload object required')
 if command=='generate':
  if set(payload)-{'reference_json','request_json','seed_decimal','rules_json'}:raise ValueError('Unknown generate field')
  ref,projection=public_reference(payload['reference_json']);req=load(payload['request_json'])
  seed_text=payload['seed_decimal']
  if not isinstance(seed_text,str) or not re.fullmatch(r'-?\d{1,19}',seed_text):raise ValueError('Seed must be exact signed64 decimal text')
  seed=int(seed_text)
  if not -(2**63)<=seed<2**63:raise ValueError('Seed exceeds signed64 bounds')
  model=build_selection_model(ref);raw=generate(model,req,seed);assessment=assess(raw,load(payload.get('rules_json','{}')))
  player=to_reference_payload(raw) if raw.get('clock_complete') and raw.get('playable') else None
  result={'model_json':canonical(model),'raw_json':canonical(raw),'assessment_json':canonical(assessment),
   'player_json':None if player is None else canonical(player),'projection_receipt':projection,
   'summary':{'seed_decimal':str(seed),'status':raw['status'],'clock_complete':raw['clock_complete'],
    'assessment':assessment['overall'],'raw_sha256':raw['raw_sha256'],'model_sha256':model['model_sha256'],
    'selection_id':model['scope_receipt']['selection']['selection_id'],'attacks':len(raw['events']),
    'pieces':len(raw['pieces']),'extent_q':raw.get('extent_q'),'natural_end_q':raw.get('natural_end_q')}}
 elif command=='assess':
  if set(payload)-{'raw_json','rules_json'}:raise ValueError('Unknown assessment field')
  raw=load(payload['raw_json'],MAX_RAW);result={'assessment_json':canonical(assess(raw,load(payload.get('rules_json','{}')))),
   'summary':{'raw_sha256':raw.get('raw_sha256'),'events_changed':False}}
 else:raise ValueError('Unknown fixed bridge command')
 size=sum(len(v.encode('utf8')) for k,v in result.items() if k.endswith('_json') and isinstance(v,str))
 if size>MAX_RAW:raise ValueError('Bridge output byte budget exceeded; no complete result transmitted')
 result['runtime_receipt']={'bridge':BRIDGE_VERSION,'law':LAW_VERSION,'python':sys.version.split()[0],
  'public_projection_identity':True,'json_text_is_authoritative':True,'package_installs':False,'target_access':False}
 return canonical(result)
