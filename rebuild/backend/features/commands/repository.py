from uuid import UUID
from sqlmodel import select
from backend.database.commands import RelayIntent, CommandAttempt

ACTIVE = ('queued', 'published', 'accepted')


def pending(session, device_id):
    return session.exec(select(RelayIntent).where(RelayIntent.device_id == device_id,
        RelayIntent.status.in_(ACTIVE))).one_or_none()


def previous(session, actor, request):
    return session.exec(select(RelayIntent).where(RelayIntent.actor_id == actor,
        RelayIntent.request_id == request)).one_or_none()


def attempt(session, command_id):
    return session.exec(select(CommandAttempt).where(CommandAttempt.command_id == command_id)
        .order_by(CommandAttempt.submitted_at.desc()).limit(1)).first()
