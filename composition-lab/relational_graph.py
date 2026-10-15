"""Occurrence-level rational graph. Interpretations never replace observations.

Membership edges use group nodes rather than quadratic track/bar cliques.
NEXT_IN_VOICE joins consecutive onset groups (including rests), not chord notes.
OVERLAPS is a half-open interval relation; ties require explicit source markings.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction


def build_graph(score, hypotheses=()):
    nodes, edges, warnings = {}, set(), []
    voices = defaultdict(list)
    timed = []
    signatures = defaultdict(list)
    relative_signatures = defaultdict(list)

    def group(kind, key, **data):
        gid = kind + ':' + str(key)
        nodes.setdefault(gid, dict(kind=kind, **data))
        return gid

    for track in score['tracks']:
        ti = track['index']
        tg = group('track', ti, observation=deepcopy({k:v for k,v in track.items() if k != 'measures'}))
        section = None
        for mi, measure in enumerate(track['measures']):
            mg = group('measure', (ti, mi), onset_q=measure['onset_q'], meter=measure['time_signature'])
            if measure.get('section'):
                section = group('section', (ti, mi), label=measure['section'], provenance='source_annotation')
            for vi, voice in enumerate(measure['voices']):
                vg = group('voice', (ti, vi))
                motif = []
                for ei, beat in enumerate(voice):
                    bid = f't{ti}:m{mi}:v{vi}:b{ei}'
                    nodes[bid] = dict(kind='beat', observation=deepcopy(beat))
                    for relation,target in [('SAME_TRACK',tg),('IN_VOICE',vg),('SAME_MEASURE',mg)]:
                        edges.add((bid,relation,target))
                    if section: edges.add((bid,'IN_SECTION',section))
                    onset, duration = Fraction(beat['onset_q']), Fraction(beat['duration_q'])
                    if duration <= 0:
                        raise ValueError('Non-positive duration; grace notes need explicit modeling')
                    members = []
                    for ni, note in enumerate(beat['notes']):
                        nid = bid + f':n{ni}'
                        nodes[nid] = dict(kind='note', track=ti, voice=vi, measure=mi,
                                          observation=deepcopy(note))
                        members.append(nid)
                        timed.append((onset, onset + duration, nid))
                        for relation, target in [('SAME_TRACK', tg), ('IN_VOICE', vg), ('SAME_MEASURE', mg), ('SAME_BEAT', bid)]:
                            edges.add((nid, relation, target))
                        if section:
                            edges.add((nid, 'IN_SECTION', section))
                    voices[ti, vi].append((onset, members or [bid]))
                    pitches = tuple(n['midi'] for n in beat['notes'])
                    motif.append((str(Fraction(beat['local_onset_q'])), str(duration), pitches))
                if motif and any(p for _, _, p in motif):
                    # Exact bar repetition; no claim of perceptual motif equivalence.
                    signatures[tuple(motif)].append(mg)
                    if all(p is not None for _,_,ps in motif for p in ps):
                        anchor=next(p for _,_,ps in motif for p in ps)
                        relative=tuple((s,d,tuple(p-anchor for p in ps)) for s,d,ps in motif)
                        relative_signatures[relative].append(mg)

    for sequence in voices.values():
        sequence.sort(key=lambda x:x[0])
        groups = defaultdict(list)
        for onset, members in sequence:
            groups[onset].extend(members)
        ordered = sorted(groups)
        for a, b in zip(ordered, ordered[1:]):
            for left in groups[a]:
                for right in groups[b]:
                    edges.add((left, 'NEXT_IN_VOICE', right))
    active = []
    for start, end, nid in sorted(timed):
        active = [(s,e,n) for s,e,n in active if e > start]
        for s,e,other in active:
            edges.add((other, 'OVERLAPS', nid))
            if s == start:
                edges.add((other, 'SIMULTANEOUS', nid))
        active.append((start,end,nid))

    by_endpoint = defaultdict(list)
    for start, end, nid in sorted(timed):
        node = nodes[nid]; note = node['observation']
        key = (node['track'], node['voice'], note.get('string'), note.get('midi'))
        tie = note.get('tie') or {}
        if tie.get('destination') == 'true':
            candidates = by_endpoint[key, start]
            if len(candidates) == 1:
                edges.add((candidates[0], 'SUSTAINS_INTO', nid))
            else:
                warnings.append(dict(note=nid, issue='unresolved_tie', candidates=candidates[:]))
        if tie.get('origin') == 'true':
            by_endpoint[key, end].append(nid)
    for measures in signatures.values():
        for repeated in measures[1:]:
            edges.add((repeated, 'REPEATS', measures[0]))
    for measures in relative_signatures.values():
        for repeated in measures[1:]:
            edges.add((repeated,'MOTIF_OF',measures[0]))
    for i, hypothesis in enumerate(hypotheses):
        # Caller supplies separate root/quality/inversion/bass/NCT/role/phrase evidence.
        hid = group('hypothesis', i, evidence=deepcopy(hypothesis))
        for member in hypothesis.get('members', []):
            if member not in nodes:
                raise ValueError('Unknown hypothesis member: ' + member)
            edges.add((member, 'HAS_HYPOTHESIS', hid))
            if hypothesis.get('kind') in ('phrase','harmony','role'):
                edges.add((member,'IN_'+hypothesis['kind'].upper()+'_HYPOTHESIS',hid))
    return dict(schema='relational-music-v1', nodes=nodes,
                edges=[dict(source=a, relation=r, target=b) for a,r,b in sorted(edges)],
                warnings=warnings)
