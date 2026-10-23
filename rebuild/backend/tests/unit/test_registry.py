import unittest
from datetime import datetime, timezone

from backend.features.registry.errors import RegistryError
from backend.features.registry.security import certificate, canonical, decode, encode, signing_input, verify
from backend.tests.registry_support import SimulatedDevice


class RegistryUnitTests(unittest.TestCase):
    def test_certificate_identity_validity_usage_and_ca(self):
        clock = datetime.now(timezone.utc)
        device = SimulatedDevice()
        self.assertIsNotNone(certificate(device.pem, device.external_id, clock))
        for pem, identity in [(device.pem, "BB-000000000099"),
                (SimulatedDevice(expired=True).pem, device.external_id),
                (SimulatedDevice(client_auth=False).pem, device.external_id),
                (SimulatedDevice(ca=True).pem, device.external_id), ("private material", device.external_id),
                (device.pem + "-----BEGIN PRIVATE KEY-----\nnot-a-certificate", device.external_id)]:
            with self.subTest(identity=identity), self.assertRaises(RegistryError):
                certificate(pem, identity, clock)

    def test_canonical_signature_domain_and_forgery(self):
        device = SimulatedDevice()
        payload = {"purpose": "sync", "nonce": "test", "device_id": device.external_id}
        self.assertEqual(canonical(payload), canonical(dict(reversed(list(payload.items())))))
        request = {"signing_input": encode(signing_input(payload))}
        signature = device.signature(request)
        verify(device.pem, device.external_id, datetime.now(timezone.utc), payload, signature)
        for value in ("bad=encoding", SimulatedDevice().signature(request), encode(b"wrong")):
            with self.assertRaises(RegistryError):
                verify(device.pem, device.external_id, datetime.now(timezone.utc), payload, value)
        with self.assertRaises(RegistryError):
            verify(device.pem, device.external_id, datetime.now(timezone.utc), {**payload, "purpose": "confirm"}, signature)
        with self.assertRaises(ValueError):
            decode("AA=")
