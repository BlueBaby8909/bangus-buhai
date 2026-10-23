"""Relational foundation and operator accounts. API/wire schemas live separately."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp():
    return sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class Hatchery(SQLModel, table=True):
    __tablename__ = "hatcheries"
    __table_args__ = (sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 200", name="hatchery_name"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=now, sa_column=timestamp())


class UserIdentity(SQLModel, table=True):
    __tablename__ = "user_identities"
    __table_args__ = (
        sa.UniqueConstraint("provider_issuer", "provider_subject", name="user_provider_identity"),
        sa.CheckConstraint("(provider_issuer IS NULL) = (provider_subject IS NULL)", name="user_provider_pair"),
        sa.CheckConstraint("NOT active OR provider_subject IS NOT NULL", name="active_user_mapped"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=now, sa_column=timestamp())
    provider_issuer: str | None = Field(default=None, max_length=512)
    provider_subject: UUID | None = None
    email: str | None = Field(default=None, max_length=320)
    active: bool = Field(default=False, sa_column=sa.Column(sa.Boolean, nullable=False, server_default=sa.false()))


class Membership(SQLModel, table=True):
    __tablename__ = "memberships"
    __table_args__ = (sa.CheckConstraint("role = 'operator'", name="membership_role"),)
    hatchery_id: UUID = Field(foreign_key="hatcheries.id", primary_key=True)
    user_id: UUID = Field(foreign_key="user_identities.id", primary_key=True)
    role: str = Field(default="operator", max_length=16)
    active: bool = Field(default=True, sa_column=sa.Column(sa.Boolean, nullable=False, server_default=sa.true()))


class Tank(SQLModel, table=True):
    __tablename__ = "tanks"
    __table_args__ = (
        sa.UniqueConstraint("id", "hatchery_id", name="tank_owner"),
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 200", name="tank_name"),
        sa.CheckConstraint("version >= 1", name="tank_version"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hatchery_id: UUID = Field(foreign_key="hatcheries.id", index=True)
    name: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=now, sa_column=timestamp())
    archived_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
    version: int = Field(default=1, sa_column=sa.Column(sa.Integer, nullable=False, server_default="1"))


class Device(SQLModel, table=True):
    __tablename__ = "devices"
    __table_args__ = (
        sa.UniqueConstraint("id", "hatchery_id", name="device_owner"),
        sa.CheckConstraint("external_id ~ '^BB-[0-9A-F]{12}$'", name="canonical_device_id"),
        sa.CheckConstraint("version >= 1", name="device_version"),
        sa.CheckConstraint("display_name IS NULL OR length(trim(display_name)) BETWEEN 1 AND 200", name="device_name"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hatchery_id: UUID = Field(foreign_key="hatcheries.id", index=True)
    external_id: str = Field(max_length=15, unique=True)
    created_at: datetime = Field(default_factory=now, sa_column=timestamp())
    display_name: str | None = Field(default=None, max_length=200)
    archived_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
    version: int = Field(default=1, sa_column=sa.Column(sa.Integer, nullable=False, server_default="1"))


class Binding(SQLModel, table=True):
    __tablename__ = "bindings"
    __table_args__ = (
        sa.ForeignKeyConstraint(["device_id", "hatchery_id"], ["devices.id", "devices.hatchery_id"], name="binding_device_owner"),
        sa.ForeignKeyConstraint(["tank_id", "hatchery_id"], ["tanks.id", "tanks.hatchery_id"], name="binding_tank_owner"),
        sa.UniqueConstraint("id", "device_id", "tank_id", "hatchery_id", name="binding_identity"),
        sa.CheckConstraint("ended_at IS NULL OR ended_at > started_at", name="binding_interval"),
        sa.Index("one_active_binding_per_device", "device_id", unique=True, postgresql_where=sa.text("ended_at IS NULL")),
        sa.Index("bindings_tank", "tank_id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    device_id: UUID
    tank_id: UUID
    hatchery_id: UUID
    started_at: datetime = Field(default_factory=now, sa_column=timestamp())
    ended_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))


class DeviceEvent(SQLModel, table=True):
    __tablename__ = "device_events"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["binding_id", "device_id", "tank_id", "hatchery_id"],
            ["bindings.id", "bindings.device_id", "bindings.tank_id", "bindings.hatchery_id"], name="event_binding_identity"),
        sa.UniqueConstraint("device_id", "boot_id", "seq", name="device_event_identity"),
        sa.UniqueConstraint("id", "hatchery_id", "tank_id", name="event_history_identity"),
        sa.CheckConstraint("seq BETWEEN 0 AND 4294967295", name="event_sequence"),
        sa.CheckConstraint("kind IN ('telemetry','command_result')", name="event_kind"),
        sa.CheckConstraint("time_quality IN ('synchronized','unsynchronized')", name="event_time_quality"),
        sa.CheckConstraint("(captured_at IS NOT NULL) = (time_quality = 'synchronized')", name="event_capture_time"),
        sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name="event_payload_object"),
        sa.Index("events_tank_captured", "tank_id", "captured_at", "id"),
        sa.Index("events_tank_received", "tank_id", "received_at", "id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    device_id: UUID
    binding_id: UUID
    tank_id: UUID
    hatchery_id: UUID
    boot_id: UUID
    seq: int = Field(sa_column=sa.Column(sa.BigInteger, nullable=False))
    kind: str = Field(max_length=24)
    time_quality: str = Field(max_length=16)
    captured_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
    received_at: datetime = Field(default_factory=now, sa_column=timestamp())
    payload: dict[str, Any] = Field(sa_column=sa.Column(JSONB, nullable=False))


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        sa.CheckConstraint("expires_at > created_at", name="auth_session_lifetime"),
        sa.CheckConstraint("length(token_hash) = 64", name="auth_session_hash"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token_hash: str = Field(max_length=64, unique=True, repr=False)
    user_id: UUID = Field(foreign_key="user_identities.id", index=True)
    provider_session_id: UUID
    encrypted_tokens: str | None = Field(default=None, sa_column=sa.Column(sa.Text), repr=False)
    created_at: datetime = Field(default_factory=now, sa_column=timestamp())
    last_seen_at: datetime = Field(default_factory=now, sa_column=timestamp())
    expires_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    revoked_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))


class AuthLoginBucket(SQLModel, table=True):
    __tablename__ = "auth_login_buckets"
    __table_args__ = (sa.CheckConstraint("attempts BETWEEN 1 AND 11", name="login_bucket_count"),)
    key_hash: str = Field(max_length=64, primary_key=True, repr=False)
    window_start: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    attempts: int


class DeviceInventory(SQLModel, table=True):
    __tablename__ = "device_inventory"
    __table_args__ = (
        sa.CheckConstraint("external_id ~ '^BB-[0-9A-F]{12}$'", name="inventory_device_id"),
        sa.CheckConstraint("length(fingerprint) = 64 AND length(key_fingerprint) = 64 AND (claim_hash IS NULL OR length(claim_hash) = 64)", name="inventory_hashes"),
        sa.CheckConstraint("verified_at IS NULL OR device_id IS NOT NULL", name="inventory_verification"),
    )
    external_id: str = Field(max_length=15, primary_key=True)
    certificate: str = Field(sa_column=sa.Column(sa.Text, nullable=False), repr=False)
    fingerprint: str = Field(max_length=64, unique=True, repr=False)
    key_fingerprint: str = Field(max_length=64, unique=True, repr=False)
    claim_hash: str | None = Field(default=None, max_length=64, unique=True, repr=False)
    device_id: UUID | None = Field(default=None, foreign_key="devices.id", unique=True)
    prepared_at: datetime = Field(default_factory=now, sa_column=timestamp())
    verified_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))


class DeviceClaim(SQLModel, table=True):
    __tablename__ = "device_claims"
    __table_args__ = (
        sa.ForeignKeyConstraint(["tank_id", "hatchery_id"], ["tanks.id", "tanks.hatchery_id"], name="claim_tank_owner"),
        sa.ForeignKeyConstraint(["device_id", "hatchery_id"], ["devices.id", "devices.hatchery_id"], name="claim_device_owner"),
        sa.CheckConstraint("state IN ('pending_proof','awaiting_confirmation','complete','expired','cancelled')", name="claim_state"),
        sa.CheckConstraint("expires_at > created_at", name="claim_lifetime"),
        sa.Index("one_pending_claim_per_device", "external_id", unique=True, postgresql_where=sa.text("state = 'pending_proof'")),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    external_id: str = Field(foreign_key="device_inventory.external_id", max_length=15, index=True)
    hatchery_id: UUID = Field(foreign_key="hatcheries.id", index=True)
    tank_id: UUID
    user_id: UUID = Field(foreign_key="user_identities.id")
    state: str = Field(default="pending_proof", max_length=24)
    created_at: datetime = Field(default_factory=now, sa_column=timestamp())
    expires_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    device_id: UUID | None = Field(default=None, foreign_key="devices.id")


class DeviceConfiguration(SQLModel, table=True):
    __tablename__ = "device_configurations"
    __table_args__ = (
        sa.CheckConstraint("revision >= 1 AND confirmed_revision BETWEEN 0 AND revision", name="configuration_revision"),
        sa.CheckConstraint("length(digest) = 64 AND jsonb_typeof(document) = 'object'", name="configuration_content"),
    )
    device_id: UUID = Field(foreign_key="devices.id", primary_key=True)
    revision: int = Field(sa_column=sa.Column(sa.BigInteger, nullable=False))
    document: dict[str, Any] = Field(sa_column=sa.Column(JSONB, nullable=False))
    digest: str = Field(max_length=64)
    confirmed_revision: int = Field(default=0, sa_column=sa.Column(sa.BigInteger, nullable=False, server_default="0"))
    confirmed_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))


class DeviceChallenge(SQLModel, table=True):
    __tablename__ = "device_challenges"
    __table_args__ = (
        sa.CheckConstraint("purpose IN ('sync','confirm')", name="challenge_purpose"),
        sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name="challenge_payload"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    external_id: str = Field(foreign_key="device_inventory.external_id", max_length=15, index=True)
    purpose: str = Field(max_length=8)
    payload: dict[str, Any] = Field(sa_column=sa.Column(JSONB, nullable=False))
    claim_id: UUID | None = Field(default=None, foreign_key="device_claims.id")
    expires_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    used_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))


class RegistryAudit(SQLModel, table=True):
    __tablename__ = "registry_audit"
    __table_args__ = (sa.CheckConstraint("actor_type IN ('owner','operator','device')", name="registry_actor"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    actor_type: str = Field(max_length=16)
    user_id: UUID | None = Field(default=None, foreign_key="user_identities.id")
    hatchery_id: UUID | None = Field(default=None, foreign_key="hatcheries.id", index=True)
    external_id: str | None = Field(default=None, foreign_key="device_inventory.external_id", max_length=15)
    resource_id: UUID | None = None
    action: str = Field(max_length=48)
    occurred_at: datetime = Field(default_factory=now, sa_column=timestamp())
    details: dict[str, Any] = Field(default_factory=dict, sa_column=sa.Column(JSONB, nullable=False))


class ReadingHistoryState(SQLModel, table=True):
    __tablename__ = "reading_history_state"
    __table_args__ = (sa.CheckConstraint("last_position >= 0", name="history_position"),)
    hatchery_id: UUID = Field(foreign_key="hatcheries.id", primary_key=True)
    last_position: int = Field(default=0, sa_column=sa.Column(sa.BigInteger, nullable=False, server_default="0"))


class ManualReading(SQLModel, table=True):
    __tablename__ = "manual_readings"
    __table_args__ = (
        sa.ForeignKeyConstraint(["tank_id", "hatchery_id"], ["tanks.id", "tanks.hatchery_id"], name="manual_tank_owner"),
        sa.UniqueConstraint("id", "hatchery_id", "tank_id", name="manual_identity"),
        sa.UniqueConstraint("hatchery_id", "created_by", "request_id", name="manual_request_identity"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hatchery_id: UUID
    tank_id: UUID
    created_by: UUID = Field(foreign_key="user_identities.id")
    request_id: UUID
    received_at: datetime = Field(default_factory=now, sa_column=timestamp())


class ManualReadingRevision(SQLModel, table=True):
    __tablename__ = "manual_reading_revisions"
    __table_args__ = (
        sa.ForeignKeyConstraint(["reading_id", "hatchery_id", "tank_id"],
            ["manual_readings.id", "manual_readings.hatchery_id", "manual_readings.tank_id"], name="revision_reading_owner"),
        sa.UniqueConstraint("reading_id", "version", name="manual_revision_version"),
        sa.UniqueConstraint("id", "hatchery_id", "tank_id", name="revision_history_identity"),
        sa.CheckConstraint("version >= 1", name="manual_version"),
        sa.CheckConstraint("(version = 1 AND reason IS NULL AND NOT voided) OR (version > 1 AND reason IS NOT NULL AND length(trim(reason)) BETWEEN 1 AND 500)", name="manual_reason"),
        sa.CheckConstraint("temperature_c IS NOT NULL OR ph IS NOT NULL OR turbidity_ntu IS NOT NULL", name="manual_has_measurement"),
        *[sa.CheckConstraint(f"{column} IS NULL OR ({column} > '-Infinity'::float8 AND {column} < 'Infinity'::float8)",
            name=f"manual_finite_{column}") for column in ("temperature_c", "ph", "turbidity_ntu")],
        sa.Index("manual_revisions_tank", "tank_id", "reading_id", "version"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    reading_id: UUID
    hatchery_id: UUID
    tank_id: UUID
    version: int
    measured_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    temperature_c: float | None = Field(default=None, sa_column=sa.Column(sa.Double))
    ph: float | None = Field(default=None, sa_column=sa.Column(sa.Double))
    turbidity_ntu: float | None = Field(default=None, sa_column=sa.Column(sa.Double))
    notes: str | None = Field(default=None, max_length=2000)
    instrument: str | None = Field(default=None, max_length=200)
    voided: bool = Field(default=False, sa_column=sa.Column(sa.Boolean, nullable=False, server_default=sa.false()))
    actor_id: UUID = Field(foreign_key="user_identities.id")
    changed_at: datetime = Field(default_factory=now, sa_column=timestamp())
    reason: str | None = Field(default=None, max_length=500)


class ReadingChange(SQLModel, table=True):
    __tablename__ = "reading_changes"
    __table_args__ = (
        sa.ForeignKeyConstraint(["device_event_id", "hatchery_id", "tank_id"],
            ["device_events.id", "device_events.hatchery_id", "device_events.tank_id"], name="history_event_owner"),
        sa.ForeignKeyConstraint(["manual_revision_id", "hatchery_id", "tank_id"],
            ["manual_reading_revisions.id", "manual_reading_revisions.hatchery_id", "manual_reading_revisions.tank_id"], name="history_revision_owner"),
        sa.CheckConstraint("(device_event_id IS NULL) <> (manual_revision_id IS NULL)", name="history_one_origin"),
        sa.CheckConstraint("position > 0", name="history_positive_position"),
        sa.Index("reading_changes_tank", "tank_id", "position"),
    )
    hatchery_id: UUID = Field(foreign_key="reading_history_state.hatchery_id", primary_key=True)
    position: int = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True))
    tank_id: UUID
    device_event_id: UUID | None = Field(default=None, unique=True)
    manual_revision_id: UUID | None = Field(default=None, unique=True)


class DeviceConfigurationReceipt(SQLModel, table=True):
    __tablename__ = "device_configuration_receipts"
    __table_args__ = (
        sa.ForeignKeyConstraint(["device_id", "hatchery_id"], ["devices.id", "devices.hatchery_id"], name="receipt_device_owner"),
        sa.ForeignKeyConstraint(["binding_id", "device_id", "tank_id", "hatchery_id"],
            ["bindings.id", "bindings.device_id", "bindings.tank_id", "bindings.hatchery_id"], name="receipt_binding_identity"),
        sa.UniqueConstraint("device_id", "revision", name="configuration_receipt_revision"),
        sa.CheckConstraint("revision >= 1 AND length(digest) = 64 AND length(credential_fingerprint) = 64", name="receipt_identity"),
        sa.CheckConstraint("(binding_id IS NULL) = (tank_id IS NULL)", name="receipt_assignment"),
        sa.CheckConstraint("jsonb_typeof(document) = 'object'", name="receipt_document"),
        sa.Index("receipts_binding", "binding_id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    device_id: UUID
    hatchery_id: UUID
    binding_id: UUID | None = None
    tank_id: UUID | None = None
    revision: int = Field(sa_column=sa.Column(sa.BigInteger, nullable=False))
    digest: str = Field(max_length=64)
    credential_fingerprint: str = Field(max_length=64)
    document: dict[str, Any] = Field(sa_column=sa.Column(JSONB, nullable=False))
    confirmed_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))


class IngestionQuarantine(SQLModel, table=True):
    __tablename__ = "ingestion_quarantine"
    __table_args__ = (
        sa.UniqueConstraint("external_id", "boot_id", "seq", "digest", name="quarantine_candidate"),
        sa.CheckConstraint("external_id ~ '^BB-[0-9A-F]{12}$' AND length(digest) = 64", name="quarantine_identity"),
        sa.CheckConstraint("seq BETWEEN 0 AND 4294967295", name="quarantine_sequence"),
        sa.CheckConstraint("kind IN ('telemetry','command_result') AND jsonb_typeof(payload) = 'object'", name="quarantine_event"),
        sa.Index("quarantine_device", "external_id"),
        sa.Index("quarantine_order", "received_at", "id"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    external_id: str = Field(max_length=15)
    boot_id: UUID
    seq: int = Field(sa_column=sa.Column(sa.BigInteger, nullable=False))
    kind: str = Field(max_length=24)
    digest: str = Field(max_length=64)
    reason: str = Field(max_length=64)
    received_at: datetime = Field(default_factory=now, sa_column=timestamp())
    payload: dict[str, Any] = Field(sa_column=sa.Column(JSONB, nullable=False))

# Register feature-owned tables after the shared foundation is defined.
from .commands import RelayIntent, CommandAttempt, CommandReceipt  # noqa: E402,F401
