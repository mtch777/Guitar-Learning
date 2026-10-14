"""Occurrence-addressed GPIF note editing, without mutating shared definitions.

A GPIF Note belongs to a Beat; Beats belong to Voices, Voices to Bars, and
Bars are referenced by each MasterBar. A source definition can have many uses.
Clone the ancestor chain for edited occurrences, leaving other uses untouched.
"""
from copy import deepcopy
from collections import Counter


def _refs(node, tag):
    child=node.find(tag)
    if child is None: raise ValueError(f'Missing {tag} reference')
    return child, (child.text or '').split()


def apply_occurrence_edits(root, source_score, track_index, proposed, write_note):
    """proposed maps (measure_index, voice_index, event_index, note_index)
    to (midi, string, fret). All indices are zero-based and refer to the parsed
    score. Every touched occurrence receives a private note definition.
    """
    if not proposed: return {'changed_note_occurrences':0,'cloned_notes':0,'cloned_beats':0,'cloned_voices':0,'cloned_bars':0}
    containers={n:root.find(n) for n in ('Bars','Voices','Beats','Notes')}
    if any(x is None for x in containers.values()):raise ValueError('Incomplete GPIF definition tables')
    lookup={name:{x.get('id'):x for x in parent} for name,parent in containers.items()}
    next_ids={name:max([int(x) for x in m if x.isdigit()] or [-1])+1 for name,m in lookup.items()}
    counts=Counter()
    def clone(name, old):
        new=deepcopy(lookup[name][old]); nid=str(next_ids[name]);next_ids[name]+=1
        new.set('id',nid);containers[name].append(new);lookup[name][nid]=new
        counts[name]+=1
        return nid,new
    grouped={}
    for (mi,vi,ei,ni),position in proposed.items():
        if not 0<=mi<len(source_score['tracks'][track_index]['measures']):raise IndexError('measure')
        ev=source_score['tracks'][track_index]['measures'][mi]['voices'][vi][ei]
        if not 0<=ni<len(ev['notes']):raise IndexError('note')
        grouped.setdefault(mi,{}).setdefault(vi,{}).setdefault(ei,{})[ni]=position
    masters=root.findall('./MasterBars/MasterBar')
    edited=0
    for mi,voices in sorted(grouped.items()):
        mb=masters[mi];bars_ref,bars=_refs(mb,'Bars');old_bar=bars[track_index]
        new_bar,bar=clone('Bars',old_bar);bars[track_index]=new_bar;bars_ref.text=' '.join(bars)
        for vi,events in sorted(voices.items()):
            voice_ref,voice_ids=_refs(bar,'Voices');old_voice=voice_ids[vi]
            new_voice,voice=clone('Voices',old_voice);voice_ids[vi]=new_voice;voice_ref.text=' '.join(voice_ids)
            beat_ref,beat_ids=_refs(voice,'Beats')
            for ei,notes in sorted(events.items()):
                old_beat=beat_ids[ei];new_beat,beat=clone('Beats',old_beat)
                beat_ids[ei]=new_beat
                note_ref,note_ids=_refs(beat,'Notes')
                for ni,position in sorted(notes.items()):
                    new_note,note=clone('Notes',note_ids[ni]);note_ids[ni]=new_note
                    write_note(note,*position);edited+=1
                note_ref.text=' '.join(note_ids)
            beat_ref.text=' '.join(beat_ids)
    return {'changed_note_occurrences':edited,'cloned_notes':counts['Notes'],
            'cloned_beats':counts['Beats'],'cloned_voices':counts['Voices'],'cloned_bars':counts['Bars']}