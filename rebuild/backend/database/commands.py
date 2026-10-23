"""Command intent, dispatch evidence and correlated device receipts."""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class RelayIntent(SQLModel, table=True):
    __tablename__ = 'relay_commands'
    __table_args__ = (
        sa.ForeignKeyConstraint(['binding_id', 'device_id', 'tank_id', 'hatchery_id'],
            ['bindings.id', 'bindings.device_id', 'bindings.tank_id', 'bindings.hatchery_id'], name='command_binding'),
        sa.UniqueConstraint('actor_id', 'request_id', name='command_idempotency'),
        sa.CheckConstraint("status IN ('queued','published','accepted','applied','rejected','failed','timed_out')", name='command_status'),
        sa.CheckConstraint("expires_at > issued_at AND jsonb_typeof(wire) = 'object'", name='command_wire'),
        sa.Index('commands_pending', 'device_id', unique=True,
            postgresql_where=sa.text("status IN ('queued','published','accepted')")),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    actor_id: UUID = Field(foreign_key='user_identities.id')
    request_id: UUID
    hatchery_id: UUID
    tank_id: UUID
    device_id: UUID
    binding_id: UUID
    wire: dict[str, Any] = Field(sa_column=sa.Column(JSONB, nullable=False))
    issued_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    expires_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    status: str = Field(default='queued', max_length=16)
    timed_out_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))
    terminal_event_id: UUID | None = Field(default=None, foreign_key='device_events.id')


class CommandAttempt(SQLModel, table=True):
    __tablename__ = 'command_attempts'
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    command_id: UUID = Field(foreign_key='relay_commands.id', index=True)
    submitted_at: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    published_at: datetime | None = Field(default=None, sa_column=sa.Column(sa.DateTime(timezone=True)))


class CommandReceipt(SQLModel, table=True):
    __tablename__ = 'command_receipts'
    command_id: UUID = Field(foreign_key='relay_commands.id', primary_key=True)
    event_id: UUID = Field(foreign_key='device_events.id', primary_key=True, unique=True)
