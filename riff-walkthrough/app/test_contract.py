import unittest,copy,threading
import server
class TestPrevious(unittest.TestCase):
 def test_previous_not_replaced_by_empty_error(self):
  s=server.Session();s.stages[0].update(status='complete',output={'phrases':[{'phrase':1}],'audio':{'notes':[1]}},applied={'random_seed':'123'})
  e=type('E',(),{'validate':lambda self,x:x})()
  s.begin(1,{},e);prior=copy.deepcopy(s.stages[0]['previous']);s.busy=False;s.stages[0].update(status='error',output={'blocker':'No source','phrases':[]})
  s.begin(1,{},e);self.assertEqual(prior,s.stages[0]['previous']);self.assertEqual(prior['applied'],{'random_seed':'123'})
if __name__=='__main__':unittest.main()
