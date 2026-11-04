"""Explicit current lane proportions through the existing material inverse.

This updater receives already chosen musical timing. It does not select a groove,
change original observations, or turn notation feasibility into musical preference.
The caller measures its complete final output against the frozen request units.
"""
from copy import deepcopy

import support_material_uses as uses
from material_rhythm_control import _check_stable_timing


def apply_shares(upper, requests):
    """Update named lane proportions atomically; keep all other live choices.

    Requests bind a stable use and its exact saved destination scope. Existing
    displacement migrates into complete current proportions before selected lanes
    change, so an unselected lane cannot silently revert to its source clock.
    """
    from material_slot_clock import current_lane_shares
    uses._shape(upper)
    if type(requests)is not list or not requests:
        raise ValueError('Explicit nonempty lane-clock requests required')
    byid={u['id']:u for u in upper['uses']};seen=set()
    for request in requests:
        if type(request)is not dict or set(request)!={'use_id','scope','lane_shares'}:
            raise ValueError('Exact use, scope and lane proportions required')
        identity=request['use_id']
        if type(identity)is not str or identity not in byid or identity in seen:
            raise ValueError('Unique existing use identity required')
        seen.add(identity)
        if request['scope']!=upper['slots'][byid[identity]['slot_ref']]['scope']:
            raise ValueError('Lane-clock request differs from saved destination scope')
        if type(request['lane_shares'])is not dict or not request['lane_shares']:
            raise ValueError('At least one complete selected lane required')
        if 'entry_shares'in byid[identity]:
            raise ValueError('Existing entry and content must be edited through their joint clock')
    before=uses.expand(upper)
    out=deepcopy(upper);changed=[]
    for request in requests:
        selected=next(u for u in out['uses']if u['id']==request['use_id'])
        definition=out['materials'][selected['material_ref']]
        resolved=uses.resolved_definition(definition,selected,parent=out['lower_tier'],slot=out['slots'][selected['slot_ref']])
        if not any(field in selected for field in ('rhythm_offset_q','rhythm_lane_shares')):
            resolved=uses.material.rhythm_context(resolved,out['lower_tier'])
        current=current_lane_shares(resolved)
        proposed=deepcopy(current)
        if set(request['lane_shares'])-set(current):
            raise ValueError('Unknown or unowned lane')
        proposed.update(deepcopy(request['lane_shares']))
        if proposed==current:continue  # zero locks the supplied current state
        selected.pop('rhythm_offset_q',None)
        selected['rhythm_lane_shares']=proposed
        changed.append(selected['id'])
    if not changed:return out,dict(changed=False,changed_uses=[],meaning='CURRENT_CLOCK_RETAINED')
    after=uses.expand(out)
    _check_stable_timing(before,after)
    # The only permitted persistent changes are current use clock parameters.
    protected=deepcopy(out)
    for previous,current in zip(upper['uses'],protected['uses']):
        for field in ('rhythm_offset_q','rhythm_lane_shares'):
            current.pop(field,None)
            if field in previous:current[field]=deepcopy(previous[field])
    if protected!=upper:
        raise ValueError('Lane-clock update changed unrelated relationships or evidence')
    return out,dict(changed=after!=before,changed_uses=changed,
                    meaning='CURRENT_LANE_PROPORTIONS_CHANGED',
                    original_observations='UNCHANGED')


def apply_entry_choices(upper, requests):
    """Set final entry and content proportions together, at stable material IDs.

    An unselected lane retains its current timing. Repeated edits replace the
    current choice rather than inserting another rest or learning new evidence.
    """
    from material_slot_clock import current_lane_shares
    uses._shape(upper)
    if type(requests)is not list or not requests:
        raise ValueError('Explicit nonempty joint clock requests required')
    byid={u['id']:u for u in upper['uses']};seen=set()
    for request in requests:
        if type(request)is not dict or set(request)!={'use_id','scope','lane_shares','entry_shares'}:
            raise ValueError('Closed use, scope, entry and content request required')
        identity=request['use_id']
        if type(identity)is not str or identity not in byid or identity in seen:
            raise ValueError('Unique existing use identity required')
        seen.add(identity)
        if request['scope']!=upper['slots'][byid[identity]['slot_ref']]['scope']:
            raise ValueError('Joint clock differs from saved destination scope')
        if (type(request['lane_shares'])is not dict or not request['lane_shares']
                or type(request['entry_shares'])is not dict
                or set(request['entry_shares'])!=set(request['lane_shares'])):
            raise ValueError('Each selected lane needs both entry and complete content shares')
    before=uses.expand(upper);out=deepcopy(upper);changed=[]
    for request in requests:
        selected=next(u for u in out['uses']if u['id']==request['use_id'])
        if 'entry_shares'in selected:
            current=deepcopy(selected['rhythm_lane_shares']);entries=deepcopy(selected['entry_shares'])
        else:
            definition=out['materials'][selected['material_ref']]
            resolved=uses.resolved_definition(definition,selected,parent=out['lower_tier'],slot=out['slots'][selected['slot_ref']])
            if not any(field in selected for field in ('rhythm_offset_q','rhythm_lane_shares')):
                resolved=uses.material.rhythm_context(resolved,out['lower_tier'])
            current=current_lane_shares(resolved);entries={ref:'0'for ref in current}
        if set(request['lane_shares'])-set(current):raise ValueError('Unknown or unowned joint lane')
        proposed=deepcopy(current);proposed.update(deepcopy(request['lane_shares']))
        entry=deepcopy(entries);entry.update(deepcopy(request['entry_shares']))
        if proposed==current and entry==entries:continue
        selected.pop('rhythm_offset_q',None)
        selected['rhythm_lane_shares']=proposed;selected['entry_shares']=entry
        changed.append(selected['id'])
    if not changed:return out,dict(changed=False,changed_uses=[],meaning='CURRENT_CLOCK_RETAINED')
    after=uses.expand(out);_check_stable_timing(before,after)
    protected=deepcopy(out)
    for previous,current in zip(upper['uses'],protected['uses']):
        for field in ('rhythm_offset_q','rhythm_lane_shares','entry_shares'):
            current.pop(field,None)
            if field in previous:current[field]=deepcopy(previous[field])
    if protected!=upper:raise ValueError('Joint clock changed unrelated relationships or original evidence')
    return out,dict(changed=after!=before,changed_uses=changed,
        meaning='JOINT_ENTRY_CONTENT_CLOCK_CHANGED',original_observations='UNCHANGED')
