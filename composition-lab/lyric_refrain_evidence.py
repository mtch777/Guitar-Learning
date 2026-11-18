"""Optional occurrence-local lyric refrain evidence. Never a role classifier.

Lyrics are transient inputs; outputs contain no text or text hashes. Timing must
be supplied by a caller that verified recording-to-score alignment. Line-onset
coverage is not a claim about vocal duration or full section boundaries.
"""
from copy import deepcopy
from math import isfinite
import re, json, hashlib


def _number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)


def feature_fingerprint(features):
    return hashlib.sha256(json.dumps(features,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def lyric_refrain_evidence(events, bar_times, *, source_fingerprint, maximum_pair_gap_seconds, maximum_alignment_error=.25,
                           candidate_distribution=None):
    if not isinstance(source_fingerprint,str) or not source_fingerprint:raise ValueError('source fingerprint required')
    if not _number(maximum_pair_gap_seconds) or maximum_pair_gap_seconds<=0:raise ValueError('pair gap limit required')
    if not _number(maximum_alignment_error) or maximum_alignment_error < 0:
        raise ValueError('invalid alignment tolerance')
    if candidate_distribution is not None:
        if (not candidate_distribution or any(not isinstance(k,str) or not _number(v) or v<0 for k,v in candidate_distribution.items())
                or abs(sum(candidate_distribution.values())-1)>1e-8):
            raise ValueError('candidate distribution must sum to one')
    normalized=[]
    for event in events or []:
        t=event['start_seconds']; text=event['text']
        if not _number(t) or t<0 or not isinstance(text,str):raise ValueError('invalid lyric event')
        words=' '.join(re.findall(r'\w+',text.casefold()))
        if words:normalized.append((t,words,event.get('timestamp_error_seconds')))
    if any(a[0]>=b[0] for a,b in zip(normalized,normalized[1:])):
        raise ValueError('lyric onsets must be strictly increasing')
    pairs={}
    for i in range(len(normalized)-1):
        if normalized[i+1][0]-normalized[i][0]<=maximum_pair_gap_seconds:
            key=(normalized[i][1],normalized[i+1][1]);pairs.setdefault(key,[]).append(i)
    repeated={}
    for ids in pairs.values():
        disjoint=[]
        for i in ids:
            if not disjoint or i>=disjoint[-1]+2:disjoint.append(i)
        if len(disjoint)>1:
            for i in disjoint:repeated[i]=disjoint
    # Both onsets of every supporting pair must have an independently usable clock.
    def onset_usable(index):
        t,_,lyric_error=normalized[index]
        if not _number(lyric_error) or lyric_error<0:return False
        for bar in bar_times:
            err=bar.get('max_error_seconds')
            if bar.get('verified') is True and _number(err) and 0<=err<=maximum_alignment_error:
                allowance=err+lyric_error
                if bar['start_seconds']+allowance<=t<bar['end_seconds']-allowance:return True
        return False
    usable_pairs={i:ids for i,ids in repeated.items() if onset_usable(i) and onset_usable(i+1)}
    repeated={i:[j for j in ids if j in usable_pairs] for i,ids in usable_pairs.items()}
    repeated={i:ids for i,ids in repeated.items() if len(ids)>1}
    rows=[];seen=set();last_end=None
    for b in bar_times:
        if b['bar'] in seen:raise ValueError('duplicate bar')
        seen.add(b['bar']);start=b['start_seconds'];end=b['end_seconds'];err=b.get('max_error_seconds')
        if not _number(start) or not _number(end) or end<=start or(last_end is not None and start<last_end):raise ValueError('invalid ordered bar times')
        last_end=end
        verified=b.get('verified') is True and _number(err) and 0<=err<=maximum_alignment_error
        # An onset near a bar edge is not assigned to either neighboring bar.
        hits=[i for i in repeated if verified and start+err<=normalized[i][0]<end-err]
        positive=bool(hits)
        rows.append(dict(bar=b['bar'],status='positive_refrain_evidence' if positive else 'no_lyrics' if not normalized else 'alignment_unverified' if not verified else 'no_positive_evidence',
            repeated_pair_onsets=len(hits),pair_gaps_seconds=[normalized[i+1][0]-normalized[i][0] for i in hits],occurrence_counts=[len(repeated[i])for i in hits],
            candidate_distribution=deepcopy(candidate_distribution)if positive else None,
            alternatives=['chorus','verse','intro','outro','other_refrain_function']if positive else [],
            confidence=None,alignment_max_error_seconds=err if verified else None,
            timing_basis='caller_verified_clock_and_declared_error_allowances; lyric_onsets_only' if verified else 'unverified_or_unavailable'))
    return dict(schema='lyric-refrain-evidence/1',source_fingerprint=source_fingerprint,maximum_pair_gap_seconds=maximum_pair_gap_seconds,bars=rows,
        distribution_basis='caller_supplied_global_uncalibrated_reference_prior'if candidate_distribution else None,
        limitations=['Positive evidence only; absence does not support verse.',
                     'Repeated lyrics can serve different functions at different occurrences.',
                     'Onset evidence does not define vocal offsets or section boundaries.',
                     'No calibrated functional confidence or automatic role labels.',
                     'Ordered adjacent lyric lines are not proof of a contiguous sung phrase; pair gaps are retained.',
                     'Timing allowances are caller declarations, not certified mathematical error bounds.'])


def attach_lyric_evidence(analysis, evidence, source_fingerprint=None):
    """Keep existing musical results and labels intact; attach an optional cue."""
    if evidence is None:return analysis
    if evidence.get('schema')!='lyric-refrain-evidence/1':raise ValueError('unsupported lyric evidence')
    if not source_fingerprint or evidence.get('source_fingerprint')!=source_fingerprint:raise ValueError('lyric evidence source mismatch')
    rows=evidence['bars']
    if [b['bar']for b in rows]!=[b['bar']for b in analysis['bars']]:raise ValueError('lyric evidence bar identity mismatch')
    result=deepcopy(analysis)
    for bar,cue in zip(result['bars'],rows):bar['lyric_refrain_evidence']=deepcopy(cue)
    result['optional_lyric_evidence']={k:deepcopy(v)for k,v in evidence.items()if k!='bars'}
    return result



