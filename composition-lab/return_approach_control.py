"""Develop an approach inside an existing source-labelled thematic return.

This composes existing operators. Source markers choose the search boundary;
discovery supplies pitches and interpretations. The existing T5 material recall
remains live, without claiming a new melodic link to the earlier occurrence.
"""
from copy import deepcopy

import approach_discovery_control as discovery
import musical_support_material as material
import section_arrangements as sections
import support_material_uses as uses
import thematic_return as theme
from source_fact_tier1 import project_documents


def source_section(documents, return_scope):
    """Require an explicit, consistent enclosing source marker interval.

    Agreement on every captured track is a conservative supported-input limit,
    not a claim that real music requires repeated annotations on every part.
    Track identity comes from partId and capture identity, never list position.
    """
    first, last = return_scope['first_bar'], return_scope['last_bar']
    if type(first) is not int or type(last) is not int or not 1 <= first <= last:
        raise ValueError('A complete positive return scope is required')
    metadata = documents.get('metadata.json', {})
    if any(k not in metadata for k in ('songId', 'revisionId')):
        raise ValueError('Source capture identity is required for section annotations')
    witnesses = []; identities = set(); consensus = None
    for name, track in documents.items():
        if not name.startswith('track-') or not name.endswith('.json'):
            continue
        part = track.get('partId')
        if type(part) is not int or part < 0 or name != f'track-{part}.json' or part in identities:
            raise ValueError('Unambiguous source part identity is required')
        if any(track.get(k) != metadata[k] for k in ('songId', 'revisionId')):
            raise ValueError('Section annotations belong to another song or revision')
        identities.add(part)
        bars = track.get('measures')
        if type(bars) is not list or last > len(bars):
            raise ValueError('Every captured track must cover the complete return')
        markers = []
        for index, bar in enumerate(bars, 1):
            if 'marker' not in bar:
                continue
            marker = bar['marker']
            if type(marker) is not dict or type(marker.get('text')) is not str or not marker['text'].strip():
                raise ValueError('Section marker text is missing or ambiguous')
            markers.append((index, marker['text']))
        preceding = [(bar, text) for bar, text in markers if bar <= first]
        if not preceding:
            raise ValueError('No source-labelled section encloses the return')
        start, label = preceding[-1]
        following = next((bar for bar, _ in markers if bar > start), len(bars)+1)
        if last >= following:
            raise ValueError('Return crosses a source-labelled section boundary')
        signature = (start, following-1, label)
        if consensus is not None and signature != consensus:
            raise ValueError('Captured tracks disagree on the enclosing source section')
        consensus = signature
        witnesses.append(dict(part_id=part, marker_ref=f'{name}#/measures/{start-1}/marker/text',
            end_ref=(f'{name}#/measures/{following-1}/marker/text' if following <= len(bars) else f'{name}#/measures'),
            ending='next_marker' if following <= len(bars) else 'score_end'))
    if not witnesses or not set(return_scope['parts']) <= identities:
        raise ValueError('Source tracks for the return are missing')
    return dict(first_bar=consensus[0], last_bar=consensus[1], label=consensus[2],
                witnesses=sorted(witnesses, key=lambda r: r['part_id']))


def _check_extension(before, after, selected, use_id):
    """Protect historical authority, not only the notes it reconstructs."""
    if set(after) != set(before):
        raise ValueError('Approach extension changed the material model fields')
    allowed_schema = {before['schema']}
    if before['schema'] == uses.SCHEMA:
        allowed_schema.add(uses.APPROACH_SCHEMA)
    if after['schema'] not in allowed_schema:
        raise ValueError('Approach extension changed an unrelated schema')
    for key in ('materials', 'slots', 'uses'):
        if len(after[key]) != len(before[key])+1 or after[key][:-1] != before[key]:
            raise ValueError('Approach extension must preserve every existing material, slot and use')
    for key in before.keys()-{'schema', 'lower_tier', 'materials', 'slots', 'uses'}:
        if after[key] != before[key]:
            raise ValueError('Approach extension changed an existing relationship or observation')
    scope = dict(parts=[selected['part_id']], first_bar=selected['bars'][0], last_bar=selected['bars'][1])
    new_use = after['uses'][-1]
    if (new_use['id'] != use_id or new_use['slot_ref'] != len(before['slots'])
            or new_use['material_ref'] != len(before['materials'])
            or after['slots'][-1]['scope'] != scope or after['materials'][-1]['scope'] != scope):
        raise ValueError('New approach ownership does not match the complete discovered run')
    if after['lower_tier'] != material._remove(before['lower_tier'], [scope]):
        raise ValueError('Approach extension changed lower relationships outside its ownership transfer')


def _embed(upper, t3):
    """Reinstall existing higher owners without replacing their choices."""
    out = deepcopy(upper); child = deepcopy(t3)
    for owner in out['lower_tier']['choices']:
        matches = [u for u in child['uses'] if u['id'] == owner['allocation']['use_id']]
        if len(matches) != 1:
            raise ValueError('Existing allocation lost its stable material-use identity')
        matches[0].pop('material_ref'); matches[0].pop('expression')
    out['lower_tier']['lower_tier'] = child
    if sections.expand(theme.expand(out)) != t3:
        raise ValueError('Embedding changed an existing section or thematic obligation')
    return out


def prepare(upper):
    """Return original/changed T5 and T3 models using the existing approach.

    No caller-supplied artist, part, bar, pitch or target sequence. Failure leaves
    the complete input untouched; no applicable approach is a retained outcome.
    """
    frozen = deepcopy(upper)
    t3 = sections.expand(theme.expand(upper))
    relationship = upper['relationship']
    matches = [u for u in t3['uses'] if u['id'] == relationship['return_use']]
    if len(matches) != 1:
        raise ValueError('A stable return-use identity is required')
    before = uses.reconstruct(t3, {'variation': 0})
    section = source_section(project_documents(before), t3['slots'][matches[0]['slot_ref']]['scope'])
    scope = {k: section[k] for k in ('first_bar', 'last_bar')}
    result = discovery.prepare_first(t3, scope=scope)
    if upper != frozen:
        raise AssertionError('Approach preparation mutated its complete input')
    result = dict(result, section=section, scope_basis='existing_return_enclosing_source_marker',
        live_reference_scope='Existing T5 material choice only; no new melodic-reference relationship')
    if result['status'] != 'PREPARED':
        return result
    row = result['selected']
    if not scope['first_bar'] <= row['bars'][0] <= row['bars'][1] <= scope['last_bar']:
        raise ValueError('Selected approach is outside the source-labelled return section')
    original_t3, changed_t3 = result['original'], result['changed']
    for value in (original_t3, changed_t3):
        _check_extension(t3, value, row, result['use_id'])
    expected = deepcopy(original_t3)
    if expected['uses'][-1].get('approach_mode') != 'original':
        raise ValueError('The new owner must first represent the unchanged approach')
    expected['uses'][-1]['approach_mode'] = 'flip'
    if changed_t3 != expected:
        raise ValueError('Changed preparation must alter only the new approach direction')
    original, changed = _embed(upper, original_t3), _embed(upper, changed_t3)
    if theme.reconstruct(original, {'variation': 0}) != before:
        raise ValueError('Approach ownership changed the complete current-zero source')
    # The approach candidate already checked its complete T3 inverse. Exact
    # embedding above preserves all higher owners; independent composed QA is
    # responsible for the changed T5 proof without repeating it during prepare.
    if upper != frozen:
        raise AssertionError('Composed approach preparation mutated its input')
    return dict(result, original=original, changed=changed,
                original_t3=original_t3, changed_t3=changed_t3)
