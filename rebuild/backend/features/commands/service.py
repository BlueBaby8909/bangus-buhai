"""Durable intent and correlated results; no broker connection at API startup."""
from datetime import timedelta
from uuid import UUID, uuid4
import sqlalchemy as sa
from sqlmodel import Session, select
from contracts import RelayCommand, CommandResult, ContractError, validate_command_result
from contracts.models import utc_datetime
from backend.database.commands import RelayIntent, CommandAttempt, CommandReceipt
from backend.database.models import (Device, DeviceInventory, Hatchery, Binding, DeviceEvent)
from backend.features.accounts.service import utc_now
from backend.features.registry.service import RegistryService
from backend.features.registry.errors import RegistryError
from . import repository as queries


class CommandService:
    def __init__(self, engine, token_key=bytes(32), clock=utc_now):
        self.engine, self.clock = engine, clock
        self.registry = RegistryService(engine, token_key, clock)

    @staticmethod
    def eligible(session, device, clock):
        from backend.mqtt.service import IngestionService
        inventory = session.get(DeviceInventory, device.external_id, with_for_update=True)
        if IngestionService.credential(inventory, device, clock):
            return None
        binding = session.exec(select(Binding).where(Binding.device_id == device.id,
            Binding.ended_at.is_(None))).one_or_none()
        if not binding:
            return None
        reason = IngestionService.current_binding(session, device, inventory, binding)
        return binding if reason is None else None

    def expire(self, row):
        if row.status in queries.ACTIVE and self.clock() >= row.expires_at:
            row.status, row.timed_out_at = 'timed_out', self.clock()

    @staticmethod
    def view(session, row):
        attempts = session.exec(select(CommandAttempt).where(CommandAttempt.command_id == row.id)
            .order_by(CommandAttempt.submitted_at, CommandAttempt.id)).all()
        events = session.exec(select(DeviceEvent).join(CommandReceipt, CommandReceipt.event_id == DeviceEvent.id)
            .where(CommandReceipt.command_id == row.id).order_by(DeviceEvent.received_at, DeviceEvent.seq)).all()
        return dict(command_id=row.id, device_id=row.wire['device_id'], binding_id=row.binding_id,
            actor_id=row.actor_id, command=row.wire, status=row.status, timed_out_at=row.timed_out_at,
            attempts=[dict(attempt_id=a.id, submitted_at=a.submitted_at, published_at=a.published_at) for a in attempts],
            results=[dict(event_id=e.id, received_at=e.received_at, **e.payload) for e in events],
            state_evidence='device_gpio_command_only')

    def create(self, hatchery, external, actor, key, body):
        with self.registry.operation(hatchery, actor, mutation=True) as session:
            old = queries.previous(session, actor, key)
            if old:
                if (old.hatchery_id != hatchery or old.wire['device_id'] != external or
                    old.wire['type'] != body.type or old.wire.get('desired_on') != body.desired_on):
                    raise RegistryError(409, 'idempotency_conflict')
                self.expire(old)
                return self.view(session, old)
            session.get(DeviceInventory, external, with_for_update=True)
            device = self.registry.device(session, hatchery, external)
            binding = self.eligible(session, device, self.clock())
            if binding is None:
                raise RegistryError(409, 'device_not_ready')
            pending = queries.pending(session, device.id)
            if pending:
                self.expire(pending)
                if pending.status in queries.ACTIVE:
                    raise RegistryError(409, 'command_pending')
                session.flush()
            command_id, now = uuid4(), self.clock()
            wire = RelayCommand(schema_version=1, device_id=external, binding_id=str(binding.id),
                command_id=str(command_id), type=body.type, desired_on=body.desired_on,
                issued_at=now.isoformat().replace('+00:00', 'Z'),
                expires_at=(now + timedelta(seconds=60)).isoformat().replace('+00:00', 'Z'))
            row = RelayIntent(id=command_id, actor_id=actor, request_id=key, hatchery_id=hatchery,
                tank_id=binding.tank_id, device_id=device.id, binding_id=binding.id,
                issued_at=now, expires_at=now + timedelta(seconds=60), wire=wire.model_dump(exclude_none=True))
            session.add(row); session.flush()
            return self.view(session, row)

    def latest(self, hatchery, external, actor):
        with self.registry.operation(hatchery, actor, mutation=True) as session:
            device = self.registry.device(session, hatchery, external)
            binding = session.exec(select(Binding).where(Binding.device_id == device.id,
                Binding.ended_at.is_(None))).one_or_none()
            if binding is None:
                return None
            row = session.exec(select(RelayIntent).where(RelayIntent.device_id == device.id,
                RelayIntent.binding_id == binding.id).order_by(RelayIntent.issued_at.desc(), RelayIntent.id.desc())
                .limit(1)).first()
            if row is None:
                return None
            self.expire(row)
            return self.view(session, row)

    def detail(self, hatchery, external, actor, command_id):
        with self.registry.operation(hatchery, actor, mutation=True) as session:
            row = session.get(RelayIntent, command_id, with_for_update=True)
            if row is None or row.hatchery_id != hatchery or row.wire['device_id'] != external:
                raise RegistryError(404, 'command_unavailable')
            self.expire(row)
            return self.view(session, row)

    def dispatch(self, publish):
        """Network owner only. Registry locks fence reassignment through publish.

        Intent is already committed. An attempt is committed BEFORE transmission;
        PUBACK evidence is recorded separately. Database work has short deadlines.
        """
        with Session(self.engine) as session:
            ids = session.exec(select(RelayIntent.id).where(RelayIntent.status.in_(queries.ACTIVE))
                .order_by(RelayIntent.issued_at).limit(16)).all()
        submitted = []
        for command_id in ids:
            with Session(self.engine) as session, session.begin():
                session.execute(sa.text("SET LOCAL statement_timeout = '2s'"))
                session.execute(sa.text("SET LOCAL lock_timeout = '1s'"))
                initial = session.get(RelayIntent, command_id)
                session.get(Hatchery, initial.hatchery_id, with_for_update=True)
                try:
                    self.registry.scope(session, initial.hatchery_id, initial.actor_id, lock=True)
                except RegistryError:
                    row = session.get(RelayIntent, command_id, with_for_update=True)
                    if row.status in queries.ACTIVE:
                        row.status, row.timed_out_at = 'timed_out', self.clock()
                    continue
                session.get(DeviceInventory, initial.wire['device_id'], with_for_update=True)
                device = session.get(Device, initial.device_id, with_for_update=True)
                row = session.get(RelayIntent, command_id, with_for_update=True, populate_existing=True)
                self.expire(row)
                if row.status not in queries.ACTIVE:
                    continue
                binding = self.eligible(session, device, self.clock())
                if binding is None or binding.id != row.binding_id:
                    # No result can be inferred from loss of assignment.
                    row.status, row.timed_out_at = 'timed_out', self.clock()
                    continue
                last = queries.attempt(session, row.id)
                if last and self.clock() < last.submitted_at + timedelta(seconds=5):
                    continue
                attempt = CommandAttempt(command_id=row.id, submitted_at=self.clock())
                session.add(attempt); session.flush()
                attempt_id, wire = attempt.id, dict(row.wire)
                hatchery_id, device_id, actor_id = row.hatchery_id, row.device_id, row.actor_id
            # Reacquire registry locks after committing the attempt. No stale
            # prepared payload survives a reassignment or expiry in that gap.
            with Session(self.engine) as session, session.begin():
                session.execute(sa.text("SET LOCAL statement_timeout = '2s'"))
                session.execute(sa.text("SET LOCAL lock_timeout = '1s'"))
                session.get(Hatchery, hatchery_id, with_for_update=True)
                try:
                    self.registry.scope(session, hatchery_id, actor_id, lock=True)
                except RegistryError:
                    continue
                session.get(DeviceInventory, wire['device_id'], with_for_update=True)
                device = session.get(Device, device_id, with_for_update=True)
                row = session.get(RelayIntent, command_id, with_for_update=True)
                binding = self.eligible(session, device, self.clock())
                if row.status not in queries.ACTIVE or self.clock() >= row.expires_at or binding is None or binding.id != row.binding_id:
                    self.expire(row)
                    continue
                mid = publish(wire)
                if mid is not None:
                    submitted.append((mid, attempt_id))
        return submitted

    def published(self, attempt_id):
        with Session(self.engine) as session, session.begin():
            attempt = session.get(CommandAttempt, attempt_id, with_for_update=True)
            if attempt is None or attempt.published_at is not None:
                return
            row = session.get(RelayIntent, attempt.command_id, with_for_update=True)
            attempt.published_at = self.clock()
            self.expire(row)
            if row.status == 'queued':
                row.status = 'published'

    @staticmethod
    def result_reason(session, device, event):
        row = session.get(RelayIntent, UUID(event.command_id), with_for_update=True)
        if row is None or row.device_id != device.id or str(row.binding_id) != event.binding_id:
            return 'command_context_unavailable'
        if queries.attempt(session, row.id) is None:
            return 'command_not_dispatched'
        try:
            validate_command_result(event, RelayCommand.model_validate(row.wire))
        except ContractError:
            return 'command_result_mismatch'
        if event.result in ('accepted', 'applied'):
            if event.created_at is None or not row.issued_at <= utc_datetime(event.created_at) < row.expires_at:
                return 'command_result_time'
        if row.terminal_event_id is not None and event.result != 'accepted':
            old = session.get(DeviceEvent, row.terminal_event_id)
            if (old.payload['result'], old.payload['observed_on'], old.payload['reason']) != (event.result, event.observed_on, event.reason):
                return 'command_terminal_conflict'
        return None

    @staticmethod
    def record_result(session, device, event):
        row = session.get(RelayIntent, UUID(event.command_id), with_for_update=True)
        stored = session.exec(select(DeviceEvent).where(DeviceEvent.device_id == device.id,
            DeviceEvent.boot_id == UUID(event.boot_id), DeviceEvent.seq == event.seq)).one()
        session.add(CommandReceipt(command_id=row.id, event_id=stored.id))
        if event.result != 'accepted':
            if row.terminal_event_id is None:
                row.terminal_event_id, row.status = stored.id, event.result
        elif row.status in ('queued', 'published'):
            row.status = 'accepted'
