import dataclasses
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from backend.core.application import create_app
from backend.core.config import AuthSettings
from backend.features.accounts.errors import AuthError
from backend.tests.auth_support import FakeAuth


class AuthUnitTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeAuth()
        self.addCleanup(self.fake.client.close)

    def test_real_signed_token_and_invalid_claims(self):
        provider = self.fake.provider
        self.assertEqual(provider.verify(self.fake.token())["sub"], str(self.fake.subject))
        cases = [{"iss": "https://attacker.test"}, {"aud": "wrong"}, {"sub": "invalid"},
                 {"session_id": "invalid"}, {"iat": int(time.time()) + 20},
                 {"exp": int(time.time()) + 3600}, {"aud": ["authenticated"]}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(AuthError):
                provider.verify(self.fake.token(**changes))
        with self.assertRaises(AuthError):
            provider.verify(self.fake.token(), subject=uuid4())
        with self.assertRaises(AuthError):
            provider.verify(self.fake.token(), session_id=uuid4())

    def test_unsigned_wrong_algorithm_and_forgery(self):
        token = self.fake.token()
        for candidate in (jwt.encode({"sub": "attacker"}, "secret" * 8, algorithm="HS256"),
                          jwt.encode({"sub": "attacker"}, None, algorithm="none"),
                          token[:-10] + "AAAAAAAAAA", "invalid", "x" * 16385):
            with self.subTest(candidate=candidate[:20]), self.assertRaises(AuthError):
                self.fake.provider.verify(candidate)

    def test_expired_and_key_rotation_refresh(self):
        self.fake.expired = True
        with self.assertRaises(AuthError) as error:
            self.fake.provider.verify(self.fake.token())
        self.assertEqual(error.exception.code, "access_expired")
        self.fake.expired = False
        self.fake.kid = "test-key-2"
        self.fake.key = ec.generate_private_key(ec.SECP256R1())
        self.fake.provider._fetched_at = float("-inf")
        self.fake.provider.verify(self.fake.token())
        self.assertEqual(self.fake.jwks_calls, 2)

    def test_timeouts_and_provider_errors_do_not_echo_secrets(self):
        with self.assertRaises(AuthError) as error:
            self.fake.provider.sign_in("operator@example.test", "wrong")
        self.assertEqual(str(error.exception), "authentication_failed")
        self.fake.unavailable = True
        with self.assertRaises(AuthError) as error:
            self.fake.provider.sign_in("operator@example.test", "private-password")
        self.assertEqual(str(error.exception), "authentication_unavailable")

    def test_invalid_settings_and_production_cookie_defaults(self):
        for changes in ({"provider_url": "http://insecure.test"}, {"origins": ("*",)},
                        {"origins": ("http://external.test",)}, {"token_key": b"invalid"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                dataclasses.replace(self.fake.settings, **changes)
        settings = dataclasses.replace(self.fake.settings, development=False, origins=("https://app.example.test",))
        self.assertTrue(settings.cookie_name.startswith("__Host-"))
        self.assertNotIn(settings.token_key.decode(), repr(settings))

    def test_unconfigured_auth_is_closed_and_health_function_is_database_free(self):
        with patch.object(AuthSettings, "load", side_effect=ValueError("missing")):
            with TestClient(create_app(), base_url="http://127.0.0.1") as client:
                response = client.get("/api/v1/me")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
        from backend.main import health
        self.assertEqual(health()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
