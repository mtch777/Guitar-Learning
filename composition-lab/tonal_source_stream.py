"""Target-independent source-context observations; evaluation is a separate join."""
from fractions import Fraction as F
from tonal_context_observations import mask

FIELDS={'id','start_q','end_q','pitch_classes','source_context_eligible','active_note_refs'}


def project_source_cells(support_cells):
    """Reads ONLY source fields; never label availability, overlaps or changes."""
    if any(c['context_eligibility'] not in ('QUARANTINED','UNBRANCHED_WRITTEN_CONTEXT_ONLY') for c in support_cells):
        raise ValueError('Unknown source context eligibility')
    return [dict(id=i,start_q=c['span_q'][0],end_q=c['span_q'][1],pitch_classes=list(c['context'][1]),
                 source_context_eligible=c['context_eligibility']=='UNBRANCHED_WRITTEN_CONTEXT_ONLY',
                 active_note_refs=list(c['active_note_refs'])) for i,c in enumerate(support_cells)]


def observations(source_cells):
    previous=None;rows=[];refs={};statuses=[];seen=set();last_end=None
    for cell in source_cells:
        if type(cell) is not dict or set(cell)!=FIELDS:raise ValueError('Only projected source context fields accepted')
        ident=cell['id']
        if type(ident) is not int or ident<0 or ident in seen or type(cell['source_context_eligible']) is not bool:raise ValueError('Exact source cell identity/eligibility required')
        seen.add(ident)
        for key in ('start_q','end_q'):
            if type(cell[key]) is not str or str(F(cell[key]))!=cell[key]:raise ValueError('Canonical source rational clock required')
        if F(cell['end_q'])<=F(cell['start_q']):raise ValueError('Positive source cell required')
        if last_end is not None and F(cell['start_q'])<last_end:raise ValueError('Source cells must be ordered and nonoverlapping, including quarantined cells')
        last_end=F(cell['end_q'])
        current=mask(cell['pitch_classes']);notes=cell['active_note_refs']
        if type(notes) is not list or any(type(n)is not str for n in notes) or len(notes)!=len(set(notes)):raise ValueError('Unique source note witnesses required')
        if not cell['source_context_eligible']:
            statuses.append(dict(observation_ref=ident,status='QUARANTINED_SOURCE_CONTEXT'));previous=None;continue
        contiguous=previous is not None and previous['end_q']==cell['start_q']
        row=dict(id=ident,mask=current,previous_mask=previous['mask'] if contiguous else None,
                 sequence=previous['sequence'] if contiguous else ident,start_q=cell['start_q'],end_q=cell['end_q'])
        rows.append(row);refs[ident]=list(notes);previous=row
        statuses.append(dict(observation_ref=ident,status='INCLUDED_SOURCE_CONTEXT'))
    return dict(observations=rows,source_note_refs=refs,source_statuses=statuses,
                scope='Source-only eligibility and predecessor sequence; no evaluation annotation can select or split inference input')
