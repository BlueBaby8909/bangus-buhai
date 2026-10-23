"""Actual command MQTT delivery, device results and restricted TLS identities."""
from dataclasses import replace
import json
from uuid import uuid4
from backend.tests.mqtt_support import BrokerFixture, DatabaseFixture, Probe, eventually
from backend.features.commands.service import CommandService
from backend.features.commands.schemas import CommandRequest
from backend.mqtt.worker import IngestionWorker


class CommandBrokerTests(DatabaseFixture):
    password_auth = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls.broker = BrokerFixture(password_auth=cls.password_auth, command_support=True).start()
            cls.broker_agent = cls.broker.agent
        except BaseException:
            super().tearDownClass(); raise

    @classmethod
    def tearDownClass(cls):
        try: cls.broker.close()
        finally: super().tearDownClass()

    def start(self):
        self.commands = CommandService(self.engine, clock=lambda:self.clock)
        self.worker = IngestionWorker(self.engine, replace(self.broker.settings(),client_id='bb-cmd-'+uuid4().hex), self.service)
        self.addCleanup(self.worker.stop); self.worker.start()
        self.assertTrue(self.worker.ready.wait(10))
        self.probe = Probe(self.broker)
        self.addCleanup(self.probe.close)
        self.base = self.topic.rsplit('/',1)[0]
        self.assertEqual(self.probe.subscribe(self.base+'/cmd'),[1])
        self.assertEqual(self.probe.subscribe(self.base+'/acks'),[1])

    def test_command_delivery_result_commit_duplicate_and_lost_ack(self):
        self.start()
        row = self.commands.create(self.hatchery,self.agent.external_id,self.user,uuid4(),CommandRequest(type='relay.set',desired_on=True))
        eventually(lambda:any(t==self.base+'/cmd' for t,_,_ in self.probe.messages))
        wire = next(p for t,p,_ in self.probe.messages if t==self.base+'/cmd')
        self.assertEqual(json.loads(wire),row['command'])
        eventually(lambda:self.detail(row)['status']=='published')
        result = dict(schema_version=1,device_id=self.agent.external_id,binding_id=str(self.binding),boot_id=str(uuid4()),
            seq=90,capture_uptime_ms=5000,time_quality='synchronized',created_at=self.clock.isoformat().replace('+00:00','Z'),
            command_id=str(row['command_id']),result='applied',reason='applied',observed_on=True)
        committed=[]
        self.probe.received=lambda message: committed.append(self.detail(row)['status']) if message.topic.endswith('/acks') else None
        self.probe.publish(self.base+'/command-results',result)
        eventually(lambda:self.detail(row)['status']=='applied')
        eventually(lambda:any(t.endswith('/acks') for t,_,_ in self.probe.messages))
        self.assertTrue(all(s=='applied' for s in committed))
        # The device lost/ignored its first ACK and resends the SAME immutable event.
        self.probe.publish(self.base+'/command-results',result)
        eventually(lambda:any(t.endswith('/acks') and json.loads(p)['result']=='duplicate' for t,p,_ in self.probe.messages))
        self.assertEqual(len(self.detail(row)['results']),1)

    def detail(self,row):
        return self.commands.detail(self.hatchery,self.agent.external_id,self.user,row['command_id'])

    def test_commands_remain_device_scoped_and_backend_only(self):
        self.start()
        foreign = self.base.replace(self.agent.external_id,'BB-000000000022')+'/cmd'
        sub = self.probe.subscribe(foreign)
        self.assertTrue(sub==[1] or all(r>=128 for r in sub))
        backend = Probe(self.broker,backend=True); self.addCleanup(backend.close)
        marker=b'invalid-wire-permission-marker'
        self.assertLess(backend.publish(self.base+'/cmd',marker),128)
        self.assertLess(backend.publish(foreign,marker),128)
        eventually(lambda:(self.base+'/cmd',marker,False) in self.probe.messages)
        self.assertFalse(any(t==foreign for t,_,_ in self.probe.messages))
        denied = Probe(self.broker); self.addCleanup(denied.close)
        self.assertEqual(denied.publish(self.base+'/cmd',marker),135)

    def test_worker_restart_dispatches_committed_intent(self):
        self.commands = CommandService(self.engine,clock=lambda:self.clock)
        row=self.commands.create(self.hatchery,self.agent.external_id,self.user,uuid4(),CommandRequest(type='relay.auto'))
        self.start()
        # Subscribe can race initial publication. A retry is due five seconds later.
        from datetime import timedelta
        self.clock+=timedelta(seconds=5)
        eventually(lambda:any(t==self.base+'/cmd' for t,_,_ in self.probe.messages))
        self.assertEqual(json.loads(next(p for t,p,_ in self.probe.messages if t.endswith('/cmd')))['command_id'],str(row['command_id']))


class PasswordCommandBrokerTests(CommandBrokerTests):
    password_auth=True

    def test_live_permission_probe_uses_invalid_nonretained_markers(self):
        from backend.mqtt.qualify import qualify
        login=self.broker.authority.write('device-probe-login.json',json.dumps(dict(username=self.agent.external_id,
            password=self.broker.device_password)).encode())
        qualify(self.broker.settings(),login,commands=True)
