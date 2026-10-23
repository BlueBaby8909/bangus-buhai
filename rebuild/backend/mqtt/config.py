"""Explicit MQTT-only settings. Never load prototype or auth configuration."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import ssl
import json

LOCAL_ENV = Path(__file__).with_name('.env')


class ClosingTLSContext(ssl.SSLContext):
    """Bound and close failed handshakes before Paho receives the socket.

    Paho 2.1 performs its handshake outside SSLContext.wrap_socket's cleanup
    path. Complete it here with normal certificate/hostname checks intact.
    """
    def wrap_socket(self, sock, **kwargs):
        secure = None
        try:
            kwargs['do_handshake_on_connect'] = False
            secure = super().wrap_socket(sock, **kwargs)
            secure.settimeout(5)
            secure.do_handshake()
            return secure
        except BaseException:
            (secure if secure is not None else sock).close()
            raise


@dataclass(frozen=True)
class MqttSettings:
    mode: str = 'disabled'
    host: str = '127.0.0.1'
    port: int = 58883
    prefix: str = 'bangusbuhai-rebuild'
    client_id: str = 'bb-rebuild-ingestion'
    ca_file: str = ''
    certificate_file: str = ''
    key_file: str = ''
    auth_mode: str = 'certificate'
    credential_file: str = ''
    broker_qualified: bool = False
    firmware_qualified: bool = False
    commands_qualified: bool = False

    @classmethod
    def load(cls):
        values = {}
        if LOCAL_ENV.is_file():
            values = dict(line.partition('=')[::2] for line in LOCAL_ENV.read_text(encoding='utf-8').splitlines()
                if line.startswith('BB_MQTT_') and '=' in line)
        def setting(key, default):
            return os.environ.get('BB_MQTT_' + key, values.get('BB_MQTT_' + key, default))
        def boolean(key):
            value = setting(key, 'false')
            if value not in ('true', 'false'):
                raise ValueError('Invalid MQTT configuration')
            return value == 'true'
        try:
            result = cls(mode=setting('MODE', 'disabled'), host=setting('HOST', '127.0.0.1'),
                port=int(setting('PORT', '58883')), prefix=setting('PREFIX', 'bangusbuhai-rebuild'),
                client_id=setting('CLIENT_ID', 'bb-rebuild-ingestion'), ca_file=setting('CA_FILE', ''),
                certificate_file=setting('CERTIFICATE_FILE', ''), key_file=setting('KEY_FILE', ''),
                auth_mode=setting('AUTH_MODE', 'certificate'), credential_file=setting('CREDENTIAL_FILE', ''),
                broker_qualified=boolean('BROKER_QUALIFIED'), firmware_qualified=boolean('FIRMWARE_QUALIFIED'),
                commands_qualified=boolean('COMMANDS_QUALIFIED'))
            result.validate()
            return result
        except (ValueError, TypeError, OSError, UnicodeError):
            raise ValueError('Invalid MQTT configuration') from None

    def validate(self, database=None):
        if self.mode not in ('disabled', 'test', 'live'):
            raise ValueError('Invalid MQTT configuration')
        if self.mode == 'disabled':
            return
        if (not self.host or len(self.host) > 253 or not 1 <= self.port <= 65535 or
                not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', self.prefix) or
                not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', self.client_id)):
            raise ValueError('Invalid MQTT configuration')
        if self.mode == 'test' and (self.host not in ('127.0.0.1', 'localhost', '::1') or
                (database is not None and database != 'bangus_buhai_rebuild_test')):
            raise ValueError('Test MQTT requires loopback and the dedicated test database')
        if self.mode == 'live' and not (self.broker_qualified and self.firmware_qualified):
            raise ValueError('Live MQTT qualification is not recorded')
        if self.auth_mode not in ('certificate', 'password'):
            raise ValueError('Invalid MQTT authentication mode')
        paths = (self.ca_file, self.certificate_file, self.key_file) if self.auth_mode == 'certificate' else (self.ca_file, self.credential_file)
        if not all(value and Path(value).is_file() for value in paths):
            raise ValueError('Invalid MQTT credential files')
        if self.auth_mode == 'password':
            self.credentials()

    def credentials(self):
        """Read only the selected private MQTT login; errors never include its contents."""
        try:
            path = Path(self.credential_file)
            if path.stat().st_size > 1024:
                raise ValueError()
            value = json.loads(path.read_text(encoding='utf-8'))
            if (not isinstance(value, dict) or set(value) != {'username', 'password'} or
                    not isinstance(value['username'], str) or
                    not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value['username']) or
                    not isinstance(value['password'], str) or not 32 <= len(value['password']) <= 256 or
                    any(ord(c) < 33 or ord(c) > 126 for c in value['password'])):
                raise ValueError()
            return value['username'], value['password']
        except (ValueError, TypeError, OSError, UnicodeError):
            raise ValueError('Invalid private MQTT login') from None

    def tls(self):
        context = ClosingTLSContext(ssl.PROTOCOL_TLS_CLIENT)
        context.verify_flags |= ssl.VERIFY_X509_STRICT | ssl.VERIFY_X509_PARTIAL_CHAIN
        context.load_verify_locations(cafile=self.ca_file)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        if self.auth_mode == 'certificate':
            context.load_cert_chain(self.certificate_file, self.key_file)
        return context
