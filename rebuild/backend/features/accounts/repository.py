"""Account queries. Callers own sessions and transactions."""
from datetime import timedelta

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select

from backend.database.models import AuthLoginBucket, AuthSession, Hatchery, Membership, UserIdentity


def memberships(session, user_id):
    return session.exec(select(Hatchery).join(Membership, Membership.hatchery_id == Hatchery.id).where(
        Membership.user_id == user_id, Membership.active.is_(True))).all()


def identity(session, issuer, subject):
    return session.exec(select(UserIdentity).where(UserIdentity.provider_issuer == issuer,
        UserIdentity.provider_subject == subject).with_for_update()).one_or_none()


def browser_session(session, digest):
    return session.exec(select(AuthSession).where(AuthSession.token_hash == digest).with_for_update()).one_or_none()


def login_attempt(session, digest, clock):
    window = clock.replace(second=0, microsecond=0)
    same_window = AuthLoginBucket.window_start == window
    count = session.execute(insert(AuthLoginBucket).values(key_hash=digest, window_start=window, attempts=1)
        .on_conflict_do_update(index_elements=["key_hash"], set_={
            "attempts": sa.case((same_window, sa.func.least(AuthLoginBucket.attempts + 1, 11)), else_=1),
            "window_start": window,
        }).returning(AuthLoginBucket.attempts)).scalar_one()
    session.execute(sa.delete(AuthLoginBucket).where(AuthLoginBucket.window_start < clock - timedelta(days=1)))
    return count
