"""Real PostgreSQL checks, always inside a newly created disposable schema.

Run from rebuild: python -m unittest backend.tests.test_database -v
Missing configuration/server is an ERROR, never a silently skipped passing suite.
"""

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlmodel import Session, SQLModel, select

from backend.database.config import database_url, make_engine
from backend.database.events import persist_event
from backend.database.migrate import configuration
from backend.database.models import Binding, Device, DeviceEvent, Hatchery, Membership, Tank, UserIdentity
from contracts import CommandResult, ContractError, Telemetry

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures" / "valid"


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = make_engine(test=True)
        with cls.engine.connect() as connection:
            version = connection.scalar(sa.text("SHOW server_version_num"))
            if int(version) < 180000:
                raise RuntimeError("T09 checks require PostgreSQL 18 or newer")

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.schema = f"t09_test_{uuid4().hex}"
        with self.engine.begin() as connection:
            connection.execute(sa.schema.CreateSchema(self.schema))
        # Fixed generated identifier, quoted by SQLAlchemy/driver; no input SQL.
        self.scoped = sa.create_engine(database_url(test=True), hide_parameters=True,
            connect_args={"options": f"-csearch_path={self.schema}", "connect_timeout": 5})
        self.addCleanup(self.cleanup_schema)
        with self.scoped.begin() as connection:
            config = configuration()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        self.hatchery = uuid4()
        self.tank = uuid4()
        self.device = uuid4()
        self.binding = UUID("97fcde45-4112-41d4-a509-17e5bb1c0d91")
        self.start = datetime(2026, 10, 16, tzinfo=timezone.utc)
        with Session(self.scoped) as session, session.begin():
            session.add(Hatchery(id=self.hatchery, name="Test hatchery"))
            session.flush()
            session.add(Tank(id=self.tank, hatchery_id=self.hatchery, name="Tank A"))
            session.add(Device(id=self.device, hatchery_id=self.hatchery, external_id="BB-AABBCC112233"))
            session.flush()
            session.add(Binding(id=self.binding, device_id=self.device, tank_id=self.tank,
                hatchery_id=self.hatchery, started_at=self.start))

    def cleanup_schema(self):
        self.scoped.dispose()
        with self.engine.begin() as connection:
            connection.execute(sa.schema.DropSchema(self.schema, cascade=True))

    def event(self, fixture="telemetry-default-ph.json", **changes):
        payload = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
        payload.update(changes)
        model = CommandResult if fixture.startswith("result-") else Telemetry
        return model.model_validate(payload)

    def store(self, event):
        with Session(self.scoped) as session, session.begin():
            return persist_event(session, event)

    def rejected(self, operation):
        with self.assertRaises(sa.exc.IntegrityError):
            with Session(self.scoped) as session, session.begin():
                operation(session)
                session.flush()

    def test_migration_repeat_and_metadata(self):
        with self.scoped.begin() as connection:
            config = configuration()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            self.assertEqual(connection.scalar(sa.text("SELECT version_num FROM alembic_version")), "0006_t14")
            self.assertEqual(compare_metadata(MigrationContext.configure(connection), SQLModel.metadata), [])

    def test_migration_downgrade_and_reupgrade(self):
        # This schema was created by this test; no dev/public tables are touched.
        with self.scoped.begin() as connection:
            config = configuration()
            config.attributes["connection"] = connection
            command.downgrade(config, "base")
            self.assertEqual(sa.inspect(connection).get_table_names(), ["alembic_version"])
            command.upgrade(config, "head")
            self.assertEqual(compare_metadata(MigrationContext.configure(connection), SQLModel.metadata), [])

    def test_migration_failure_rolls_back(self):
        with self.assertRaises(RuntimeError):
            with self.scoped.begin() as connection:
                config = configuration()
                config.attributes["connection"] = connection
                command.downgrade(config, "base")
                raise RuntimeError("injected migration failure")
        with self.scoped.connect() as connection:
            self.assertEqual(connection.scalar(sa.text("SELECT version_num FROM alembic_version")), "0006_t14")
            self.assertEqual(connection.scalar(sa.select(sa.func.count()).select_from(Hatchery)), 1)

    def test_membership_roles_and_foreign_keys(self):
        user = uuid4()
        with Session(self.scoped) as session, session.begin():
            session.add(UserIdentity(id=user))
            session.flush()
            session.add(Membership(user_id=user, hatchery_id=self.hatchery, role="operator"))
        self.rejected(lambda session: session.add(Membership(user_id=uuid4(), hatchery_id=self.hatchery, role="operator")))
        for role in ("root", "", "ADMIN", "admin", "viewer"):
            self.rejected(lambda session: session.execute(sa.update(Membership).values(role=role)))
        for role in ("operator",):
            with Session(self.scoped) as session, session.begin():
                session.execute(sa.update(Membership).values(role=role))
        self.rejected(lambda session: session.add(Membership(user_id=user, hatchery_id=self.hatchery, role="operator")))

    def test_device_identity_and_owner_constraints(self):
        for external in ("BB-AABBCC112233", "bb-aabbcc112233", "BB-123", "BB-AABBCC11223G"):
            self.rejected(lambda session: session.add(Device(hatchery_id=self.hatchery, external_id=external)))
        self.rejected(lambda session: session.add(Tank(hatchery_id=uuid4(), name="Orphan")))
        self.rejected(lambda session: session.add(Device(hatchery_id=uuid4(), external_id="BB-000000000001")))

    def test_binding_isolation_and_missing_references(self):
        foreign_hatchery, foreign_tank, spare_device = uuid4(), uuid4(), uuid4()
        with Session(self.scoped) as session, session.begin():
            session.add(Hatchery(id=foreign_hatchery, name="Other"))
            session.flush()
            session.add(Tank(id=foreign_tank, hatchery_id=foreign_hatchery, name="Other"))
            session.add(Device(id=spare_device, hatchery_id=self.hatchery, external_id="BB-000000000001"))
        for device, tank, owner in ((spare_device, foreign_tank, self.hatchery),
                                   (spare_device, foreign_tank, foreign_hatchery),
                                   (uuid4(), self.tank, self.hatchery),
                                   (spare_device, uuid4(), self.hatchery)):
            self.rejected(lambda session: session.add(Binding(device_id=device, tank_id=tank, hatchery_id=owner)))

    def test_resource_identity_cannot_rewrite_history(self):
        self.rejected(lambda session: session.execute(sa.update(Device).values(external_id="BB-000000000003")))
        with Session(self.scoped) as session, session.begin():
            unbound = Device(hatchery_id=self.hatchery, external_id="BB-000000000004")
            session.add(unbound)
            session.flush()
            device_id = unbound.id
            owner = Hatchery(name="Another owner")
            session.add(owner)
            session.flush()
            owner_id = owner.id
        self.rejected(lambda session: session.execute(sa.update(Device).where(Device.id == device_id).values(hatchery_id=owner_id)))
        with Session(self.scoped) as session, session.begin():
            session.execute(sa.update(Tank).values(name="Renamed tank"))
        with Session(self.scoped) as session:
            self.assertEqual(session.get(Tank, self.tank).name, "Renamed tank")

    def test_multiple_devices_one_tank_single_active_binding(self):
        spare_device = uuid4()
        with Session(self.scoped) as session, session.begin():
            session.add(Device(id=spare_device, hatchery_id=self.hatchery, external_id="BB-000000000002"))
            session.flush()
            session.add(Binding(device_id=spare_device, tank_id=self.tank, hatchery_id=self.hatchery))
        self.rejected(lambda session: session.add(Binding(device_id=self.device, tank_id=self.tank, hatchery_id=self.hatchery)))
        with Session(self.scoped) as session:
            self.assertEqual(len(session.exec(select(Binding)).all()), 2)

    def test_reassignment_retains_event_and_binding_history(self):
        self.assertEqual(self.store(self.event()), "stored")
        new_tank, new_binding = uuid4(), uuid4()
        with Session(self.scoped) as session, session.begin():
            session.add(Tank(id=new_tank, hatchery_id=self.hatchery, name="New tank"))
            session.execute(sa.update(Binding).where(Binding.id == self.binding).values(ended_at=self.start + timedelta(days=1)))
            session.flush()
            session.add(Binding(id=new_binding, device_id=self.device, tank_id=new_tank,
                hatchery_id=self.hatchery, started_at=self.start + timedelta(days=1)))
        self.assertEqual(self.store(self.event()), "duplicate")
        with Session(self.scoped) as session:
            old = session.exec(select(DeviceEvent)).one()
            self.assertEqual((old.tank_id, old.binding_id), (self.tank, self.binding))
        for values in ({"tank_id": new_tank}, {"ended_at": None}, {"started_at": self.start - timedelta(days=1)}):
            self.rejected(lambda session: session.execute(sa.update(Binding).where(Binding.id == self.binding).values(**values)))
        self.rejected(lambda session: session.execute(sa.delete(Binding).where(Binding.id == self.binding)))

    def test_binding_invalid_interval(self):
        self.rejected(lambda session: session.execute(sa.update(Binding).values(ended_at=self.start)))

    def test_duplicate_content_and_cross_kind_conflicts(self):
        event = self.event()
        self.assertEqual(self.store(event), "stored")
        self.assertEqual(self.store(self.event()), "duplicate")
        for candidate in (self.event(fw_version="changed"), self.event("result-accepted.json", seq=event.seq)):
            with self.assertRaises(ContractError) as error:
                self.store(candidate)
            self.assertEqual(error.exception.code, "event_conflict")
        with Session(self.scoped) as session:
            self.assertEqual(len(session.exec(select(DeviceEvent)).all()), 1)

    def test_concurrent_identical_and_conflicting_inserts(self):
        def race(left, right):
            barrier = Barrier(2)
            def write(event):
                barrier.wait(timeout=10)
                try:
                    return self.store(event)
                except ContractError as error:
                    return error.code
            with ThreadPoolExecutor(max_workers=2) as executor:
                return sorted(executor.map(write, [left, right]))
        self.assertEqual(race(self.event(), self.event()), ["duplicate", "stored"])
        self.assertEqual(race(self.event(seq=99), self.event(seq=99, fw_version="different")), ["event_conflict", "stored"])

    def test_null_time_provenance_and_uint32_boundary(self):
        event = self.event("telemetry-unsynchronized-clock.json", seq=4294967295)
        self.assertEqual(self.store(event), "stored")
        with Session(self.scoped) as session:
            row = session.exec(select(DeviceEvent)).one()
            self.assertIsNone(row.captured_at)
            self.assertIsNotNone(row.received_at.tzinfo)
            self.assertEqual(row.payload, event.model_dump(mode="json"))
            self.assertEqual(row.payload["readings"]["ph"]["source"], "default")
        self.assertEqual(self.store(self.event("result-accepted.json")), "stored")

    def test_append_only_and_restrict_deletion(self):
        self.store(self.event())
        self.rejected(lambda session: session.execute(sa.update(DeviceEvent).values(payload={})))
        self.rejected(lambda session: session.execute(sa.delete(DeviceEvent)))
        for model in (Tank, Device, Hatchery):
            self.rejected(lambda session: session.execute(sa.delete(model)))

    def test_rollback_does_not_store_event(self):
        with self.assertRaises(RuntimeError):
            with Session(self.scoped) as session, session.begin():
                self.assertEqual(persist_event(session, self.event()), "stored")
                raise RuntimeError("injected failure before commit")
        self.assertEqual(self.store(self.event()), "stored")

    def test_unknown_binding_and_device_rejected(self):
        for candidate in (self.event(binding_id=str(uuid4())), self.event(device_id="BB-000000000000")):
            with self.assertRaisesRegex(ValueError, "Unknown device/binding"):
                self.store(candidate)

    def test_event_relational_constraints(self):
        def row(**changes):
            values = dict(device_id=self.device, binding_id=self.binding, tank_id=self.tank,
                hatchery_id=self.hatchery, boot_id=uuid4(), seq=1, kind="telemetry",
                time_quality="unsynchronized", captured_at=None, payload={})
            values.update(changes)
            return DeviceEvent(**values)
        for changes in ({"seq": -1}, {"seq": 4294967296}, {"kind": "status"},
                        {"time_quality": "guessed"}, {"time_quality": "synchronized"},
                        {"captured_at": self.start}, {"tank_id": uuid4()},
                        {"device_id": uuid4()}, {"hatchery_id": uuid4()}, {"binding_id": uuid4()}):
            self.rejected(lambda session: session.add(row(**changes)))


if __name__ == "__main__":
    unittest.main()
