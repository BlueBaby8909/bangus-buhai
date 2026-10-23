"""Transactional admission/quarantine tests with generated public credentials."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from threading import Barrier
from unittest.mock import patch
from uuid import UUID, uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import sqlalchemy as sa
from sqlmodel import Session, SQLModel, select

from backend.database.events import persist_event
from backend.database.migrate import configuration
from backend.database.models import (Binding, Device, DeviceConfiguration, DeviceConfigurationReceipt,
    DeviceEvent, DeviceInventory, Hatchery, IngestionQuarantine, ReadingChange, Tank)
from backend.features.readings.service import ReadingsService
from backend.features.registry.security import digest
from backend.features.registry.service import RegistryService
from backend.mqtt.inspect import page
from backend.mqtt.lease import WorkerBusy, WorkerLease
from backend.mqtt.config import MqttSettings
from backend.mqtt.service import IngestionService
from backend.tests.mqtt_support import DatabaseFixture
from contracts import Acknowledgement, CommandResult, Telemetry, validate_acknowledgement


class IngestionTests(DatabaseFixture):
    def count(self, model):
        with Session(self.engine) as s:
            return s.scalar(sa.select(sa.func.count()).select_from(model))

    def test_stored_then_duplicate_ack_and_one_history_entry(self):
        payload = self.event()
        for expected in ('stored', 'duplicate'):
            result = self.process(payload)
            self.assertEqual(result.disposition, expected)
            ack = Acknowledgement.model_validate_json(result.acknowledgement)
            validate_acknowledgement(ack, Telemetry.model_validate(payload))
            self.assertEqual(ack.result, expected)
        self.assertEqual(self.count(DeviceEvent), 1)
        self.assertEqual(self.count(ReadingChange), 1)

    def test_raw_limits_duplicate_keys_and_invalid_types(self):
        for raw in (b'not JSON', b'[]', b'{' + b' ' * 4096 + b'}', b'{"schema_version":1,"schema_version":1}',
                    json.dumps(self.event(schema_version=True)).encode(), json.dumps(self.event(schema_version=2)).encode(),
                    b'\xff', json.dumps(self.event(seq=True)).encode()):
            with self.subTest(raw=raw[:40]):
                result = self.service.process(self.topic, raw)
                self.assertEqual(result.disposition, 'rejected')
                self.assertIsNone(result.acknowledgement)
        self.assertEqual(self.count(IngestionQuarantine), 0)
        self.assertEqual(self.count(DeviceEvent), 0)

    def test_delivery_and_topic_identity_checks(self):
        for changes in ({'qos': 0}, {'qos': 2}, {'retained': True}):
            self.assertEqual(self.process(**changes).disposition, 'rejected')
        for topic in (self.topic + '/extra', self.topic.replace('rebuild', 'prototype'),
                      self.topic.replace('telemetry', 'status'), self.topic.replace('BB-AABBCC112233', 'BB-000000000000')):
            self.assertEqual(self.process(topic=topic).disposition, 'rejected')

    def test_unknown_device_is_quarantined_without_enrollment(self):
        identity = 'BB-000000000000'
        result = self.process(self.event(device_id=identity), topic=self.topic.replace(self.agent.external_id, identity))
        self.assertEqual(result.reason, 'device_unverified')
        self.assertEqual(result.disposition, 'quarantined')
        self.assertEqual(self.count(Device), 1)
        self.assertEqual(self.count(IngestionQuarantine), 1)
        self.assertEqual(self.count(DeviceEvent), 0)

    def test_unverified_and_expired_inventory_denied(self):
        with Session(self.engine) as s, s.begin():
            s.get(DeviceInventory, self.agent.external_id).verified_at = None
        self.assertEqual(self.process().reason, 'device_unverified')
        with Session(self.engine) as s, s.begin():
            inventory = s.get(DeviceInventory, self.agent.external_id)
            inventory.verified_at = self.clock
            inventory.certificate = 'not a certificate'
        self.assertEqual(self.process(self.event(seq=8)).reason, 'invalid_device_credential')

    def test_unknown_and_foreign_binding_never_reassign(self):
        self.assertEqual(self.process(self.event(binding_id=str(uuid4()))).reason, 'binding_unavailable')
        hatchery, tank, device, binding = [uuid4() for _ in range(4)]
        with Session(self.engine) as s, s.begin():
            s.add(Hatchery(id=hatchery, name='Foreign')); s.flush()
            s.add(Tank(id=tank, hatchery_id=hatchery, name='Foreign'))
            s.add(Device(id=device, hatchery_id=hatchery, external_id='BB-000000000022')); s.flush()
            s.add(Binding(id=binding, hatchery_id=hatchery, tank_id=tank, device_id=device))
        self.assertEqual(self.process(self.event(binding_id=str(binding), seq=8)).reason, 'binding_unavailable')
        with Session(self.engine) as s:
            self.assertEqual(s.get(Binding, self.binding).tank_id, self.tank)

    def test_unconfirmed_desired_revision_quarantined_until_proof(self):
        registry = RegistryService(self.engine, bytes(32), lambda: self.clock)
        with Session(self.engine) as s, s.begin():
            config = s.get(DeviceConfiguration, self.device)
            config.revision = 2; config.document = self.document | {'revision': 2}; config.digest = digest(config.document)
        self.assertEqual(self.process().reason, 'binding_unconfirmed')
        challenge = registry.challenge(self.agent.external_id, 'confirm', 2, digest(self.document | {'revision': 2}), 'test')
        registry.proof(challenge['challenge_id'], self.agent.signature(challenge), 'test')
        self.assertEqual(self.process().disposition, 'stored')
        self.assertEqual(self.count(DeviceConfigurationReceipt), 2)
        self.assertEqual(self.count(IngestionQuarantine), 1)  # Evidence is retained after a later admissible retry.

    def test_capture_start_and_future_boundaries(self):
        with Session(self.engine) as s:
            start = s.get(Binding, self.binding).started_at
        def stamp(value): return value.isoformat().replace('+00:00', 'Z')
        self.assertEqual(self.process(self.event(seq=8, measured_at=stamp(start - timedelta(microseconds=1)))).reason, 'capture_before_binding')
        self.assertEqual(self.process(self.event(seq=9, measured_at=stamp(start))).disposition, 'stored')
        self.assertEqual(self.process(self.event(seq=10, measured_at=stamp(self.clock + timedelta(minutes=5)))).disposition, 'stored')
        self.assertEqual(self.process(self.event(seq=11, measured_at=stamp(self.clock + timedelta(minutes=5, microseconds=1)))).reason, 'future_capture')

    def test_unsynchronized_open_binding_preserves_null_capture(self):
        payload = self.event(measured_at=None, time_quality='unsynchronized')
        self.assertEqual(self.process(payload).disposition, 'stored')
        with Session(self.engine) as s:
            row = s.exec(select(DeviceEvent)).one()
            self.assertIsNone(row.captured_at)
            self.assertEqual(row.payload, payload)
        view = ReadingsService(self.engine, bytes(32)).history(self.hatchery, self.tank, self.user, time_basis='received')
        self.assertIsNone(view['items'][0]['measured_at'])

    def close_binding(self):
        with Session(self.engine) as s, s.begin():
            s.get(Binding, self.binding).ended_at = self.clock

    def test_closed_binding_window_preserves_historical_tank(self):
        self.close_binding()
        with Session(self.engine) as s, s.begin():
            s.get(Device, self.device).archived_at = self.clock
            s.get(Tank, self.tank).archived_at = self.clock
        self.assertEqual(self.process().disposition, 'stored')
        with Session(self.engine) as s:
            self.assertEqual(s.exec(select(DeviceEvent)).one().tank_id, self.tank)
        self.assertEqual(self.process(self.event(seq=8, measured_at=self.clock.isoformat().replace('+00:00', 'Z'))).reason, 'capture_after_binding')
        self.assertEqual(self.process(self.event(seq=9, measured_at=None, time_quality='unsynchronized')).reason, 'closed_binding_unknown_capture')

    def test_missing_old_confirmation_is_not_inferred(self):
        self.close_binding()
        binding = uuid4()
        with Session(self.engine) as s, s.begin():
            s.add(Binding(id=binding, device_id=self.device, hatchery_id=self.hatchery, tank_id=self.tank,
                started_at=self.clock - timedelta(minutes=30), ended_at=self.clock - timedelta(minutes=20)))
        payload = self.event(binding_id=str(binding), measured_at=(self.clock - timedelta(minutes=25)).isoformat().replace('+00:00', 'Z'))
        self.assertEqual(self.process(payload).reason, 'binding_unconfirmed')

    def test_archived_active_target_denied_but_committed_duplicate_acknowledged(self):
        payload = self.event()
        self.assertEqual(self.process(payload).disposition, 'stored')
        with Session(self.engine) as s, s.begin(): s.get(Tank, self.tank).archived_at = self.clock
        self.assertEqual(self.process(payload).disposition, 'duplicate')
        self.assertEqual(self.process(self.event(seq=8)).reason, 'resource_archived')

    def test_changed_content_and_cross_kind_conflict_retained(self):
        self.process()
        changed = self.process(self.event(fw_version='different'))
        result = self.event('result-applied.json', seq=7)
        conflict = self.process(result, topic=self.topic.replace('telemetry', 'command-results'))
        self.assertEqual((changed.reason, conflict.reason), ('event_conflict', 'event_conflict'))
        self.assertEqual(self.count(DeviceEvent), 1)
        self.assertEqual(self.count(IngestionQuarantine), 2)

    def test_new_results_wait_for_t14_command_context(self):
        result = self.process(self.event('result-applied.json'), topic=self.topic.replace('telemetry', 'command-results'))
        self.assertEqual(result.reason, 'command_context_unavailable')
        self.assertIsNone(result.acknowledgement)
        self.assertEqual(self.count(ReadingChange), 0)

    def test_existing_result_duplicate_is_correlated(self):
        payload = self.event('result-applied.json')
        with Session(self.engine) as s, s.begin(): persist_event(s, CommandResult.model_validate(payload))
        result = self.process(payload, topic=self.topic.replace('telemetry', 'command-results'))
        self.assertEqual(result.disposition, 'duplicate')
        validate_acknowledgement(Acknowledgement.model_validate_json(result.acknowledgement), CommandResult.model_validate(payload))

    def test_concurrent_duplicates_and_conflicts(self):
        barrier = Barrier(2)
        def process(payload):
            barrier.wait(); return self.process(payload).disposition
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(sorted(executor.map(process, [self.event(), self.event()])), ['duplicate', 'stored'])
        barrier.reset()
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(process, [self.event(seq=8), self.event(seq=8, fw_version='changed')]))
        self.assertEqual(sorted(outcomes), ['quarantined', 'stored'])
        self.assertEqual(self.count(DeviceEvent), 2)

    def test_quarantine_deduplicates_and_enforces_both_caps(self):
        self.service = IngestionService(self.engine, clock=lambda: self.clock, quarantine_limits=(2, 3))
        self.close_binding()
        def uncertain(seq): return self.event(seq=seq, measured_at=None, time_quality='unsynchronized')
        self.assertEqual(self.process(uncertain(1)).disposition, 'quarantined')
        self.assertEqual(self.process(uncertain(1)).disposition, 'quarantined')
        self.assertEqual(self.count(IngestionQuarantine), 1)
        self.process(uncertain(2))
        self.assertEqual(self.process(uncertain(3)).disposition, 'quarantine_full')
        other = 'BB-000000000099'
        self.assertEqual(self.process(self.event(device_id=other), topic=self.topic.replace(self.agent.external_id, other)).disposition, 'quarantined')
        self.assertEqual(self.process(self.event(device_id=other, seq=8), topic=self.topic.replace(self.agent.external_id, other)).disposition, 'quarantine_full')
        self.assertEqual(self.process(self.event(seq=10)).disposition, 'stored')

    def test_quarantine_capacity_race_is_serialized(self):
        self.service = IngestionService(self.engine, clock=lambda: self.clock, quarantine_limits=(1, 1))
        barrier = Barrier(2)
        def attempt(seq):
            barrier.wait(); return self.process(self.event(seq=seq, binding_id=str(uuid4()))).disposition
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(sorted(executor.map(attempt, (8, 9))), ['quarantine_full', 'quarantined'])
        self.assertEqual(self.count(IngestionQuarantine), 1)

    def test_inspection_pagination_is_read_only_and_payload_opt_in(self):
        for seq in (8, 9, 10): self.process(self.event(seq=seq, binding_id=str(uuid4())))
        first = page(self.engine, limit=2)
        self.assertNotIn('payload', first['items'][0])
        second = page(self.engine, limit=2, cursor=first['next_cursor'], payload=True)
        self.assertEqual(len(second['items']), 1)
        self.assertIn('payload', second['items'][0])
        self.assertEqual(self.count(IngestionQuarantine), 3)

    def test_quarantine_and_receipts_are_immutable(self):
        self.process(self.event(binding_id=str(uuid4())))
        for table in ('ingestion_quarantine', 'device_configuration_receipts'):
            for sql in (f'DELETE FROM {table}', f'UPDATE {table} SET id=id'):
                with self.assertRaises(sa.exc.IntegrityError):
                    with self.engine.begin() as c: c.execute(sa.text(sql))

    def test_rollback_and_database_failure_return_no_outcome(self):
        from backend.mqtt import service as module
        real = module.persist_event
        def fail(s, event):
            real(s, event)
            raise RuntimeError('Injected after insertion')
        with patch.object(module, 'persist_event', side_effect=fail), self.assertRaises(RuntimeError): self.process()
        self.assertEqual(self.count(DeviceEvent), 0)
        self.assertEqual(self.count(ReadingChange), 0)
        with patch.object(module, 'Session', side_effect=sa.exc.OperationalError('private SQL', {}, Exception('private'))):
            with self.assertRaises(sa.exc.OperationalError): self.process()

    def test_lost_ack_and_restart_recover_as_duplicate(self):
        payload = self.event()
        self.assertEqual(self.process(payload).disposition, 'stored')  # Simulate dropping the response.
        service = IngestionService(self.engine, clock=lambda: self.clock)
        self.assertEqual(service.process(self.topic, json.dumps(payload).encode()).disposition, 'duplicate')

    def test_singleton_lease_cannot_be_bypassed_by_host_alias(self):
        first = WorkerLease(self.engine, MqttSettings())
        second = WorkerLease(self.engine, MqttSettings(host='localhost', client_id='different'))
        first.acquire()
        try:
            first.heartbeat()
            with self.assertRaises(WorkerBusy): second.acquire()
        finally: first.close()
        second.acquire(); second.close()

    def test_receipt_owner_foreign_keys(self):
        with self.assertRaises(sa.exc.IntegrityError):
            with Session(self.engine) as s, s.begin():
                s.add(DeviceConfigurationReceipt(device_id=self.device, hatchery_id=uuid4(), binding_id=self.binding,
                    tank_id=self.tank, revision=2, document={}, digest='a'*64, credential_fingerprint='b'*64, confirmed_at=self.clock))

    def test_populated_t12_upgrade_preserves_rows_and_backfills_only_current_proof(self):
        payload = self.event()
        self.assertEqual(self.process(payload).disposition, 'stored')
        with self.engine.begin() as c:
            cfg = configuration(); cfg.attributes['connection'] = c; command.downgrade(cfg, '0004_t12')
            tables = [n for n in sa.inspect(c).get_table_names() if n != 'alembic_version']
            before = {n: c.execute(sa.text(f'SELECT * FROM "{n}"')).mappings().all() for n in tables}
            command.upgrade(cfg, 'head'); command.upgrade(cfg, 'head')
            self.assertEqual(compare_metadata(MigrationContext.configure(c), SQLModel.metadata), [])
            for name in tables:
                self.assertEqual(c.execute(sa.text(f'SELECT * FROM "{name}"')).mappings().all(), before[name])
        self.assertEqual(self.count(DeviceConfigurationReceipt), 1)
        self.assertEqual(self.process(payload).disposition, 'duplicate')

    def test_unconfirmed_current_configuration_is_not_backfilled(self):
        with self.engine.begin() as c:
            cfg = configuration(); cfg.attributes['connection'] = c; command.downgrade(cfg, '0004_t12')
            c.execute(sa.text('UPDATE device_configurations SET confirmed_revision=0'))
            command.upgrade(cfg, 'head')
        self.assertEqual(self.count(DeviceConfigurationReceipt), 0)
        self.assertEqual(self.process().reason, 'binding_unconfirmed')

    def test_history_snapshot_and_provenance_survive_ingestion(self):
        self.process()
        self.process(self.event(seq=8))
        history = ReadingsService(self.engine, bytes(32))
        first = history.history(self.hatchery, self.tank, self.user, limit=1)
        self.process(self.event(seq=9))
        second = history.history(self.hatchery, self.tank, self.user, limit=1, cursor=first['next_cursor'])
        self.assertEqual(second['snapshot_position'], first['snapshot_position'])
        self.assertIsNone(second['next_cursor'])
        self.assertEqual(second['items'][0]['telemetry']['readings']['ph']['source'], 'default')
        self.assertEqual(second['items'][0]['telemetry']['readings']['ph']['validity'], 'unverified')

    def test_admission_serializes_against_reassignment(self):
        payload = self.event(measured_at=None, time_quality='unsynchronized')
        barrier = Barrier(2)
        def ingest(): barrier.wait(); return self.process(payload).disposition
        # Simulate registry's established hatchery lock, not a raw update race.
        def registry_close():
            barrier.wait()
            with Session(self.engine) as s, s.begin():
                s.get(Hatchery, self.hatchery, with_for_update=True)
                s.get(Binding, self.binding).ended_at = self.clock
        with ThreadPoolExecutor(max_workers=2) as executor:
            pending = executor.submit(ingest); other = executor.submit(registry_close)
            outcome = pending.result(); other.result()
        self.assertIn(outcome, ('stored', 'quarantined'))
        self.assertEqual(self.count(DeviceEvent), 1 if outcome == 'stored' else 0)

    def test_actual_commit_failure_returns_no_ack_and_rolls_back(self):
        def fail(session):
            raise RuntimeError('Injected commit failure')
        sa.event.listen(Session, 'before_commit', fail)
        try:
            with self.assertRaises(RuntimeError): self.process()
        finally:
            sa.event.remove(Session, 'before_commit', fail)
        self.assertEqual(self.count(DeviceEvent), 0)
        self.assertEqual(self.count(ReadingChange), 0)

    def test_lease_connection_loss_never_silently_reacquires(self):
        lease = WorkerLease(self.engine, MqttSettings())
        lease.acquire()
        try:
            pid = lease.connection.scalar(sa.text('SELECT pg_backend_pid()'))
            with self.engine.connect() as c:
                self.assertTrue(c.scalar(sa.text('SELECT pg_terminate_backend(:pid)'), {'pid': pid}))
            with self.assertRaises(sa.exc.SQLAlchemyError): lease.heartbeat()
            with self.assertRaises(RuntimeError): lease.heartbeat()
        finally: lease.close()
