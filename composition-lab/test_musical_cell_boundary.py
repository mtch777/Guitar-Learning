"""No result pitches, raw score or physical choices enter the T3 control packet."""
import unittest
from qa_isolation_harness import validate_request


class MusicalCellBoundaryTests(unittest.TestCase):
    def test_only_named_later_instance_and_bounded_phase_release_enter(self):
        good=dict(context_policy='source_musical_cell_phase',variation=100,instance=1,phase=1,seed=0)
        for level in (0,50,100):
            validate_request('musical_cell_phase',dict(good,variation=level))
        for key,value in [('pitches',[60,61]),('source','source.json'),('contacts',[]),('lower_tier',{})]:
            with self.assertRaises(ValueError):validate_request('musical_cell_phase',dict(good,**{key:value}))
        for key,value in [('variation',101),('variation',True),('variation',50.0),('instance',0),('phase',3),('seed',True)]:
            with self.assertRaises(ValueError):validate_request('musical_cell_phase',dict(good,**{key:value}))


if __name__=='__main__':unittest.main()
