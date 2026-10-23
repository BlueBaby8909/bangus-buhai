"""Disposable PostgreSQL and certificate fixtures. Never loads real device keys."""
from datetime import datetime, timedelta, timezone
import ipaddress
import json
from pathlib import Path
import ssl
import subprocess
import tempfile
import time
import threading
import unittest
from uuid import UUID, uuid4

from alembic import command
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import sqlalchemy as sa
from sqlmodel import Session

from backend.database.config import database_url, make_engine
from backend.database.migrate import configuration
from backend.database.models import (Binding, Device, DeviceConfiguration, DeviceConfigurationReceipt,
    DeviceInventory, Hatchery, Membership, Tank, UserIdentity)
from backend.features.registry.security import digest
from backend.mqtt.config import MqttSettings
from backend.mqtt.service import IngestionService
from backend.tests.registry_support import SimulatedDevice
import paho.mqtt.client as mqtt

BROKER_IMAGE = 'eclipse-mosquitto@sha256:38c0da4f2ef84284d47b3b3eeea1cb3bdeabe81ee10caf0cd5c5ff61ee3ea408'
FIXTURES = Path(__file__).resolve().parents[2] / 'contracts/fixtures/valid'


def eventually(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate(): return
        time.sleep(.03)
    raise AssertionError('Timed out waiting for test condition')


class DatabaseFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = make_engine(test=True)

    @classmethod
    def tearDownClass(cls):
        cls.admin.dispose()

    def setUp(self):
        self.schema = 't13_test_' + uuid4().hex
        with self.admin.begin() as c: c.execute(sa.schema.CreateSchema(self.schema))
        self.engine = sa.create_engine(database_url(test=True), hide_parameters=True,
            connect_args={'options': f'-csearch_path={self.schema}', 'connect_timeout': 5})
        self.addCleanup(self.cleanup_schema)
        with self.engine.begin() as c:
            cfg = configuration(); cfg.attributes['connection'] = c; command.upgrade(cfg, 'head')
        self.clock = datetime.now(timezone.utc)
        self.hatchery, self.tank, self.device, self.user = [uuid4() for _ in range(4)]
        self.binding = UUID('97fcde45-4112-41d4-a509-17e5bb1c0d91')
        self.agent = getattr(self, 'broker_agent', None) or SimulatedDevice('BB-AABBCC112233')
        self.document = dict(schema_version=1, device_id=self.agent.external_id, hatchery_id=str(self.hatchery),
            tank_id=str(self.tank), binding_id=str(self.binding), archived=False, revision=1)
        cert = x509.load_pem_x509_certificate(self.agent.pem.encode())
        fingerprint = cert.fingerprint(hashes.SHA256()).hex()
        key_fingerprint = hashes.Hash(hashes.SHA256())
        key_fingerprint.update(cert.public_key().public_bytes(serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo))
        with Session(self.engine) as s, s.begin():
            s.add(Hatchery(id=self.hatchery, name='Synthetic hatchery'))
            s.add(UserIdentity(id=self.user, provider_issuer='https://example.invalid/auth/v1', provider_subject=uuid4(), active=True))
            s.flush()
            s.add(Membership(hatchery_id=self.hatchery, user_id=self.user))
            s.add(Tank(id=self.tank, hatchery_id=self.hatchery, name='Synthetic tank'))
            s.add(Device(id=self.device, hatchery_id=self.hatchery, external_id=self.agent.external_id))
            s.flush()
            s.add(Binding(id=self.binding, device_id=self.device, tank_id=self.tank, hatchery_id=self.hatchery,
                started_at=self.clock - timedelta(hours=1)))
            s.add(DeviceInventory(external_id=self.agent.external_id, certificate=self.agent.pem, fingerprint=fingerprint,
                key_fingerprint=key_fingerprint.finalize().hex(), device_id=self.device, verified_at=self.clock))
            s.add(DeviceConfiguration(device_id=self.device, revision=1, document=self.document,
                digest=digest(self.document), confirmed_revision=1, confirmed_at=self.clock - timedelta(minutes=2)))
            s.flush()
            s.add(DeviceConfigurationReceipt(device_id=self.device, hatchery_id=self.hatchery,
                binding_id=self.binding, tank_id=self.tank, revision=1, document=self.document,
                digest=digest(self.document), credential_fingerprint=fingerprint,
                confirmed_at=self.clock - timedelta(minutes=2)))
        self.service = IngestionService(self.engine, clock=lambda: self.clock)
        self.topic = f'bangusbuhai-rebuild/devices/{self.agent.external_id}/telemetry'

    def cleanup_schema(self):
        self.engine.dispose()
        with self.admin.begin() as c: c.execute(sa.schema.DropSchema(self.schema, cascade=True))

    def event(self, fixture='telemetry-default-ph.json', **changes):
        payload = json.loads((FIXTURES / fixture).read_text())
        payload['measured_at' if fixture.startswith('telemetry') else 'created_at'] = (
            self.clock - timedelta(minutes=1)).isoformat().replace('+00:00', 'Z')
        payload.update(changes)
        return payload

    def process(self, document=None, *, topic=None, **delivery):
        return self.service.process(topic or self.topic, json.dumps(document or self.event()).encode(), **delivery)


class CertificateAuthority:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'BB-SYNTHETIC-TEST-CA')])
        now = datetime.now(timezone.utc)
        self.cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(self.key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=2)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
            .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(self.key.public_key()), False)
            .sign(self.key, hashes.SHA256()))
        self.ca = self.write('ca.pem', self.cert.public_bytes(serialization.Encoding.PEM))

    def write(self, name, content):
        path = self.directory / name
        path.write_bytes(content)
        path.chmod(0o644)  # Synthetic files only, inside a private temporary parent.
        return str(path)

    def issue(self, identity, *, server=False, expired=False):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, identity)])
        now = datetime.now(timezone.utc)
        builder = (x509.CertificateBuilder().subject_name(name).issuer_name(self.cert.subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=2))
            .not_valid_after(now + timedelta(days=-1 if expired else 1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self.key.public_key()), False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]), False))
        if server:
            builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),
                x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), False)
        cert = builder.sign(self.key, hashes.SHA256())
        pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        cert_file = self.write(identity + '.pem', pem.encode())
        key_file = self.write(identity + '-key.pem', key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        agent = SimulatedDevice(identity, key=key) if not server else None
        if agent is not None: agent.pem = pem
        return cert_file, key_file, agent


class BrokerFixture:
    def __init__(self, *, password_auth=False, command_support=False):
        self.password_auth = password_auth
        self.command_support = command_support
        self.backend_password = 'synthetic-backend-password-for-disposable-test-only'
        self.device_password = 'synthetic-device-password-for-disposable-test-only'
        self.temp = tempfile.TemporaryDirectory(prefix='bb-t13-synthetic-')
        self.directory = Path(self.temp.name)
        self.authority = CertificateAuthority(self.directory)
        self.server_cert, self.server_key, _ = self.authority.issue('localhost', server=True)
        self.backend_cert, self.backend_key, _ = self.authority.issue('BB-INGESTOR')
        self.device_cert, self.device_key, self.agent = self.authority.issue('BB-AABBCC112233')
        self.other_cert, self.other_key, _ = self.authority.issue('BB-000000000022')
        self.name = 'bb-t13-test-' + uuid4().hex
        self.port = None

    def docker(self, *args):
        result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError('Disposable broker operation failed: ' + result.stderr[-1500:])
        return result.stdout.strip()

    def start(self):
        import socket
        # Keep the selected port stable across container restarts. Docker may
        # reallocate an automatically published port on restart.
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            self.port = reservation.getsockname()[1]
        config = '''listener 8883
cafile /mosquitto/config/ca.pem
certfile /mosquitto/config/server.pem
keyfile /mosquitto/config/server-key.pem
require_certificate true
use_identity_as_username true
allow_anonymous false
acl_file /mosquitto/config/acl
persistence false
max_queued_messages 100
max_inflight_messages 20
max_packet_size 8192
retain_available false
log_type error
'''
        acl = '''user BB-INGESTOR
topic read bangusbuhai-rebuild/devices/+/telemetry
topic read bangusbuhai-rebuild/devices/+/command-results
topic write bangusbuhai-rebuild/devices/+/acks
topic write bangusbuhai-rebuild/devices/+/quarantine-receipts
pattern write bangusbuhai-rebuild/devices/%u/telemetry
pattern write bangusbuhai-rebuild/devices/%u/command-results
pattern read bangusbuhai-rebuild/devices/%u/acks
pattern read bangusbuhai-rebuild/devices/%u/quarantine-receipts
'''
        if self.command_support:
            acl = acl.replace('user BB-INGESTOR\n', 'user BB-INGESTOR\ntopic write bangusbuhai-rebuild/devices/+/cmd\n')
            acl += 'pattern read bangusbuhai-rebuild/devices/%u/cmd\n'
        files = [('mosquitto.conf', self.authority.write('mosquitto.conf', config.encode())),
                 ('acl', self.authority.write('acl', acl.encode())), ('ca.pem', self.authority.ca),
                 ('server.pem', self.server_cert), ('server-key.pem', self.server_key)]
        if self.password_auth:
            config = config.replace('require_certificate true\nuse_identity_as_username true',
                                    'require_certificate false\npassword_file /mosquitto/config/passwords')
            self.authority.write('mosquitto.conf', config.encode())
            # Fixed synthetic passwords only; no real credentials or private device keys.
            passwords = self.docker('run', '--rm', '--entrypoint', 'sh', BROKER_IMAGE, '-c',
                'mosquitto_passwd -b -c /tmp/passwords BB-INGESTOR ' + self.backend_password +
                ' && mosquitto_passwd -b /tmp/passwords BB-AABBCC112233 ' + self.device_password +
                ' && cat /tmp/passwords')
            files.append(('passwords', self.authority.write('passwords', (passwords + '\n').encode())))
        try:
            self.docker('create', '--name', self.name, '--label', 'bangusbuhai.test=t13',
                '-p', f'127.0.0.1:{self.port}:8883', BROKER_IMAGE,
                'mosquitto', '-c', '/mosquitto/config/mosquitto.conf')
            for name, path in files: self.docker('cp', path, f'{self.name}:/mosquitto/config/{name}')
            self.docker('start', self.name)
            state = json.loads(self.docker('inspect', self.name))[0]
            self.port = int(state['NetworkSettings']['Ports']['8883/tcp'][0]['HostPort'])
            eventually(self.listening, timeout=15)
            return self
        except BaseException:
            self.close(); raise

    def listening(self):
        import socket
        try:
            with socket.create_connection(('127.0.0.1', self.port), timeout=.3): return True
        except OSError: return False

    def settings(self):
        if self.password_auth:
            login = self.authority.write('backend-login.json', json.dumps(dict(
                username='BB-INGESTOR', password=self.backend_password)).encode())
            return MqttSettings(mode='test', port=self.port, ca_file=self.authority.ca,
                auth_mode='password', credential_file=login)
        return MqttSettings(mode='test', port=self.port, ca_file=self.authority.ca,
            certificate_file=self.backend_cert, key_file=self.backend_key)

    def close(self):
        try:
            self.docker('rm', '-f', self.name)
        finally:
            self.temp.cleanup()


class Probe:
    """Real TLS/MQTT client; no production credentials and no permissive TLS."""
    def __init__(self, broker, *, backend=False, client_id=None, protocol=mqtt.MQTTv5):
        self.messages, self.subacks, self.pubacks = [], {}, {}
        self.connected = threading.Event()
        self.lock = threading.RLock()
        self.received = None
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id or 'bb-test-' + uuid4().hex,
            protocol=protocol, reconnect_on_failure=False)
        context = ssl.create_default_context(cafile=broker.authority.ca)
        if broker.password_auth:
            self.client.username_pw_set('BB-INGESTOR' if backend else 'BB-AABBCC112233',
                broker.backend_password if backend else broker.device_password)
        else:
            context.load_cert_chain(broker.backend_cert if backend else broker.device_cert,
                broker.backend_key if backend else broker.device_key)
        self.client.tls_set_context(context)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_publish = self.on_publish
        self.client.connect('127.0.0.1', broker.port, keepalive=10)
        self.client.loop_start()
        if not self.connected.wait(5):
            self.close(); raise AssertionError('Synthetic MQTT client did not connect')

    def on_connect(self, client, userdata, flags, reason, properties):
        if not reason.is_failure: self.connected.set()

    def on_message(self, client, userdata, message):
        if self.received: self.received(message)
        with self.lock: self.messages.append((message.topic, bytes(message.payload), message.retain))

    def on_subscribe(self, client, userdata, mid, reasons, properties):
        with self.lock: self.subacks[mid] = [reason.value for reason in reasons]

    def on_publish(self, client, userdata, mid, reason, properties):
        with self.lock: self.pubacks[mid] = reason.value

    def subscribe(self, topic):
        result, mid = self.client.subscribe(topic, qos=1)
        if result != 0: raise AssertionError('Synthetic subscribe failed')
        eventually(lambda: mid in self.subacks)
        return self.subacks[mid]

    def publish(self, topic, payload, retain=False):
        if isinstance(payload, dict): payload = json.dumps(payload).encode()
        info = self.client.publish(topic, payload, qos=1, retain=retain)
        if info.rc != 0: raise AssertionError('Synthetic publish failed')
        eventually(lambda: info.mid in self.pubacks)
        return self.pubacks[info.mid]

    def close(self):
        self.client.disconnect(); self.client.loop_stop()
