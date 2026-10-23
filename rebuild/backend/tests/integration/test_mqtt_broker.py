"""Real disposable broker, mTLS/ACL and worker-to-PostgreSQL integration."""
import json
import dataclasses
import socket
import ssl
import tempfile
from unittest.mock import patch

import paho.mqtt.client as mqtt
import sqlalchemy as sa
from sqlmodel import Session, select

from backend.database.models import DeviceEvent, IngestionQuarantine, ReadingChange
from backend.mqtt.lease import WorkerBusy
from backend.mqtt.worker import IngestionWorker
from backend.tests.mqtt_support import (BrokerFixture, CertificateAuthority, DatabaseFixture,
    Probe, eventually)
from contracts import Acknowledgement, QuarantineReceipt, Telemetry, validate_acknowledgement


class BrokerTests(DatabaseFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls.broker = BrokerFixture().start()
            cls.broker_agent = cls.broker.agent
        except BaseException:
            super().tearDownClass(); raise

    @classmethod
    def tearDownClass(cls):
        try: cls.broker.close()
        finally: super().tearDownClass()

    def worker(self):
        settings = dataclasses.replace(self.broker.settings(), client_id='bb-test-' + self.schema[-32:])
        worker = IngestionWorker(self.engine, settings, self.service)
        self.addCleanup(worker.stop)
        worker.start()
        self.assertTrue(worker.ready.wait(10), dict(worker.counters))
        return worker

    def probe(self, **options):
        probe = Probe(self.broker, **options)
        self.addCleanup(probe.close)
        return probe

    def rows(self, model):
        with Session(self.engine) as s:
            return s.scalar(sa.select(sa.func.count()).select_from(model))

    def test_actual_mqtt_commits_before_ack_and_retries_once(self):
        self.worker()
        probe = self.probe(protocol=mqtt.MQTTv311)
        self.assertEqual(probe.subscribe(self.topic.replace('telemetry', 'acks')), [1])
        committed_at_ack = []
        probe.received = lambda message: committed_at_ack.append(self.rows(DeviceEvent))
        payload = self.event()
        probe.publish(self.topic, payload)
        eventually(lambda: len(probe.messages) == 1)
        validate_acknowledgement(Acknowledgement.model_validate_json(probe.messages[0][1]), Telemetry.model_validate(payload))
        self.assertEqual(committed_at_ack, [1])
        self.assertEqual(json.loads(probe.messages[0][1])['result'], 'stored')
        probe.publish(self.topic, payload)
        eventually(lambda: len(probe.messages) == 2)
        self.assertEqual(json.loads(probe.messages[-1][1])['result'], 'duplicate')
        self.assertEqual(self.rows(DeviceEvent), 1)
        self.assertEqual(self.rows(ReadingChange), 1)
        self.assertFalse(any(message[2] for message in probe.messages))

    def test_lost_ack_then_worker_restart_recovers_duplicate(self):
        worker = self.worker()
        probe = self.probe()
        payload = self.event()
        probe.publish(self.topic, payload)  # No ACK subscription: application response is lost.
        eventually(lambda: self.rows(DeviceEvent) == 1)
        worker.stop()
        replacement = self.worker()
        self.assertTrue(replacement.ready.is_set())
        probe.subscribe(self.topic.replace('telemetry', 'acks'))
        probe.publish(self.topic, payload)
        eventually(lambda: bool(probe.messages))
        self.assertEqual(json.loads(probe.messages[-1][1])['result'], 'duplicate')
        self.assertEqual(self.rows(DeviceEvent), 1)

    def test_processing_outage_withholds_ack_and_recovers(self):
        worker = self.worker()
        probe = self.probe(); probe.subscribe(self.topic.replace('telemetry', 'acks'))
        with patch.object(self.service, 'process', side_effect=sa.exc.OperationalError('private', {}, Exception('secret'))):
            probe.publish(self.topic, self.event())
            eventually(lambda: worker.counters['processing_unavailable'] >= 1)
            self.assertEqual(probe.messages, [])
            self.assertEqual(self.rows(DeviceEvent), 0)
        # Broker redelivery and an application retry are both safe.
        probe.publish(self.topic, self.event())
        eventually(lambda: bool(probe.messages), timeout=15)
        self.assertEqual(self.rows(DeviceEvent), 1)

    def test_invalid_and_quarantined_messages_receive_no_success_ack(self):
        worker = self.worker()
        probe = self.probe(); probe.subscribe(self.topic.replace('telemetry', 'acks'))
        probe.publish(self.topic, b'not JSON')
        eventually(lambda: worker.counters['invalid_json'] == 1)
        from uuid import uuid4
        probe.publish(self.topic, self.event(binding_id=str(uuid4())))
        eventually(lambda: self.rows(IngestionQuarantine) == 1)
        self.assertEqual(probe.messages, [])
        probe.publish(self.topic, self.event(seq=8))
        eventually(lambda: bool(probe.messages))
        self.assertEqual(json.loads(probe.messages[-1][1])['result'], 'stored')

    def test_quarantine_receipt_after_commit_retry_and_next_reading(self):
        import hashlib
        self.worker()
        probe = self.probe()
        receipts = self.topic.replace('telemetry', 'quarantine-receipts')
        probe.subscribe(receipts)
        probe.subscribe(self.topic.replace('telemetry', 'acks'))
        raw = json.dumps(self.event(binding_id='11111111-1111-4111-8111-111111111111')).encode()
        # The receipt callback observes the database independently of the worker.
        committed = []
        probe.received = lambda message: committed.append(self.rows(IngestionQuarantine))
        probe.publish(self.topic, raw)
        eventually(lambda: len(probe.messages) == 1)
        a = QuarantineReceipt.model_validate_json(probe.messages[0][1])
        self.assertEqual(committed, [1])
        self.assertEqual(a.payload_sha256, hashlib.sha256(raw).hexdigest())
        self.assertFalse(probe.messages[0][2])
        probe.publish(self.topic, raw)  # Lost response simulation: same candidate, same custody.
        eventually(lambda: len(probe.messages) == 2)
        self.assertEqual(a.quarantine_id, json.loads(probe.messages[1][1])['quarantine_id'])
        probe.publish(self.topic, self.event(seq=8))
        eventually(lambda: len(probe.messages) == 3)
        self.assertEqual(json.loads(probe.messages[2][1])['result'], 'stored')
        self.assertEqual(self.rows(DeviceEvent), 1)

    def test_quarantine_receipt_acl_is_backend_only_and_device_scoped(self):
        probe = self.probe(client_id='BB-INGESTOR')
        own = self.topic.replace('telemetry', 'quarantine-receipts')
        foreign = own.replace(self.agent.external_id, 'BB-000000000022')
        probe.subscribe(own)
        probe.subscribe(foreign)
        self.assertEqual(probe.publish(own, b'forged'), 135)
        backend = self.probe(backend=True)
        backend.publish(foreign, b'foreign')
        backend.publish(own, b'own')
        eventually(lambda: len(probe.messages) >= 1)
        self.assertEqual([(topic, payload) for topic, payload, _ in probe.messages], [(own, b'own')])

    def test_device_acl_uses_certificate_not_spoofed_client_id(self):
        self.worker()
        probe = self.probe(client_id='BB-000000000022')
        payload = self.event()
        self.assertEqual(probe.publish(self.topic, payload), 0)
        eventually(lambda: self.rows(DeviceEvent) == 1)
        foreign = self.topic.replace(self.agent.external_id, 'BB-000000000022')
        self.assertEqual(probe.publish(foreign, self.event(device_id='BB-000000000022')), 135)
        self.assertEqual(probe.publish(self.topic.replace('telemetry', 'acks'), b'{}'), 135)
        self.assertEqual(probe.publish(self.topic.replace('telemetry', 'cmd'), b'{}'), 135)
        # Mosquitto's file ACL filters deliveries rather than rejecting every
        # broad SUBSCRIBE. Prove actual isolation with an ordered positive marker.
        self.assertEqual(probe.subscribe('bangusbuhai-rebuild/devices/#'), [1])
        backend = self.probe(backend=True)
        backend.publish(foreign.replace('telemetry', 'acks'), b'forbidden-foreign-ack')
        backend.publish(self.topic.replace('telemetry', 'acks'), b'permitted-own-ack')
        eventually(lambda: any(message[1] == b'permitted-own-ack' for message in probe.messages))
        self.assertFalse(any(message[1] == b'forbidden-foreign-ack' for message in probe.messages))
        self.assertEqual(self.rows(IngestionQuarantine), 0)

    def test_backend_acl_cannot_publish_device_or_command_traffic(self):
        probe = self.probe(backend=True)
        self.assertEqual(probe.subscribe('bangusbuhai-rebuild/devices/+/telemetry'), [1])
        self.assertEqual(probe.publish(self.topic, self.event()), 135)
        self.assertEqual(probe.publish(self.topic.replace('telemetry', 'cmd'), b'{}'), 135)
        self.assertEqual(probe.subscribe('#'), [1])
        self.assertEqual(probe.subscribe(self.topic.replace('telemetry', 'acks')), [1])
        probe.publish(self.topic.replace('telemetry', 'acks'), b'forbidden-backend-readback')
        device = self.probe()
        device.publish(self.topic, self.event())
        eventually(lambda: bool(probe.messages))
        self.assertTrue(all(message[0] == self.topic for message in probe.messages))

    def test_tls_missing_untrusted_expired_and_wrong_hostname_fail(self):
        # A successful control distinguishes denied credentials from an unavailable broker.
        control = self.probe(backend=True); control.close()
        def exchange(context, hostname='localhost'):
            with socket.create_connection(('127.0.0.1', self.broker.port), timeout=3) as raw:
                with context.wrap_socket(raw, server_hostname=hostname) as secure:
                    secure.settimeout(3)
                    # MQTT 3.1.1 CONNECT, clean session, one-byte synthetic client ID.
                    secure.sendall(b'\x10\x0d\x00\x04MQTT\x04\x02\x00\x0a\x00\x01x')
                    return secure.recv(4)
        missing = ssl.create_default_context(cafile=self.broker.authority.ca)
        with self.assertRaises(ssl.SSLError): exchange(missing)
        expired_cert, expired_key, _ = self.broker.authority.issue('BB-000000000033', expired=True)
        expired = ssl.create_default_context(cafile=self.broker.authority.ca)
        expired.load_cert_chain(expired_cert, expired_key)
        with self.assertRaises(ssl.SSLError): exchange(expired)
        with tempfile.TemporaryDirectory(prefix='bb-t13-alien-') as directory:
            alien = CertificateAuthority(directory)
            cert, key, _ = alien.issue('BB-000000000044')
            wrong_client = ssl.create_default_context(cafile=self.broker.authority.ca)
            wrong_client.load_cert_chain(cert, key)
            with self.assertRaises(ssl.SSLError): exchange(wrong_client)
            wrong_server = ssl.create_default_context(cafile=alien.ca)
            wrong_server.load_cert_chain(self.broker.backend_cert, self.broker.backend_key)
            with self.assertRaises(ssl.SSLCertVerificationError): exchange(wrong_server)
        with self.assertRaises(ssl.SSLCertVerificationError): exchange(self.broker.settings().tls(), 'wrong.invalid')
        self.probe(backend=True)

    def test_broker_restart_resubscribes_and_preserves_database(self):
        worker = self.worker()
        before = worker.generation
        probe = self.probe(); probe.subscribe(self.topic.replace('telemetry', 'acks'))
        probe.publish(self.topic, self.event())
        eventually(lambda: bool(probe.messages)); probe.close()
        self.broker.docker('restart', self.broker.name)
        eventually(lambda: worker.generation > before and worker.ready.is_set(), timeout=20)
        replacement = self.probe(); replacement.subscribe(self.topic.replace('telemetry', 'acks'))
        replacement.publish(self.topic, self.event(seq=8))
        eventually(lambda: bool(replacement.messages))
        self.assertEqual(self.rows(DeviceEvent), 2)

    def test_second_worker_cannot_open_competing_subscription(self):
        self.worker()
        other = IngestionWorker(self.engine, self.broker.settings(), self.service)
        self.addCleanup(other.stop)
        with self.assertRaises(WorkerBusy): other.start()
