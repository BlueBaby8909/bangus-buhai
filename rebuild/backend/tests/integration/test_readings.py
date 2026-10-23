"""Real PostgreSQL and HTTP; synthetic measurements and mocked provider only."""
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier, Event
from unittest.mock import patch
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from backend.core.application import create_app
from backend.database.config import database_url, make_engine
from backend.database.events import persist_event
from backend.database.migrate import configuration
from backend.database.models import (Binding, Device, DeviceEvent, Hatchery, ManualReading,
    ManualReadingRevision, Membership, ReadingChange, ReadingHistoryState, Tank, UserIdentity)
from backend.features.accounts.service import AccountService
from backend.features.readings.errors import ReadingsError
from backend.features.readings.schemas import CorrectMeasurement, CreateMeasurement, RevisionAction
from backend.features.readings.service import ReadingsService
from backend.features.registry.errors import RegistryError
from backend.tests.auth_support import FakeAuth
from contracts import CommandResult, ContractError, Telemetry

FIXTURES = Path(__file__).resolve().parents[3] / "contracts/fixtures/valid"


class ReadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = make_engine(test=True)

    @classmethod
    def tearDownClass(cls):
        cls.admin.dispose()

    def setUp(self):
        self.schema = "t12_test_" + uuid4().hex
        with self.admin.begin() as connection:
            connection.execute(sa.schema.CreateSchema(self.schema))
        self.engine = sa.create_engine(database_url(test=True), hide_parameters=True,
            connect_args={"options": f"-csearch_path={self.schema}", "connect_timeout": 5})
        self.addCleanup(self.cleanup)
        with self.engine.begin() as connection:
            config = configuration(); config.attributes["connection"] = connection
            command.upgrade(config, "head")
        self.fake = FakeAuth()
        self.addCleanup(self.fake.client.close)
        self.clock = datetime.now(timezone.utc)
        self.accounts = AccountService(self.fake.settings, self.engine, self.fake.provider, lambda: self.clock)
        self.service = ReadingsService(self.engine, self.fake.settings.token_key, lambda: self.clock)
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
        login = self.client.post("/api/v1/auth/login", json={"email": "operator@example.test", "password": "correct-test-password"})
        self.assertEqual(login.status_code, 200)
        self.client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        self.base = f"/api/v1/hatcheries/{self.hatchery}/tanks/{self.tank}"

    def cleanup(self):
        self.engine.dispose()
        with self.admin.begin() as connection:
            connection.execute(sa.schema.DropSchema(self.schema, cascade=True))

    def body(self, **changes):
        return dict(request_id=str(uuid4()), measured_at=(self.clock - timedelta(hours=1)).isoformat(), ph=7.2) | changes

    def create(self, **changes):
        response = self.client.post(self.base + "/manual-readings", json=self.body(**changes))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def history(self, **params):
        response = self.client.get(self.base + "/readings", params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def stored(self, fixture="telemetry-default-ph.json", **changes):
        payload = json.loads((FIXTURES / fixture).read_text()) | changes
        event = (CommandResult if fixture.startswith("result-") else Telemetry).model_validate(payload)
        with Session(self.engine) as session, session.begin():
            device = session.exec(select(Device).where(Device.external_id == event.device_id)).one_or_none()
            if not device:
                device = Device(hatchery_id=self.hatchery, external_id=event.device_id)
                session.add(device); session.flush()
                session.add(Binding(id=UUID(event.binding_id), device_id=device.id, tank_id=self.tank,
                    hatchery_id=self.hatchery, started_at=self.clock - timedelta(days=30)))
                session.flush()
            result = persist_event(session, event)
        return event, result

    def change(self, row, action="correct", **changes):
        body = dict(expected_version=row["version"], reason="Correct test-kit transcription")
        if action == "correct":
            body.update(measured_at=row["measured_at"], ph=7.8)
        body.update(changes)
        path = self.base + "/manual-readings/" + row["id"]
        return self.client.patch(path, json=body) if action == "correct" else self.client.post(path + "/" + action, json=body)

    def test_manual_lifecycle_partial_measurements_and_audit(self):
        first = self.create(instrument="pH test kit", notes="Morning sample")
        self.assertEqual(first["missing_metrics"], ["temperature_c", "turbidity_ntu"])
        self.assertEqual(first["provenance"], "operator_reported_measurement")
        second = self.change(first).json()
        self.assertEqual(second["version"], 2)
        self.assertEqual(second["received_at"], first["received_at"])
        void = self.change(second, "void")
        self.assertEqual(void.status_code, 200)
        self.assertEqual(self.history()["items"], [])
        self.assertTrue(self.history(include_voided=True)["items"][0]["voided"])
        self.assertEqual(self.change(void.json()).status_code, 409)
        restored = self.change(void.json(), "restore")
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["version"], 4)
        revisions = self.client.get(self.base + "/manual-readings/" + first["id"] + "/revisions", params={"limit": 2}).json()
        self.assertEqual([r["version"] for r in revisions["items"]], [4, 3])
        next_page = self.client.get(self.base + "/manual-readings/" + first["id"] + "/revisions",
            params={"before_version": revisions["next_before_version"]}).json()
        self.assertEqual([r["version"] for r in next_page["items"]], [2, 1])
        self.assertEqual(next_page["items"][-1]["ph"], 7.2)
        self.assertEqual(next_page["items"][-1]["actor_id"], str(self.user))
        self.assertEqual(len(self.history()["items"]), 1)

    def test_validation_and_safe_errors(self):
        for changes in ({"ph": None}, {"ph": "7.1"}, {"ph": True}, {"extra": 12}, {"source": "estimated"},
                        {"measured_at": "2026-10-21T00:00:00"}, {"measured_at": 123}, {"measured_at": "123"},
                        {"measured_at": (self.clock + timedelta(minutes=5, microseconds=1)).isoformat()},
                        {"notes": "a" * 2001}):
            with self.subTest(changes=changes):
                response = self.client.post(self.base + "/manual-readings", json=self.body(**changes))
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn("input", response.text)
        for special in ("NaN", "Infinity", "-Infinity"):
            raw = json.dumps(self.body(ph=0)).replace('"ph": 0', '"ph": ' + special)
            self.assertEqual(self.client.post(self.base + "/manual-readings", content=raw,
                headers={"Content-Type": "application/json"}).status_code, 422)
        response = self.client.post(self.base + "/manual-readings", json=self.body(
            measured_at=(self.clock + timedelta(minutes=5)).isoformat()))
        self.assertEqual(response.status_code, 201)

    def test_units_timezone_and_no_quality_classification(self):
        when = (self.clock - timedelta(hours=1)).astimezone(timezone(timedelta(hours=8)))
        row = self.create(measured_at=when.isoformat(), ph=None, temperature_c=28.5, turbidity_ntu=12.1)
        self.assertEqual(datetime.fromisoformat(row["measured_at"].replace("Z", "+00:00")), when)
        self.assertEqual(row["missing_metrics"], ["ph"])
        self.assertNotIn("quality", row)
        self.assertNotIn("relay", row)

    def test_idempotent_creation_and_conflicting_reuse(self):
        body = self.body()
        first = self.client.post(self.base + "/manual-readings", json=body)
        retry = self.client.post(self.base + "/manual-readings", json=body)
        self.assertEqual((first.status_code, retry.status_code), (201, 200))
        self.assertEqual(first.json()["id"], retry.json()["id"])
        self.assertEqual(self.client.post(self.base + "/manual-readings", json=body | {"ph": 8}).status_code, 409)
        corrected = self.change(first.json()).json()
        self.assertEqual(self.client.post(self.base + "/manual-readings", json=body).json()["version"], corrected["version"])
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(ManualReading)).all()), 1)
            self.assertEqual(session.get(ReadingHistoryState, self.hatchery).last_position, 2)

    def test_concurrent_creation_and_conflicting_retries(self):
        body = CreateMeasurement.model_validate(self.body())
        barrier = Barrier(2)
        def create(_):
            barrier.wait()
            return self.service.create(self.hatchery, self.tank, self.user, body)
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(create, range(2)))
        self.assertEqual(sorted(created for _, created in outcomes), [False, True])
        self.assertEqual(outcomes[0][0]["id"], outcomes[1][0]["id"])

    def test_concurrent_corrections_return_one_conflict(self):
        first = self.create()
        barrier = Barrier(2)
        def change(value):
            body = CorrectMeasurement.model_validate(dict(measured_at=first["measured_at"], ph=value,
                expected_version=1, reason="Race test"))
            barrier.wait()
            try:
                self.service.change(self.hatchery, self.tank, self.user, UUID(first["id"]), body, "correct")
                return 200
            except ReadingsError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(sorted(executor.map(change, [7.1, 7.3])), [200, 409])

    def test_stale_versions_and_reasons(self):
        first = self.create()
        for changes in ({"reason": " "}, {"expected_version": True}, {"reason": None}):
            self.assertEqual(self.change(first, **changes).status_code, 422)
        self.assertEqual(self.change(first).status_code, 200)
        self.assertEqual(self.change(first).status_code, 409)
        self.assertEqual(self.change(first, "void").status_code, 409)

    def test_disabled_membership_and_user_rechecked_in_mutation(self):
        body = CreateMeasurement.model_validate(self.body())
        for model, identity, values in ((Membership, (self.hatchery, self.user), {"active": False}),
                                       (UserIdentity, self.user, {"active": False})):
            with Session(self.engine) as session, session.begin():
                row = session.get(model, identity); row.active = False
            with self.assertRaises(RegistryError) as raised:
                self.service.create(self.hatchery, self.tank, self.user, body)
            self.assertEqual(raised.exception.status, 403)
            with Session(self.engine) as session, session.begin():
                session.get(model, identity).active = True

    def test_http_auth_csrf_origins_and_safe_database_error(self):
        no_auth = self.enterContext(TestClient(self.app, base_url="http://127.0.0.1"))
        self.assertEqual(no_auth.get(self.base + "/readings").status_code, 401)
        body = self.body()
        for headers in ({"Origin": "https://evil.example"}, {"X-CSRF-Token": "wrong"}):
            self.assertEqual(self.client.post(self.base + "/manual-readings", json=body, headers=headers).status_code, 403)
        self.assertEqual(self.client.post(self.base + "/manual-readings", content="a" * 16385,
            headers={"Content-Type": "application/json"}).status_code, 413)
        with patch("backend.features.readings.repository.history", side_effect=sa.exc.OperationalError("secret SQL", {}, Exception("private"))):
            response = self.client.get(self.base + "/readings")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": {"code": "readings_unavailable"}})
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_cross_hatchery_and_other_tank_are_hidden(self):
        row = self.create()
        denied = self.base.replace(str(self.hatchery), str(self.other_hatchery)).replace(str(self.tank), str(self.other_tank))
        self.assertEqual(self.client.get(denied + "/readings").status_code, 403)
        wrong_tank = self.base.replace(str(self.tank), str(self.other_tank))
        self.assertEqual(self.client.get(wrong_tank + "/readings/manual/" + row["id"]).status_code, 404)
        self.assertEqual(self.client.post(wrong_tank + "/manual-readings", json=self.body()).status_code, 404)
        with Session(self.engine) as session, session.begin():
            session.add(Membership(user_id=self.user, hatchery_id=self.other_hatchery))
        self.assertEqual(self.client.get(denied + "/readings/manual/" + row["id"]).status_code, 404)

    def test_another_operator_can_correct_and_is_attributed(self):
        row = self.create()
        with Session(self.engine) as session, session.begin():
            session.add(Membership(user_id=self.other_user, hatchery_id=self.hatchery))
        result = self.service.change(self.hatchery, self.tank, self.other_user, UUID(row["id"]),
            CorrectMeasurement(measured_at=row["measured_at"], ph=8, expected_version=1, reason="Retested"), "correct")
        self.assertEqual(result["actor_id"], self.other_user)
        self.assertEqual(result["created_by"], self.user)

    def test_archived_tank_readable_but_all_manual_writes_blocked(self):
        row = self.create()
        with Session(self.engine) as session, session.begin():
            session.get(Tank, self.tank).archived_at = self.clock
        self.assertEqual(len(self.history()["items"]), 1)
        self.assertEqual(self.client.get(self.base + "/readings/manual/" + row["id"]).status_code, 200)
        self.assertEqual(self.client.get(self.base + "/manual-readings/" + row["id"] + "/revisions").status_code, 200)
        self.assertEqual(self.client.post(self.base + "/manual-readings", json=self.body()).status_code, 409)
        for action in ("correct", "void", "restore"):
            self.assertEqual(self.change(row, action).status_code, 409)
        with Session(self.engine) as session, session.begin():
            session.get(Tank, self.tank).archived_at = None
        self.assertEqual(self.change(row).status_code, 200)

    def test_device_provenance_unsynchronized_and_command_exclusion(self):
        event, _ = self.stored()
        self.stored(seq=event.seq + 1, time_quality="unsynchronized", measured_at=None)
        self.stored("result-applied.json", seq=event.seq + 2)
        measured = self.history()
        self.assertEqual(len(measured["items"]), 1)
        self.assertEqual(measured["items"][0]["telemetry"], event.model_dump(mode="json"))
        received = self.history(time_basis="received")
        self.assertEqual(len(received["items"]), 2)
        self.assertTrue(any(row["measured_at"] is None for row in received["items"]))
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(ReadingChange)).all()), 2)
        detail = self.client.get(self.base + "/readings/device/" + measured["items"][0]["id"])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(self.client.patch(self.base + "/manual-readings/" + measured["items"][0]["id"],
            json=dict(expected_version=1, reason="Cannot edit device captures", measured_at=event.measured_at, ph=7)).status_code, 404)

    def test_duplicate_telemetry_and_conflict_do_not_add_history(self):
        event, result = self.stored()
        self.assertEqual(result, "stored")
        self.assertEqual(self.stored()[1], "duplicate")
        with self.assertRaises(ContractError) as conflict:
            self.stored(fw_version="changed-content")
        self.assertEqual(conflict.exception.code, "event_conflict")
        with self.assertRaises(ContractError) as conflict:
            self.stored("result-applied.json", seq=event.seq, boot_id=event.boot_id)
        self.assertEqual(conflict.exception.code, "event_conflict")
        with Session(self.engine) as session:
            self.assertEqual(session.get(ReadingHistoryState, self.hatchery).last_position, 1)

    def test_original_attribution_survives_reassignment(self):
        event, _ = self.stored()
        with Session(self.engine) as session, session.begin():
            old = session.get(Binding, UUID(event.binding_id)); old.ended_at = self.clock
            new_tank = Tank(hatchery_id=self.hatchery, name="New")
            session.add(new_tank); session.flush()
            session.add(Binding(device_id=old.device_id, hatchery_id=self.hatchery, tank_id=new_tank.id, started_at=self.clock))
        row = self.history()["items"][0]
        self.assertEqual(row["tank_id"], str(self.tank))
        self.assertEqual(row["binding_id"], event.binding_id)
        self.assertEqual(row["telemetry"], event.model_dump(mode="json"))

    def test_snapshot_pagination_survives_edits_voids_and_late_inserts(self):
        initial = [self.create(measured_at=(self.clock - timedelta(hours=h)).isoformat()) for h in (1, 2, 3, 4)]
        first = self.history(limit=1)
        self.create(measured_at=(self.clock - timedelta(hours=2, minutes=30)).isoformat())
        self.assertEqual(self.change(initial[1], measured_at=(self.clock - timedelta(minutes=30)).isoformat()).status_code, 200)
        self.assertEqual(self.change(initial[2], "void").status_code, 200)
        self.stored()
        seen = first["items"][:]
        cursor = first["next_cursor"]
        while cursor:
            page = self.history(limit=1, cursor=cursor)
            self.assertEqual(page["snapshot_position"], first["snapshot_position"])
            seen.extend(page["items"]); cursor = page["next_cursor"]
        self.assertEqual([r["id"] for r in seen], [r["id"] for r in initial])
        self.assertTrue(all(r["version"] == 1 and not r["voided"] for r in seen))
        self.assertEqual(len(self.history()["items"]), 5)

    def test_equal_timestamp_mixed_origin_order_filters_and_cursor_scope(self):
        event, _ = self.stored()
        for _ in range(3):
            self.create(measured_at=event.measured_at)
        first = self.history(limit=2)
        second = self.history(limit=2, cursor=first["next_cursor"])
        self.assertEqual(len({row["id"] for row in first["items"] + second["items"]}), 4)
        self.assertEqual(len(self.history(origin="manual")["items"]), 3)
        self.assertEqual(len(self.history(origin="device")["items"]), 1)
        for params in ({"time_basis": "received"}, {"origin": "manual"}, {"include_voided": True},
                       {"since": "2020-01-01T00:00:00Z"}, {"cursor": first["next_cursor"][:-4] + "AAAA"}):
            query = {"limit": 2, "cursor": first["next_cursor"]} | params
            self.assertEqual(self.client.get(self.base + "/readings", params=query).status_code, 422)

    def test_time_range_boundaries_and_limits(self):
        row = self.create()
        measured = datetime.fromisoformat(row["measured_at"].replace("Z", "+00:00"))
        self.assertEqual(len(self.history(since=measured.isoformat())["items"]), 1)
        self.assertEqual(self.history(until=measured.isoformat())["items"], [])
        for params in ({"limit": 201}, {"limit": 0}, {"time_basis": "guessed"},
                       {"since": "2026-01-01T00:00:00"}, {"since": "123"},
                       {"since": "2030-01-01T00:00:00Z", "until": "2020-01-01T00:00:00Z"}):
            self.assertEqual(self.client.get(self.base + "/readings", params=params).status_code, 422)

    def test_restart_keeps_cursor_and_revisions(self):
        for _ in range(3): self.create()
        first = self.history(limit=1)
        service = ReadingsService(self.engine, self.fake.settings.token_key, lambda: self.clock)
        page = service.history(self.hatchery, self.tank, self.user, limit=1, cursor=first["next_cursor"])
        self.assertNotEqual(str(page["items"][0]["id"]), first["items"][0]["id"])
        self.assertEqual(page["snapshot_position"], first["snapshot_position"])

    def test_uncommitted_changes_never_leak_into_snapshot(self):
        first = self.create()
        ready, release = Event(), Event()
        event = Telemetry.model_validate(json.loads((FIXTURES / "telemetry-default-ph.json").read_text()))
        self.stored()  # Establish device/binding before the pending transaction.
        def pending():
            with Session(self.engine) as session, session.begin():
                persist_event(session, event.model_copy(update={"seq": event.seq + 1}))
                ready.set()
                if not release.wait(10): raise RuntimeError("Test barrier timed out")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(pending)
            try:
                self.assertTrue(ready.wait(10))
                snapshot = self.history(limit=1)
                self.assertEqual(snapshot["snapshot_position"], 2)
            finally:
                release.set()
            future.result(timeout=10)
        second = self.history(limit=1, cursor=snapshot["next_cursor"])
        self.assertEqual(second["snapshot_position"], 2)
        self.assertEqual(len(snapshot["items"] + second["items"]), 2)
        self.assertEqual(len(self.history()["items"]), 3)

    def test_rollback_removes_manual_revision_and_journal(self):
        with patch("backend.features.readings.service.ReadingsService.manual_view", side_effect=RuntimeError("Injected after flush")):
            with self.assertRaises(RuntimeError):
                self.service.create(self.hatchery, self.tank, self.user, CreateMeasurement.model_validate(self.body()))
        with Session(self.engine) as session:
            for model in (ManualReading, ManualReadingRevision, ReadingChange):
                self.assertEqual(session.exec(select(model)).all(), [])
            self.assertEqual(session.get(ReadingHistoryState, self.hatchery).last_position, 0)

    def test_correction_and_device_rollback_preserve_watermark(self):
        row = self.create()
        event, _ = self.stored()
        with patch("backend.features.readings.service.ReadingsService.manual_view", side_effect=RuntimeError("Injected")):
            with self.assertRaises(RuntimeError):
                self.service.change(self.hatchery, self.tank, self.user, UUID(row["id"]),
                    CorrectMeasurement(measured_at=row["measured_at"], ph=8, expected_version=1, reason="Test rollback"), "correct")
        with self.assertRaises(RuntimeError):
            with Session(self.engine) as session, session.begin():
                persist_event(session, event.model_copy(update={"seq": event.seq + 1}))
                raise RuntimeError("Injected")
        with Session(self.engine) as session:
            self.assertEqual(session.get(ReadingHistoryState, self.hatchery).last_position, 2)
            self.assertEqual(len(session.exec(select(ReadingChange)).all()), 2)
            self.assertEqual(len(session.exec(select(ManualReadingRevision)).all()), 1)
            self.assertEqual(len(session.exec(select(DeviceEvent)).all()), 1)

    def test_concurrent_telemetry_duplicates_create_one_journal_record(self):
        event, _ = self.stored()
        barrier = Barrier(2)
        def store(_):
            with Session(self.engine) as session, session.begin():
                barrier.wait()
                return persist_event(session, event.model_copy(update={"seq": event.seq + 1}))
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(sorted(executor.map(store, range(2))), ["duplicate", "stored"])
        with Session(self.engine) as session:
            self.assertEqual(session.get(ReadingHistoryState, self.hatchery).last_position, 2)
            self.assertEqual(len(session.exec(select(ReadingChange)).all()), 2)

    def test_archive_and_manual_create_serialize(self):
        barrier = Barrier(2)
        def create():
            barrier.wait()
            try:
                self.service.create(self.hatchery, self.tank, self.user, CreateMeasurement.model_validate(self.body()))
                return 201
            except ReadingsError as error:
                return error.status
        def archive():
            barrier.wait()
            return self.service.registry.change_tank(self.hatchery, self.user, self.tank, 1, archive=True)
        with ThreadPoolExecutor(max_workers=2) as executor:
            create_future, archive_future = executor.submit(create), executor.submit(archive)
            result = create_future.result(); archived = archive_future.result()
        self.assertIsNotNone(archived["archived_at"])
        self.assertIn(result, (201, 409))
        self.assertEqual(len(self.history()["items"]), 1 if result == 201 else 0)

    def test_database_history_immutable_and_owner_foreign_keys(self):
        row = self.create()
        for table in ("manual_readings", "manual_reading_revisions", "reading_changes"):
            for sql in (f"DELETE FROM {table}", f"UPDATE {table} SET tank_id = tank_id"):
                with self.assertRaises(sa.exc.IntegrityError):
                    with self.engine.begin() as connection:
                        connection.execute(sa.text(sql))
        with self.assertRaises(sa.exc.IntegrityError):
            with Session(self.engine) as session, session.begin():
                session.add(ManualReading(hatchery_id=self.other_hatchery, tank_id=self.tank,
                    created_by=self.user, request_id=uuid4()))
        with self.assertRaises(sa.exc.IntegrityError):
            with Session(self.engine) as session, session.begin():
                session.delete(session.get(Tank, self.tank))

    def test_database_rejects_nonfinite_missing_reason_and_revision_gaps(self):
        row = self.create()
        valid = dict(reading_id=UUID(row["id"]), hatchery_id=self.hatchery, tank_id=self.tank,
            measured_at=self.clock, ph=7.1, actor_id=self.user, version=2, reason="Retest")
        for changes in ({"ph": float("nan")}, {"ph": float("inf")}, {"reason": None},
                        {"reason": " "}, {"ph": None}, {"version": 3}, {"hatchery_id": self.other_hatchery}):
            with self.subTest(changes=changes), self.assertRaises(sa.exc.IntegrityError):
                with Session(self.engine) as session, session.begin():
                    session.add(ManualReadingRevision(**(valid | changes)))

    def test_populated_t11_upgrade_preserves_every_existing_table(self):
        with self.engine.begin() as connection:
            config = configuration(); config.attributes["connection"] = connection
            command.downgrade(config, "0003_t11")
        event, _ = self.stored()
        with self.engine.begin() as connection:
            tables = [name for name in sa.inspect(connection).get_table_names() if name != "alembic_version"]
            before = {name: connection.execute(sa.text(f'SELECT * FROM "{name}"')).mappings().all() for name in tables}
            config = configuration(); config.attributes["connection"] = connection
            command.upgrade(config, "head"); command.upgrade(config, "head")
            self.assertEqual(compare_metadata(MigrationContext.configure(connection), SQLModel.metadata), [])
            for name in tables:
                self.assertEqual(connection.execute(sa.text(f'SELECT * FROM "{name}"')).mappings().all(), before[name])
        self.assertEqual(self.history()["items"][0]["telemetry"], event.model_dump(mode="json"))


if __name__ == "__main__":
    unittest.main()
