"""Pure adapter for the existing neutral reference scheduler; never synthesizes audio."""
import copy
from .evidence import check,digest

def to_reference_payload(raw_plan):
 """Convert a complete raw clock to the existing player shape without mutation.
 Endpoint aliases are for neutral audition only. Original unknown notation is retained
 under raw_notation; never describe this payload as a guitar score or source replay.
 """
 check(raw_plan,'raw_sha256')
 if not raw_plan.get('clock_complete') or not raw_plan.get('playable'):
  raise ValueError('Incomplete raw plan cannot be adapted as complete playable notes')
 events=[]
 for source_event in raw_plan['events']:
  event=copy.deepcopy(source_event)
  for member in event['members']:
   member['raw_notation']={'written_end_q':member['written_end_q'],'tied_end_q':member['tied_end_q']}
   member['occurrence']=member['id']  # Generated identity, never dedupe by donor occurrence.
   member['onset_q']=event['onset_q']
   member['pitch']=None;member['pitch_known']=False
   member['tied_end_q']=member['neutral_end_q']
   member['neutral_envelope_only']=True
  events.append(event)
 end=raw_plan['natural_end_q'];selection={'selection_id':raw_plan['raw_sha256'],'range_q':['0',end],
  'view_id':'generated_neutral','voices':sorted({str(m['voice']) for e in events for m in e['members'] if m['voice'] is not None}),
  'generated_compositional_horizon_q':raw_plan['extent_q'],'binding':{'raw_sha256':raw_plan['raw_sha256'],'model_sha256':raw_plan['model_sha256']}}
 return {'schema':'generated-neutral-reference/1','available':True,'selection':selection,'range_q':['0',end],
  'events':events,'carry_in':[],'carry_out':[],'explicit_rests':[],
  'tempo_map':copy.deepcopy(raw_plan['tempo_map']),'meter_map':copy.deepcopy(raw_plan['meter_map']),
  'record':{'id':raw_plan['raw_sha256'],'song':'Generated neutral rhythm','artist':'Exploratory selection law'},
  'source_hash_bindings':{'raw_plan':raw_plan['raw_sha256']},'boundary_conflicts':copy.deepcopy(raw_plan['boundary_conflicts']),
  'recommended_player_options':{'mode':'neutral','normalized':True,'bpm':raw_plan['request']['tempo_bpm'],'speed':1,'loop':False},
  'warnings':['Neutral generated rhythm, not source pitch or guitar performance.',
   'Source technique evidence is retained, not acoustically executed.',
   'Audition endpoint aliases use neutral_end_q. Original unknown notation remains in raw_notation.',
   'Range includes untrimmed hold tails beyond the requested compositional horizon.'],
  'coverage':copy.deepcopy(raw_plan['coverage']),'raw_sha256':raw_plan['raw_sha256'],'model_sha256':raw_plan['model_sha256']}
