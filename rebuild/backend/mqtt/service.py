"""Qualified-broker admission. Nothing here publishes before transaction exit."""
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import re
from uuid import UUID

import sqlalchemy as sa
from pydantic import ValidationError
from sqlmodel import Session, select

from contracts import (Acknowledgement, CommandResult, ContractError, QuarantineReceipt, Telemetry, ValidationContext,
    classify_event, decode_payload, validate_message)
from contracts.models import utc_datetime
from backend.database.events import persist_event
from backend.database.models import (Binding, Device, DeviceConfiguration, DeviceConfigurationReceipt,
    DeviceInventory, Hatchery, Tank)
from backend.features.accounts.service import utc_now
from backend.features.registry.errors import RegistryError
from backend.features.registry.security import certificate, digest
from . import repository


@dataclass(frozen=True)
class Outcome:
    disposition: str
    reason: str
    ack_topic: str | None = None
    acknowledgement: bytes | None = None


class IngestionService:
    def __init__(self, engine, prefix="bangusbuhai-rebuild", clock=utc_now, quarantine_limits=(1000, 10000)):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", prefix) or not all(type(n) is int and n > 0 for n in quarantine_limits):
            raise ValueError("Invalid ingestion configuration")
        self.engine, self.prefix, self.clock, self.limits = engine, prefix, clock, quarantine_limits

    def process(self, topic, payload, *, qos=1, retained=False):
        received = self.clock()
        if retained or type(qos) is not int or qos != 1:
            return Outcome("rejected", "invalid_delivery")
        if not isinstance(topic, str) or len(topic) > 256:
            return Outcome("rejected", "invalid_topic")
        parts = topic.split('/')
        if (len(parts) != 4 or parts[:2] != [self.prefix, 'devices'] or
                not re.fullmatch(r"BB-[0-9A-F]{12}", parts[2]) or parts[3] not in ('telemetry', 'command-results')):
            return Outcome("rejected", "invalid_topic")
        try:
            model = Telemetry if parts[3] == 'telemetry' else CommandResult
            # Structural parsing alone grants no binding permission. The trusted
            # binding allowlist is checked again after database admission below.
            document = decode_payload(payload)
            if type(document.get('schema_version')) is not int or document['schema_version'] != 1:
                return Outcome("rejected", "unsupported_version")
            event = model.model_validate(document)
            if event.device_id != parts[2]:
                return Outcome("rejected", "identity_mismatch")
        except ContractError as error:
            return Outcome("rejected", error.code)
        except ValidationError:
            return Outcome("rejected", "invalid_schema")
        with Session(self.engine) as session, session.begin():
            session.execute(sa.text("SET LOCAL statement_timeout = '10s'"))
            session.execute(sa.text("SET LOCAL lock_timeout = '5s'"))
            device = session.exec(select(Device).where(Device.external_id == event.device_id)).one_or_none()
            if device:
                # Registry order: hatchery -> inventory -> device. Refresh after
                # locks, including when a reassignment committed while waiting.
                session.get(Hatchery, device.hatchery_id, with_for_update=True)
            inventory = session.get(DeviceInventory, event.device_id, with_for_update=True)
            device = session.get(Device, device.id, with_for_update=True, populate_existing=True) if device else None
            reason = self.credential(inventory, device, received)
            credential_verified = reason is None
            if reason is None:
                previous = repository.previous(session, device.id, event)
                if previous:
                    old_model = Telemetry if previous.kind == 'telemetry' else CommandResult
                    try:
                        classify_event(event, old_model.model_validate(previous.payload))
                    except ContractError:
                        reason = 'event_conflict'
                    else:
                        return self.ack(event, 'duplicate')  # Context manager commits before caller receives it.
                else:
                    reason = self.admission(session, device, inventory, event, received)
            if reason:
                disposition = repository.quarantine(session, event, reason, received, self.limits)
                if disposition == 'quarantined' and credential_verified and isinstance(event, Telemetry):
                    row = repository.quarantined_candidate(session, event)
                    receipt = QuarantineReceipt(schema_version=1, device_id=event.device_id,
                        boot_id=event.boot_id, seq=event.seq, event_kind='telemetry',
                        quarantine_id=str(row.id), reason=row.reason,
                        payload_sha256=hashlib.sha256(payload).hexdigest())
                    # Returned only after transaction exit/commit. Normal ACKs stay unchanged.
                    return Outcome(disposition, reason,
                        f'{self.prefix}/devices/{event.device_id}/quarantine-receipts',
                        receipt.model_dump_json().encode('utf-8'))
                return Outcome(disposition, reason)
            validate_message(topic, payload, ValidationContext(device_id=device.external_id,
                prefix=self.prefix, binding_ids=frozenset({event.binding_id})))
            result = persist_event(session, event)
            if isinstance(event, CommandResult):
                from backend.features.commands.service import CommandService
                CommandService.record_result(session, device, event)
            return self.ack(event, result)

    @staticmethod
    def credential(inventory, device, received):
        if device is None or inventory is None or inventory.device_id != device.id or inventory.verified_at is None:
            return 'device_unverified'
        try:
            cert = certificate(inventory.certificate, inventory.external_id, received)
            from cryptography.hazmat.primitives import hashes
            if cert.fingerprint(hashes.SHA256()).hex() != inventory.fingerprint:
                return 'invalid_device_credential'
        except RegistryError:
            return 'invalid_device_credential'
        return None

    @staticmethod
    def admission(session, device, inventory, event, received):
        binding = session.get(Binding, UUID(event.binding_id))
        if binding is None or binding.device_id != device.id or binding.hatchery_id != device.hatchery_id:
            return 'binding_unavailable'
        proof = session.exec(select(DeviceConfigurationReceipt).where(
            DeviceConfigurationReceipt.binding_id == binding.id,
            DeviceConfigurationReceipt.credential_fingerprint == inventory.fingerprint)).first()
        if proof is None:
            return 'binding_unconfirmed'
        capture = event.measured_at if isinstance(event, Telemetry) else event.created_at
        capture = utc_datetime(capture) if capture else None
        if capture is not None and capture > received + timedelta(minutes=5):
            return 'future_capture'
        if isinstance(event, CommandResult):
            from backend.features.commands.service import CommandService
            return CommandService.result_reason(session, device, event)
        if capture is not None and capture < binding.started_at:
            return 'capture_before_binding'
        if binding.ended_at is not None:
            if capture is None:
                return 'closed_binding_unknown_capture'
            if capture >= binding.ended_at:
                return 'capture_after_binding'
            return None
        return IngestionService.current_binding(session, device, inventory, binding)

    @staticmethod
    def current_binding(session, device, inventory, binding):
        tank = session.get(Tank, binding.tank_id)
        config = session.get(DeviceConfiguration, device.id)
        if config is not None:
            proof = session.exec(select(DeviceConfigurationReceipt).where(
                DeviceConfigurationReceipt.device_id == device.id,
                DeviceConfigurationReceipt.revision == config.revision,
                DeviceConfigurationReceipt.binding_id == binding.id,
                DeviceConfigurationReceipt.credential_fingerprint == inventory.fingerprint)).one_or_none()
        if device.archived_at is not None or tank.archived_at is not None:
            return 'resource_archived'
        if (config is None or proof is None or config.confirmed_revision != config.revision or
                config.document.get('binding_id') != str(binding.id) or
                config.document != proof.document or config.digest != proof.digest or
                digest(config.document) != config.digest):
            return 'binding_unconfirmed'
        return None

    def ack(self, event, result):
        acknowledgement = Acknowledgement(schema_version=1, device_id=event.device_id,
            boot_id=event.boot_id, seq=event.seq, event_kind=event.kind, result=result)
        return Outcome(result, result, f'{self.prefix}/devices/{event.device_id}/acks',
            acknowledgement.model_dump_json().encode('utf-8'))
