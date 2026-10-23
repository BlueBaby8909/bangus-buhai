"""Actual PostgreSQL + HTTP + generated JWTs, isolated from all existing schemas."""
import argparse
import dataclasses
import json
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import command
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.core.application import create_app
from backend.database.config import database_url, make_engine
from backend.database.events import persist_event
from backend.database.migrate import configuration
from backend.database.models import AuthLoginBucket, AuthSession, Binding, Device, DeviceEvent, Hatchery, Membership, Tank, UserIdentity
from backend.features.accounts.errors import AuthError
from backend.features.accounts.owner import execute
from backend.features.accounts.router import hatchery_operator
from backend.features.accounts.service import AccountService, Operator
from backend.tests.auth_support import FakeAuth
from contracts import Telemetry


class AccountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_engine = make_engine(test=True)

    @classmethod
    def tearDownClass(cls):
        cls.admin_engine.dispose()

    def setUp(self):
        self.schema = "t10_test_" + uuid4().hex
        with self.admin_engine.begin() as connection:
            connection.execute(sa.schema.CreateSchema(self.schema))
        self.engine = sa.create_engine(database_url(test=True), hide_parameters=True,
            connect_args={"options": f"-csearch_path={self.schema}", "connect_timeout": 5})
        self.addCleanup(self.cleanup)
        with self.engine.begin() as connection:
            config = configuration()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        self.fake = FakeAuth()
        self.addCleanup(self.fake.client.close)
        self.clock = datetime.now(timezone.utc)
        self.service = AccountService(self.fake.settings, self.engine, self.fake.provider, lambda: self.clock)
        self.hatchery, self.user = uuid4(), uuid4()
        with Session(self.engine) as session, session.begin():
            session.add(Hatchery(id=self.hatchery, name="Owned hatchery"))
            session.add(UserIdentity(id=self.user, provider_issuer=self.fake.settings.issuer,
                provider_subject=self.fake.subject, email="operator@example.test", active=True))
            session.flush()
            session.add(Membership(user_id=self.user, hatchery_id=self.hatchery))
        self.app = create_app(service=self.service)

        @self.app.get("/api/v1/test/hatcheries/{hatchery_id}")
        def scoped_probe(operator: Operator = Depends(hatchery_operator)):
            return {"allowed": True}

        self.client = self.enterContext(TestClient(self.app, base_url="http://127.0.0.1",
                                                  headers={"Origin": self.fake.settings.origins[0]}))

    def cleanup(self):
        self.engine.dispose()
        with self.admin_engine.begin() as connection:
            connection.execute(sa.schema.DropSchema(self.schema, cascade=True))

    def login(self, password="correct-test-password"):
        return self.client.post("/api/v1/auth/login", json={"email": "operator@example.test", "password": password})

    def token(self):
        return self.client.cookies.get(self.service.settings.cookie_name)

    def force_refresh(self):
        token = self.fake.token(iat=int(time.time()) - 900, exp=int(time.time()) - 1)
        payload = self.service.cipher.encrypt(json.dumps({"access": token, "refresh": "test-refresh-token"}).encode()).decode()
        with Session(self.engine) as session, session.begin():
            session.execute(sa.update(AuthSession).values(encrypted_tokens=payload))

    def test_login_me_encrypted_storage_logout_and_cookie_replay(self):
        response = self.login()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["role"], "operator")
        self.assertEqual(response.json()["hatcheries"][0]["id"], str(self.hatchery))
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=lax", response.headers["set-cookie"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        token, csrf = self.token(), response.json()["csrf_token"]
        with Session(self.engine) as session:
            row = session.exec(select(AuthSession)).one()
            self.assertNotEqual(row.token_hash, token)
            self.assertNotIn("test-refresh-token", row.encrypted_tokens)
            self.assertNotIn("access_token", response.text)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 200)
        response = self.client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
        self.assertEqual(response.status_code, 204, response.text)
        self.client.cookies.set(self.fake.settings.cookie_name, token)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)
        with Session(self.engine) as session:
            row = session.exec(select(AuthSession)).one()
            self.assertIsNotNone(row.revoked_at)
            self.assertIsNone(row.encrypted_tokens)

    def test_production_cookie_is_secure_host_only(self):
        settings = dataclasses.replace(self.fake.settings, development=False, origins=("https://app.example.test",))
        service = AccountService(settings, self.engine, self.fake.provider)
        with TestClient(create_app(service=service), base_url="https://app.example.test") as client:
            response = client.post("/api/v1/auth/login", headers={"Origin": settings.origins[0]},
                json={"email": "operator@example.test", "password": "correct-test-password"})
            self.assertEqual(response.status_code, 200)
            cookie = response.headers["set-cookie"]
            self.assertIn("__Host-bb_session=", cookie)
            self.assertIn("Secure", cookie)
            self.assertNotIn("Domain=", cookie)
        with TestClient(create_app(service=service), base_url="http://app.example.test") as client:
            response = client.post("/api/v1/auth/login", headers={"Origin": settings.origins[0]},
                json={"email": "operator@example.test", "password": "correct-test-password"})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "https_required")

    def test_wrong_credentials_and_validation_are_secret_free(self):
        response = self.login("private-wrong-password")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("private-wrong-password", response.text)
        response = self.client.post("/api/v1/auth/login", json={"email": 42, "password": "private-validation-password"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("private-validation-password", response.text)
        response = self.client.post("/api/v1/auth/login", json={"email": "operator@example.test", "password": "x" * 10000})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)

    def test_external_identity_does_not_auto_enroll(self):
        self.fake.subject = uuid4()
        self.assertEqual(self.login().status_code, 403)
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(UserIdentity)).all()), 1)
            self.assertEqual(len(session.exec(select(AuthSession)).all()), 0)

    def test_disabled_and_missing_membership_fail_closed(self):
        with Session(self.engine) as session, session.begin():
            session.execute(sa.update(UserIdentity).values(active=False))
        self.assertEqual(self.login().status_code, 403)
        with Session(self.engine) as session, session.begin():
            session.execute(sa.update(UserIdentity).values(active=True))
            session.execute(sa.update(Membership).values(active=False))
        self.assertEqual(self.login().status_code, 403)

    def test_hatchery_access_and_live_membership_revocation(self):
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/test/hatcheries/{self.hatchery}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/test/hatcheries/{uuid4()}").status_code, 403)
        execute(argparse.Namespace(command="revoke", user=self.user, hatchery=self.hatchery), self.engine)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 403)

    def test_owner_disable_revokes_all_persistent_sessions(self):
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.login().status_code, 200)
        execute(argparse.Namespace(command="disable", user=self.user), self.engine)
        restarted = AccountService(self.fake.settings, self.engine, self.fake.provider)
        with self.assertRaises(AuthError):
            restarted.authenticate(self.token())
        with Session(self.engine) as session:
            self.assertTrue(all(row.revoked_at is not None and row.encrypted_tokens is None for row in session.exec(select(AuthSession)).all()))

    def test_idle_timeout_boundary_persists_revocation(self):
        self.assertEqual(self.login().status_code, 200)
        self.clock += timedelta(minutes=30)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)

    def test_absolute_timeout_cannot_be_extended_by_requests(self):
        self.assertEqual(self.login().status_code, 200)
        with Session(self.engine) as session, session.begin():
            session.execute(sa.update(AuthSession).values(last_seen_at=self.clock + timedelta(hours=7, minutes=59)))
        self.clock += timedelta(hours=8)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)

    def test_authenticated_request_updates_idle_time(self):
        self.assertEqual(self.login().status_code, 200)
        self.clock += timedelta(minutes=29)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 200)
        self.clock += timedelta(minutes=29)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 200)

    def test_persistent_session_survives_service_restart(self):
        self.assertEqual(self.login().status_code, 200)
        restarted = AccountService(self.fake.settings, self.engine, self.fake.provider)
        self.assertEqual(restarted.authenticate(self.token()).id, self.user)

    def test_simultaneous_refresh_is_serialized(self):
        self.assertEqual(self.login().status_code, 200)
        self.force_refresh()
        self.fake.refresh_delay = 0.05
        token = self.token()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.service.authenticate, [token, token]))
        self.assertEqual([item.id for item in results], [self.user, self.user])
        self.assertEqual(self.fake.refresh_calls, 1)

    def test_refresh_identity_change_revokes_session(self):
        self.assertEqual(self.login().status_code, 200)
        self.force_refresh()
        self.fake.switched_subject = True
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)
        self.fake.switched_subject = False
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)

    def test_provider_outage_does_not_turn_into_access_or_destroy_retry(self):
        self.assertEqual(self.login().status_code, 200)
        self.force_refresh()
        self.fake.unavailable = True
        response = self.client.get("/api/v1/me")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("credential details", response.text)
        self.fake.unavailable = False
        self.assertEqual(self.client.get("/api/v1/me").status_code, 200)

    def test_logout_stays_revoked_during_provider_outage(self):
        response = self.login()
        csrf, token = response.json()["csrf_token"], self.token()
        self.fake.logout_unavailable = True
        self.assertEqual(self.client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code, 204)
        with self.assertRaises(AuthError):
            self.service.authenticate(token)

    def test_origin_csrf_json_and_cors_guards(self):
        response = self.login()
        csrf = response.json()["csrf_token"]
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "wrong"}).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/auth/logout", headers={"Origin": "https://attacker.test", "X-CSRF-Token": csrf}).status_code, 403)
        response = self.client.options("/api/v1/auth/login", headers={"Origin": "https://attacker.test", "Access-Control-Request-Method": "POST"})
        self.assertNotIn("access-control-allow-origin", response.headers)
        response = self.client.options("/api/v1/auth/login", headers={"Access-Control-Request-Method": "POST"})
        self.assertEqual(response.headers.get("access-control-allow-origin"), self.fake.settings.origins[0])
        response = self.client.post("/api/v1/auth/login", content="password=private", headers={"Content-Type": "text/plain"})
        self.assertEqual(response.status_code, 415)

    def test_shared_throttling_cannot_be_bypassed_with_forwarded_header(self):
        for number in range(10):
            response = self.client.post("/api/v1/auth/login", headers={"X-Forwarded-For": f"192.0.2.{number}"},
                json={"email": "operator@example.test", "password": "wrong"})
            self.assertEqual(response.status_code, 401)
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertTrue(1 <= int(response.headers["Retry-After"]) <= 60)
        self.assertEqual(self.fake.login_calls, 10)
        self.clock += timedelta(minutes=1)
        self.assertEqual(self.login().status_code, 200)

    def test_concurrent_attempts_share_limit_across_service_instances(self):
        services = [AccountService(self.fake.settings, self.engine, self.fake.provider, lambda: self.clock)
                    for _ in range(2)]

        def attempt(number):
            try:
                services[number % 2].login("operator@example.test", "wrong", "192.0.2.88")
            except AuthError as error:
                return error.status
            return 200

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(attempt, range(16)))
        self.assertEqual(results.count(401), 10)
        self.assertEqual(results.count(429), 6)
        self.assertEqual(self.fake.login_calls, 10)

    def test_owner_link_is_idempotent_and_preserves_unmapped_identity(self):
        unmapped, subject = uuid4(), uuid4()
        with Session(self.engine) as session, session.begin():
            session.add(UserIdentity(id=unmapped))
        args = argparse.Namespace(command="link", subject=subject, hatchery=self.hatchery, identity=unmapped)
        for _ in range(2):
            self.assertEqual(execute(args, self.engine, self.fake.settings), str(unmapped))
        with Session(self.engine) as session:
            user = session.get(UserIdentity, unmapped)
            self.assertTrue(user.active)
            self.assertEqual(user.provider_subject, subject)
            self.assertEqual(session.get(Membership, (self.hatchery, unmapped)).role, "operator")

    def test_populated_t09_migration_preserves_data_and_disables_unmapped_users(self):
        tank, device = uuid4(), uuid4()
        binding = UUID("97fcde45-4112-41d4-a509-17e5bb1c0d91")
        fixture = Path(__file__).resolve().parents[3] / "contracts/fixtures/valid/telemetry-default-ph.json"
        event = Telemetry.model_validate(json.loads(fixture.read_text(encoding="utf-8")))
        with Session(self.engine) as session, session.begin():
            session.add(Tank(id=tank, hatchery_id=self.hatchery, name="Preserved tank"))
            session.add(Device(id=device, hatchery_id=self.hatchery, external_id=event.device_id))
            session.flush()
            session.add(Binding(id=binding, device_id=device, tank_id=tank, hatchery_id=self.hatchery))
            session.flush()
            self.assertEqual(persist_event(session, event), "stored")
        with self.engine.begin() as connection:
            config = configuration()
            config.attributes["connection"] = connection
            command.downgrade(config, "0001_t09")
            connection.execute(sa.text("UPDATE memberships SET role = 'admin'"))
            command.upgrade(config, "head")
        with Session(self.engine) as session:
            self.assertFalse(session.get(UserIdentity, self.user).active)
            self.assertEqual(session.get(Membership, (self.hatchery, self.user)).role, "operator")
            self.assertEqual(session.get(Tank, tank).name, "Preserved tank")
            self.assertEqual(session.exec(select(DeviceEvent)).one().payload, event.model_dump(mode="json"))


if __name__ == "__main__":
    unittest.main()
