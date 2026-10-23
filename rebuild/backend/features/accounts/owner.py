"""Trusted local owner CLI. No public provisioning endpoint or privileged cloud key."""
import argparse
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from cryptography.fernet import Fernet
from sqlmodel import Session, select

from backend.core.config import AUTH_ENV, AuthSettings
from backend.database.config import make_engine
from backend.database.models import AuthSession, Hatchery, Membership, UserIdentity, now
from . import repository


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("init-config", help="Create private auth config only if absent")
    create = commands.add_parser("create-hatchery")
    create.add_argument("--name", required=True)
    link = commands.add_parser("link", help="Link Supabase user UUID and grant hatchery access")
    link.add_argument("--subject", required=True, type=UUID)
    link.add_argument("--hatchery", required=True, type=UUID)
    link.add_argument("--identity", type=UUID, help="Explicitly map an existing unmapped identity")
    disable = commands.add_parser("disable")
    disable.add_argument("--user", required=True, type=UUID)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("--user", required=True, type=UUID)
    revoke.add_argument("--hatchery", required=True, type=UUID)
    return cli


def execute(args, engine, settings=None):
    with Session(engine) as session, session.begin():
        if args.command == "create-hatchery":
            row = Hatchery(name=args.name)
            session.add(row)
            session.flush()
            result = str(row.id)
        elif args.command == "link":
            if session.get(Hatchery, args.hatchery) is None:
                raise ValueError("Unknown hatchery")
            user = repository.identity(session, settings.issuer, args.subject)
            if args.identity:
                explicit = session.get(UserIdentity, args.identity, with_for_update=True)
                if explicit is None or (user is not None and user.id != explicit.id):
                    raise ValueError("Identity mapping conflict")
                if explicit.provider_subject is not None and (explicit.provider_issuer, explicit.provider_subject) != (settings.issuer, args.subject):
                    raise ValueError("Identity already mapped")
                user = explicit
            if user is None:
                user = UserIdentity()
            user.provider_issuer, user.provider_subject, user.active = settings.issuer, args.subject, True
            session.add(user)
            session.flush()
            membership = session.get(Membership, (args.hatchery, user.id))
            if membership is None:
                membership = Membership(hatchery_id=args.hatchery, user_id=user.id)
            membership.active = True
            session.add(membership)
            result = str(user.id)
        elif args.command == "disable":
            user = session.get(UserIdentity, args.user, with_for_update=True)
            if user is None:
                raise ValueError("Unknown identity")
            user.active = False
            session.execute(sa.update(AuthSession).where(AuthSession.user_id == user.id).values(revoked_at=now(), encrypted_tokens=None))
            result = "Account disabled; local sessions revoked"
        else:
            membership = session.get(Membership, (args.hatchery, args.user), with_for_update=True)
            if membership is None:
                raise ValueError("Unknown membership")
            membership.active = False
            result = "Hatchery membership revoked"
    return result


def main():
    args = parser().parse_args()
    if args.command == "init-config":
        template = Path(__file__).resolve().parents[2] / ".env.example"
        try:
            with AUTH_ENV.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(template.read_text(encoding="utf-8").replace("GENERATE-A-PRIVATE-FERNET-KEY", Fernet.generate_key().decode()))
            print("Created ignored backend/.env with a private token key. Fill in the Supabase URL and publishable key locally.")
        except FileExistsError:
            print("Existing backend/.env preserved; nothing overwritten")
        return
    engine = None
    try:
        settings = AuthSettings.load() if args.command == "link" else None
        engine = make_engine()
        print(execute(args, engine, settings))
    except (sa.exc.SQLAlchemyError, ValueError, RuntimeError, OSError):
        raise SystemExit("Owner operation failed; check configuration, migration and identifiers. No credentials printed.") from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
