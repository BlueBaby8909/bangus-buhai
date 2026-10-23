"""T14 HTTP, PostgreSQL, dispatch and result integrity in disposable schemas."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from uuid import uuid4, UUID
import sqlalchemy as sa
from sqlmodel import Session, select
from fastapi.testclient import TestClient
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlmodel import SQLModel
from backend.tests.mqtt_support import DatabaseFixture
from backend.tests.auth_support import FakeAuth
from backend.features.accounts.service import AccountService
from backend.core.application import create_app
from backend.features.commands.service import CommandService
from backend.features.commands.schemas import CommandRequest
from backend.features.registry.errors import RegistryError
from backend.database.commands import RelayIntent, CommandAttempt, CommandReceipt
from backend.database.models import DeviceEvent, DeviceConfiguration, Membership, UserIdentity, ReadingChange, Binding


class CommandTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.commands = CommandService(self.engine, clock=lambda: self.clock)
        self.key = uuid4()
        self.body = CommandRequest(type='relay.set', desired_on=True)

    def create(self, **kwargs):
        args = dict(hatchery=self.hatchery, external=self.agent.external_id, actor=self.user, key=self.key, body=self.body)
        return self.commands.create(**(args | kwargs))

    def dispatch(self):
        self.sent = []
        return self.commands.dispatch(lambda wire: self.sent.append(wire) or len(self.sent))

    def result(self, command, outcome='applied', seq=100, **changes):
        payload = dict(schema_version=1, device_id=self.agent.external_id, binding_id=str(self.binding),
            boot_id=str(uuid4()), seq=seq, capture_uptime_ms=5000, time_quality='synchronized',
            created_at=self.clock.isoformat().replace('+00:00', 'Z'), command_id=str(command['command_id']),
            result=outcome, reason='applied' if outcome == 'applied' else 'queued', observed_on=True)
        payload.update(changes)
        return self.process(payload, topic=self.topic.replace('/telemetry', '/command-results'))

    def detail(self, row):
        return self.commands.detail(self.hatchery, self.agent.external_id, self.user, row['command_id'])

    def test_idempotency_and_busy_are_persisted(self):
        row = self.create(); self.assertEqual(row['status'], 'queued')
        self.assertEqual(self.create()['command_id'], row['command_id'])
        for kwargs, code in ((dict(body=CommandRequest(type='relay.auto')), 'idempotency_conflict'),
                             (dict(key=uuid4()), 'command_pending')):
            with self.assertRaises(RegistryError) as raised: self.create(**kwargs)
            self.assertEqual(raised.exception.code, code)
        self.assertEqual((row['command']['expires_at'], row['command']),
                         (self.create()['command']['expires_at'], self.create()['command']))

    def test_concurrent_identical_requests_create_once(self):
        with ThreadPoolExecutor(2) as executor:
            rows = list(executor.map(lambda _: self.create(), range(2)))
        self.assertEqual(rows[0]['command_id'], rows[1]['command_id'])

    def test_concurrent_distinct_requests_only_one_active(self):
        def create(_):
            try: return self.create(key=uuid4())['status']
            except RegistryError as error: return error.code
        with ThreadPoolExecutor(2) as executor: outcomes = list(executor.map(create, range(2)))
        self.assertCountEqual(outcomes, ['queued', 'command_pending'])

    def test_dispatch_retry_puback_and_timeout_are_distinct(self):
        row = self.create()
        first = self.dispatch(); self.assertEqual(len(first), 1)
        self.assertEqual(self.detail(row)['status'], 'queued')
        self.assertEqual(self.dispatch(), [])
        self.commands.published(first[0][1]); self.assertEqual(self.detail(row)['status'], 'published')
        self.clock += timedelta(seconds=5)
        self.assertEqual(len(self.dispatch()), 1)
        self.assertEqual(self.sent[0], row['command'])
        self.clock += timedelta(seconds=55)
        self.assertEqual(self.dispatch(), [])
        detail = self.detail(row)
        self.assertEqual(detail['status'], 'timed_out'); self.assertIsNotNone(detail['timed_out_at'])
        self.create(key=uuid4())  # Expired intent no longer blocks new work.

    def test_late_result_resolves_timeout_and_retains_evidence(self):
        row = self.create(); self.dispatch()
        applied_time = (self.clock + timedelta(seconds=2)).isoformat().replace('+00:00', 'Z')
        self.clock += timedelta(seconds=61)
        self.assertEqual(self.detail(row)['status'], 'timed_out')
        self.assertEqual(self.result(row, created_at=applied_time).disposition, 'stored')
        detail = self.detail(row)
        self.assertEqual(detail['status'], 'applied'); self.assertIsNotNone(detail['timed_out_at'])
        self.assertEqual(len(detail['results']), 1)
        with Session(self.engine) as s: self.assertEqual(s.scalar(sa.select(sa.func.count()).select_from(ReadingChange)), 0)

    def test_result_correlation_and_no_success_before_dispatch(self):
        row = self.create()
        self.assertEqual(self.result(row).reason, 'command_not_dispatched')
        self.dispatch()
        self.assertEqual(self.result(row, observed_on=False).reason, 'command_result_mismatch')
        self.assertEqual(self.result(row, command_id=str(uuid4())).reason, 'command_context_unavailable')
        self.assertEqual(self.result(row, created_at=None, time_quality='unsynchronized').reason, 'command_result_time')
        self.assertEqual(self.result(row, created_at=row['command']['expires_at']).reason, 'command_result_time')

    def test_duplicate_and_reordered_results_do_not_regress(self):
        row = self.create(); self.dispatch()
        boot = str(uuid4())
        self.assertEqual(self.result(row, boot_id=boot).disposition, 'stored')
        self.assertEqual(self.result(row, boot_id=boot).disposition, 'duplicate')
        self.assertEqual(self.result(row, 'accepted', seq=101).disposition, 'stored')
        self.assertEqual(self.detail(row)['status'], 'applied')
        self.assertEqual(len(self.detail(row)['results']), 2)
        self.assertEqual(self.result(row, 'failed', seq=102, reason='output_unavailable').reason, 'command_terminal_conflict')

    def test_rejected_and_interrupted_unsynchronized_results(self):
        row = self.create(); self.dispatch()
        self.assertEqual(self.result(row, 'rejected', created_at=None, time_quality='unsynchronized',
            reason='clock_unsynchronized', observed_on=False).disposition, 'stored')
        self.assertEqual(self.detail(row)['status'], 'rejected')
        row = self.create(key=uuid4()); self.dispatch()
        self.assertEqual(self.result(row, 'failed', seq=101, created_at=None, time_quality='unsynchronized',
            reason='interrupted_by_restart', observed_on=None).disposition, 'stored')

    def test_auto_wire_has_no_desired_state(self):
        row = self.create(body=CommandRequest(type='relay.auto'))
        self.assertNotIn('desired_on', row['command']); self.dispatch()
        self.assertEqual(self.result(row, observed_on=False, reason='applied').disposition, 'stored')

    def test_unconfirmed_or_unassigned_cannot_dispatch(self):
        row = self.create()
        with Session(self.engine) as s, s.begin():
            config = s.get(DeviceConfiguration, self.device)
            config.confirmed_revision, config.confirmed_at = 0, None
        self.assertEqual(self.dispatch(), [])
        self.assertEqual(self.detail(row)['status'], 'timed_out')
        with self.assertRaises(RegistryError): self.create(key=uuid4())

    def test_binding_closed_after_dispatch_still_allows_result(self):
        row = self.create(); self.dispatch()
        with Session(self.engine) as s, s.begin():
            s.get(Binding, self.binding).ended_at = self.clock + timedelta(seconds=2)
        self.clock += timedelta(seconds=3)
        self.assertEqual(self.result(row).disposition, 'stored')
        self.assertEqual(self.detail(row)['status'], 'applied')

    def test_membership_and_foreign_status_denied(self):
        row = self.create()
        with self.assertRaises(RegistryError): self.create(hatchery=uuid4())
        with self.assertRaises(RegistryError): self.commands.detail(self.hatchery, 'BB-000000000000', self.user, row['command_id'])
        with Session(self.engine) as s, s.begin(): s.get(Membership, (self.hatchery, self.user)).active = False
        with self.assertRaises(RegistryError): self.detail(row)

    def test_metadata_and_immutable_intent_receipts(self):
        with self.engine.connect() as c:
            self.assertEqual(compare_metadata(MigrationContext.configure(c), SQLModel.metadata), [])
        row = self.create(); self.dispatch(); self.result(row)
        for sql in ("UPDATE relay_commands SET wire='{}'", 'DELETE FROM relay_commands', 'DELETE FROM command_receipts',
                    'DELETE FROM command_attempts', "UPDATE command_attempts SET submitted_at=submitted_at+interval '1 second'"):
            with self.assertRaises(sa.exc.DatabaseError):
                with self.engine.begin() as c: c.execute(sa.text(sql))

    def test_operator_revocation_before_dispatch_stops_delivery(self):
        row=self.create()
        with Session(self.engine) as s, s.begin(): s.get(UserIdentity,self.user).active=False
        self.assertEqual(self.dispatch(),[])
        with Session(self.engine) as s: self.assertEqual(s.get(RelayIntent,row['command_id']).status,'timed_out')

    def test_commit_failure_never_acknowledges_result(self):
        from unittest.mock import patch
        row = self.create(); self.dispatch()
        dialect = self.engine.dialect
        with patch.object(dialect, 'do_commit', side_effect=RuntimeError('injected')):
            with self.assertRaises(RuntimeError): self.result(row)
        self.assertEqual(self.detail(row)['status'], 'queued')
        self.assertEqual(self.detail(row)['results'], [])

    def test_authenticated_http_csrf_and_validation(self):
        fake = FakeAuth(); self.addCleanup(fake.client.close)
        with Session(self.engine) as s, s.begin():
            user = s.get(UserIdentity, self.user)
            user.provider_issuer, user.provider_subject = fake.settings.issuer, fake.subject
        accounts = AccountService(fake.settings, self.engine, fake.provider, lambda: self.clock)
        client = self.enterContext(TestClient(create_app(service=accounts), base_url='http://127.0.0.1',
            headers={'Origin': fake.settings.origins[0]}))
        url = f'/api/v1/hatcheries/{self.hatchery}/devices/{self.agent.external_id}/commands'
        self.assertEqual(client.post(url, json=self.body.model_dump(), headers={'Idempotency-Key':str(self.key)}).status_code, 401)
        login = client.post('/api/v1/auth/login', json={'email':'operator@example.test','password':'correct-test-password'})
        self.assertEqual(login.status_code, 200)
        from backend.core.security import csrf_token
        headers = {'Idempotency-Key':str(self.key), 'X-CSRF-Token':csrf_token(client.cookies.get(fake.settings.cookie_name))}
        self.assertEqual(client.post(url, json={'type':'relay.set','desired_on':'true'}, headers=headers).status_code, 422)
        self.assertEqual(client.post(url, json={'type':'relay.auto'}, headers={'Idempotency-Key':str(self.key)}).status_code, 403)
        response = client.post(url, json={'type':'relay.auto'}, headers=headers)
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(client.get(url+'/'+response.json()['command_id']).status_code, 200)
