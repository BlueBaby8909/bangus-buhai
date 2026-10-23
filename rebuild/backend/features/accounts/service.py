"""Managed login plus durable, revocable local browser sessions."""
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlmodel import Session

from backend.core.security import csrf_token, new_session_token, token_hash, valid_token
from backend.database.models import AuthSession, UserIdentity
from . import repository
from .errors import AuthError

LOGGER = logging.getLogger(__name__)


def utc_now():
    return datetime.now(timezone.utc)


@dataclass
class Operator:
    id: UUID
    email: str | None
    hatcheries: list[dict]
    csrf: str

    def require_hatchery(self, hatchery_id: UUID):
        if str(hatchery_id) not in {row["id"] for row in self.hatcheries}:
            raise AuthError(403, "access_denied")
        return self


class AccountService:
    def __init__(self, settings, engine, provider, clock=utc_now):
        self.settings, self.engine, self.provider, self.clock = settings, engine, provider, clock
        self.cipher = Fernet(settings.token_key)

    def _pack(self, bundle):
        return self.cipher.encrypt(json.dumps({"access": bundle.access_token, "refresh": bundle.refresh_token}).encode()).decode()

    def _unpack(self, encrypted):
        try:
            data = json.loads(self.cipher.decrypt(encrypted.encode()))
            if any(not isinstance(data.get(k), str) or not 1 <= len(data[k]) <= 16384 for k in ("access", "refresh")):
                raise ValueError()
            return data
        except (InvalidToken, ValueError, TypeError, AttributeError):
            raise AuthError(401, "invalid_session") from None

    def _operator(self, session, user, token):
        if user is None:
            raise AuthError(403, "access_denied")
        hatcheries = repository.memberships(session, user.id)
        if not user.active or not hatcheries:
            raise AuthError(403, "access_denied")
        return Operator(user.id, user.email, [{"id": str(h.id), "name": h.name} for h in hatcheries], csrf_token(token))

    def _sign_out(self, access):
        try:
            self.provider.sign_out(access)
        except AuthError:
            LOGGER.warning("provider_sign_out_unavailable")

    def login(self, email, password, client_ip):
        clock = self.clock()
        digest = hmac.new(self.settings.token_key, b"login-ip:" + client_ip.encode(), hashlib.sha256).hexdigest()
        with Session(self.engine) as session, session.begin():
            count = repository.login_attempt(session, digest, clock)
        if count > 10:
            raise AuthError(429, "authentication_throttled", 60 - clock.second)
        bundle = self.provider.sign_in(email, password)
        token = new_session_token()
        try:
            with Session(self.engine) as session, session.begin():
                user = repository.identity(session, self.settings.issuer, UUID(bundle.claims["sub"]))
                if user is None:
                    raise AuthError(403, "access_denied")
                email = bundle.claims.get("email")
                if isinstance(email, str) and len(email) <= 320:
                    user.email = email  # Display only; issuer/subject remains the identity key.
                context = self._operator(session, user, token)
                clock = self.clock()
                session.add(AuthSession(token_hash=token_hash(token), user_id=user.id,
                    provider_session_id=UUID(bundle.claims["session_id"]), encrypted_tokens=self._pack(bundle),
                    created_at=clock, last_seen_at=clock, expires_at=clock + timedelta(hours=8)))
            return token, context
        except Exception:
            self._sign_out(bundle.access_token)
            raise

    def authenticate(self, token, *, touch=True):
        """Validate/refresh a session; passive streams must not extend inactivity."""
        if not valid_token(token):
            raise AuthError(401, "invalid_session")
        error, operator = None, None
        with Session(self.engine) as session, session.begin():
            row = repository.browser_session(session, token_hash(token))
            clock = self.clock()
            if row is None or row.revoked_at is not None:
                error = AuthError(401, "invalid_session")
            else:
                try:
                    if clock >= row.expires_at or clock >= row.last_seen_at + timedelta(minutes=30):
                        raise AuthError(401, "session_expired")
                    user = session.get(UserIdentity, row.user_id)
                    operator = self._operator(session, user, token)
                    tokens = self._unpack(row.encrypted_tokens)
                    try:
                        claims = self.provider.verify(tokens["access"], subject=user.provider_subject,
                                                      session_id=row.provider_session_id)
                        refresh = claims["exp"] <= self.clock().timestamp() + 30
                    except AuthError as failure:
                        if failure.code != "access_expired":
                            raise
                        refresh = True
                    if refresh:
                        bundle = self.provider.refresh(tokens["refresh"], user.provider_subject, row.provider_session_id)
                        row.encrypted_tokens = self._pack(bundle)
                    # Recheck wall clock after bounded network work; never extend the absolute deadline.
                    clock = self.clock()
                    if clock >= row.expires_at or clock >= row.last_seen_at + timedelta(minutes=30):
                        raise AuthError(401, "session_expired")
                    if touch:
                        row.last_seen_at = clock
                except AuthError as failure:
                    error = failure
                    if failure.status in (401, 403):
                        row.revoked_at, row.encrypted_tokens = clock, None
        if error:
            raise error
        return operator

    def logout(self, token):
        if not valid_token(token):
            return
        access = None
        with Session(self.engine) as session, session.begin():
            row = repository.browser_session(session, token_hash(token))
            if row is not None and row.revoked_at is None:
                try:
                    access = self._unpack(row.encrypted_tokens)["access"]
                except AuthError:
                    pass
                row.revoked_at, row.encrypted_tokens = self.clock(), None
        # Revocation is committed before the external side effect.
        if access:
            self._sign_out(access)
