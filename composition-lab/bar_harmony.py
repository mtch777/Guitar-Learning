"""Bar-level observed harmony candidates; relative evidence, not confidence.

Pure separate analysis output. No files, network, transposition or source mutation.
See BAR_HARMONY.md for the normalized evidence-cell input contract.
"""
from math import isfinite
from fractions import Fraction as Q
from collections import defaultdict, Counter
from musical_tier2 import THEORY_FORMS
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def core_candidates(pcs):
    out = {}
    pcs = set(pcs)
    for root in sorted(pcs):
        relative = {(p - root) % 12 for p in pcs}
        for (kind, form) in THEORY_FORMS:
            if len(form) < 2 or not set(form) <= relative:
                continue
            members = tuple(sorted(((root + i) % 12 for i in form)))
            key = (root, members)
            row = out.setdefault(key, dict(root_pc=root, core_pcs=list(members), kinds=[], missing_pcs=[], basis='complete_simultaneously_observed_core'))
            row['kinds'].append(kind)
    for root in sorted(pcs):
        for (third, name) in ((3, 'minor-third-core'), (4, 'major-third-core')):
            tone = (root + third) % 12
            if tone in pcs and (not any((x['root_pc'] == root and tone in x['core_pcs'] for x in out.values()))):
                members = tuple(sorted((root, tone)))
                out[root, members] = dict(root_pc=root, core_pcs=list(members), kinds=[name], missing_pcs=[], unobserved_fifth_pc=(root + 7) % 12, interpretation_limit='Root-third hypothesis only; inversion or omitted-root reading remains unresolved without corroboration; not a definitive chord', basis='observed_root_third_only_fifth_quality_unestablished')
    return list(out.values())
WEIGHTS = dict(core_persistence=2.0, explained_pitch_duration=2.0, bass_root=1.0, bass_member=0.25, chordal_role=0.75, simultaneous_core=0.5, scale_support=0.5, tonal_center=0.25, third_conflict=-1.0, unsupported_extension_union=-0.5)

def _bars(e, cells, tonal):
    scales = [set(r['pcs']) for r in tonal.get('selected_collections', [])]
    roots = defaultdict(float)
    for r in tonal.get('original_report', {}).get('ranked', []):
        roots[NAMES.index(r['tonic'])] = max(roots[NAMES.index(r['tonic'])], r['score'])
    rootden = sum((max(0.0, v) for v in roots.values()))
    out = []
    for bar in e['bars']:
        a = Q(bar['start_q'])
        b = a + Q(bar['span_q'])
        width = float(b - a)
        slices = [(c, float(min(b, Q(c['end_q'])) - max(a, Q(c['start_q'])))) for c in cells if Q(c['start_q']) < b and Q(c['end_q']) > a]
        pc = Counter()
        bass = Counter()
        role = Counter()
        sounding = unknown = 0.0
        ids = set()
        for (c, d) in slices:
            if c['pcs']:
                sounding += d
            if c['unknown_pitch']:
                unknown += d
            ids.update(c['source_ids'])
            for p in c['pcs']:
                pc[p] += d
            if c['low_pc'] is not None:
                bass[c['low_pc']] += d
            rp = set((p for z in c.get('role_evidence', []) for p in z['pcs']))
            for p in rp:
                role[p] += d
        candidates = core_candidates(pc)
        mass = sum(pc.values())
        bassden = sum(bass.values())
        for h in candidates:
            core = set(h['core_pcs'])
            root = h['root_pc']
            rel = {(p - root) % 12 for p in core}
            simult = sum((d for (c, d) in slices if core <= set(c['pcs']))) / sounding if sounding else 0
            conflict = 0.0
            if 3 in rel and 4 not in rel:
                conflict = pc[(root + 4) % 12] / sounding
            if 4 in rel and 3 not in rel:
                conflict = pc[(root + 3) % 12] / sounding
            if any(('suspended' in k for k in h['kinds'])):
                conflict = max(conflict, max(pc[(root + 3) % 12], pc[(root + 4) % 12]) / sounding)
            terms = dict(core_persistence=sum((pc[p] / sounding for p in core)) / len(core), explained_pitch_duration=sum((pc[p] for p in core)) / mass, bass_root=bass[root] / bassden if bassden else 0, bass_member=sum((bass[p] for p in core)) / bassden if bassden else 0, chordal_role=sum((role[p] / sounding for p in core)) / len(core), simultaneous_core=simult, scale_support=sum((len(core & s) / len(core) for s in scales)) / len(scales) if scales else 0, tonal_center=max(0.0, roots[root]) / rootden if rootden else 0, third_conflict=conflict, unsupported_extension_union=max(0, len(core) - 3) * (1 - simult))
            h.update(label=NAMES[root] + ':' + '/'.join(h['kinds']), terms=terms, score=max(0.0, sum((WEIGHTS[k] * v for (k, v) in terms.items()))), basis='observed_within_bar_simultaneously_or_sequentially', simultaneous_fraction=simult, temporal_only=simult == 0, extra_observed_pcs=sorted(set(pc) - core), confidence=None)
        candidates.sort(key=lambda h: (-h['score'], h['root_pc'], h['kinds']))
        unknown_score = (1 - (candidates[0]['terms']['explained_pitch_duration'] if candidates else 0)) * 2 + unknown / width
        if not candidates:
            unknown_score = 1.0
        denom = sum((h['score'] for h in candidates)) + unknown_score
        for h in candidates:
            h['relative_weight'] = h['score'] / denom if denom else 0
        out.append(dict(bar=bar['bar'], start_q=str(a), end_q=str(b), length_q=str(b - a), status='candidates' if candidates else 'unknown' if sounding or unknown else 'no_pitched_evidence', pitch_class_duration_q=dict(pc), sounding_fraction=sounding / width, unresolved_fraction=unknown / width, no_pitched_evidence_fraction=max(0.0, 1 - sum((d for (c, d) in slices if c['pcs'] or c['unknown_pitch'])) / width), candidates=candidates, unknown_weight=(unknown_score / denom if denom else 1) if sounding or unknown else 0, source_ids=sorted(ids), confidence=None))
    return out

def analyze_bar_harmony(source_bars, cells, tonal=None):
    """Return one row per source bar, preserving rational quarter-note positions.

    Cells must be nonoverlapping and sorted. Gaps mean no pitched evidence,
    not necessarily silence. Inputs are never modified.
    """
    for (rows, start, end) in ((source_bars, 'start_q', None), (cells, 'start_q', 'end_q')):
        previous_end = None
        for row in rows:
            a = Q(row[start])
            b = Q(row[end]) if end else a + Q(row['span_q'])
            if b <= a or (previous_end is not None and a < previous_end):
                raise ValueError('Intervals must be positive, sorted and nonoverlapping')
            if end is None and previous_end is not None and (a != previous_end):
                raise ValueError('Source bars must be contiguous')
            previous_end = b
    for cell in cells:
        if any((not isinstance(p, int) or not 0 <= p < 12 for p in cell['pcs'])):
            raise ValueError('pcs must contain pitch classes 0..11')
        if len(cell['pcs']) != len(set(cell['pcs'])):
            raise ValueError('Each cell must contain unique pitch classes')
        if cell['low_pc'] is not None and cell['low_pc'] not in cell['pcs']:
            raise ValueError('Lowest pitch class must be observed')
        for evidence in cell.get('role_evidence', []):
            if not set(evidence['pcs']) <= set(cell['pcs']):
                raise ValueError('Role pitch classes must be observed in the same cell')
    for collection in (tonal or {}).get('selected_collections', []):
        if any(type(p) is not int or not 0 <= p < 12 for p in collection['pcs']):
            raise ValueError('Tonal pitch classes must be 0..11')
    for rank in (tonal or {}).get('original_report', {}).get('ranked', []):
        if rank['tonic'] not in NAMES or not isinstance(rank['score'], (int, float)) or not isfinite(rank['score']):
            raise ValueError('Tonal ranking requires a supported tonic and finite score')
    return _bars({'bars': source_bars}, cells, tonal or {})
