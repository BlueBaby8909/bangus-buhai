import dataclasses
import json
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import patch

from backend.mqtt.config import MqttSettings
from backend.mqtt.credentials import prepare
from backend.mqtt.worker import IngestionWorker


class PasswordConfigurationTests(unittest.TestCase):
    def test_preparation_separates_logins_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            directory = prepare(Path(root) / 'private', 'BB-AABBCC112233')
            device = json.loads((directory / 'device-login.json').read_text())
            backend = json.loads((directory / 'backend-login.json').read_text())
            self.assertNotEqual(device['password'], backend['password'])
            self.assertEqual(len(device['password']), 43)
            self.assertIn(json.dumps(device['password']), (directory / 'device_mqtt_login.h').read_text())
            settings = MqttSettings(mode='test', auth_mode='password', credential_file=str(directory / 'backend-login.json'), ca_file=__file__)
            settings.validate('bangus_buhai_rebuild_test')
            self.assertEqual(settings.credentials(), (backend['username'], backend['password']))
            with self.assertRaises(FileExistsError): prepare(directory, 'BB-AABBCC112233')
            self.assertEqual(json.loads((directory / 'backend-login.json').read_text()), backend)
            # Selected password mode must not attempt to load retained client keys.
            with patch('backend.mqtt.config.ClosingTLSContext') as context:
                settings.tls()
                context.return_value.load_cert_chain.assert_not_called()
                context.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
            from types import SimpleNamespace
            from unittest.mock import Mock
            client = Mock()
            with patch.object(MqttSettings, 'tls'):
                IngestionWorker(SimpleNamespace(url=SimpleNamespace(database='bangus_buhai_rebuild_test')),
                                settings, Mock(), client=client)
            client.username_pw_set.assert_called_once_with(backend['username'], backend['password'])

    def test_invalid_login_fails_closed_without_exposing_content(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'login.json'
            settings = MqttSettings(mode='test', auth_mode='password', credential_file=str(path), ca_file=__file__)
            for document in [[], {'username': 'x', 'password': 'private-secret'},
                             {'username': '#', 'password': 'private-secret'*4},
                             {'username': 'x', 'password': 'private-secret'*4, 'extra': True}]:
                path.write_text(json.dumps(document))
                with self.assertRaises(ValueError) as error: settings.validate()
                self.assertNotIn('private-secret', str(error.exception))
            with self.assertRaises(ValueError): dataclasses.replace(settings, auth_mode='invalid').validate()

    def test_private_material_cannot_be_generated_inside_repository(self):
        with self.assertRaises(ValueError):
            prepare(Path(__file__).resolve().parents[2] / 'forbidden', 'BB-AABBCC112233')
