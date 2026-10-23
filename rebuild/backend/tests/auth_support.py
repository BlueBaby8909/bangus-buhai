"""Test-only managed provider with generated signing keys; never contacts Supabase."""
import json
import time
from uuid import uuid4

import httpx
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec

from backend.core.config import AuthSettings
from backend.features.accounts.provider import SupabaseProvider


class FakeAuth:
    def __init__(self):
        self.settings = AuthSettings(provider_url="https://test-project.supabase.co", publishable_key="test-publishable",
            token_key=Fernet.generate_key(), origins=("http://127.0.0.1:5174",), development=True)
        self.subject, self.session_id = uuid4(), uuid4()
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.kid = "test-key-1"
        self.jwks_calls = self.refresh_calls = self.login_calls = 0
        self.refresh_delay = 0
        self.expired = False
        self.unavailable = False
        self.logout_unavailable = False
        self.switched_subject = False
        self.client = httpx.Client(transport=httpx.MockTransport(self.handle))
        self.provider = SupabaseProvider(self.settings, self.client)

    def token(self, **changes):
        claims = dict(iss=self.settings.issuer, aud="authenticated", sub=str(self.subject),
            session_id=str(self.session_id), iat=int(time.time()) - (1000 if self.expired else 0),
            exp=int(time.time()) + (-100 if self.expired else 900), email="operator@example.test", role="authenticated")
        claims.update(changes)
        return jwt.encode(claims, self.key, algorithm="ES256", headers={"kid": self.kid})

    def handle(self, request):
        if self.unavailable:
            raise httpx.ConnectError("test upstream credential details must never appear", request=request)
        if request.url.path.endswith("/jwks.json"):
            self.jwks_calls += 1
            key = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(self.key.public_key()))
            key.update(kid=self.kid, alg="ES256", use="sig")
            return httpx.Response(200, json={"keys": [key]})
        if request.url.path.endswith("/logout"):
            return httpx.Response(503 if self.logout_unavailable else 204)
        data = json.loads(request.content)
        if request.url.params.get("grant_type") == "password":
            self.login_calls += 1
            if data.get("password") != "correct-test-password":
                return httpx.Response(400, json={"message": "wrong secret password"})
        else:
            self.refresh_calls += 1
            time.sleep(self.refresh_delay)
            self.expired = False
        return httpx.Response(200, json={"access_token": self.token(sub=str(uuid4())) if self.switched_subject else self.token(),
                                       "refresh_token": "test-refresh-token"})
