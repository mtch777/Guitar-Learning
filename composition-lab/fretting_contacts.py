"""A bounded contact-coverage relation, not a human-playability certificate.

The same maximum-contact equation evaluates an observed shape and realizes
frets from a cover. No pitch, chord or preferred shape is chosen here.
"""
from itertools import combinations

SCHEMA = 'fretting-contact-coverage/1'


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _required(required):
    if not isinstance(required, list) or not required:
        raise ValueError('At least one explicit active string is required')
    if any(not isinstance(r, dict) or set(r) != {'string', 'fret'}
           or not _integer(r['string']) or not _integer(r['fret']) for r in required):
        raise ValueError('Strings and frets must be nonnegative integers')
    if len({r['string'] for r in required}) != len(required):
        raise ValueError('Each string must occur exactly once')
    return sorted((dict(r) for r in required), key=lambda r: r['string'])


def realize(strings, contacts):
    """Effective fret = maximum positive contact covering each active string.

    Inactive intervening strings cannot silently be assumed muted or safe.
    Open/lower-fret obstruction is detected by comparing this result with the
    required shape. A higher contact may override a lower barre.
    """
    if not isinstance(strings, list) or not strings or any(not _integer(s) for s in strings) or len(set(strings)) != len(strings):
        raise ValueError('Unique nonnegative active strings required')
    if not isinstance(contacts, list):
        raise ValueError('Contacts must be a list')
    active = set(strings)
    result = {s: 0 for s in strings}
    seen = set()
    for c in contacts:
        if not isinstance(c, dict) or set(c) != {'fret', 'first_string', 'last_string'}:
            raise ValueError('Invalid contact fields')
        f, a, b = c['fret'], c['first_string'], c['last_string']
        if not _integer(f, 1) or not _integer(a) or not _integer(b) or a > b:
            raise ValueError('Invalid contact extent')
        if b-a+1 > len(active) or any(s not in active for s in range(a, b+1)):
            raise ValueError('Contact crosses an inactive string')
        key = (f, a, b)
        if key in seen:
            raise ValueError('Duplicate contact')
        seen.add(key)
        for s in range(a, b+1):
            result[s] = max(result[s], f)
    return [dict(string=s, fret=result[s]) for s in sorted(result)]


def analyze(required, max_digits=4, search_limit=100000):
    required = _required(required)
    if not _integer(max_digits, 1) or max_digits > 4:
        raise ValueError('This bounded model uses one to four digits, excluding the thumb')
    if not _integer(search_limit, 1):
        raise ValueError('Positive integer search limit required')
    strings = [r['string'] for r in required]
    frets = {r['string']: r['fret'] for r in required}
    result = dict(schema=SCHEMA, required=required, max_digits=max_digits,
                  search_limit=search_limit, examined=0, minimum_contacts=None,
                  covers=[], human_playability='UNVERIFIED')
    # Every useful contact in a minimum cover must supply at least one required
    # positive fret. Contacts supplying none can be deleted without changing it.
    candidates = []
    for f in sorted(set(frets.values()) - {0}):
        for a in strings:
            for b in strings:
                if b < a or b-a+1 > len(strings):
                    continue
                span = range(a, b+1)
                if any(s not in frets or frets[s] < f for s in span):
                    continue
                if not any(frets[s] == f for s in span):
                    continue
                candidates.append(dict(fret=f, first_string=a, last_string=b))
    for count in range(max_digits+1):
        covers = []
        for cover in combinations(candidates, count):
            if result['examined'] == search_limit:
                result['status'] = 'SEARCH_LIMIT'
                return result  # Never present an incomplete set as all covers.
            result['examined'] += 1
            if realize(strings, list(cover)) == required:
                covers.append(list(cover))
        if covers:
            result.update(status='COVERED', minimum_contacts=count, covers=covers)
            return result
    result['status'] = 'NO_COVER_WITHIN_MODEL'
    return result
