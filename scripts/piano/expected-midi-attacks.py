#!/usr/bin/env python3
"""Independently decode original MIDI notes for round-trip fidelity verification."""
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

import mido


def expected_attacks(path):
    data = mido.MidiFile(str(path))
    ppq = data.ticks_per_beat
    if ppq <= 0:
        raise ValueError('SMPTE MIDI timing is unsupported.')
    events = {}
    for index, track in enumerate(data.tracks):
        tick = 0
        active = defaultdict(deque)
        for message in track:
            tick += message.time
            if message.is_meta:
                continue
            if message.type == 'note_on' and message.velocity > 0:
                active[(message.channel, message.note)].append(tick)
            elif message.type == 'note_off' or (message.type == 'note_on' and message.velocity == 0):
                starts = active[(message.channel, message.note)]
                if not starts:
                    continue
                start = starts.popleft()
                if message.channel == 9 or start >= tick:
                    continue
                key = (message.note, start)
                events[key] = max(events.get(key, tick), tick)
        if any(active.values()):
            raise ValueError(f'Track {index+1} has unterminated MIDI notes.')
    return sorted((dict(midi=pitch, onset=start/ppq, end=end/ppq)
                   for (pitch, start), end in events.items()),
                  key=lambda x: (x['midi'], x['onset']))


if __name__ == '__main__':
    print(json.dumps(expected_attacks(Path(sys.argv[1]))))
