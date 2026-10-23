"""Same ingestion/custody boundaries over server-verified TLS and distinct logins."""
import ssl
import threading

import paho.mqtt.client as mqtt

from backend.tests.integration import test_mqtt_broker
from backend.tests.mqtt_support import BrokerFixture, DatabaseFixture


class PasswordBrokerTests(test_mqtt_broker.BrokerTests):
    def test_trusted_permission_probe_checks_real_broker_without_database_events(self):
        import json
        from backend.mqtt.qualify import qualify
        from backend.database.models import DeviceEvent
        login = self.broker.authority.write('device-probe-login.json', json.dumps(dict(
            username='BB-AABBCC112233', password=self.broker.device_password)).encode())
        qualify(self.broker.settings(), login)
        self.assertEqual(self.rows(DeviceEvent), 0)

    @classmethod
    def setUpClass(cls):
        DatabaseFixture.setUpClass.__func__(cls)
        try:
            cls.broker = BrokerFixture(password_auth=True).start()
            cls.broker_agent = cls.broker.agent
        except BaseException:
            DatabaseFixture.tearDownClass.__func__(cls)
            raise

    def test_tls_missing_untrusted_expired_and_wrong_hostname_fail(self):
        # Password mode deliberately does not request a client certificate.
        # Server identity verification and authentication remain mandatory.
        self.probe()
        import socket
        for context, host in [(ssl.create_default_context(), 'localhost'),
                              (ssl.create_default_context(cafile=self.broker.authority.ca), 'wrong.invalid')]:
            with socket.create_connection(('127.0.0.1', self.broker.port), timeout=3) as raw:
                with self.assertRaises(ssl.SSLCertVerificationError):
                    context.wrap_socket(raw, server_hostname=host)

    def test_wrong_or_missing_password_is_denied(self):
        for password in (None, 'wrong-synthetic-password'):
            completed = threading.Event()
            reasons = []
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            client.tls_set_context(ssl.create_default_context(cafile=self.broker.authority.ca))
            if password is not None:
                client.username_pw_set('BB-AABBCC112233', password)
            def connected(client, userdata, flags, reason, properties):
                reasons.append(reason.is_failure)
                completed.set()
            client.on_connect = connected
            try:
                client.connect('127.0.0.1', self.broker.port)
                client.loop_start()
                self.assertTrue(completed.wait(5))
                self.assertEqual(reasons, [True])
            finally:
                client.disconnect()
                client.loop_stop()
