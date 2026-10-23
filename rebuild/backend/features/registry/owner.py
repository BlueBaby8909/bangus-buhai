"""Trusted one-time device preparation. Reads public certificates, never private keys."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
from uuid import UUID

import sqlalchemy as sa
from cryptography.hazmat.primitives import hashes, serialization
from sqlmodel import Session, select

from backend.database.config import make_engine
from backend.database.models import Device, DeviceInventory, RegistryAudit
from backend.features.accounts.service import utc_now
from .errors import RegistryError
from .security import certificate, code_hash


def prepare(engine, external_id, pem, output, *, existing_device=None, clock=utc_now):
    cert = certificate(pem, external_id, clock())
    output = Path(output).resolve()
    checkout = Path(__file__).resolve().parents[4]
    if output.is_relative_to(checkout) or output.exists() or not output.parent.is_dir():
        raise ValueError("Choose a new private output file outside the repository")
    token = secrets.token_urlsafe(32) if existing_device is None else None
    created = False
    try:
        with Session(engine) as session, session.begin():
            known = session.exec(select(Device).where(Device.external_id == external_id)).one_or_none()
            if known is not None and known.id != existing_device:
                raise ValueError("Explicit existing-device attachment required")
            if existing_device:
                row = session.get(Device, existing_device)
                if row is None or row.external_id != external_id:
                    raise ValueError("Existing device mismatch")
                # Match normal registry lock order for an explicit legacy attachment.
                from backend.database.models import Hatchery
                session.get(Hatchery, row.hatchery_id, with_for_update=True)
            session.add(DeviceInventory(external_id=external_id,
                certificate=cert.public_bytes(serialization.Encoding.PEM).decode("ascii"),
                fingerprint=cert.fingerprint(hashes.SHA256()).hex(), claim_hash=code_hash(token) if token else None,
                key_fingerprint=hashlib.sha256(cert.public_key().public_bytes(serialization.Encoding.DER,
                    serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest(),
                device_id=existing_device, prepared_at=clock()))
            session.flush()
            session.add(RegistryAudit(actor_type="owner", action="device.prepared", external_id=external_id,
                resource_id=existing_device, occurred_at=clock(), details={"legacy_attachment": bool(existing_device)}))
            # Exclusive creation; remove only our own output if database commit fails.
            descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created = True
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(dict(schema_version=1, device_id=external_id, claim_code=token), stream)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--device-id", required=True)
    cli.add_argument("--certificate", required=True, type=Path)
    cli.add_argument("--output", required=True, type=Path)
    cli.add_argument("--existing-device", type=UUID, help="Explicitly attach an existing owned identity without issuing a claim code")
    args = cli.parse_args()
    engine = None
    try:
        if args.certificate.stat().st_size > 16384:
            raise ValueError()
        pem = args.certificate.read_text(encoding="ascii")
        engine = make_engine()
        prepare(engine, args.device_id, pem, args.output, existing_device=args.existing_device)
        print("Device prepared. Private QR payload written to the selected file; no claim code printed.")
    except (RegistryError, ValueError, OSError, RuntimeError, sa.exc.SQLAlchemyError):
        raise SystemExit("Preparation failed; inspect certificate, identifiers, private output location and database. Existing material preserved.") from None
    finally:
        if engine:
            engine.dispose()


if __name__ == "__main__":
    main()
