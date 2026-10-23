"""Explicit T13A owner preparation and interactive operator claim on isolated development DB."""
import argparse
import getpass
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from backend.core.config import AuthSettings
from backend.database.config import make_engine
from backend.database.models import DeviceInventory, Hatchery, Tank, UserIdentity
from backend.features.accounts.owner import execute
from backend.features.registry.owner import prepare
from backend.features.registry.security import certificate
from backend.features.registry.service import RegistryService
from backend.features.accounts.service import utc_now
from backend.features.accounts.errors import AuthError
from backend.features.registry.errors import RegistryError
from .lab import DEFAULT_DIRECTORY

NAME = 'T13A hardware verification'


def provision(engine, settings, subject, certificate_path, claim_file, *, test=False):
    url = engine.url
    expected = 'bangus_buhai_rebuild_test' if test else 'bangus_buhai_rebuild'
    if url.database != expected or url.host not in ('127.0.0.1', 'localhost') or (not test and url.port != 55432):
        raise ValueError('T13A preparation requires the existing isolated local development database')
    pem = Path(certificate_path).read_text(encoding='ascii')
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    external_id = x509.load_pem_x509_certificate(pem.encode()).subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    certificate(pem, external_id, utc_now())
    with Session(engine) as session:
        hatchery = session.exec(select(Hatchery).where(Hatchery.name == NAME)).one_or_none()
        identity = session.exec(select(UserIdentity).where(UserIdentity.provider_issuer == settings.issuer,
            UserIdentity.provider_subject == subject)).one_or_none()
        if identity is not None and not identity.active:
            raise ValueError('Existing account is disabled; explicit account review required')
        hatchery_id = hatchery.id if hatchery else None
    if hatchery_id is None:
        hatchery_id = UUID(execute(SimpleNamespace(command='create-hatchery', name=NAME), engine, settings))
    user_id = UUID(execute(SimpleNamespace(command='link', subject=subject, hatchery=hatchery_id, identity=None), engine, settings))
    registry = RegistryService(engine, settings.token_key)
    with Session(engine) as session:
        tank = session.exec(select(Tank).where(Tank.hatchery_id == hatchery_id, Tank.name == 'T13A test tank')).one_or_none()
        if tank and tank.archived_at:
            raise ValueError('Existing test tank archived; restore explicitly')
        tank_id = tank.id if tank else None
    if tank_id is None:
        tank_id = registry.create_tank(hatchery_id, user_id, 'T13A test tank')['id']
    with Session(engine) as session:
        inventory = session.get(DeviceInventory, external_id)
        if inventory:
            # Never replace a credential, consumed code, ownership or private file.
            if inventory.certificate.strip() != pem.strip() or not Path(claim_file).is_file():
                raise ValueError('Inventory already exists; explicit recovery required')
        else:
            prepare(engine, external_id, pem, claim_file)
    return dict(hatchery_id=str(hatchery_id), tank_id=str(tank_id), device_id=external_id)


def claim(claim_file, hatchery_id, tank_id):
    settings = AuthSettings.load()
    material = json.loads(Path(claim_file).read_text(encoding='utf-8'))
    if set(material) != {'schema_version', 'device_id', 'claim_code'} or material['schema_version'] != 1:
        raise ValueError('Invalid private claim file')
    email = input('Dedicated operator email: ').strip()
    password = getpass.getpass('Password (hidden): ')
    with httpx.Client(base_url='http://127.0.0.1:8001', timeout=15,
                      headers={'Origin': settings.origins[0]}, trust_env=False) as client:
        logged_in = False
        try:
            response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
            password = None
            if response.status_code != 200:
                raise ValueError(f'Login unavailable (HTTP {response.status_code})')
            logged_in = True
            client.headers['X-CSRF-Token'] = response.json()['csrf_token']
            response = client.post(f'/api/v1/hatcheries/{hatchery_id}/device-claims', json={
                'device_id': material['device_id'], 'claim_code': material['claim_code'], 'tank_id': str(tank_id)})
            if response.status_code != 201:
                raise ValueError(f'Claim unavailable (HTTP {response.status_code}); inspect current claim before retrying')
            row = response.json()
            print('Claim started:', row['id'], 'state:', row['state'])
            print('The ESP32 will prove its key and confirm its saved configuration automatically.')
        finally:
            if logged_in:
                try:
                    if client.post('/api/v1/auth/logout').status_code != 204:
                        print('Logout unavailable; local session expiry still applies.')
                except httpx.HTTPError: print('Logout unavailable; local session expiry still applies.')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest='action', required=True)
    owner = sub.add_parser('prepare')
    owner.add_argument('--subject', required=True, type=UUID)
    owner.add_argument('--certificate', type=Path, default=Path.home() / 'BangusBuhai-Secrets/t07/device-cert.pem')
    owner.add_argument('--claim-file', type=Path, default=DEFAULT_DIRECTORY / 'device-claim.json')
    operator = sub.add_parser('claim')
    operator.add_argument('--hatchery', required=True, type=UUID)
    operator.add_argument('--tank', required=True, type=UUID)
    operator.add_argument('--claim-file', type=Path, default=DEFAULT_DIRECTORY / 'device-claim.json')
    args = cli.parse_args()
    engine = None
    try:
        if args.action == 'prepare':
            engine = make_engine()
            result = provision(engine, AuthSettings.load(), args.subject, args.certificate, args.claim_file)
            print(json.dumps(result))
            print('Prepared explicit local test resources; no device ownership was created.')
        else:
            claim(args.claim_file, args.hatchery, args.tank)
    except (ValueError, OSError, RuntimeError, httpx.HTTPError, SQLAlchemyError, AuthError, RegistryError):
        raise SystemExit('T13A setup unavailable; check local configuration and existing resources. No secrets printed.') from None
    finally:
        if engine: engine.dispose()


if __name__ == '__main__':
    main()
