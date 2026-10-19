"""Opt-in source-conditioned palm continuity; no marginal-rate target or defaults.

State is the previous eligible coattack's actual output flag. It resets at track,
section, rest/gap, overlap, grace and excluded/unknown groups. This is written
annotation modeling, not physical muting depth or musical-quality evidence.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
import random
from xml.etree import ElementTree as ET

from artist_profiles import connected_families, context, stable_hash
from palm_mute_method import eligible
from exact_score import extract_score
from technique_edits import transact, enable_property
from technique_strength import released


def state_key(ctx, previous):
    return ctx + '|previous=' + ('start' if previous is None else str(int(previous)))


def prior(previous, event, max_ioi):
    if previous is None or not event['sequence_ok']:
        return None
    if (event['onset_q'] != previous['end_q'] or event['section'] != previous['section']
            or not 0 < event['onset_q'] - previous['onset_q'] <= max_ioi):
        return None
    return previous['value']


def source_events(report, artist, max_ioi_q='1'):
    max_ioi = F(max_ioi_q)
    if max_ioi <= 0:
        raise ValueError('Positive maximum interattack interval required')
    families = connected_families(report['songs'])
    result = []
    for song in report['songs']:
        if song.get('artist') != artist:
            continue
        for track in song['tracks']:
            if not track.get('guitar_or_bass') or not track.get('temporal_relationships_eligible'):
                continue
            groups = defaultdict(list)
            for row in track['rows']:
                groups[F(row['onset_q'])].append(row)
            tied = {ident for chain in track.get('sustain_relationships', {}).get('chains', [])
                    if len(chain.get('members', [])) > 1 for ident in chain['members']}
            endings = defaultdict(list)
            for row in track['rows']:
                endings[row['voice'], row['string'], F(row['onset_q']) + F(row['duration_q'])].append(row['occurrence'])
            for row in track['rows']:
                if row['tie_destination']:
                    tied.add(row['occurrence'])
                    tied.update(endings[row['voice'], row['string'], F(row['onset_q'])])
            grace = {F(n['onset_q']) for n in track.get('grace_rows', [])}
            pitches = [n['midi'] for n in track['rows'] if n['midi'] is not None]
            register = (min(pitches), max(pitches)) if pitches else (None, None)
            previous = None
            for q, all_notes in sorted(groups.items()):
                # Match output masking: do not learn an apparent monophonic
                # opportunity by stripping a simultaneous tied/grace event.
                if q in grace or any(n['tie_destination'] or F(n['duration_q']) <= 0 for n in all_notes):
                    previous = None
                    continue
                notes = [n for n in all_notes if not n['tie_destination']]
                if not notes or any(not eligible(n) or n['occurrence'] in tied for n in notes):
                    previous = None
                    continue
                labels = [bool(n.get('raw_beat_effects', {}).get('palmMute')
                               or n.get('raw_note', {}).get('palmMute')) for n in notes]
                if any(labels) and not all(labels):
                    previous = None
                    continue
                sections = {n.get('section_start') for n in all_notes}
                section = next(iter(sections)) if len(sections) == 1 else ('ambiguous', q)
                sequence_ok = (len(sections) == 1 and not any(n['tie_destination'] for n in all_notes)
                               and q not in grace)
                if previous is not None and any(previous['onset_q'] < g <= q for g in grace):
                    previous = None
                event = dict(onset_q=q, end_q=q + max(F(n['duration_q']) for n in notes),
                             section=section, sequence_ok=sequence_ok)
                previous_value = prior(previous, event, max_ioi)
                result.append(dict(song_id=song['song_id'], family=families[song['song_id']],
                    artist=artist, max_ioi_q=str(max_ioi),
                    partition=song['provisional_partition'],
                    flagged=not (song.get('ai_generated') is False and song.get('is_junk') is False),
                    part_id=track['part_id'], onset_q=str(q),
                    context=context(notes[0], notes, register), previous=previous_value,
                    label=all(labels), sequence_ok=sequence_ok))
                previous = dict(event, value=all(labels)) if sequence_ok else None
    return result


def fit(events, artist, max_ioi_q='1'):
    if F(max_ioi_q) <= 0:
        raise ValueError('Positive maximum interattack interval required')
    if any(e.get('artist') != artist or F(e.get('max_ioi_q', '0')) != F(max_ioi_q) for e in events):
        raise ValueError('Event artist/state-reset configuration differs from requested model')
    train = [e for e in events if e['partition'] == 'development' and not e['flagged']]
    held = [e for e in events if e['partition'] == 'held_out' and not e['flagged']]
    if (not train or {e['family'] for e in train} & {e['family'] for e in held}
            or {e['song_id'] for e in train} & {e['song_id'] for e in held}):
        raise ValueError('Nonempty family-separated development cohort required')
    counts = Counter((e['family'], e['song_id']) for e in train)
    songs = defaultdict(set)
    for family, song in counts:
        songs[family].add(song)
    tables = {name: defaultdict(lambda: [F(0), F(0)]) for name in ('global', 'static', 'state')}
    for e in train:
        weight = F(1, counts[e['family'], e['song_id']] * len(songs[e['family']]))
        for name, key in (('global', '*'), ('static', e['context']),
                          ('state', state_key(e['context'], e['previous']))):
            table = tables[name][key]
            table[0] += weight
            table[1] += weight * e['label']
    return dict(schema='sequence-palm-mute-v1', artist=artist, max_ioi_q=str(F(max_ioi_q)),
                alpha='1/2000', training_songs=sorted({e['song_id'] for e in train}),
                training_families=sorted({e['family'] for e in train}),
                training_sha256=stable_hash(train),
                tables={name: {key: [str(n), str(y)] for key, (n, y) in rows.items()}
                        for name, rows in tables.items()})


def predict(model, ctx, previous, *, stateful=True):
    choices = [('state', state_key(ctx, previous))] if stateful else []
    choices += [('static', ctx), ('global', '*')]
    for name, key in choices:
        if key in model['tables'][name]:
            n, y = map(F, model['tables'][name][key])
            alpha = F(model['alpha'])
            if n <= 0 or not 0 <= y <= n:
                raise ValueError('Invalid sequence model count')
            return float((y + alpha) / (n + 2 * alpha)), name
    raise ValueError('No source support for palm model')


def apply(source, destination, model, artist, freedom, seed=17, *, stateful=True, window=None):
    if isinstance(freedom, bool) or not isinstance(freedom, int) or not 0 <= freedom <= 100:
        raise ValueError('Integer freedom 0-100 required')
    if window is not None:
        if (not isinstance(window,(tuple,list)) or len(window)!=3
            or any(type(x) is not int for x in window)
            or window[0]<0 or not 1<=window[1]<=window[2]):
            raise ValueError('Window requires track index and inclusive positive bar bounds')
    if freedom == 0:
        return dict(**transact(source, destination, {}, {}), all_locked=True)
    if (model.get('schema') != 'sequence-palm-mute-v1' or model.get('artist') != artist
            or not model.get('training_sha256') or F(model.get('max_ioi_q', '0')) <= 0):
        raise ValueError('Same-artist sequence palm model required')
    score = extract_score(source)
    if window is not None and (window[0]>=len(score['tracks'])
        or window[2]>len(score['tracks'][window[0]]['measures'])):
        raise ValueError('Window outside source score')
    counts = Counter(n['note_id'] for t in score['tracks'] for m in t['measures']
                     for v in m['voices'] for e in v for n in e['notes'])
    if any(n != 1 for n in counts.values()):
        raise ValueError('Shared note definitions require occurrence cloning')
    edits, permissions, decisions = {}, {}, []
    max_ioi = F(model['max_ioi_q'])
    for ti, track in enumerate(score['tracks']):
        if window is not None and ti!=window[0]:continue
        if not isinstance(track.get('program'), int) or not 24 <= track['program'] <= 39:
            continue
        groups, pitches = defaultdict(list), []
        section_instance = 0
        for m in track['measures']:
            if m.get('section') is not None:
                section_instance = m['number']
            for vi, voice in enumerate(m['voices']):
                for ei, event in enumerate(voice):
                    for ni, note in enumerate(event['notes']):
                        groups[F(event['onset_q'])].append((note, event, section_instance, f'{ti}:{m["number"]}:{vi}:{ei}:{ni}'))
                        if note['midi'] is not None:
                            pitches.append(note['midi'])
        register = (min(pitches), max(pitches)) if pitches else (None, None)
        previous = None
        for q, group in sorted(groups.items()):
            if window is not None and any(not window[1]<=int(occurrence.split(':')[1])<=window[2]
                                          for n,e,section,occurrence in group):
                previous=None
                continue
            if any(n.get('grace_type') or F(e['duration_q']) <= 0 or not eligible(n)
                   or n.get('tie') or any(p in n['property_names'] for p in ('Muted', 'HarmonicType'))
                   for n, e, section, occurrence in group):
                previous = None
                continue
            sections = {section for n, e, section, occurrence in group}
            event = dict(onset_q=q, end_q=q + max(F(e['duration_q']) for n, e, section, occurrence in group),
                         section=next(iter(sections)) if len(sections) == 1 else ('ambiguous', q), sequence_ok=len(sections) == 1)
            previous_value = prior(previous, event, max_ioi)
            basic = [dict(midi=n['midi'], fret=n['fret'], duration_q=e['duration_q'], bar_offset_q=e['local_onset_q'])
                     for n, e, section, occurrence in group]
            ctx = context(basic[0], basic, register)
            probability, table = predict(model, ctx, previous_value, stateful=stateful)
            selected = random.Random(f'{seed}:palm_mute:{ti}:{q}').random() < probability
            unlocked = released(('palm_mute', ti, str(q)), freedom)
            output_labels = []
            for n, e, section, occurrence in group:
                key = ('note', n['note_id'], 'property')
                permissions[key] = {'PalmMuted'}
                if unlocked:
                    edits[key] = [enable_property('PalmMuted')] if selected else []
                    output_labels.append(selected)
                else:
                    original = ET.fromstring(n['note_xml']).find('./Properties/Property[@name="PalmMuted"]')
                    edits[key] = [] if original is None else [ET.tostring(original, encoding='unicode')]
                    output_labels.append(original is not None and original.find('Enable') is not None)
            actual = all(output_labels) if all(output_labels) or not any(output_labels) else None
            previous = dict(event, value=actual) if event['sequence_ok'] and actual is not None else None
            decisions.append(dict(track=ti, onset_q=str(q), context=ctx, previous=previous_value,
                probability=probability, probability_table=table, proposed_selected=selected,
                actual_selected=actual, released=unlocked, members=[o for n, e, s, o in group]))
    return dict(**transact(source, destination, edits, permissions), decisions=decisions,
                freedom=freedom, seed=seed, stateful=stateful,
                window=list(window) if window is not None else None,
                model_sha256=stable_hash(model),
                limitations=['Written annotation sequence only; no physical muting-depth or quality claim.',
                             'Track/section/grace/exclusion/clock-gap resets; no inferred phrase boundaries.'])
