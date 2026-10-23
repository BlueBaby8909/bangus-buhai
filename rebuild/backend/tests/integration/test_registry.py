"""Real PostgreSQL/HTTP registry and cryptographic device simulation; no cloud/device secrets."""
import dataclasses
import json
import secrets
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import command
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.core.application import create_app
from backend.database.config import database_url, make_engine
from backend.database.events import persist_event
from backend.database.migrate import configuration
from backend.database.models import (AuthSession, Binding, Device, DeviceChallenge, DeviceClaim,
    DeviceConfiguration, DeviceEvent, DeviceInventory, Hatchery, Membership, RegistryAudit, Tank, UserIdentity)
from backend.features.accounts.service import AccountService
from backend.features.registry.errors import RegistryError
from backend.features.registry.owner import prepare
from backend.features.registry.security import code_hash, digest
from backend.features.registry.service import RegistryService
from backend.tests.auth_support import FakeAuth
from backend.tests.registry_support import SimulatedDevice
from contracts import Telemetry


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = make_engine(test=True)

    @classmethod
    def tearDownClass(cls):
        cls.admin.dispose()

    def setUp(self):
        self.schema = "t11_test_" + uuid4().hex
        with self.admin.begin() as connection:
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
        self.accounts = AccountService(self.fake.settings, self.engine, self.fake.provider, lambda: self.clock)
        self.registry = RegistryService(self.engine, self.fake.settings.token_key, lambda: self.clock)
        self.hatchery, self.other_hatchery, self.user, self.other_user, self.tank, self.other_tank = [uuid4() for _ in range(6)]
        with Session(self.engine) as session, session.begin():
            session.add_all([Hatchery(id=self.hatchery, name="Home"), Hatchery(id=self.other_hatchery, name="Other"),
                UserIdentity(id=self.user, provider_issuer=self.fake.settings.issuer, provider_subject=self.fake.subject, active=True),
                UserIdentity(id=self.other_user, provider_issuer=self.fake.settings.issuer, provider_subject=uuid4(), active=True)])
            session.flush()
            session.add_all([Membership(user_id=self.user, hatchery_id=self.hatchery),
                Membership(user_id=self.other_user, hatchery_id=self.other_hatchery),
                Tank(id=self.tank, hatchery_id=self.hatchery, name="First"),
                Tank(id=self.other_tank, hatchery_id=self.other_hatchery, name="Private")])
        self.app = create_app(service=self.accounts)
        self.client = self.enterContext(TestClient(self.app, base_url="http://127.0.0.1",
            headers={"Origin": self.fake.settings.origins[0]}))
        self.device_client = self.enterContext(TestClient(self.app, base_url="http://127.0.0.1"))
        login = self.client.post("/api/v1/auth/login", json={"email": "operator@example.test", "password": "correct-test-password"})
        self.assertEqual(login.status_code, 200)
        self.client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        self.base = f"/api/v1/hatcheries/{self.hatchery}"
        self.temp = self.enterContext(tempfile.TemporaryDirectory(prefix="bb-t11-synthetic-"))

    def cleanup(self):
        self.engine.dispose()
        with self.admin.begin() as connection:
            connection.execute(sa.schema.DropSchema(self.schema, cascade=True))

    def prepare(self, identity="BB-000000000011", *, existing=None):
        device = SimulatedDevice(identity)
        output = Path(self.temp) / (identity + ".json")
        prepare(self.engine, identity, device.pem, output, existing_device=existing)
        return device, json.loads(output.read_text())["claim_code"]

    def start(self, device, code, *, tank=None):
        response = self.client.post(self.base + "/device-claims", json={"device_id": device.external_id,
            "claim_code": code, "tank_id": str(tank or self.tank)})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def challenge(self, device, purpose="sync", config=None):
        data = dict(device_id=device.external_id, purpose=purpose)
        if config:
            data.update(configuration_revision=config["document"]["revision"], configuration_digest=config["digest"])
        response = self.device_client.post("/api/device/v1/challenges", json=data)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def proof(self, device, challenge):
        return self.device_client.post("/api/device/v1/proofs", json={"challenge_id": challenge["challenge_id"],
            "signature": device.signature(challenge)})

    def enroll(self, identity="BB-000000000011"):
        device, code = self.prepare(identity)
        claim = self.start(device, code)
        response = self.proof(device, self.challenge(device))
        self.assertEqual(response.status_code, 200, response.text)
        return device, code, claim, response.json()["configuration"]

    def get_device(self, device):
        response = self.client.get(self.base + "/devices/" + device.external_id)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_claim_proof_confirmation_and_secret_free_views(self):
        device, code, claim, config = self.enroll()
        self.assertEqual(config["status"], "pending")
        self.assertEqual(config["digest"], digest(config["document"]))
        response = self.proof(device, self.challenge(device, "confirm", config))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["state"], "complete")
        self.assertEqual(self.client.get(self.base + "/device-claims/" + claim["id"]).json()["state"], "complete")
        view = self.get_device(device)
        self.assertTrue(view["verified"])
        self.assertEqual(view["configuration"]["status"], "confirmed")
        self.assertNotIn(code, json.dumps(view))
        self.assertNotIn("CERTIFICATE", json.dumps(view))
        with Session(self.engine) as session:
            inventory = session.get(DeviceInventory, device.external_id)
            self.assertIsNone(inventory.claim_hash)
            self.assertEqual(session.exec(select(Device)).one().hatchery_id, self.hatchery)
            self.assertNotIn(code, json.dumps([row.model_dump(mode="json") for row in session.exec(select(RegistryAudit)).all()]))

    def test_unknown_wrong_code_body_validation_and_browser_guards(self):
        device, code = self.prepare()
        payload = dict(device_id=device.external_id, claim_code=secrets.token_urlsafe(32), tank_id=str(self.tank))
        self.assertEqual(self.client.post(self.base + "/device-claims", json=payload).status_code, 404)
        payload["device_id"] = "BB-000000000099"
        self.assertEqual(self.client.post(self.base + "/device-claims", json=payload).status_code, 404)
        payload.update(device_id=device.external_id, claim_code=code, user_id=str(self.other_user))
        result = self.client.post(self.base + "/device-claims", json=payload)
        self.assertEqual(result.status_code, 422)
        self.assertNotIn(code, result.text)
        self.assertEqual(self.client.post(self.base + "/tanks", json={"name": "safe"}, headers={"X-CSRF-Token": "bad"}).status_code, 403)
        self.assertEqual(self.client.post(self.base + "/tanks", json={"name": "safe"}, headers={"Origin": "https://attacker.test"}).status_code, 403)

    def test_expired_and_cancelled_claim_never_own_device(self):
        device, code = self.prepare()
        claim = self.start(device, code)
        old = self.challenge(device)
        self.clock += timedelta(minutes=10)
        self.assertEqual(self.proof(device, old).status_code, 401)
        result = self.client.get(self.base + "/device-claims/" + claim["id"])
        self.assertEqual(result.json()["state"], "expired")
        new = self.start(device, code)
        challenge = self.challenge(device)
        self.assertEqual(self.client.post(self.base + "/device-claims/" + new["id"] + "/cancel").json()["state"], "cancelled")
        self.assertEqual(self.proof(device, challenge).status_code, 409)
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(Device)).all(), [])
            self.assertEqual(session.get(DeviceInventory, device.external_id).claim_hash, code_hash(code))

    def test_challenge_expiry_boundary_forgery_wrong_key_and_replay(self):
        device, code = self.prepare()
        self.start(device, code)
        challenge = self.challenge(device)
        wrong = SimulatedDevice(device.external_id)
        self.assertEqual(self.proof(wrong, challenge).status_code, 401)
        response = self.proof(device, challenge)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.proof(device, challenge).status_code, 409)
        current = self.challenge(device)
        self.clock += timedelta(minutes=2)
        self.assertEqual(self.proof(device, current).status_code, 401)

    def test_concurrent_cross_hatchery_claims_have_one_reservation(self):
        device, code = self.prepare()
        def attempt(pair):
            hatchery, user, tank = pair
            try:
                return self.registry.start_claim(hatchery, user, device.external_id, tank, code, str(user))["state"]
            except RegistryError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [(self.hatchery, self.user, self.tank),
                (self.other_hatchery, self.other_user, self.other_tank)]))
        self.assertCountEqual(results, ["pending_proof", 409])

    def test_concurrent_proofs_create_one_device_binding_and_config(self):
        device, code = self.prepare()
        self.start(device, code)
        challenge = self.challenge(device)
        signature = device.signature(challenge)
        def attempt(_):
            try:
                return self.registry.proof(UUID(challenge["challenge_id"]), signature, "concurrent")["state"]
            except RegistryError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(attempt, range(2))), ["awaiting_confirmation", 409])
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(Device)).all()), 1)
            self.assertEqual(len(session.exec(select(Binding)).all()), 1)
            self.assertEqual(len(session.exec(select(DeviceConfiguration)).all()), 1)

    def test_claim_commit_failure_rolls_back_all_ownership_changes(self):
        device, code = self.prepare()
        self.start(device, code)
        challenge = self.challenge(device)
        with patch.object(self.registry, "audit", side_effect=RuntimeError("injected rollback")):
            with self.assertRaises(RuntimeError):
                self.registry.proof(UUID(challenge["challenge_id"]), device.signature(challenge), "rollback")
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(Device)).all(), [])
            self.assertEqual(session.exec(select(Binding)).all(), [])
            self.assertEqual(session.exec(select(DeviceConfiguration)).all(), [])
            self.assertIsNone(session.get(DeviceChallenge, UUID(challenge["challenge_id"])).used_at)
            self.assertEqual(session.get(DeviceInventory, device.external_id).claim_hash, code_hash(code))
        self.assertEqual(self.proof(device, challenge).status_code, 200)

    def test_proof_rechecks_disabled_user_revoked_membership_and_archived_tank(self):
        device, code = self.prepare()
        self.start(device, code)
        challenge = self.challenge(device)
        with Session(self.engine) as session, session.begin():
            session.get(UserIdentity, self.user).active = False
        self.assertEqual(self.proof(device, challenge).status_code, 403)
        self.assertEqual(self.client.get(self.base + "/tanks").status_code, 403)
        with Session(self.engine) as session, session.begin():
            session.get(UserIdentity, self.user).active = True
            session.get(Membership, (self.hatchery, self.user)).active = False
        self.assertEqual(self.proof(device, challenge).status_code, 403)
        with Session(self.engine) as session, session.begin():
            session.get(Membership, (self.hatchery, self.user)).active = True
            session.get(Tank, self.tank).archived_at = self.clock
        self.assertEqual(self.proof(device, challenge).status_code, 409)
        with Session(self.engine) as session:
            self.assertIsNone(session.get(DeviceInventory, device.external_id).device_id)

    def test_lost_response_restart_and_cancellation_after_ownership(self):
        device, code, claim, config = self.enroll()
        self.assertEqual(self.client.post(self.base + "/device-claims/" + claim["id"] + "/cancel").status_code, 409)
        restarted = RegistryService(self.engine, self.fake.settings.token_key, lambda: self.clock)
        challenge = restarted.challenge(device.external_id, "sync", None, None, "restart")
        result = restarted.proof(challenge["challenge_id"], device.signature(challenge), "restart")
        self.assertEqual(result["configuration"]["digest"], config["digest"])
        self.assertEqual(result["state"], "awaiting_confirmation")
        self.assertEqual(self.client.post(self.base + "/device-claims", json={"device_id": device.external_id,
            "claim_code": code, "tank_id": str(self.tank)}).status_code, 404)

    def test_stale_confirmation_and_current_configuration_confirmation(self):
        device, _, _, config = self.enroll()
        old = self.challenge(device, "confirm", config)
        next_tank = self.registry.create_tank(self.hatchery, self.user, "Second")
        self.registry.assign(self.hatchery, self.user, device.external_id, next_tank["id"], 1)
        self.assertEqual(self.proof(device, old).status_code, 409)
        self.clock += timedelta(minutes=1)
        current = self.proof(device, self.challenge(device)).json()["configuration"]
        self.assertEqual(current["document"]["revision"], 2)
        self.assertEqual(self.proof(device, self.challenge(device, "confirm", current)).json()["state"], "complete")

    def test_reassignment_retains_event_payload_and_binding_history(self):
        device, _, _, config = self.enroll()
        fixture = Path(__file__).resolve().parents[3] / "contracts/fixtures/valid/telemetry-default-ph.json"
        data = json.loads(fixture.read_text())
        data.update(device_id=device.external_id, binding_id=config["document"]["binding_id"])
        event = Telemetry.model_validate(data)
        with Session(self.engine) as session, session.begin():
            self.assertEqual(persist_event(session, event), "stored")
        next_tank = self.registry.create_tank(self.hatchery, self.user, "Second")
        result = self.registry.assign(self.hatchery, self.user, device.external_id, next_tank["id"], 1)
        self.assertNotEqual(str(result["binding"]["id"]), data["binding_id"])
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(DeviceEvent)).one().payload, event.model_dump(mode="json"))
            bindings = session.exec(select(Binding).order_by(Binding.started_at)).all()
            self.assertEqual(len(bindings), 2)
            self.assertEqual(bindings[0].ended_at, bindings[1].started_at)

    def test_multiple_devices_one_tank_and_concurrent_assignments(self):
        device, _, _, _ = self.enroll()
        self.clock += timedelta(minutes=1)
        self.enroll("BB-000000000012")
        tanks = [self.registry.create_tank(self.hatchery, self.user, name) for name in ("Second", "Third")]
        def attempt(tank):
            try:
                self.registry.assign(self.hatchery, self.user, device.external_id, tank["id"], 1)
                return 200
            except RegistryError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(attempt, tanks)), [200, 409])
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(Binding).where(Binding.ended_at.is_(None))).all()), 2)

    def test_archive_restore_and_no_automatic_reassignment(self):
        device, _, _, _ = self.enroll()
        url = self.base + "/devices/" + device.external_id
        self.assertEqual(self.client.post(url + "/archive", json={"expected_version": 1}).status_code, 409)
        self.assertEqual(self.client.post(self.base + f"/tanks/{self.tank}/archive", json={"expected_version": 1}).status_code, 409)
        unassigned = self.client.post(url + "/assignment", json={"tank_id": None, "expected_version": 1})
        self.assertEqual(unassigned.status_code, 200, unassigned.text)
        archived = self.client.post(url + "/archive", json={"expected_version": 2})
        self.assertEqual(archived.status_code, 200, archived.text)
        self.assertEqual(self.client.get(self.base + "/devices").json()["items"], [])
        self.assertEqual(len(self.client.get(self.base + "/devices?include_archived=true").json()["items"]), 1)
        restored = self.client.post(url + "/restore", json={"expected_version": 3})
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertIsNone(restored.json()["binding"])
        tank = self.client.post(self.base + f"/tanks/{self.tank}/archive", json={"expected_version": 1})
        self.assertEqual(tank.status_code, 200, tank.text)
        self.assertEqual(self.client.post(url + "/assignment", json={"tank_id": str(self.tank), "expected_version": 4}).status_code, 409)
        self.assertEqual(self.client.post(self.base + f"/tanks/{self.tank}/restore", json={"expected_version": 2}).status_code, 200)

    def test_assignment_racing_tank_archive_cannot_leave_active_archived_tank(self):
        device, _, _, _ = self.enroll()
        tank = self.registry.create_tank(self.hatchery, self.user, "Race target")
        def attempt(archive):
            try:
                if archive:
                    self.registry.change_tank(self.hatchery, self.user, tank["id"], 1, archive=True)
                else:
                    self.registry.assign(self.hatchery, self.user, device.external_id, tank["id"], 1)
                return 200
            except RegistryError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(attempt, [True, False])), [200, 409])

    def test_scope_resource_hiding_and_pagination(self):
        self.assertEqual(self.client.get(f"/api/v1/hatcheries/{self.other_hatchery}/tanks").status_code, 403)
        self.assertEqual(self.client.get(self.base + f"/tanks/{self.other_tank}").status_code, 404)
        for name in ("second", "third"):
            self.assertEqual(self.client.post(self.base + "/tanks", json={"name": name}).status_code, 201)
        first = self.client.get(self.base + "/tanks?limit=2").json()
        second = self.client.get(self.base + "/tanks", params={"limit": 2, "cursor": first["next_cursor"]}).json()
        self.assertEqual(len(first["items"]) + len(second["items"]), 3)
        self.assertEqual(len({row["id"] for row in first["items"] + second["items"]}), 3)
        self.assertEqual(self.client.get(self.base + "/tanks?cursor=bad").status_code, 422)
        self.assertEqual(self.client.get(self.base + "/tanks?limit=201").status_code, 422)
        renamed = self.client.patch(self.base + f"/tanks/{self.tank}", json={"name": " Changed ", "expected_version": 1})
        self.assertEqual(renamed.json()["name"], "Changed")
        self.assertEqual(self.client.patch(self.base + f"/tanks/{self.tank}", json={"name": "stale", "expected_version": 1}).status_code, 409)

    def test_unverified_legacy_device_requires_explicit_attachment_and_proof(self):
        identity = uuid4()
        with Session(self.engine) as session, session.begin():
            session.add(Device(id=identity, external_id="BB-000000000011", hatchery_id=self.hatchery))
        with self.assertRaises(RegistryError) as caught:
            self.registry.assign(self.hatchery, self.user, "BB-000000000011", self.tank, 1)
        self.assertEqual(caught.exception.code, "device_unverified")
        device, code = self.prepare(existing=identity)
        self.assertIsNone(code)
        self.assertEqual(self.proof(device, self.challenge(device)).status_code, 200)
        result = self.registry.assign(self.hatchery, self.user, device.external_id, self.tank, 1)
        self.assertEqual(result["id"], identity)
        self.assertTrue(result["verified"])

    def test_preparation_refuses_duplicate_overwrite_and_audit_is_append_only(self):
        device, _ = self.prepare()
        output = Path(self.temp) / (device.external_id + ".json")
        original = output.read_bytes()
        with self.assertRaises(ValueError):
            prepare(self.engine, device.external_id, device.pem, output)
        self.assertEqual(output.read_bytes(), original)
        other = Path(self.temp) / "new.json"
        with self.assertRaises(sa.exc.IntegrityError):
            prepare(self.engine, device.external_id, device.pem, other)
        self.assertFalse(other.exists())
        for sql in ("DELETE FROM registry_audit", "UPDATE registry_audit SET action='changed'"):
            with self.assertRaises(sa.exc.IntegrityError):
                with self.engine.begin() as connection:
                    connection.execute(sa.text(sql))

    def test_populated_t10_upgrade_preserves_sessions_resources_and_events(self):
        device_id, binding_id = uuid4(), uuid4()
        fixture = Path(__file__).resolve().parents[3] / "contracts/fixtures/valid/telemetry-default-ph.json"
        data = json.loads(fixture.read_text())
        data.update(device_id="BB-000000000011", binding_id=str(binding_id))
        event = Telemetry.model_validate(data)
        with Session(self.engine) as session, session.begin():
            session.add(Device(id=device_id, external_id=event.device_id, hatchery_id=self.hatchery))
            session.flush()
            session.add(Binding(id=binding_id, device_id=device_id, tank_id=self.tank, hatchery_id=self.hatchery))
            session.flush()
            persist_event(session, event)
        with self.engine.begin() as connection:
            config = configuration()
            config.attributes["connection"] = connection
            command.downgrade(config, "0002_t10")
            self.assertEqual(connection.scalar(sa.text("SELECT count(*) FROM device_events")), 1)
            command.upgrade(config, "head")
        self.assertEqual(self.client.get("/api/v1/me").status_code, 200)
        with Session(self.engine) as session:
            self.assertEqual(session.get(Device, device_id).version, 1)
            self.assertEqual(session.get(Binding, binding_id).tank_id, self.tank)
            self.assertEqual(session.exec(select(DeviceEvent)).one().payload, event.model_dump(mode="json"))
            self.assertEqual(session.exec(select(DeviceInventory)).all(), [])
            self.assertEqual(len(session.exec(select(AuthSession)).all()), 1)

    def test_request_limits_https_and_proof_errors_do_not_echo_secrets(self):
        device, _ = self.prepare()
        response = self.device_client.post("/api/device/v1/proofs", json={"challenge_id": str(uuid4()), "signature": "private-signature", "private": "do-not-echo"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("do-not-echo", response.text)
        self.assertEqual(self.device_client.post("/api/device/v1/challenges", content=b"x" * 16385,
            headers={"Content-Type": "application/json"}).status_code, 413)
        settings = dataclasses.replace(self.fake.settings, development=False, origins=("https://app.example.test",))
        service = AccountService(settings, self.engine, self.fake.provider)
        with TestClient(create_app(service=service), base_url="http://app.example.test") as client:
            self.assertEqual(client.post("/api/device/v1/challenges", json={"device_id": device.external_id, "purpose": "sync"}).status_code, 503)
        result = self.client.options(self.base + f"/tanks/{self.tank}", headers={"Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "X-CSRF-Token"})
        self.assertEqual(result.status_code, 200)

    def test_shared_throttling_is_separate_from_login_and_ignores_forwarded_ip(self):
        device, _ = self.prepare()
        for number in range(10):
            response = self.device_client.post("/api/device/v1/challenges", headers={"X-Forwarded-For": f"192.0.2.{number}"},
                json={"device_id": device.external_id, "purpose": "sync"})
            self.assertEqual(response.status_code, 200, response.text)
        response = self.device_client.post("/api/device/v1/challenges", json={"device_id": device.external_id, "purpose": "sync"})
        self.assertEqual(response.status_code, 429)
        self.assertTrue(1 <= int(response.headers["Retry-After"]) <= 60)
        response = self.client.post("/api/v1/auth/login", json={"email": "operator@example.test", "password": "correct-test-password"})
        self.assertEqual(response.status_code, 200)

    def test_valid_device_key_alone_does_not_claim_or_target_later_claim(self):
        device, code = self.prepare()
        old = self.challenge(device)
        claim = self.start(device, code)
        response = self.proof(device, old)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"state": "unclaimed", "configuration": None})
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(Device)).all(), [])
            self.assertEqual(session.get(DeviceClaim, UUID(claim["id"])).state, "pending_proof")
        self.assertEqual(self.proof(device, self.challenge(device)).status_code, 200)

    def test_claim_retry_reuses_reservation_and_old_cancelled_proof_cannot_claim_new(self):
        device, code = self.prepare()
        first = self.start(device, code)
        self.assertEqual(self.start(device, code)["id"], first["id"])
        old = self.challenge(device)
        self.client.post(self.base + "/device-claims/" + first["id"] + "/cancel")
        next_claim = self.start(device, code)
        self.assertNotEqual(next_claim["id"], first["id"])
        self.assertEqual(self.proof(device, old).status_code, 409)
        self.assertEqual(self.proof(device, self.challenge(device)).status_code, 200)

    def test_claim_start_limits_persist_across_services(self):
        device, _ = self.prepare()
        wrong = secrets.token_urlsafe(32)
        for _ in range(10):
            with self.assertRaises(RegistryError) as caught:
                RegistryService(self.engine, self.fake.settings.token_key, lambda: self.clock).start_claim(
                    self.hatchery, self.user, device.external_id, self.tank, wrong, "same-client")
            self.assertEqual(caught.exception.status, 404)
        with self.assertRaises(RegistryError) as caught:
            self.registry.start_claim(self.hatchery, self.user, device.external_id, self.tank, wrong, "same-client")
        self.assertEqual(caught.exception.status, 429)

    def test_scoped_device_binding_history_names_and_foreign_targets(self):
        device, _, claim, _ = self.enroll()
        url = self.base + "/devices/" + device.external_id
        response = self.client.patch(url, json={"display_name": " Nursery sensor ", "expected_version": 1})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["display_name"], "Nursery sensor")
        self.assertEqual(self.client.post(url + "/assignment", json={"tank_id": str(self.other_tank), "expected_version": 2}).status_code, 404)
        self.assertEqual(self.client.post(url + "/assignment", json={"tank_id": str(uuid4()), "expected_version": 2}).status_code, 404)
        self.assertEqual(len(self.client.get(url + "/bindings").json()["items"]), 1)
        self.assertEqual(len(self.client.get(self.base + "/devices").json()["items"]), 1)
        self.assertEqual(self.client.get(url.lower()).status_code, 422)
        self.assertEqual(self.client.get(self.base + "/device-claims/" + str(uuid4())).status_code, 404)

    def test_preparation_commit_failure_removes_only_its_new_file(self):
        device = SimulatedDevice()
        target = Path(self.temp) / "failed.json"
        def fail(connection):
            raise RuntimeError("injected commit failure")
        sa.event.listen(self.engine, "commit", fail)
        try:
            with self.assertRaises(RuntimeError):
                prepare(self.engine, device.external_id, device.pem, target)
        finally:
            sa.event.remove(self.engine, "commit", fail)
        self.assertFalse(target.exists())
        with Session(self.engine) as session:
            self.assertIsNone(session.get(DeviceInventory, device.external_id))
        repository_target = Path(__file__).resolve().parents[2] / "unwanted-private-output.json"
        with self.assertRaises(ValueError):
            prepare(self.engine, device.external_id, device.pem, repository_target)
        self.assertFalse(repository_target.exists())

    def test_preparation_rejects_shared_keys_and_implicit_legacy_attachment(self):
        device, _ = self.prepare()
        reused = SimulatedDevice("BB-000000000012", key=device.key)
        output = Path(self.temp) / "reused-key.json"
        with self.assertRaises(sa.exc.IntegrityError):
            prepare(self.engine, reused.external_id, reused.pem, output)
        self.assertFalse(output.exists())
        legacy = SimulatedDevice("BB-000000000013")
        with Session(self.engine) as session, session.begin():
            session.add(Device(external_id=legacy.external_id, hatchery_id=self.hatchery))
        with self.assertRaises(ValueError):
            prepare(self.engine, legacy.external_id, legacy.pem, Path(self.temp) / "implicit-legacy.json")
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(DeviceInventory)).all()), 1)
