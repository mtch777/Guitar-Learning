"""Opt-in recording-time model evidence, never authoritative function labels.

No model loading, downloads, audio I/O or automatic alignment. Caller supplies
identity-bound alignment attestations; this module validates their contract, not
acoustic correctness. Unvalidated/model-derived clocks remain unresolved.
"""
from copy import deepcopy
from math import isfinite
import re


def number(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v)


def identity(v):
    return isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) is not None


def recording_evidence(segments, *, audio_sha256, recording_duration, model_id,
                       model_revision, source_fingerprint, bar_times=(), maximum_alignment_error=.25):
    if not identity(audio_sha256) or not identity(source_fingerprint):raise ValueError('SHA256 identities required')
    if not number(recording_duration) or recording_duration<=0:raise ValueError('invalid recording duration')
    if not isinstance(model_id,str) or not model_id or not isinstance(model_revision,str) or not model_revision:raise ValueError('model provenance required')
    if not number(maximum_alignment_error) or maximum_alignment_error<0:raise ValueError('invalid alignment tolerance')
    bar_times=list(bar_times)
    normalized=[];last=0.
    for s in segments:
        a=s['start_seconds'];b=s['end_seconds'];w=s['candidate_weights']
        if not number(a) or not number(b) or a<last or b<=a or b>recording_duration:raise ValueError('invalid/overlapping model interval')
        if not isinstance(w,dict) or not w or any(not isinstance(k,str) or not k or not number(v) or v<0 for k,v in w.items()) or abs(sum(w.values())-1)>1e-8:raise ValueError('invalid candidate distribution')
        normalized.append({'start_seconds':a,'end_seconds':b,'candidate_weights':deepcopy(w)});last=b
    timeline=[];cursor=0.
    for s in normalized:
        if s['start_seconds']>cursor:timeline.append({'start_seconds':cursor,'end_seconds':s['start_seconds'],'candidate_weights':{},'status':'uncovered'})
        timeline.append(dict(s,status='uncalibrated_model_evidence'));cursor=s['end_seconds']
    if cursor<recording_duration:timeline.append({'start_seconds':cursor,'end_seconds':recording_duration,'candidate_weights':{},'status':'uncovered'})
    bars=[];seen=set();previous_end=None
    for bt in bar_times:
        bar=bt['bar']
        if not isinstance(bar,int) or isinstance(bar,bool) or bar<1 or bar in seen:raise ValueError('invalid/duplicate bar')
        seen.add(bar);out={'bar':bar,'label':'unknown','candidate_weights':{},'status':'alignment_unresolved','confidence':None}
        a=bt.get('start_seconds');b=bt.get('end_seconds');e=bt.get('max_error_seconds')
        valid=(bt.get('validation_status')=='verified' and isinstance(bt.get('validation_method'),str) and bool(bt.get('validation_method').strip()) and bt.get('audio_sha256')==audio_sha256 and bt.get('source_fingerprint')==source_fingerprint and number(a) and number(b) and number(e) and e>=0 and e<=maximum_alignment_error and a-e>=0 and b+e<=recording_duration and b>a)
        if valid:
            if previous_end is not None and a<previous_end:raise ValueError('nonmonotonic/overlapping verified bar times')
            previous_end=b;cover=[s for s in timeline if s['start_seconds']<b+e and s['end_seconds']>a-e]
            # Timing near any distribution boundary is ambiguous; never silently
            # assign a winner by majority overlap or renormalize missing coverage.
            if any(not s['candidate_weights'] for s in cover):out['status']='model_coverage_incomplete'
            elif e>0 and any(a-e<s['start_seconds']<a+e or b-e<s['start_seconds']<b+e for s in cover):out['status']='timing_boundary_ambiguous'
            else:
                weights={}
                for s in timeline:
                    d=max(0,min(b,s['end_seconds'])-max(a,s['start_seconds']))
                    if d==0:continue
                    for k,v in s['candidate_weights'].items():weights[k]=weights.get(k,0)+v*d/(b-a)
                out.update(candidate_weights=weights,status='aligned_uncalibrated_model_evidence',start_seconds=a,end_seconds=b,max_error_seconds=e,validation_method=bt['validation_method'])
        bars.append(out)
    return {'schema':'recording-function-evidence/1','audio_sha256':audio_sha256,'source_fingerprint':source_fingerprint,'model_id':model_id,'model_revision':model_revision,'recording_duration':recording_duration,'maximum_alignment_error':maximum_alignment_error,'alignment_attestations':deepcopy(list(bar_times)),'weight_kind':'uncalibrated_candidate_distribution_nominal_time_average','timeline':timeline,'bars':bars,'limitations':['Model weights are uncalibrated, not accuracy probabilities.','Timing attestations are caller-supplied, not independently verified here.','Unsupported functions are not remapped; original labels remain unknown.','Bar mixtures use nominal times, not uncertainty-integrated probabilities.']}


def attach_recording_evidence(result,evidence,source_fingerprint=None):
    if evidence is None:return result
    if evidence.get('schema')!='recording-function-evidence/1' or evidence.get('source_fingerprint')!=source_fingerprint:raise ValueError('recording evidence source mismatch')
    try:
        rebuilt=recording_evidence([s for s in evidence['timeline'] if s.get('candidate_weights')],audio_sha256=evidence['audio_sha256'],recording_duration=evidence['recording_duration'],model_id=evidence['model_id'],model_revision=evidence['model_revision'],source_fingerprint=evidence['source_fingerprint'],bar_times=evidence['alignment_attestations'],maximum_alignment_error=evidence['maximum_alignment_error'])
    except (KeyError,TypeError,ValueError) as exc:raise ValueError('invalid recording evidence payload') from exc
    if rebuilt!=evidence:raise ValueError('recording evidence payload modified or inconsistent')
    expected=[b['bar']for b in result['bars']];actual=[b['bar']for b in evidence['bars']]
    if actual and actual!=expected:raise ValueError('recording evidence bar identity/order mismatch')
    out=deepcopy(result);out['recording_function_evidence']=deepcopy(evidence)
    return out



