"""Independent literal minimum-contact-cover oracle, not a playability model.

No producer imports, candidate/search calls, source-specific shape or fret span.
The result certifies only the stated simultaneous nominal contact equations.
"""
from itertools import combinations
import json

FIELDS={'fret','first_string','last_string'}
def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)

def canonical_required(required,max_digits=4,search_limit=100000):
    if type(required)is not list or not required:raise ValueError('Nonempty required string/fret list expected')
    if type(max_digits)is not int or not 1<=max_digits<=4:raise ValueError('One to four fretting digits required')
    if type(search_limit)is not int or search_limit<1:raise ValueError('Positive integer search limit required')
    rows=[]
    for row in required:
        if type(row)is not dict or set(row)!={'string','fret'}or any(type(row[k])is not int or row[k]<0 for k in row):raise ValueError('Exact nonnegative integer string/fret required')
        rows.append(dict(row))
    if len({r['string']for r in rows})!=len(rows):raise ValueError('Duplicate required string')
    return sorted(rows,key=lambda r:r['string'])

def _contact_key(c):return(c['fret'],c['first_string'],c['last_string'])

def effective(required,cover):
    """Check literal contacts and calculate their effective fret on each string."""
    target={r['string']:r['fret']for r in required};observed={s:0 for s in target}
    if type(cover)is not list:raise ValueError('Contact cover list required')
    seen=set()
    for c in cover:
        if type(c)is not dict or set(c)!=FIELDS or any(type(v)is not int for v in c.values()):raise ValueError('Typed exact contact fields required')
        fret,first,last=_contact_key(c)
        if fret<=0 or first<0 or last<first:raise ValueError('Positive contact and ordered string interval required')
        if _contact_key(c)in seen:raise ValueError('Duplicate contact')
        seen.add(_contact_key(c));covered=[s for s in target if first<=s<=last]
        if len(covered)!=last-first+1:raise ValueError('Contact crosses inactive strings')
        for s in covered:
            if fret>target[s]:raise ValueError('Contact blocks required open/lower fret')
            observed[s]=max(observed[s],fret)
    return observed

def expected(required,*,max_digits=4,search_limit=100000):
    """Brute-force every small subset, independent of producer search strategy."""
    rows=canonical_required(required,max_digits,search_limit);target={r['string']:r['fret']for r in rows};strings=list(target)
    # A contact not attaining any required fret is redundant in a minimum cover.
    # Every nonredundant fret must therefore occur in the required fret values.
    candidates=[]
    for fret in sorted({r['fret']for r in rows if r['fret']>0}):
        for i,first in enumerate(strings):
            for last in strings[i:]:
                c=dict(fret=fret,first_string=first,last_string=last)
                try:effective(rows,[c])
                except ValueError:continue
                candidates.append(c)
    candidates.sort(key=_contact_key);examined=0
    for size in range(max_digits+1):
        covers=[]
        for indices in combinations(range(len(candidates)),size):
            examined+=1
            if examined>search_limit:return dict(status='SEARCH_LIMIT',minimum_contacts=None,covers=[],examined_subsets=examined-1)
            cover=[dict(candidates[i])for i in indices]
            if effective(rows,cover)==target:covers.append(cover)
        if covers:
            covers.sort(key=lambda cover:tuple(map(_contact_key,cover)))
            return dict(status='COVERED',minimum_contacts=size,covers=covers,examined_subsets=examined)
    return dict(status='NO_COVER_WITHIN_MODEL',minimum_contacts=None,covers=[],examined_subsets=examined)

def check(required,result,*,max_digits=4,search_limit=100000):
    issues=[];oracle=None;complete=False
    try:
        rows=canonical_required(required,max_digits,search_limit)
        needed={'schema','required','max_digits','search_limit','examined','status','minimum_contacts','covers','human_playability'}
        if type(result)is not dict or needed!=set(result):raise ValueError('Exact complete contact result required')
        if result['schema']!='fretting-contact-coverage/1'or result['human_playability']!='UNVERIFIED':raise ValueError('Incorrect model schema or playability claim')
        if type(result['max_digits'])is not int or result['max_digits']!=max_digits or encoded(result['required'])!=encoded(rows):raise ValueError('External model inputs differ')
        if type(result['search_limit'])is not int or result['search_limit']!=search_limit or type(result['examined'])is not int or not 0<=result['examined']<=search_limit:raise ValueError('External search budget/counter differs')
        status=result['status'];covers=result['covers'];minimum=result['minimum_contacts']
        if status not in ('COVERED','NO_COVER_WITHIN_MODEL','SEARCH_LIMIT'):raise ValueError('Unsupported outcome')
        if type(covers)is not list:raise ValueError('Cover inventory list required')
        if status=='SEARCH_LIMIT':
            if covers or minimum is not None:raise ValueError('Search refusal leaked partial covers')
            if result['examined']!=search_limit:raise ValueError('Search refusal did not exhaust declared budget')
            oracle=expected(rows,max_digits=max_digits,search_limit=search_limit)
            if oracle['status']!='SEARCH_LIMIT':raise ValueError('Even independent superset search finishes inside budget; resource refusal unjustified')
        else:
            oracle=expected(rows,max_digits=max_digits,search_limit=search_limit)
            if oracle['status']=='SEARCH_LIMIT':
                return dict(status='INDEPENDENT_SEARCH_LIMIT',issues=[],complete=False,scope='Independent combination budget exhausted; no feasibility or completeness verdict')
            complete=True
            if status!=oracle['status']:raise ValueError('Independent coverage outcome differs')
            if status=='COVERED'and(type(minimum)is not int or not 0<=minimum<=max_digits):raise ValueError('Typed minimum cardinality required')
            if minimum!=oracle['minimum_contacts']:raise ValueError('Independent minimum differs')
            for cover in covers:
                if len(cover)!=minimum or effective(rows,cover)!={r['string']:r['fret']for r in rows}:raise ValueError('Incomplete or nonminimum contact cover')
                if cover!=sorted(cover,key=_contact_key):raise ValueError('Noncanonical contact order')
            if encoded(covers)!=encoded(oracle['covers']):raise ValueError('Omitted, extra, duplicate or noncanonical minimum covers')
    except Exception as exc:issues.append(str(exc))
    return dict(status='PASS_INDEPENDENT_FRETTING_CONTACTS'if not issues else'FAIL',issues=issues,complete=complete,
        scope='Nominal contact coverage only; search refusal is not infeasibility, and coverage does not prove reach, comfort, movement, clean execution or human playability')
