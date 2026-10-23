"""Explicit live-provider smoke check. Real Supabase; temporary local test schema.

Run interactively from rebuild: python -m backend.features.accounts.smoke
Never pass a password in command arguments, logs or chat.
"""
import getpass
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import command
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.core.application import create_app
from backend.core.config import AuthSettings
from backend.database.config import database_url, make_engine
from backend.database.migrate import configuration
from backend.database.models import Hatchery, Membership, UserIdentity
from .errors import AuthError
from .provider import SupabaseProvider
from .service import AccountService


def main():
    admin = engine = provider = None
    schema = None
    initial = None
    service = token = None
    try:
        settings = AuthSettings.load()
        email = input("Dedicated test account email: ").strip()
        password = getpass.getpass("Test account password (hidden): ")
        provider = SupabaseProvider(settings)
        initial = provider.sign_in(email, password)
        subject = UUID(initial.claims["sub"])
        provider.sign_out(initial.access_token)
        initial = None
        admin = make_engine(test=True)
        temporary_schema = "t10_live_" + uuid4().hex
        with admin.begin() as connection:
            connection.execute(sa.schema.CreateSchema(temporary_schema))
        schema = temporary_schema
        engine = sa.create_engine(database_url(test=True), hide_parameters=True,
            connect_args={"options": f"-csearch_path={schema}", "connect_timeout": 5})
        with engine.begin() as connection:
            config = configuration()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        hatchery, user = uuid4(), uuid4()
        with Session(engine) as session, session.begin():
            session.add(Hatchery(id=hatchery, name="Temporary T10 live verification"))
            session.add(UserIdentity(id=user, provider_issuer=settings.issuer, provider_subject=subject, active=True))
            session.flush()
            session.add(Membership(user_id=user, hatchery_id=hatchery))
        service = AccountService(settings, engine, provider)
        origin = settings.origins[0]
        with TestClient(create_app(service=service), base_url=origin, headers={"Origin": origin}) as client:
            result = client.post("/api/v1/auth/login", json={"email": email, "password": password})
            if result.status_code != 200:
                raise AuthError(result.status_code, "live_login_failed")
            token = client.cookies.get(settings.cookie_name)
            csrf = result.json()["csrf_token"]
            print("PASS: real-provider login and protected cookie")
            if client.get("/api/v1/me").status_code != 200:
                raise AuthError(401, "live_current_user_failed")
            print("PASS: authenticated /api/v1/me")
            if client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code != 204:
                raise AuthError(503, "live_logout_failed")
            client.cookies.set(settings.cookie_name, token)
            if client.get("/api/v1/me").status_code != 401:
                raise AuthError(503, "live_revocation_failed")
            print("PASS: logout and rejection of reused session cookie")
        print("Live Supabase + in-process HTTP smoke PASS; no production account/data seeded")
    except (AuthError, sa.exc.SQLAlchemyError, ValueError, RuntimeError, OSError) as error:
        code = error.code if isinstance(error, AuthError) else "check_private_configuration_and_database"
        raise SystemExit("Live smoke failed: " + code) from None
    finally:
        if service is not None and token is not None:
            try:
                service.logout(token)
            except (AuthError, sa.exc.SQLAlchemyError):
                print("Temporary session cleanup unavailable; check provider sessions")
        if initial is not None and provider is not None:
            try:
                provider.sign_out(initial.access_token)
            except AuthError:
                pass
        if engine is not None:
            engine.dispose()
        if admin is not None:
            try:
                if schema is not None:
                    with admin.begin() as connection:
                        connection.execute(sa.schema.DropSchema(schema, cascade=True))
                    print("Temporary live-test schema removed")
            finally:
                admin.dispose()
        if provider is not None:
            provider.close()


if __name__ == "__main__":
    main()
