import dataclasses
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from backend.mqtt.__main__ import main
from backend.mqtt.config import MqttSettings
from backend.mqtt.service import Outcome
from backend.mqtt.worker import Delivery, IngestionWorker


class FakeClient:
    def __init__(self):
        self.published, self.acknowledged = [], []
        self.rc = 0
    def tls_set_context(self, context): pass
    def max_queued_messages_set(self, size): pass
    def max_inflight_messages_set(self, size): pass
    def disconnect(self): pass
    def publish(self, topic, payload, **options):
        self.published.append((topic, payload, options)); return SimpleNamespace(rc=self.rc)
    def ack(self, mid, qos): self.acknowledged.append((mid, qos)); return 0


class MqttUnitTests(unittest.TestCase):
    def worker(self, outcome=None, queue_size=64):
        settings = MqttSettings(mode='test', ca_file=__file__, certificate_file=__file__, key_file=__file__)
        engine = SimpleNamespace(url=SimpleNamespace(database='bangus_buhai_rebuild_test'))
        client, service = FakeClient(), Mock()
        service.process.return_value = outcome or Outcome('stored', 'stored', 'prefix/acks', b'ack')
        with patch.object(MqttSettings, 'tls', return_value=object()):
            worker = IngestionWorker(engine, settings, service, queue_size=queue_size, client=client)
        worker.connected = True
        worker.lease = Mock()
        return worker, client, service

    def delivery(self, **changes):
        return dataclasses.replace(Delivery(0, 9, 'topic', b'payload', 1, False), **changes)

    def test_disabled_main_opens_no_connections(self):
        with patch.object(MqttSettings, 'load', return_value=MqttSettings()), patch('backend.mqtt.__main__.make_engine') as engine:
            self.assertEqual(main(), 0)
            engine.assert_not_called()

    def test_live_gates_and_test_isolation(self):
        paths = dict(ca_file=__file__, certificate_file=__file__, key_file=__file__)
        for settings in (MqttSettings(mode='live', **paths), MqttSettings(mode='test', host='external.example', **paths),
                         MqttSettings(mode='test', prefix='#', **paths), MqttSettings(mode='test', **paths)):
            with self.assertRaises(ValueError): settings.validate('wrong_database')
        MqttSettings(mode='test', **paths).validate('bangus_buhai_rebuild_test')
        MqttSettings(mode='live', broker_qualified=True, firmware_qualified=True, **paths).validate()

    def test_private_configuration_is_separate_and_invalid_settings_are_safe(self):
        with patch('backend.mqtt.config.LOCAL_ENV', Path(__file__).with_name('does-not-exist')), patch.dict(
                'os.environ', {'BB_MQTT_MODE': 'test', 'BB_MQTT_PORT': 'secret-bad-value'}, clear=True):
            with self.assertRaises(ValueError) as raised: MqttSettings.load()
            self.assertNotIn('secret', str(raised.exception))

    def test_application_publish_follows_processing_and_broker_ack(self):
        worker, client, service = self.worker()
        def process(*args, **kwargs):
            self.assertEqual(client.published, [])
            self.assertEqual(client.acknowledged, [])
            return Outcome('stored', 'stored', 'acks', b'committed')
        service.process.side_effect = process
        worker.handle(self.delivery())
        self.assertEqual(client.published, [])
        self.assertEqual(client.acknowledged, [])
        worker.flush_completions()
        self.assertEqual(client.published, [('acks', b'committed', {'qos': 1, 'retain': False})])
        self.assertEqual(client.acknowledged, [(9, 1)])

    def test_processing_failure_never_acknowledges(self):
        worker, client, service = self.worker()
        service.process.side_effect = RuntimeError('private error')
        with self.assertRaises(RuntimeError): worker.handle(self.delivery())
        self.assertEqual(client.published, [])
        self.assertEqual(client.acknowledged, [])

    def test_failed_publish_leaves_delivery_unacknowledged(self):
        worker, client, _ = self.worker(); client.rc = 4
        worker.handle(self.delivery())
        worker.flush_completions()
        self.assertEqual(client.acknowledged, [])
        self.assertTrue(worker.recover_event.is_set())

    def test_quarantine_only_acknowledges_broker_transport(self):
        worker, client, _ = self.worker(Outcome('quarantined', 'binding_unconfirmed'))
        worker.handle(self.delivery())
        worker.flush_completions()
        self.assertEqual(client.published, [])
        self.assertEqual(client.acknowledged, [(9, 1)])

    def test_stale_generation_and_disconnect_during_commit_are_fenced(self):
        worker, client, service = self.worker()
        worker.handle(self.delivery(generation=8))
        service.process.assert_not_called()
        def commit_then_disconnect(*args, **kwargs):
            worker.fence()
            return Outcome('stored', 'stored', 'acks', b'ack')
        service.process.side_effect = commit_then_disconnect
        worker.handle(self.delivery())
        worker.flush_completions()
        self.assertEqual(client.published, [])
        self.assertEqual(client.acknowledged, [])

    def test_queue_saturation_requests_reconnect_without_ack(self):
        worker, client, _ = self.worker(queue_size=1)
        message = SimpleNamespace(mid=1, topic='topic', payload=b'payload', qos=1, retain=False)
        worker.on_message(client, None, message); worker.on_message(client, None, message)
        self.assertEqual(worker.inbox.qsize(), 1)
        self.assertTrue(worker.recover_event.is_set())
        self.assertEqual(client.acknowledged, [])

    def test_oversized_delivery_never_enters_database_queue(self):
        worker, client, service = self.worker()
        worker.on_message(client, None, SimpleNamespace(mid=3, topic='topic', payload=b'x'*4097, qos=1, retain=False))
        self.assertEqual(worker.inbox.qsize(), 0)
        service.process.assert_not_called()
        self.assertEqual(client.acknowledged, [(3, 1)])

    def test_lease_loss_stops_without_connecting(self):
        worker, client, _ = self.worker()
        worker.lease = Mock(); worker.lease.heartbeat.side_effect = RuntimeError('lost')
        client.connect = Mock()
        worker.network_loop()
        self.assertTrue(worker.stop_event.is_set())
        self.assertEqual(worker.counters['lease_lost'], 1)
        client.connect.assert_not_called()

    def test_lease_loss_after_commit_prevents_application_ack(self):
        worker, client, _ = self.worker()
        worker.lease.heartbeat.side_effect = RuntimeError('Lease connection failed')
        worker.handle(self.delivery())
        worker.flush_completions()
        self.assertTrue(worker.stop_event.is_set())
        self.assertEqual(client.published, [])
        self.assertEqual(client.acknowledged, [])

    def test_disconnect_between_commit_and_network_completion_cannot_ack(self):
        worker, client, _ = self.worker()
        worker.handle(self.delivery())
        worker.fence()
        worker.connected = True
        worker.flush_completions()
        self.assertEqual(client.published, [])
        self.assertEqual(client.acknowledged, [])

    def test_commands_require_live_gate_and_current_lease(self):
        worker, client, _ = self.worker()
        worker.commands = Mock(); worker.ready.set()
        worker.settings = dataclasses.replace(worker.settings, mode='live')
        worker.dispatch_commands(); worker.commands.dispatch.assert_not_called()
        worker.settings = dataclasses.replace(worker.settings, commands_qualified=True)
        worker.lease.heartbeat.side_effect = RuntimeError('lost')
        worker.dispatch_commands()
        self.assertTrue(worker.stop_event.is_set()); self.assertFalse(worker.ready.is_set())
        worker.commands.dispatch.assert_not_called(); self.assertEqual(client.published, [])

    def test_command_publication_rechecks_lease_and_is_fenced_on_disconnect(self):
        worker, client, _ = self.worker(); worker.ready.set()
        worker.commands = Mock()
        worker.commands.dispatch.side_effect = lambda publish: [(publish({'device_id':'BB-AABBCC112233'}), 'attempt')]
        worker.lease.heartbeat.side_effect = [None, RuntimeError('lost before publish')]
        with self.assertRaises(RuntimeError): worker.dispatch_commands()
        self.assertTrue(worker.stop_event.is_set()); self.assertEqual(client.published, [])
        worker.command_mids[10]='attempt'; worker.fence(); self.assertEqual(worker.command_mids,{})
