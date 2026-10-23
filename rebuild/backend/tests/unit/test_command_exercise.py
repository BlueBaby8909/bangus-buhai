import contextlib
import io
import json
import unittest
from unittest.mock import patch
import httpx
from backend.features.commands.live import exercise


class CommandExerciseTests(unittest.TestCase):
    def run_cycle(self, status='applied'):
        requests=[]; keys={}
        def handle(request):
            if request.method=='POST':
                key=request.headers['Idempotency-Key'];body=json.loads(request.content)
                requests.append((key,body))
                keys.setdefault(key,str(len(keys)+1))
                return httpx.Response(202,json={'command_id':keys[key]})
            return httpx.Response(200,json={'status':status})
        with httpx.Client(base_url='http://127.0.0.1:8001',transport=httpx.MockTransport(handle)) as client:
            with patch('backend.features.commands.live.time.sleep'),contextlib.redirect_stdout(io.StringIO()) as output:
                if status=='applied': exercise(client,'/commands')
                else:
                    with self.assertRaises(RuntimeError): exercise(client,'/commands')
        return requests,output.getvalue()

    def test_single_session_cycles_and_reuses_each_key(self):
        requests,output=self.run_cycle()
        self.assertEqual(len(requests),6)
        for index in (0,2,4): self.assertEqual(requests[index],requests[index+1])
        self.assertEqual([requests[i][1] for i in (0,2,4)],
            [{'type':'relay.set','desired_on':True},{'type':'relay.set','desired_on':False},{'type':'relay.auto'}])
        self.assertIn('API cycle passed',output)

    def test_uncertain_result_stops_before_another_intent(self):
        requests,output=self.run_cycle('timed_out')
        self.assertEqual(len(requests),1)
        self.assertNotIn('API cycle passed',output)
        self.assertIn('timeout does not prove ON or OFF',output)
