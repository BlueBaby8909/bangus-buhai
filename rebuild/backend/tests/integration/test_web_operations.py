"""T16–18 additions use disposable PostgreSQL and synthetic operator sessions."""
import csv
import io
from datetime import timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from backend.tests.mqtt_support import DatabaseFixture
from backend.tests.auth_support import FakeAuth
from backend.core.application import create_app
from backend.core.security import token_hash
from backend.database.models import AuthSession, UserIdentity, Tank, Device, Binding
from backend.features.accounts.service import AccountService
from backend.features.commands.service import CommandService
from backend.features.commands.schemas import CommandRequest
from backend.features.readings.service import ReadingsService
from backend.features.readings.schemas import CreateMeasurement, CorrectMeasurement
from backend.features.readings.export import prepare


class WebOperationsTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.fake=FakeAuth(); self.addCleanup(self.fake.client.close)
        with Session(self.engine) as s, s.begin():
            user=s.get(UserIdentity,self.user);user.provider_issuer=self.fake.settings.issuer;user.provider_subject=self.fake.subject
        self.accounts=AccountService(self.fake.settings,self.engine,self.fake.provider,lambda:self.clock)
        self.client=self.enterContext(TestClient(create_app(service=self.accounts),base_url='http://127.0.0.1',headers={'Origin':self.fake.settings.origins[0]}))
        response=self.client.post('/api/v1/auth/login',json={'email':'operator@example.test','password':'correct-test-password'})
        self.assertEqual(response.status_code,200)
        self.client.headers['X-CSRF-Token']=response.json()['csrf_token']
        self.token=self.client.cookies.get(self.fake.settings.cookie_name)
        self.base=f'/api/v1/hatcheries/{self.hatchery}'
        self.readings=ReadingsService(self.engine,self.fake.settings.token_key,lambda:self.clock)

    def test_background_header_does_not_extend_idle_foreground_still_does(self):
        self.clock+=timedelta(minutes=1)
        response=self.client.get('/api/v1/me',headers={'X-BB-Passive':'1'})
        self.assertEqual(response.status_code,200)
        with Session(self.engine) as s:
            row=s.exec(select(AuthSession).where(AuthSession.token_hash==token_hash(self.token))).one()
            self.assertEqual(row.last_seen_at,self.clock-timedelta(minutes=1))
        self.client.get('/api/v1/me')
        with Session(self.engine) as s:
            row=s.exec(select(AuthSession).where(AuthSession.token_hash==token_hash(self.token))).one()
            self.assertEqual(row.last_seen_at,self.clock)

    def test_overview_latest_current_binding_multiple_devices_and_nulls(self):
        self.process(self.event(measured_at=None,time_quality='unsynchronized'))
        with Session(self.engine) as s, s.begin():
            device=Device(hatchery_id=self.hatchery,external_id='BB-000000000022');s.add(device);s.flush()
            s.add(Binding(hatchery_id=self.hatchery,device_id=device.id,tank_id=self.tank,started_at=self.clock))
        response=self.client.get(self.base+'/tank-summaries')
        self.assertEqual(response.status_code,200,response.text)
        page=response.json();self.assertEqual(page['temperature_stale_after_ms'],60000)
        self.assertEqual(len(page['items'][0]['devices']),2)
        devices={d['device_id']:d for d in page['items'][0]['devices']}
        self.assertEqual(devices[self.agent.external_id]['connectivity'],'unknown')
        self.assertIsNone(devices[self.agent.external_id]['latest']['measured_at'])
        self.assertIsNone(devices['BB-000000000022']['latest'])
        with Session(self.engine) as s,s.begin():s.get(Binding,self.binding).ended_at=self.clock
        page=self.client.get(self.base+'/tank-summaries').json()
        self.assertEqual(len(page['items'][0]['devices']),1)

    def test_overview_pagination_archival_and_scope(self):
        with Session(self.engine) as s,s.begin():
            s.add(Tank(hatchery_id=self.hatchery,name='Later',created_at=self.clock+timedelta(seconds=1),archived_at=self.clock))
        first=self.client.get(self.base+'/tank-summaries?include_archived=true&limit=1').json()
        second=self.client.get(self.base+'/tank-summaries',params={'include_archived':True,'limit':1,'cursor':first['next_cursor']}).json()
        self.assertEqual(second['items'][0]['tank']['name'],'Later')
        self.assertEqual(len(self.client.get(self.base+'/tank-summaries').json()['items']),1)
        self.assertEqual(self.client.get(f'/api/v1/hatcheries/{uuid4()}/tank-summaries').status_code,403)

    def test_export_quotes_formulas_preserves_unknown_and_provenance(self):
        self.process(self.event(measured_at=None,time_quality='unsynchronized'))
        self.readings.create(self.hatchery,self.tank,self.user,CreateMeasurement(request_id=uuid4(),measured_at=self.clock,ph=7.2,notes=' =HYPERLINK("example"),\ntext'))
        response=self.client.get(self.base+'/readings/export')
        self.assertEqual(response.status_code,200,response.text)
        rows=list(csv.DictReader(io.StringIO(response.text)))
        self.assertEqual(len(rows),2)
        manual=next(r for r in rows if r['origin']=='manual');device=next(r for r in rows if r['origin']=='device')
        self.assertTrue(manual['notes'].startswith("' ="));self.assertEqual(manual['version'],'1')
        self.assertEqual(device['measured_at'],'');self.assertEqual(device['ph_source'],'default')
        self.assertEqual(device['ph_validity'],'unverified')
        self.assertEqual(self.client.get(self.base+'/readings/export',params={'tank_id':str(uuid4())}).status_code,404)
        self.assertEqual(self.client.get(self.base+'/readings/export',params={'since':self.clock.isoformat(),'until':(self.clock-timedelta(days=1)).isoformat()}).status_code,422)

    def test_export_snapshot_ignores_intervening_corrections_and_commits(self):
        initial=self.readings.create(self.hatchery,self.tank,self.user,CreateMeasurement(request_id=uuid4(),measured_at=self.clock,ph=7.2))[0]
        generator=prepare(self.readings,self.accounts,self.token,self.hatchery,self.user,self.tank,
            dict(time_basis='received',origin='all',include_voided=True,since=None,until=None))
        header=next(generator)
        self.readings.change(self.hatchery,self.tank,self.user,initial['id'],CorrectMeasurement(expected_version=1,reason='Fix',measured_at=self.clock,ph=8.0),'correct')
        self.readings.create(self.hatchery,self.tank,self.user,CreateMeasurement(request_id=uuid4(),measured_at=self.clock,ph=6.9))
        rows=list(csv.DictReader(io.StringIO(header+''.join(generator))))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['ph_value'],'7.2');self.assertEqual(rows[0]['version'],'1')

    def test_export_revalidates_and_batched_pages(self):
        for i in range(205):
            self.readings.create(self.hatchery,self.tank,self.user,CreateMeasurement(request_id=uuid4(),measured_at=self.clock,ph=7.2))
        content=self.client.get(self.base+'/readings/export').text
        self.assertEqual(len(list(csv.DictReader(io.StringIO(content)))),205)
        generator=prepare(self.readings,self.accounts,self.token,self.hatchery,self.user,self.tank,
            dict(time_basis='received',origin='all',include_voided=True,since=None,until=None))
        next(generator);self.accounts.logout(self.token)
        from backend.features.accounts.errors import AuthError
        with self.assertRaises(AuthError):next(generator)

    def test_latest_command_current_binding_only_no_actuation(self):
        commands=CommandService(self.engine,self.fake.settings.token_key,lambda:self.clock)
        path=self.base+f'/devices/{self.agent.external_id}/commands/latest'
        self.assertIsNone(self.client.get(path).json())
        intent=commands.create(self.hatchery,self.agent.external_id,self.user,uuid4(),CommandRequest(type='relay.auto'))
        response=self.client.get(path);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['command_id'],str(intent['command_id']))
        self.assertEqual(response.json()['status'],'queued');self.assertEqual(response.json()['attempts'],[])
        with Session(self.engine) as s,s.begin():s.get(Binding,self.binding).ended_at=self.clock
        self.assertIsNone(self.client.get(path).json())

    def test_preflight_headers_and_no_auth_bypass(self):
        response=self.client.options(self.base+f'/devices/{self.agent.external_id}/commands',headers={
            'Origin':self.fake.settings.origins[0],'Access-Control-Request-Method':'POST',
            'Access-Control-Request-Headers':'idempotency-key,x-bb-passive,x-csrf-token,content-type'})
        self.assertEqual(response.status_code,200)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(self.base+'/tank-summaries',headers={'X-BB-Passive':'1'}).status_code,401)
