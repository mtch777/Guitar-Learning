"""Shared input/permission/evidence boundary over existing GP edit methods.

No sampling changes and no new technique detector. This checks recorded edits
against actual GPIF/archive data. Independent native playback and musical
acceptance remain separate gates. Source-located records must stay private.
"""
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile

from reference_levers import BEND_PROPERTIES
from technique_edits import strip
from technique_strength import released

REPRESENTATIONS = {
    'bend': 'written_curve', 'finger_vibrato': 'note_marker',
    'hammer_on_from_open': 'directed_open_transition',
    'pull_off_to_open': 'directed_open_transition',
    'palm_mute': 'coattack_annotation',
}
UNITS = {'written_curve': 'note_attack', 'note_marker': 'note_attack',
         'directed_open_transition': 'directed_note_pair',
         'coattack_annotation': 'coattack_group'}
CONTEXT_FIELDS = {
    'continuous_expression': ('duration_q', 'midi', 'fret', 'string', 'cardinality', 'register', 'bar_offset_q'),
    'directed_transition': ('origin', 'destination', 'gap_q'),
    'sequence_context': ('duration_q', 'cardinality', 'register', 'bar_offset_q', 'previous_output_state'),
    'role_harmony': ('tuning', 'duration_q', 'cardinality', 'locked_harmony'),
}
NOTE_FIELDS = ('duration_q', 'midi', 'fret', 'string')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def proposal_context(kind, observed):
    """Whitelist permitted scalar context; target XML/annotations stay outside.

    Comparison reference and provenance are deliberately not inputs here. This
    builder is an opt-in boundary, not a claim every legacy method uses it yet.
    """
    if kind not in CONTEXT_FIELDS or not isinstance(observed, dict):
        raise ValueError('Known context kind and object required')
    result = {}
    for key in CONTEXT_FIELDS[kind]:
        if key not in observed:
            continue
        value = observed[key]
        if key in ('origin', 'destination'):
            if not isinstance(value, dict):raise ValueError('Transition note context required')
            result[key] = {k: deepcopy(value[k]) for k in NOTE_FIELDS if k in value}
        else:
            result[key] = deepcopy(value)
    # Arbitrary nested objects could smuggle raw XML or original target values.
    def field(key, value):
        if key in ('duration_q', 'bar_offset_q', 'gap_q'):
            if type(value) not in (str, int):raise ValueError('Exact rational context required')
            try: valid = F(value) >= 0
            except (ValueError, ZeroDivisionError):valid = False
            if not valid:raise ValueError('Nonnegative rational context required')
        elif key in ('midi', 'fret', 'string', 'cardinality'):
            if type(value) is not int or value < 0 or (key == 'midi' and value > 127):
                raise ValueError('Nonnegative integer note context required')
        elif key == 'previous_output_state':
            if type(value) is not bool:raise ValueError('Boolean generated state required')
        elif key == 'register':
            if value not in ('low', 'middle', 'high'):raise ValueError('Known register required')
        else:raise ValueError('Unsupported context field')
    for key, value in result.items():
        if key in ('origin', 'destination'):
            for k, v in value.items():field(k, v)
        elif key in ('tuning', 'locked_harmony'):
            if not isinstance(value, list) or any(type(v) is not int or not 0 <= v <= 127 for v in value):
                raise ValueError('Explicit locked pitch list required')
        else:field(key, value)
    return result


def request(feature, representation, freedom, support, *, conflicts=()):
    """Describe an executable request or an explicit refusal, not musical truth."""
    if type(freedom) is not int or not 0 <= freedom <= 100:
        raise ValueError('Integer freedom0–100 required')
    if conflicts:
        return dict(status='refused', reason='conflicting_locks', conflicts=list(conflicts))
    if REPRESENTATIONS.get(feature) != representation:
        return dict(status='refused', reason='unsupported_representation')
    if freedom == 0:
        return dict(status='locked', feature=feature, representation=representation,
                    unit=UNITS[representation], freedom=0)
    if not isinstance(support, dict) or support.get('known') is not True:
        return dict(status='refused', reason='unknown_support')
    try:
        if type(support['eligible_mass_q']) not in (str, int):raise ValueError()
        mass = F(support['eligible_mass_q'])
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        raise ValueError('Exact eligible support mass required') from None
    if mass <= 0 or not support.get('denominator_unit') or not support.get('model_sha256'):
        return dict(status='refused', reason='unsupported_evidence')
    return dict(status='supported', feature=feature, representation=representation,
                unit=UNITS[representation], freedom=freedom, support=deepcopy(support))


def _read(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):raise ValueError('Duplicate GP archive members')
        members = {n: archive.read(n) for n in names if n != 'Content/score.gpif'}
        root = ET.fromstring(archive.read('Content/score.gpif'))
        comment = archive.comment
    # Reuse the exact extractor's occurrence mapping, not global note order.
    from exact_score import extract_score
    score = extract_score(path)
    lookup = {}
    for ti, track in enumerate(score['tracks']):
        for measure in track['measures']:
            for vi, voice in enumerate(measure['voices']):
                for ei, event in enumerate(voice):
                    for ni, note in enumerate(event['notes']):
                        key = f'{ti}:{measure["number"]}:{vi}:{ei}:{ni}'
                        lookup[key] = dict(note=note, onset=F(event['onset_q']), duration=F(event['duration_q']))
    return root, members, comment, lookup


def _scope(feature, decision):
    if feature in ('bend', 'finger_vibrato'):
        return [(decision['occurrence'], 'property' if feature == 'bend' else 'tag',
                 set(BEND_PROPERTIES) if feature == 'bend' else {'Vibrato'})]
    if feature == 'palm_mute':
        return [(ident, 'property', {'PalmMuted'}) for ident in decision['members']]
    return [(decision['origin'], 'property', {'HopoOrigin'}),
            (decision['destination'], 'property', {'HopoDestination'})]


def _value(note, domain, names):
    node = ET.fromstring(note['note_xml'])
    container = node.find('Properties') if domain == 'property' else node
    return sorted(ET.tostring(x, encoding='unicode') for x in list(container) if
                  (x.get('name') if domain == 'property' else x.tag) in names) if container is not None else []


def _selected(note, feature, names):
    node = ET.fromstring(note['note_xml'])
    if feature == 'finger_vibrato':
        value = node.findtext('Vibrato')
        return value not in (None, '', 'None')
    marker = 'Bended' if feature == 'bend' else next(iter(names))
    return any(p.get('name') == marker and p.find('Enable') is not None
               for p in node.findall('./Properties/Property'))


def audit_existing_edit(source, output, audit, freedoms, supports, *, method, method_source):
    """Current GPIF check of an existing method audit; no export or model run.

    The support denominator can be global model support; it is named explicitly
    and must not be advertised as a conditional cell count. Only reported audit
    decisions are covered. This does not establish missing opportunities.
    """
    source, output = Path(source), Path(output)
    frozen = (sha(source), sha(output))
    code_seal = sha(method_source)
    if not method or audit.get('sha256') != frozen[1]:raise ValueError('Actual method/output seal required')
    if audit.get('locked_xml_verified') is not True or audit.get('archive_members_verified') is not True:
        raise ValueError('Existing transaction preservation evidence required')
    for feature, amount in freedoms.items():
        decision = request(feature, REPRESENTATIONS.get(feature), amount, supports.get(feature))
        if decision['status'] == 'refused':raise ValueError('Unsupported request: '+decision['reason'])
    before, members, comment, left = _read(source)
    after, other_members, other_comment, right = _read(output)
    if members != other_members or comment != other_comment or set(left) != set(right):
        raise AssertionError('Locked archive/occurrence identity changed')
    permissions, records, units = {}, [], set()
    for index, raw in enumerate(audit.get('decisions', [])):
        feature = raw.get('family', 'palm_mute')
        if feature not in freedoms or freedoms[feature] == 0:
            raise ValueError('Decision outside declared feature scope')
        if type(raw.get('released')) is not bool or type(raw.get('proposed_selected')) is not bool:
            raise ValueError('Explicit release and proposed selection required')
        if freedoms[feature] == 100 and not raw['released']:
            raise AssertionError('Full freedom decision was retained')
        probability = raw.get('probability')
        if type(probability) not in (int, float) or not 0 <= probability <= 1:
            raise ValueError('Known finite annotation probability required')
        scope = _scope(feature, raw)
        if not scope or len({x[0] for x in scope}) != len(scope):raise ValueError('Unique nonempty occurrence scope required')
        unit = (feature, tuple(sorted(x[0] for x in scope)))
        if unit in units:raise ValueError('Duplicate decision unit')
        units.add(unit)
        if feature == 'palm_mute':
            release_key = (feature, raw['track'], str(F(raw['onset_q'])))
            expected = {ident for ident, row in left.items()
                        if int(ident.split(':')[0]) == raw['track'] and row['onset'] == F(raw['onset_q'])
                        and row['duration'] > 0 and not row['note'].get('grace_type')
                        and (row['note'].get('tie') or {}).get('destination') != 'true'}
            if set(raw['members']) != expected:raise ValueError('Incomplete coattack scope')
        elif feature in ('bend', 'finger_vibrato'):
            release_key = (feature, raw['occurrence'])
        else:
            release_key = (feature, raw['origin'], raw['destination'])
            if raw['origin'] not in left or raw['destination'] not in left:raise ValueError('Unknown directed occurrence')
            a, b = left[raw['origin']], left[raw['destination']]
            if (raw['origin'].split(':')[0] != raw['destination'].split(':')[0]
                or a['note']['string'] != b['note']['string']
                or a['onset'] >= b['onset']
                or (feature == 'hammer_on_from_open' and not (a['note']['fret'] == 0 and b['note']['fret'] > 0))
                or (feature == 'pull_off_to_open' and not (a['note']['fret'] > 0 and b['note']['fret'] == 0))):
                raise ValueError('Invalid directed open-string scope')
        if raw['released'] != released(release_key, freedoms[feature]):
            raise AssertionError('Release mask differs from existing deterministic rule')
        bindings = []
        for ident, domain, names in scope:
            if ident not in left or ident not in right:raise ValueError('Unknown output occurrence')
            a, b = left[ident]['note'], right[ident]['note']
            if a['note_id'] != b['note_id']:raise AssertionError('Note definition identity changed')
            if feature == 'palm_mute' and (left[ident]['onset'] != F(raw['onset_q']) or int(ident.split(':')[0]) != raw['track']):
                raise ValueError('Coattack decision identity mismatch')
            if not raw['released'] and _value(a, domain, names) != _value(b, domain, names):
                raise AssertionError('Retained feature changed')
            if raw['released'] and _selected(b, feature, names) != raw['proposed_selected']:
                raise AssertionError('Written result differs from proposed selection')
            permissions.setdefault(('note', a['note_id'], domain), set()).update(names)
            bindings.append(dict(occurrence=ident, domain=domain, fields=sorted(names)))
        records.append(dict(decision=index, feature=feature, unit=UNITS[REPRESENTATIONS[feature]],
            representation=REPRESENTATIONS[feature], support=deepcopy(supports[feature]),
            backoff=raw.get('context_backoff'), released=raw['released'],
            proposed_selected=raw['proposed_selected'], probability=probability, output_scope=bindings,
            coverage=dict(annotation_selection='checked', retained_xml='checked',
                          native_curve_values='pending' if feature == 'bend' else 'not_applicable',
                          native_directed_links='pending' if 'open' in feature else 'not_applicable')))
    if strip(before, permissions) != strip(after, permissions):raise AssertionError('Undeclared score change')
    if not any(freedoms.values()) and source.read_bytes() != output.read_bytes():raise AssertionError('Zero byte lock failed')
    if frozen != (sha(source), sha(output)) or code_seal != sha(method_source):raise AssertionError('Inputs changed during audit')
    return dict(schema='shared-engine-edit-contract-v1', method=method,
        source_sha256=frozen[0], output_sha256=frozen[1], requests=freedoms, decisions=records,
        method_evidence=dict(current_code_sha256=code_seal,
                             historical_run_code_identity='not_established'),
        validation=dict(gpif_scope='current_checked', archive_members='current_checked',
                        native_playback='not_checked_here', musical_acceptance='not_established'),
        limitations=['Only recorded eligible decisions, not exhaustive opportunity recall',
                     'Audit adapter does not change or certify legacy proposal input isolation',
                     'Marker/curve presence checked; native gesture/links/curve values require separate verification'])
