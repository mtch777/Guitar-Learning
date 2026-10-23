"""Source-only ordered pitch-set observations and separately normalized targets.

Encoded written score time; analyst labels never define observation boundaries.
Conventional interval definitions are not learned artist rules.
"""
from fractions import Fraction as F
import re

MAJOR=(0,2,4,5,7,9,11)
MINOR=(0,2,3,5,7,8,10)
ROMANS=('I','II','III','IV','V','VI','VII')


def named_tonic(name):
    match=re.fullmatch(r'([A-Ga-g])([#b]*)',name)
    if not match:raise ValueError('Unsupported named global tonic')
    letter,acc=match.groups()
    if '#' in acc and 'b' in acc:raise ValueError('Mixed accidental spelling')
    return (dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[letter.upper()]+acc.count('#')-acc.count('b'))%12,letter.islower()


def relative_tonic(expression,parent_tonic,parent_minor):
    """Compose nested key-relative scale-degree intervals right-to-left."""
    tonic=parent_tonic;minor=parent_minor
    for token in reversed(expression.split('/')):
        match=re.fullmatch(r'([#]*|b*)(VII|VI|IV|III|II|I|V|vii|vi|iv|iii|ii|i|v)',token)
        if not match:raise ValueError('Unsupported relative-key token')
        acc,roman=match.groups();degree=ROMANS.index(roman.upper())
        tonic=(tonic+(MINOR if minor else MAJOR)[degree]+acc.count('#')-acc.count('b'))%12
        minor=roman.islower()
    return tonic,minor


def normalize_target(raw):
    """Structural local key and applied target stay distinct, including mode."""
    if '@none' in raw.get('label','') or any(v for k,v in raw.items() if k.startswith('alt_')):raise ValueError('Unresolved/no-harmony/alternative target')
    global_pc,global_minor=named_tonic(raw.get('globalkey',''))
    local_pc,local_minor=relative_tonic(raw.get('localkey',''),global_pc,global_minor)
    for field,value in (('globalkey_is_minor',global_minor),('localkey_is_minor',local_minor)):
        if raw.get(field,'') not in ('',str(int(value))):raise ValueError('Explicit target mode disagrees with key expression')
    applied=None
    if raw.get('relativeroot'):
        pc,minor=relative_tonic(raw['relativeroot'],local_pc,local_minor);applied=dict(tonic_pc=pc,mode='minor' if minor else 'major')
    return dict(tonic_pc=local_pc,mode='minor' if local_minor else 'major',state=12*int(local_minor)+local_pc,applied_target=applied)


def mask(pitch_classes):
    if any(type(p) is not int or not 0<=p<12 for p in pitch_classes):raise ValueError('Exact pitch classes required')
    return sum(1<<p for p in set(pitch_classes))


def rotate(bits,tonic):
    if type(bits) is not int or not 0<=bits<4096 or type(tonic) is not int or not 0<=tonic<12:raise ValueError('Invalid PC-set coordinate')
    return ((bits>>tonic)|(bits<<(12-tonic)))&4095


def target_cells(support_rows):
    """No target-based segmentation: every source cell stays present once."""
    rows=[];previous=None
    for index,cell in enumerate(support_rows):
        reasons=[];targets=cell['target_overlaps']
        if cell['context_eligibility']!='UNBRANCHED_WRITTEN_CONTEXT_ONLY':reasons.append('UNVERIFIED_CONTEXT')
        if cell['internal_annotation_change'] or len(targets)!=1 or len(targets[0]['targets'])!=1:reasons.append('TARGET_CHANGES_OR_ALTERNATIVES_IN_SOURCE_CELL')
        if cell['target_eligibility']=='QUARANTINED_UNPARSED_ALTERNATIVES':reasons.append('UNPARSED_ALTERNATIVE')
        normalized=None
        if not reasons:
            try:normalized=normalize_target(targets[0]['targets'][0])
            except ValueError as error:reasons.append('TARGET_NORMALIZATION:'+str(error))
        current=mask(cell['context'][1]);eligible=not reasons
        if eligible and previous is not None and previous['end_q']==cell['span_q'][0]:sequence=previous['sequence']
        else:sequence=index
        row=dict(id=index,start_q=cell['span_q'][0],end_q=cell['span_q'][1],duration_q=str(F(cell['span_q'][1])-F(cell['span_q'][0])),mask=current,previous_mask=previous['mask'] if eligible and previous is not None and sequence==previous['sequence'] else None,sequence=sequence,target=normalized,quarantine_reasons=reasons,active_note_refs=cell['active_note_refs'])
        rows.append(row);previous=row if eligible else None
    return rows
