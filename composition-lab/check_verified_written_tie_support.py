"""Independent supporting-chain check from captured positions and source clocks.

Does not import the producer or its tie-edge/qualification functions. Traverses
each literal continuation backward, then audits the whole connected component.
"""
from collections import defaultdict
from fractions import Fraction as F
from source_fact_tier1 import project_documents
from source_tie_tier1 import extract_documents

REASON='written_tie_continuation_or_unsupported_tie'


def derive(tier1,raw_view,edited_refs):
    docs=project_documents(tier1);lower=extract_documents(docs)
    events={r['id']:r for r in lower['events']}
    fields={r['occurrence_ref']:r['fields']for r in lower['tie_notation']['occurrences']}
    settings={r['part_id']:r['fields']for r in lower['tie_notation']['parts']}
    rows={r['occurrence_ref']:r for r in raw_view['occurrence_inventory']}
    lanes=defaultdict(list);lane_for={};bad=set();tie_nodes=set();links={}
    clock_bars={w['bar']for k in ('layout_warnings','timing_warnings')for w in lower['source_coverage'][k]}
    for ref,event in events.items():
        f=fields[ref];s=f.get('string');p=settings[event['part_id']];t=p.get('tuning')
        if type(s)is int and type(t)is list and 0<=s<len(t):
            lane=(event['part_id'],event['voice'],int(s));lanes[lane].append(ref);lane_for[ref]=lane
        if f.get('tie')is not None and f.get('tie')is not False:tie_nodes.add(ref)
    # Immediate previous onset, not nearest matching pitch. An intervening note,
    # duplicate lane attack, missing origin or gap prevents certification.
    for ref in sorted(tie_nodes):
        event=events[ref];lane=lane_for.get(ref);t=F(event['onset_q'])
        candidates=lanes.get(lane,[])
        same=[r for r in candidates if F(events[r]['onset_q'])==t and F(events[r]['duration_q'])>0]
        prior=[r for r in candidates if F(events[r]['onset_q'])<t and F(events[r]['duration_q'])>0]
        previous_time=max((F(events[r]['onset_q'])for r in prior),default=None)
        previous=[r for r in prior if F(events[r]['onset_q'])==previous_time]
        contiguous=[r for r in previous if F(events[r]['onset_q'])+F(events[r]['duration_q'])==t]
        valid=fields[ref].get('tie')is True and len(same)==1 and len(previous)==1 and len(contiguous)==1 and F(event['duration_q'])>0
        if valid:
            origin=contiguous[0];a,b=fields[origin],fields[ref]
            valid=(type(a.get('fret'))in (int,float)and type(b.get('fret'))in (int,float)
                and F(str(a['fret']))>=0 and F(str(a['fret']))==F(str(b['fret']))
                and not a.get('dead')and not b.get('dead')
                and events[origin]['pitch']is not None and event['pitch']is not None
                and F(events[origin]['pitch'])==F(event['pitch']))
        if valid:links[ref]=origin
        else:bad.update([ref,*contiguous])
    connected=set(links)|set(links.values())
    adjacency=defaultdict(set)
    for destination,origin in links.items():adjacency[origin].add(destination);adjacency[destination].add(origin)
    components=[];seen=set();cleared=set();blocked=set(edited_refs)&(tie_nodes|connected|bad)
    for ref in sorted(connected):
        if ref in seen:continue
        component=set();stack=[ref]
        while stack:
            current=stack.pop()
            if current in component:continue
            component.add(current);stack.extend(adjacency[current]-component)
        seen|=component
        ordered=sorted(component,key=lambda r:(F(events[r]['onset_q']),r))
        invalid=bool(component&bad or component&set(edited_refs))
        invalid|=any(events[r]['bar']in clock_bars for r in component)
        invalid|=any(q!=REASON for r in component for q in rows[r]['written_pitch_qualifications'])
        invalid|=any(events[r]['pitch']is None or F(events[r]['pitch']).denominator!=1 for r in component)
        for r in component:
            e=events[r];beat=docs[f"track-{e['part_id']}.json"]['measures'][e['bar']-1]['voices'][e['voice']]['beats'][e['beat']]
            note=beat['notes'][e['note']]
            note_fields={'string','fret','rest','tie','velocity','accentuated'}
            beat_fields={'notes','type','duration','beamStart','beamStop','beam','beamMode','velocity','chord','rest','dots','dotted','tuplet','tupletStart','tupletStop'}
            invalid|=any(k not in note_fields and v is not None and v is not False for k,v in note.items())
            invalid|=any(k not in beat_fields and v is not None and v is not False for k,v in beat.items())
        if not invalid:
            components.append(dict(origin_ref=ordered[0],occurrence_refs=ordered,status='VERIFIED_WRITTEN_PITCH_CONTINUITY'))
            cleared.update(ordered[1:])
    return dict(chains=sorted(components,key=lambda r:r['origin_ref']),cleared_refs=cleared,blocked_edited_refs=blocked)
