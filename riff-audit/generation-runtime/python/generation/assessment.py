"""Pure end diagnostics: changing rules never consumes RNG or changes raw events."""
import copy
from fractions import Fraction as Q
from .evidence import q, check

def assess(raw_plan,rule_profile=None):
 rules=copy.deepcopy(rule_profile or {})
 if set(rules)-{'grid_q','density_min','density_max','max_coattack','max_similarity','max_extent_q'}: raise ValueError('Unknown assessment rule')
 check(raw_plan,'raw_sha256'); ds=[]
 def add(name,state,detail,**facts): ds.append({'rule':name,'state':state,'detail':detail,**facts})
 complete=raw_plan.get('clock_complete') is True
 add('complete_clock','pass' if complete else 'reject','Complete raw clock retained.' if complete else 'No complete clock; do not audition as completed output.')
 if complete:
  extent=q(raw_plan['extent_q']); events=raw_plan['events']
  add('musical_support','warn','Selected evidence is exploratory. Occurrences/views do not count as independent songs.',coverage=raw_plan['coverage'])
  add('requested_length','pass' if raw_plan['extent_q']==raw_plan['request']['extent_q'] else 'reject','All proportional piece lengths were chosen before timing, with no last-piece remainder patch.',actual_q=str(extent))
  conflicts=raw_plan.get('boundary_conflicts',[])
  add('return_boundary_gap_consistency','reject' if conflicts else 'pass','Generated return and incoming sampled gap proposals are both retained; no source clock is silently shortened.',conflicts=conflicts)
  tail=q(raw_plan['natural_end_q'])-extent
  add('crossing_holds','warn' if tail>0 else 'pass','Crossing holds remain untrimmed.',beyond_requested_q=str(tail))
  grid=q(rules.get('grid_q',raw_plan['request'].get('notation_grid_q','1/4')))
  if grid<=0: raise ValueError('Grid must be positive')
  off=[e['attack_id'] for e in events if q(e['onset_q'])%grid]
  add('requested_grid','warn' if off else 'pass','Exact rational clocks preserved without quantization.',grid_q=str(grid),offgrid_attacks=off)
  density=Q(len(events))/extent; lo=Q(str(rules.get('density_min',0))); hi=Q(str(rules.get('density_max',16)))
  add('density','reject' if not lo<=density<=hi else 'pass','Assessment never adds/removes attacks.',attacks=len(events),attacks_per_quarter_q=str(density))
  cap=rules.get('max_coattack',8); maximum=max([len(e['members']) for e in events] or [0])
  add('capacity','reject' if maximum>cap else 'pass','Abstract coattack capacity, not a physical guitar solve.',max_coattack=maximum,requested_max=cap)
  source=raw_plan['source_onsets_relative_q']; output=[e['onset_q'] for e in events]; union=set(source)|set(output)
  similarity=Q(len(set(source)&set(output)),len(union)) if union else Q(1); threshold=Q(str(rules.get('max_similarity',1)))
  add('source_similarity','reject' if similarity>threshold else 'warn' if source==output else 'pass','Onset-set overlap only, not musical originality or legal judgment.',onset_jaccard_q=str(similarity),exact_onset_sequence_copy=source==output)
  unknown=sum(bool(m['unknowns']) for e in events for m in e['members'])
  add('unknown_source_facts','warn' if unknown else 'pass','Unknown facts remain unknown; any neutral pulse surrogate is labeled.',members_with_unknowns=unknown)
  add('technique_execution','warn','Source marks/relations retained as evidence. Neutral player does not execute guitar techniques.')
  add('physical_feasibility','warn','Not evaluated: no pitch/contact/target mapping was generated.')
  if 'max_extent_q' in rules: add('extent_rule','reject' if extent>q(rules['max_extent_q']) else 'pass','Requested length rule assessed only after construction.')
 overall='reject' if any(d['state']=='reject' for d in ds) else 'warn' if any(d['state']=='warn' for d in ds) else 'pass'
 return {'raw_sha256':raw_plan['raw_sha256'],'rule_profile':rules,'diagnostics':ds,'overall':overall,'events_changed':False}
