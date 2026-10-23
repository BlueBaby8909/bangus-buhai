"""Quarantine custody receipts use disposable schemas, never real devices."""
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import sqlalchemy as sa
from sqlmodel import Session, select

from backend.database.models import DeviceEvent, DeviceInventory, IngestionQuarantine, ReadingChange
from backend.mqtt.service import IngestionService
from backend.tests.mqtt_support import DatabaseFixture
from backend.tests.auth_support import FakeAuth
from backend.tests.registry_support import SimulatedDevice
from backend.features.registry.live import provision
from contracts import QuarantineReceipt, ValidationContext, validate_message


class QuarantineReceiptTests(DatabaseFixture):
    def candidate(self, **changes):
        return self.event(binding_id='11111111-1111-4111-8111-111111111111', **changes)

    def test_committed_receipt_matches_exact_bytes_and_not_history(self):
        raw = json.dumps(self.candidate(), indent=2).encode()
        result = self.service.process(self.topic, raw)
        receipt = validate_message(result.ack_topic, result.acknowledgement,
            ValidationContext(self.agent.external_id))
        self.assertIsInstance(receipt, QuarantineReceipt)
        self.assertEqual(receipt.payload_sha256, hashlib.sha256(raw).hexdigest())
        with Session(self.engine) as session:
            row = session.exec(select(IngestionQuarantine)).one()
            self.assertEqual(str(row.id), receipt.quarantine_id)
            self.assertEqual(row.reason, receipt.reason)
            self.assertEqual(session.scalar(sa.select(sa.func.count()).select_from(DeviceEvent)), 0)
            self.assertEqual(session.scalar(sa.select(sa.func.count()).select_from(ReadingChange)), 0)

    def test_lost_receipt_retry_reuses_custody_record(self):
        first = self.process(self.candidate())
        # A restart has no in-memory receipt state. Different whitespace gets its
        # own exact-wire hash but refers to the same semantic quarantine record.
        service = IngestionService(self.engine, clock=lambda: self.clock)
        second_raw = json.dumps(self.candidate(), separators=(',', ':')).encode()
        second = service.process(self.topic, second_raw)
        a, b = [QuarantineReceipt.model_validate_json(x.acknowledgement) for x in (first, second)]
        self.assertEqual(a.quarantine_id, b.quarantine_id)
        self.assertNotEqual(a.payload_sha256, b.payload_sha256)

    def test_conflicting_variants_have_different_receipts(self):
        a = QuarantineReceipt.model_validate_json(self.process(self.candidate()).acknowledgement)
        b = QuarantineReceipt.model_validate_json(self.process(self.candidate(fw_version='variant')).acknowledgement)
        self.assertNotEqual(a.quarantine_id, b.quarantine_id)
        self.assertNotEqual(a.payload_sha256, b.payload_sha256)

    def test_unverified_or_invalid_credential_gets_no_receipt(self):
        with Session(self.engine) as session, session.begin():
            session.get(DeviceInventory, self.agent.external_id).verified_at = None
        self.assertIsNone(self.process(self.candidate()).acknowledgement)

    def test_capacity_failure_gets_no_receipt_but_duplicate_still_does(self):
        self.service = IngestionService(self.engine, clock=lambda: self.clock, quarantine_limits=(1, 1))
        self.assertIsNotNone(self.process(self.candidate()).acknowledgement)
        result = self.process(self.candidate(seq=8))
        self.assertEqual(result.disposition, 'quarantine_full')
        self.assertIsNone(result.acknowledgement)
        self.assertIsNotNone(self.process(self.candidate()).acknowledgement)
        self.assertEqual(self.process(self.event(seq=9)).disposition, 'stored')

    def test_failed_quarantine_commit_cannot_return_receipt(self):
        with patch.object(self.engine.dialect, 'do_commit', side_effect=RuntimeError('injected commit failure')):
            with self.assertRaises(RuntimeError):
                self.process(self.candidate())
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(sa.select(sa.func.count()).select_from(IngestionQuarantine)), 0)

    def test_explicit_hardware_preparation_is_repeatable_without_ownership(self):
        from uuid import uuid4
        auth = FakeAuth()
        self.addCleanup(auth.provider.close)
        device = SimulatedDevice('BB-000000000044')
        with tempfile.TemporaryDirectory() as directory:
            cert, output = Path(directory) / 'cert.pem', Path(directory) / 'claim.json'
            cert.write_text(device.pem)
            subject = uuid4()
            first = provision(self.engine, auth.settings, subject, cert, output, test=True)
            original = output.read_bytes()
            second = provision(self.engine, auth.settings, subject, cert, output, test=True)
            self.assertEqual(first, second)
            self.assertEqual(output.read_bytes(), original)
            with Session(self.engine) as session:
                inventory = session.get(DeviceInventory, device.external_id)
                self.assertIsNone(inventory.device_id)
                self.assertIsNone(inventory.verified_at)

