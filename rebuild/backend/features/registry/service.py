"""Registry transactions, self-service ownership and acknowledged device configuration."""
import hmac
import hashlib
import secrets
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID, uuid4

from sqlmodel import Session, select

from backend.database.models import (Binding, Device, DeviceChallenge, DeviceClaim,
    DeviceConfiguration, DeviceConfigurationReceipt, Hatchery, Membership, RegistryAudit, Tank, UserIdentity)
from backend.features.accounts.repository import login_attempt
from backend.features.accounts.service import utc_now
from . import repository as queries
from .errors import RegistryError
from .security import code_hash, digest, encode, signing_input, verify


class RegistryService:
    def __init__(self, engine, token_key, clock=utc_now):
        self.engine, self.token_key, self.clock = engine, token_key, clock

    def throttle(self, namespace, identifiers):
        clock = self.clock()
        with Session(self.engine) as session, session.begin():
            counts = [login_attempt(session, hmac.new(self.token_key,
                f"registry:{namespace}:{kind}:{value}".encode(), hashlib.sha256).hexdigest(), clock)
                for kind, value in identifiers]
        if any(count > 10 for count in counts):
            raise RegistryError(429, "registry_throttled", 60 - clock.second)

    def scope(self, session, hatchery_id, user_id, *, lock=False):
        hatchery = session.get(Hatchery, hatchery_id, with_for_update=lock)
        user = session.get(UserIdentity, user_id, with_for_update=lock)
        member = session.get(Membership, (hatchery_id, user_id), with_for_update=lock)
        if hatchery is None or user is None or not user.active or member is None or not member.active:
            raise RegistryError(403, "access_denied")

    @contextmanager
    def operation(self, hatchery_id, user_id, *, mutation=False):
        with Session(self.engine) as session, session.begin():
            self.scope(session, hatchery_id, user_id, lock=mutation)
            yield session

    def audit(self, session, action, *, user_id=None, hatchery_id=None, external_id=None,
              resource_id=None, actor_type="operator", details=None):
        session.add(RegistryAudit(action=action, actor_type=actor_type, user_id=user_id,
            hatchery_id=hatchery_id, external_id=external_id, resource_id=resource_id,
            occurred_at=self.clock(), details=details or {}))

    @staticmethod
    def version(row, expected):
        if row.version != expected:
            raise RegistryError(409, "stale_version")

    @staticmethod
    def tank(session, hatchery_id, tank_id):
        row = session.get(Tank, tank_id)
        if row is None or row.hatchery_id != hatchery_id:
            raise RegistryError(404, "resource_unavailable")
        return row

    @staticmethod
    def device(session, hatchery_id, external_id):
        row = session.exec(select(Device).where(Device.external_id == external_id,
            Device.hatchery_id == hatchery_id).with_for_update()).one_or_none()
        if row is None:
            raise RegistryError(404, "resource_unavailable")
        return row

    @staticmethod
    def tank_view(row):
        return {key: getattr(row, key) for key in ("id", "hatchery_id", "name", "version", "created_at", "archived_at")}

    @staticmethod
    def binding_view(row):
        if row is None:
            return None
        return {key: getattr(row, key) for key in ("id", "device_id", "tank_id", "hatchery_id", "started_at", "ended_at")}

    @staticmethod
    def config_view(row):
        if row is None:
            return None
        return dict(document=row.document, digest=row.digest, confirmed_revision=row.confirmed_revision,
            confirmed_at=row.confirmed_at, status="confirmed" if row.confirmed_revision == row.revision else "pending")

    def device_view(self, session, row):
        inventory = queries.inventory(session, row.external_id)
        return dict(id=row.id, device_id=row.external_id, hatchery_id=row.hatchery_id,
            display_name=row.display_name, version=row.version, created_at=row.created_at,
            archived_at=row.archived_at, verified=bool(inventory and inventory.device_id == row.id and inventory.verified_at),
            binding=self.binding_view(queries.active_binding(session, row.id)),
            configuration=self.config_view(queries.configuration(session, row.id)))

    @staticmethod
    def claim_view(row):
        return dict(id=row.id, device_id=row.external_id, hatchery_id=row.hatchery_id,
            tank_id=row.tank_id, state=row.state, expires_at=row.expires_at)

    def expire(self, session, claim):
        if claim and claim.state == "pending_proof" and self.clock() >= claim.expires_at:
            claim.state = "expired"
            self.audit(session, "claim.expired", hatchery_id=claim.hatchery_id,
                external_id=claim.external_id, resource_id=claim.id, actor_type="device")
            session.flush()

    def tanks(self, hatchery_id, user_id, limit, cursor, include_archived):
        with self.operation(hatchery_id, user_id) as session:
            query = select(Tank).where(Tank.hatchery_id == hatchery_id)
            if not include_archived:
                query = query.where(Tank.archived_at.is_(None))
            rows, cursor = queries.page(session, query, Tank, Tank.created_at, limit, cursor)
            return dict(items=[self.tank_view(row) for row in rows], next_cursor=cursor)

    def get_tank(self, hatchery_id, user_id, tank_id):
        with self.operation(hatchery_id, user_id) as session:
            return self.tank_view(self.tank(session, hatchery_id, tank_id))

    def create_tank(self, hatchery_id, user_id, name):
        with self.operation(hatchery_id, user_id, mutation=True) as session:
            row = Tank(hatchery_id=hatchery_id, name=name, created_at=self.clock())
            session.add(row)
            session.flush()
            self.audit(session, "tank.created", user_id=user_id, hatchery_id=hatchery_id, resource_id=row.id)
            return self.tank_view(row)

    def change_tank(self, hatchery_id, user_id, tank_id, expected, *, name=None, archive=None):
        with self.operation(hatchery_id, user_id, mutation=True) as session:
            row = self.tank(session, hatchery_id, tank_id)
            self.version(row, expected)
            if archive is not None:
                if archive == (row.archived_at is not None):
                    return self.tank_view(row)
                if archive and session.exec(select(Binding.id).where(Binding.tank_id == row.id,
                        Binding.ended_at.is_(None)).limit(1)).first():
                    raise RegistryError(409, "active_bindings")
                row.archived_at = self.clock() if archive else None
                action = "tank.archived" if archive else "tank.restored"
            else:
                if row.archived_at:
                    raise RegistryError(409, "resource_archived")
                row.name, action = name, "tank.renamed"
            row.version += 1
            self.audit(session, action, user_id=user_id, hatchery_id=hatchery_id, resource_id=row.id)
            return self.tank_view(row)

    def devices(self, hatchery_id, user_id, limit, cursor, include_archived):
        with self.operation(hatchery_id, user_id) as session:
            query = select(Device).where(Device.hatchery_id == hatchery_id)
            if not include_archived:
                query = query.where(Device.archived_at.is_(None))
            rows, cursor = queries.page(session, query, Device, Device.created_at, limit, cursor)
            return dict(items=[self.device_view(session, row) for row in rows], next_cursor=cursor)

    def get_device(self, hatchery_id, user_id, external_id):
        with self.operation(hatchery_id, user_id) as session:
            return self.device_view(session, self.device(session, hatchery_id, external_id))

    def desired(self, session, device):
        binding = queries.active_binding(session, device.id)
        row = queries.configuration(session, device.id)
        revision = row.revision + 1 if row else 1
        document = dict(schema_version=1, device_id=device.external_id, hatchery_id=str(device.hatchery_id),
            tank_id=str(binding.tank_id) if binding else None, binding_id=str(binding.id) if binding else None,
            archived=device.archived_at is not None, revision=revision)
        if row is None:
            row = DeviceConfiguration(device_id=device.id, revision=revision, document=document, digest=digest(document))
            session.add(row)
        else:
            row.revision, row.document, row.digest = revision, document, digest(document)
        session.flush()
        return row

    def change_device(self, hatchery_id, user_id, external_id, expected, *, display_name=None, archive=None):
        with self.operation(hatchery_id, user_id, mutation=True) as session:
            row = self.device(session, hatchery_id, external_id)
            self.version(row, expected)
            if archive is not None:
                if archive == (row.archived_at is not None):
                    return self.device_view(session, row)
                if archive and queries.active_binding(session, row.id):
                    raise RegistryError(409, "active_bindings")
                row.archived_at = self.clock() if archive else None
                self.desired(session, row)
                action = "device.archived" if archive else "device.restored"
            else:
                if row.archived_at:
                    raise RegistryError(409, "resource_archived")
                row.display_name, action = display_name, "device.renamed"
            row.version += 1
            self.audit(session, action, user_id=user_id, hatchery_id=hatchery_id, resource_id=row.id)
            return self.device_view(session, row)

    def bind(self, session, device, tank_id):
        previous = queries.active_binding(session, device.id)
        if previous and previous.tank_id == tank_id:
            return False
        if previous is None and tank_id is None:
            return False
        clock = self.clock()
        if previous:
            clock = max(clock, previous.started_at + timedelta(microseconds=1))
            previous.ended_at = clock
            session.flush()  # Close before inserting under the partial unique index.
        if tank_id is not None:
            session.add(Binding(device_id=device.id, tank_id=tank_id, hatchery_id=device.hatchery_id, started_at=clock))
            session.flush()
        self.desired(session, device)
        return True

    def assign(self, hatchery_id, user_id, external_id, tank_id, expected):
        with self.operation(hatchery_id, user_id, mutation=True) as session:
            device = self.device(session, hatchery_id, external_id)
            self.version(device, expected)
            inventory = queries.inventory(session, external_id)
            if device.archived_at:
                raise RegistryError(409, "resource_archived")
            # Legacy/unverified devices may be explicitly unassigned for retirement.
            if tank_id is not None:
                if not inventory or inventory.device_id != device.id or not inventory.verified_at:
                    raise RegistryError(409, "device_unverified")
                if self.tank(session, hatchery_id, tank_id).archived_at:
                    raise RegistryError(409, "resource_archived")
            if self.bind(session, device, tank_id):
                device.version += 1
                self.audit(session, "device.assignment", user_id=user_id, hatchery_id=hatchery_id,
                    resource_id=device.id, details={"tank_id": str(tank_id) if tank_id else None})
            return self.device_view(session, device)

    def bindings(self, hatchery_id, user_id, external_id, limit, cursor):
        with self.operation(hatchery_id, user_id) as session:
            device = self.device(session, hatchery_id, external_id)
            rows, cursor = queries.page(session, select(Binding).where(Binding.device_id == device.id),
                Binding, Binding.started_at, limit, cursor)
            return dict(items=[self.binding_view(row) for row in rows], next_cursor=cursor)

    def start_claim(self, hatchery_id, user_id, external_id, tank_id, code, ip):
        self.throttle("claim", [("user", user_id), ("ip", ip)])
        with self.operation(hatchery_id, user_id, mutation=True) as session:
            inventory = queries.inventory(session, external_id, lock=True)
            if not inventory or not inventory.claim_hash or not hmac.compare_digest(inventory.claim_hash, code_hash(code)):
                raise RegistryError(404, "claim_unavailable")
            if inventory.device_id:
                raise RegistryError(409, "device_already_owned")
            if self.tank(session, hatchery_id, tank_id).archived_at:
                raise RegistryError(409, "resource_archived")
            previous = queries.pending_claim(session, external_id)
            self.expire(session, previous)
            if previous and previous.state == "pending_proof":
                if (previous.hatchery_id, previous.user_id, previous.tank_id) == (hatchery_id, user_id, tank_id):
                    return self.claim_view(previous)
                raise RegistryError(409, "claim_pending")
            row = DeviceClaim(external_id=external_id, hatchery_id=hatchery_id, user_id=user_id,
                tank_id=tank_id, created_at=self.clock(), expires_at=self.clock() + timedelta(minutes=10))
            session.add(row)
            session.flush()
            self.audit(session, "claim.started", user_id=user_id, hatchery_id=hatchery_id,
                external_id=external_id, resource_id=row.id)
            return self.claim_view(row)

    def get_claim(self, hatchery_id, user_id, claim_id, *, cancel=False):
        with self.operation(hatchery_id, user_id, mutation=True) as session:
            claim = session.get(DeviceClaim, claim_id)
            if claim is None or claim.hatchery_id != hatchery_id:
                raise RegistryError(404, "resource_unavailable")
            # Same hatchery lock serializes cancellation against a valid proof.
            self.expire(session, claim)
            if cancel:
                if claim.state != "pending_proof":
                    raise RegistryError(409, "claim_not_cancellable")
                claim.state = "cancelled"
                self.audit(session, "claim.cancelled", user_id=user_id, hatchery_id=hatchery_id,
                    external_id=claim.external_id, resource_id=claim.id)
            return self.claim_view(claim)

    def challenge(self, external_id, purpose, revision, config_digest, ip):
        self.throttle("setup", [("device", external_id), ("ip", ip)])
        with Session(self.engine) as session, session.begin():
            inventory = queries.inventory(session, external_id)
            if not inventory:
                raise RegistryError(404, "device_unavailable")
            claim = queries.pending_claim(session, external_id)
            if purpose == "confirm":
                config = queries.configuration(session, inventory.device_id) if inventory.device_id else None
                if not config or (revision, config_digest) != (config.revision, config.digest):
                    raise RegistryError(409, "stale_configuration")
            elif revision is not None or config_digest is not None:
                raise RegistryError(422, "invalid_request")
            identity = uuid4()
            expires = self.clock() + timedelta(minutes=2)
            payload = dict(challenge_id=str(identity), device_id=external_id, purpose=purpose,
                nonce=secrets.token_urlsafe(32), expires_at=expires.isoformat(),
                claim_id=str(claim.id) if claim and self.clock() < claim.expires_at else None,
                configuration_revision=revision, configuration_digest=config_digest)
            session.add(DeviceChallenge(id=identity, external_id=external_id, purpose=purpose,
                payload=payload, claim_id=UUID(payload["claim_id"]) if payload["claim_id"] else None, expires_at=expires))
            return dict(challenge_id=identity, payload=payload, signing_input=encode(signing_input(payload)))

    def proof(self, challenge_id, signature, ip):
        # Resolve only the public device identifier before charging durable limits.
        with Session(self.engine) as session:
            preliminary = session.get(DeviceChallenge, challenge_id)
            external_id = preliminary.external_id if preliminary else "unknown"
        self.throttle("setup", [("device", external_id), ("ip", ip)])
        with Session(self.engine) as session, session.begin():
            preliminary = session.get(DeviceChallenge, challenge_id)
            if preliminary is None:
                raise RegistryError(401, "invalid_device_proof")
            inventory = queries.inventory(session, preliminary.external_id)
            claim = session.get(DeviceClaim, preliminary.claim_id) if preliminary.claim_id else None
            device = session.get(Device, inventory.device_id) if inventory.device_id else None
            hatchery_id = device.hatchery_id if device else claim.hatchery_id if claim else None
            if hatchery_id:
                session.get(Hatchery, hatchery_id, with_for_update=True)
            # Refresh after obtaining locks; never use a pre-lock ownership snapshot.
            inventory = session.get(type(inventory), preliminary.external_id, with_for_update=True, populate_existing=True)
            challenge = session.get(DeviceChallenge, challenge_id, with_for_update=True, populate_existing=True)
            if challenge.used_at is not None:
                raise RegistryError(409, "challenge_used")
            if self.clock() >= challenge.expires_at:
                raise RegistryError(401, "challenge_expired")
            verify(inventory.certificate, inventory.external_id, self.clock(), challenge.payload, signature)
            device = session.get(Device, inventory.device_id, with_for_update=True) if inventory.device_id else None
            if device and device.hatchery_id != hatchery_id:
                raise RegistryError(409, "retry_device_setup")
            if challenge.purpose == "sync":
                if device is None and challenge.claim_id:
                    claim = session.get(DeviceClaim, challenge.claim_id, populate_existing=True)
                    if claim.state != "pending_proof" or self.clock() >= claim.expires_at:
                        raise RegistryError(409, "claim_unavailable")
                    self.scope(session, claim.hatchery_id, claim.user_id, lock=True)
                    if self.tank(session, claim.hatchery_id, claim.tank_id).archived_at:
                        raise RegistryError(409, "resource_archived")
                    device = Device(external_id=inventory.external_id, hatchery_id=claim.hatchery_id, created_at=self.clock())
                    session.add(device)
                    session.flush()
                    inventory.device_id, inventory.claim_hash, inventory.verified_at = device.id, None, self.clock()
                    claim.device_id, claim.state = device.id, "awaiting_confirmation"
                    self.bind(session, device, claim.tank_id)
                    self.audit(session, "claim.proved", actor_type="device", user_id=claim.user_id,
                        hatchery_id=claim.hatchery_id, external_id=inventory.external_id, resource_id=claim.id)
                if device:
                    if inventory.verified_at is None:
                        inventory.verified_at = self.clock()
                        self.audit(session, "credential.verified", actor_type="device", hatchery_id=device.hatchery_id,
                            external_id=inventory.external_id, resource_id=device.id)
                    config = queries.configuration(session, device.id) or self.desired(session, device)
                else:
                    config = None
            else:
                if inventory.verified_at is None:
                    raise RegistryError(409, "device_unverified")
                config = queries.configuration(session, device.id) if device else None
                if not config or (config.revision, config.digest) != (
                        challenge.payload["configuration_revision"], challenge.payload["configuration_digest"]):
                    raise RegistryError(409, "stale_configuration")
                if config.confirmed_revision != config.revision:
                    config.confirmed_revision, config.confirmed_at = config.revision, self.clock()
                    for pending in session.exec(select(DeviceClaim).where(DeviceClaim.device_id == device.id,
                            DeviceClaim.state == "awaiting_confirmation")).all():
                        pending.state = "complete"
                    self.audit(session, "configuration.confirmed", actor_type="device", hatchery_id=device.hatchery_id,
                        external_id=inventory.external_id, resource_id=device.id, details={"revision": config.revision})
            challenge.used_at = self.clock()
            if challenge.purpose == "confirm":
                # Retain each proved document before a later desired revision replaces it.
                receipt = session.exec(select(DeviceConfigurationReceipt).where(
                    DeviceConfigurationReceipt.device_id == device.id,
                    DeviceConfigurationReceipt.revision == config.revision)).one_or_none()
                if receipt is None:
                    session.add(DeviceConfigurationReceipt(device_id=device.id, hatchery_id=device.hatchery_id,
                        binding_id=UUID(config.document["binding_id"]) if config.document["binding_id"] else None,
                        tank_id=UUID(config.document["tank_id"]) if config.document["tank_id"] else None,
                        revision=config.revision, digest=config.digest, document=config.document,
                        credential_fingerprint=inventory.fingerprint, confirmed_at=config.confirmed_at))
            return dict(state="unclaimed" if config is None else
                "complete" if config.revision == config.confirmed_revision else "awaiting_confirmation",
                configuration=self.config_view(config))
