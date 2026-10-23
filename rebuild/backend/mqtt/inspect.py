"""Trusted local read-only quarantine inspection; no release/delete interface."""
import argparse
import base64
from datetime import datetime
import json
import re
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Session, select

from backend.database.config import make_engine
from backend.database.models import IngestionQuarantine


def page(engine, *, limit=50, cursor=None, device=None, payload=False):
    if not 1 <= limit <= 200 or (device is not None and not re.fullmatch(r'BB-[0-9A-F]{12}', device)):
        raise ValueError('Invalid inspection options')
    query = select(IngestionQuarantine)
    if device:
        query = query.where(IngestionQuarantine.external_id == device)
    if cursor:
        try:
            if len(cursor) > 512: raise ValueError()
            clock, identity = json.loads(base64.urlsafe_b64decode(cursor + '=' * (-len(cursor) % 4)))
            clock = datetime.fromisoformat(clock)
            if clock.tzinfo is None: raise ValueError()
            query = query.where(sa.tuple_(IngestionQuarantine.received_at, IngestionQuarantine.id) >
                sa.tuple_(clock, UUID(identity)))
        except (ValueError, TypeError, UnicodeError):
            raise ValueError('Invalid inspection cursor') from None
    with Session(engine) as session:
        rows = session.exec(query.order_by(IngestionQuarantine.received_at, IngestionQuarantine.id).limit(limit + 1)).all()
        items = [{field: getattr(row, field) for field in ('id', 'external_id', 'boot_id', 'seq', 'kind',
            'digest', 'reason', 'received_at') + (('payload',) if payload else ())} for row in rows[:limit]]
        following = None
        if len(rows) > limit:
            last = rows[limit - 1]
            following = base64.urlsafe_b64encode(json.dumps([last.received_at.isoformat(), str(last.id)]).encode()).rstrip(b'=').decode()
        return dict(items=items, next_cursor=following)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--cursor')
    parser.add_argument('--device')
    parser.add_argument('--payload', action='store_true')
    args = parser.parse_args()
    engine = make_engine(test=args.test)
    try:
        print(json.dumps(page(engine, limit=args.limit, cursor=args.cursor, device=args.device,
            payload=args.payload), default=str, ensure_ascii=True))
        return 0
    except Exception:
        print('Quarantine inspection unavailable')
        return 1
    finally:
        engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
