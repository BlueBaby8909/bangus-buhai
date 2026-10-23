"""Queries only; registry service owns transactions and lock order."""
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import select

from backend.database.models import Binding, DeviceClaim, DeviceConfiguration, DeviceInventory
from .errors import RegistryError
from .security import canonical, decode, encode


def inventory(session, external_id, *, lock=False):
    return session.get(DeviceInventory, external_id, with_for_update=lock)


def pending_claim(session, external_id):
    return session.exec(select(DeviceClaim).where(DeviceClaim.external_id == external_id,
        DeviceClaim.state == "pending_proof")).one_or_none()


def active_binding(session, device_id):
    return session.exec(select(Binding).where(Binding.device_id == device_id, Binding.ended_at.is_(None))).one_or_none()


def configuration(session, device_id):
    return session.get(DeviceConfiguration, device_id)


def page(session, statement, model, clock_column, limit, cursor):
    if cursor:
        try:
            import json
            if len(cursor) > 512:
                raise ValueError()
            timestamp, identity = json.loads(decode(cursor))
            timestamp = datetime.fromisoformat(timestamp)
            if timestamp.tzinfo is None:
                raise ValueError()
            identity = UUID(identity)
        except (ValueError, TypeError, UnicodeError, OverflowError):
            raise RegistryError(422, "invalid_cursor") from None
        statement = statement.where(sa.tuple_(clock_column, model.id) > sa.tuple_(timestamp, identity))
    rows = session.exec(statement.order_by(clock_column, model.id).limit(limit + 1)).all()
    following = None
    if len(rows) > limit:
        last = rows[limit - 1]
        following = encode(canonical([getattr(last, clock_column.key).isoformat(), str(last.id)]))
    return rows[:limit], following
