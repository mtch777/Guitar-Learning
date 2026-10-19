"""Preserved-GP replay/redaction/overlay utilities, without new music decisions.

Source answers belong to replay/evaluation. Learned methods receive the redacted
file; only their declared, eligible in-window fields return to the source GP.
"""
from copy import deepcopy

from engine_contract import _read, _value, _scope, sha, REPRESENTATIONS
from reference_levers import BEND_PROPERTIES
from technique_edits import transact, strip


def api_to_gpif_string(index, api_tuning, gpif_tuning):
    """Known API/GPIF opposite string order, verified against actual tunings."""
    if (not isinstance(api_tuning,list) or not api_tuning or
        any(type(p) is not int or not 0<=p<=127 for p in api_tuning) or
        list(reversed(api_tuning))!=gpif_tuning):raise ValueError('Source/GPIF tuning convention differs')
    if type(index) is not int or not 0<=index<len(api_tuning):raise ValueError('Invalid API string index')
    return len(api_tuning)-1-index


def fields(feature):
    if feature not in REPRESENTATIONS:raise ValueError('Unsupported technique')
    if feature=='finger_vibrato':return 'tag',{'Vibrato'}
    return 'property', (set(BEND_PROPERTIES) if feature=='bend' else {'PalmMuted'}
                        if feature=='palm_mute' else {'HopoOrigin','HopoDestination'})


def inside(occurrence, window):
    if (not isinstance(window,(list,tuple)) or len(window)!=3
        or any(type(v) is not int for v in window)
        or window[0]<0 or not 1<=window[1]<=window[2]):raise ValueError('Explicit track/bar window required')
    track,bar,*_=map(int,occurrence.split(':'))
    return track==window[0] and window[1]<=bar<=window[2]


def _permissions(rows, feature, window=None):
    domain,names=fields(feature)
    if len({row['note']['note_id'] for row in rows.values()})!=len(rows):
        raise ValueError('Shared note definitions require occurrence cloning')
    selected={('note',row['note']['note_id'],domain):set(names)
              for ident,row in rows.items() if window is None or inside(ident,window)}
    if not selected:raise ValueError('No source note occurrences in scope')
    return selected


def redact(source,destination,feature,*,window=None):
    _,_,_,rows=_read(source)
    permissions=_permissions(rows,feature,window)
    return transact(source,destination,{k:[] for k in permissions},permissions)


def replay(source,redacted,destination,feature,*,window=None):
    """Reapply original annotations; explicitly NOT a learned reconstruction."""
    original,members,comment,rows=_read(source);hidden,hm,hc,other=_read(redacted)
    if set(rows)!=set(other) or members!=hm or comment!=hc:
        raise ValueError('Replay occurrence/archive identity differs')
    permissions=_permissions(rows,feature,window)
    if strip(original,permissions)!=strip(hidden,permissions):raise ValueError('Redaction changed locked data')
    domain,names=fields(feature)
    values={('note',row['note']['note_id'],domain):_value(row['note'],domain,names)
            for ident,row in rows.items() if window is None or inside(ident,window)}
    return transact(redacted,destination,values,permissions)


def overlay(source,redacted,proposal,destination,feature,window,audit):
    """Copy declared complete decision units; never copy a rewritten score."""
    original,members,comment,rows=_read(source)
    _permissions(rows,feature,window)  # Reject invalid/empty windows before export.
    hidden,hm,hc,hr=_read(redacted);proposed,pm,pc,pr=_read(proposal)
    permissions=_permissions(rows,feature)
    if (set(rows)!=set(hr) or set(rows)!=set(pr) or members!=hm or members!=pm
        or comment!=hc or comment!=pc):raise ValueError('Proposal identity/archive changed')
    if strip(original,permissions)!=strip(hidden,permissions) or strip(hidden,permissions)!=strip(proposed,permissions):
        raise ValueError('Proposal changed data outside requested feature')
    domain,names=fields(feature)
    if any(_value(row['note'],domain,names) for row in hr.values()):
        raise ValueError('Target annotations were not fully redacted')
    if audit.get('sha256')!=sha(proposal):raise ValueError('Proposal audit seal differs')
    chosen=[];excluded=0;allowed={};values={}
    for raw in audit.get('decisions',[]):
        if raw.get('family','palm_mute')!=feature:raise ValueError('Unexpected feature decision')
        scope=_scope(feature,raw)
        if any(ident not in rows for ident,_,_ in scope):raise ValueError('Unknown decision occurrence')
        if not all(inside(ident,window) for ident,_,_ in scope):excluded+=1;continue
        if raw.get('released') is not True:raise ValueError('Full-freedom proposals required')
        chosen.append(deepcopy(raw))
        for ident,domain,names in scope:
            key=('note',rows[ident]['note']['note_id'],domain)
            allowed.setdefault(key,set()).update(names)
            for xml in _value(pr[ident]['note'],domain,names):
                values.setdefault(key,set()).add(xml)
    result=transact(source,destination,{k:sorted(values.get(k,set())) for k in allowed},allowed)
    return dict(**result,decisions=chosen,excluded_outside_window_decisions=excluded,
                proposal_input_sha256=sha(redacted),proposal_output_sha256=sha(proposal),
                source_sha256=sha(source),window=list(window),
                limitation='Replay/overlay integrity is not learned musical understanding')
