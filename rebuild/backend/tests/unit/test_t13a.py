import ipaddress
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from cryptography import x509
from fastapi.testclient import TestClient

from backend.core.application import create_app
from backend.features.registry.lab import prepare, broker_identity
from backend.tests.auth_support import FakeAuth
from backend.mqtt.service import IngestionService, Outcome
from backend.mqtt.verify_live import DropFirstStoredAck


class DeviceListenerTests(unittest.TestCase):
    def setUp(self):
        self.auth = FakeAuth()
        self.addCleanup(self.auth.provider.close)
        service = SimpleNamespace(settings=self.auth.settings, engine=None, clock=lambda: None)
        self.app = create_app(service=service, device_only=True, device_hosts=('192.168.1.20',))

    def test_listener_exposes_only_device_routes(self):
        with TestClient(self.app, base_url='https://192.168.1.20') as client:
            self.assertEqual(client.get('/api/v1/me').status_code, 404)
            self.assertEqual(client.get('/docs').status_code, 404)
            self.assertEqual(client.post('/api/device/v1/challenges', json={}).status_code, 422)

    def test_tls_host_and_forwarded_headers_cannot_bypass_boundary(self):
        for url in ('http://192.168.1.20', 'https://192.168.1.21'):
            with TestClient(self.app, base_url=url) as client:
                response = client.post('/api/device/v1/challenges', json={},
                    headers={'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': '192.168.1.20'})
                self.assertEqual(response.status_code, 503)

    def test_private_certificate_identity_and_refuse_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'material'
            prepare(target, '192.168.1.20')
            cert = x509.load_pem_x509_certificate((target / 'server-cert.pem').read_bytes())
            self.assertEqual(cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
                .value.get_values_for_type(x509.IPAddress), [ipaddress.ip_address('192.168.1.20')])
            before = (target / 'server-key.pem').read_bytes()
            with self.assertRaises(FileExistsError): prepare(target, '192.168.1.21')
            self.assertEqual(before, (target / 'server-key.pem').read_bytes())
            self.assertFalse((target / 'ca-key.pem').exists())

    def test_separate_backend_identity_and_no_overwrite(self):
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
        with tempfile.TemporaryDirectory() as directory:
            broker_identity(directory)
            target = Path(directory)
            cert = x509.load_pem_x509_certificate((target / 'mqtt-backend-cert.pem').read_bytes())
            self.assertEqual(cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value, 'BB-REBUILD-INGESTOR')
            self.assertIn(ExtendedKeyUsageOID.CLIENT_AUTH,
                cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value)
            before = (target / 'mqtt-backend-key.pem').read_bytes()
            with self.assertRaises(ValueError): broker_identity(directory)
            self.assertEqual(before, (target / 'mqtt-backend-key.pem').read_bytes())

    def test_explicit_lost_ack_hook_preserves_commit_and_next_response(self):
        from sqlalchemy.engine import make_url
        engine = Mock(url=make_url('postgresql+psycopg://bb@127.0.0.1:55432/bangus_buhai_rebuild'))
        service = DropFirstStoredAck(engine, 'bangusbuhai-rebuild')
        quarantined = Outcome('quarantined', 'binding_unavailable', 'quarantine-receipts', b'receipt')
        stored = Outcome('stored', 'stored', 'acks', b'stored')
        duplicate = Outcome('duplicate', 'duplicate', 'acks', b'duplicate')
        with patch.object(IngestionService, 'process', side_effect=[quarantined, stored, duplicate]):
            self.assertEqual(service.process('topic', b'bytes'), quarantined)
            self.assertIsNone(service.process('topic', b'bytes').acknowledgement)
            self.assertEqual(service.process('topic', b'bytes'), duplicate)
