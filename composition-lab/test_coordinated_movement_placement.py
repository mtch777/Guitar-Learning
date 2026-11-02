"""Authored coordinated contacts; retained links, original evidence and atomicity."""
from copy import deepcopy
import json
import unittest

import melodic_movement_ownership as movement
from test_melodic_movement_ownership import SONG,TARGET,beat,bar,v2_documents,build_v2,output,set_pitches


PEERS=[f'event:{SONG}:1:2:0:{i}:0' for i in range(3)]

def fixture():
    docs=v2_documents()
    part=docs['track-1.json'];part.update(instrumentId=27,tuning=[59,54,49,44,39,34],frets=24)
    part['measures'][1]=bar([beat(p,tuning=59) for p in (60,61,62)]+[beat()])
    links=[dict(occurrence_ref=a,backing_ref=b) for a,b in zip(PEERS,TARGET)]
    _,lower,_,owned=build_v2(docs,references=None,bindings=links)
    context=movement._original_register_context(lower,owned['source_origin'],PEERS)
    return docs,lower,owned,context

def parameters(pitches):
    result=movement.relation(pitches=list(map(str,pitches)))
    return {k:result[k] for k in ('pitch_class','octave','steps')}


class CoordinatedMovementPlacementTests(unittest.TestCase):
    def test_peer_contact_moves_without_rebinding_and_survives_saved_next_edit(self):
        docs,lower,owned,context=fixture();before=deepcopy(owned);original_context=deepcopy(context)
        changed,contacts=movement._placed_candidate(owned,parameters([60,58,62]),lower,dependent_contexts=[context])
        expected=set_pitches(docs,[60,58,62]);peer=expected['track-1.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]
        peer.update(string=1,fret=4)
        self.assertEqual(output(changed),expected)
        self.assertEqual(contacts[PEERS[1]],dict(string=1,fret=4))
        self.assertEqual(changed['musical_relationships'],owned['musical_relationships'])
        self.assertEqual(changed['owned_parameters'][movement.SLOT]['observations'],owned['owned_parameters'][movement.SLOT]['observations'])
        saved=json.loads(json.dumps(changed));current=movement._realize(saved)
        again,_=movement._placed_candidate(saved,parameters([60,57,62]),current,dependent_contexts=[context])
        later=set_pitches(expected,[60,57,62]);later['track-1.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]['fret']=3
        self.assertEqual(output(again),later)
        self.assertEqual(again['musical_relationships'],owned['musical_relationships'])
        self.assertEqual(owned,before);self.assertEqual(context,original_context)

    def test_ordinary_control_does_not_silently_release_peer_contacts(self):
        _,lower,owned,_=fixture();before=deepcopy(owned)
        with self.assertRaises(ValueError):movement._placed_candidate(owned,parameters([60,58,62]),lower)
        self.assertEqual(owned,before)

    def test_unbound_dependency_and_impossible_placement_refuse_atomically(self):
        _,lower,owned,context=fixture();before=deepcopy(owned)
        unrelated=[f'event:{SONG}:1:1:0:0:0']
        bad=movement._original_register_context(lower,owned['source_origin'],unrelated)
        with self.assertRaisesRegex(ValueError,'existing selected backing link'):
            movement._placed_candidate(owned,parameters([60,58,62]),lower,dependent_contexts=[bad])
        with self.assertRaises(ValueError):
            movement._placed_candidate(owned,parameters([60,-1,62]),lower,dependent_contexts=[context])
        self.assertEqual(owned,before)


if __name__=='__main__':unittest.main()
